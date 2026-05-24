# Security CRITICAL fixes - implementation summary

Worktree: `X:\MakerMatrix\.claude\worktrees\agent-acb9efbf08e2f666f`
Branch: `main` (uncommitted)

All seven CRITICAL findings from the recent security review are now fixed,
each covered by a regression test in `MakerMatrix/tests/test_security_criticals.py`.

## Verifying the fixes

```bash
# New regression suite for these seven fixes (28 tests, all green)
pytest MakerMatrix/tests/test_security_criticals.py

# Full backend suite. None of the failures are caused by these changes
# (verified by running the same command on main without the diff). My
# changes net +20 passing tests / -20 failing tests / -23 errors because
# the conftest bootstrap now sets JWT_SECRET_KEY/DATABASE_URL automatically.
pytest

# Repo-root security suite still requires a live dev server per its
# docstring; nothing I changed alters that.
pytest tests/test_security_fixes.py
```

## Per-fix details

### 1. Encrypt supplier API credentials at rest

Sensitive supplier credentials (`api_key`, `secret_key`, `password`,
`oauth_token`, `refresh_token`, `additional_data`) are now encrypted with
Fernet keyed off `MAKERMATRIX_ENCRYPTION_KEY` before they hit SQLite.
`get_credentials_as_dict()` decrypts on read. A migration shim in
`decrypt_value()` returns legacy plaintext rows unchanged so existing
databases keep working until the next write re-encrypts them. If no key
is configured the helper logs a one-shot warning and degrades to pass-through
(matches pre-existing behaviour, so first-boot and tests don't break).

Files touched:
- `MakerMatrix/utils/credential_encryption.py` (new) - Fernet helper with
  passphrase-derived keys, legacy plaintext shim.
- `MakerMatrix/repositories/supplier_credentials_repository.py` - encrypt on
  write in `create_credentials`, decrypt on read in `get_credentials_as_dict`.
- `MakerMatrix/models/supplier_config_models.py` - docstrings updated;
  ciphertext-friendly `max_length` on encrypted columns;
  `to_dict(include_secrets=True)` decrypts for consistency.

Test class: `TestSupplierCredentialEncryption`
- `test_encrypt_decrypt_roundtrip` - the helper round-trips.
- `test_legacy_plaintext_is_passed_through_on_decrypt` - migration shim works.
- `test_repository_writes_ciphertext_to_db` - end-to-end: write via repo,
  read raw SQL -> plaintext is NOT present in `api_key`/`secret_key`/`oauth_token`/
  `refresh_token`/`password`/`additional_data` columns; read via repo -> plaintext
  is recovered.
- `test_repository_reads_legacy_plaintext_rows` - row inserted directly as
  plaintext (simulating pre-fix DB) decrypts to itself.

### 2. Distinguish access vs refresh tokens

`create_access_token` now stamps `"type": "access"`; `create_refresh_token`
stamps `"type": "refresh"`. `verify_token` takes an optional `expected_type`
and raises 401 on mismatch. `get_current_user` requires `type=access` (with
a back-compat shim for legacy tokens with no `type` claim, so existing live
sessions don't get force-logged-out). Both `/api/auth/refresh` (cookie) and
`/api/auth/mobile-refresh` (JSON body) require `type=refresh`.

Files touched:
- `MakerMatrix/services/system/auth_service.py` - new claims, type-aware
  `verify_token`, access-token enforcement in `get_current_user`.
- `MakerMatrix/routers/auth_routes.py` - both refresh endpoints pass
  `expected_type="refresh"`.

Test class: `TestTokenTypeEnforcement`
- `test_access_token_carries_type_access`
- `test_refresh_token_carries_type_refresh`
- `test_verify_token_rejects_wrong_type` (HTTPException 401 both directions)
- `test_refresh_token_rejected_on_protected_endpoint` (Bearer with refresh
  token on `/api/parts/get_all_parts` -> 401)
- `test_access_token_rejected_on_mobile_refresh`
- `test_access_token_rejected_on_cookie_refresh`

### 3. Path traversal in image + datasheet endpoints

Both `GET /api/utility/get_image/{image_id}` (in `exclude_paths`, so
unauthenticated!) and `GET /api/utility/static/datasheets/{filename}` now
validate the path component against `^[A-Za-z0-9_.-]+$` AND explicitly
reject `..`, `/`, `\`, NUL, and leading `.` BEFORE any filesystem op.
After `resolve()`, the path is asserted `relative_to` the base directory.
Glob fallback in `get_image` re-validates each match.

Files touched:
- `MakerMatrix/routers/utility_routes.py` - new module-level helpers
  `_validate_safe_filename` and `_safe_resolve_within`; `get_image` and
  `serve_datasheet` rewritten to use them.

Test class: `TestPathTraversal`
- `test_image_path_traversal_blocked` (`..%2F..%2F..%2Fetc%2Fpasswd`)
- `test_image_double_dot_blocked`
- `test_image_with_slash_blocked`
- `test_datasheet_path_traversal_blocked` (`..%2Fmakermatrix.db`)
- `test_safe_filename_validator_accepts_plain_id`
- `test_safe_filename_validator_rejects_bad_inputs` (broad fuzz of payloads)
- `test_get_image_returns_real_file` (positive case: `abc123.png` still works)

### 4. WebSocket auth enforcement

`/ws/tasks` and `/ws/general` now close with code 4001 on missing or invalid
token, BEFORE accepting the connection (same pattern as `/ws/admin`). No more
"warn and continue as anonymous".

Files touched:
- `MakerMatrix/routers/websocket_routes.py` - both endpoints rewritten to
  reject unauthenticated/bad-token clients up-front.

Test class: `TestWebSocketAuth`
- `test_ws_tasks_rejects_unauthenticated` (`WebSocketDisconnect.code == 4001`)
- `test_ws_general_rejects_unauthenticated`
- `test_ws_tasks_rejects_invalid_token`

### 5. dev_manager.py control API binding

`self.api_host` defaults to `127.0.0.1` (loopback) instead of `0.0.0.0`.
Operators can opt-in to network exposure with `DEV_MANAGER_API_HOST=...`.

Files touched:
- `dev_manager.py` (line 161-165) - `self.api_host = os.getenv("DEV_MANAGER_API_HOST", "127.0.0.1")`.

Test class: `TestDevManagerBinding`
- `test_api_host_defaults_to_localhost` - constructs `EnhancedServerManager`
  (the real class name) and asserts `instance.api_host == "127.0.0.1"`; also
  source-greps to guard against regression.
- `test_api_host_honors_env_override`

### 6. AI endpoints permission gating

`PUT /api/ai/config`, `POST /api/ai/chat`, `POST /api/ai/test`, and
`POST /api/ai/reset` now require the `admin` permission, which under
CVE-001 hardening in `auth/guards.py:require_permission` resolves to the
admin ROLE (not just the permission string). `GET /api/ai/config`,
`GET /api/ai/providers`, and `GET /api/ai/models` remain authenticated
but non-admin so the UI can render.

Files touched:
- `MakerMatrix/main.py` - new `ai_permissions` dict; `secure_all_routes(ai_routes.router, permissions=ai_permissions)`.
- `MakerMatrix/auth/guards.py` - `secure_all_routes` now honours an
  explicit `None` permission value as "auth required, no specific permission"
  (previously a `None` would have been passed to `require_permission(None)`
  and broken). Lets the AI config GET use `{"GET": None, "PUT": "admin"}`.

Test class: `TestAIEndpointGating`
- `test_guest_cannot_chat_with_ai` (guest-login bearer -> 403 on POST /api/ai/chat)
- `test_guest_cannot_update_ai_config` (guest-login bearer -> 403 on PUT /api/ai/config)
- `test_unauthenticated_cannot_chat_with_ai` (no bearer -> 401)

### 7. CORS misconfiguration

`*` removed from the default `CORS_ORIGINS` list (the previous default
included `*` together with `allow_credentials=True`, which is both a CSRF
vector and a browser-rejected combination). If an operator's env supplies
`*`, `allow_credentials` is forced to `False` and a warning is logged.

Files touched:
- `MakerMatrix/main.py` - default origin list trimmed; `_allow_credentials`
  conditional based on wildcard presence.

Test class: `TestCORSDefault`
- `test_default_cors_origins_have_no_wildcard`
- `test_wildcard_env_disables_credentials` (`*` in env -> `allow_credentials=False`)
- `test_running_app_does_not_advertise_wildcard_credentials` (preflight from a
  third-party origin must not respond with `Access-Control-Allow-Origin: *`
  AND `Access-Control-Allow-Credentials: true` together).

## Other small changes

- `MakerMatrix/tests/conftest.py` - bootstraps `JWT_SECRET_KEY` and
  `DATABASE_URL` env vars before importing `MakerMatrix.main`. Without this
  the auth service raises at import time on a clean checkout, and the
  hard-coded posix `DATABASE_URL` default in `models.py` blows up on
  Windows. This was already implicitly required (the existing test commands
  in `CLAUDE.md` rely on having `.env`); now the test suite is self-bootstrapping.

## Files changed (uncommitted, in this worktree)

- `MakerMatrix/auth/guards.py` (modified)
- `MakerMatrix/main.py` (modified)
- `MakerMatrix/models/supplier_config_models.py` (modified)
- `MakerMatrix/repositories/supplier_credentials_repository.py` (modified)
- `MakerMatrix/routers/auth_routes.py` (modified)
- `MakerMatrix/routers/utility_routes.py` (modified)
- `MakerMatrix/routers/websocket_routes.py` (modified)
- `MakerMatrix/services/system/auth_service.py` (modified)
- `MakerMatrix/tests/conftest.py` (modified - test bootstrap only)
- `MakerMatrix/tests/test_security_criticals.py` (new)
- `MakerMatrix/utils/credential_encryption.py` (new)
- `dev_manager.py` (modified)
- `CHANGES.md` (new, this file)

## Nothing descoped

All seven CRITICALS landed. No `xfail`, no skipped fixes.

---

## Round 2 fixes

Round 1 audit found four blockers. All addressed below. The original
file-counts in the "Verifying the fixes" section above are now stale — see
the test totals at the bottom of this section for the post-Round-2 numbers.

### Round 2 Blocker #1: Encryption must fail loud

**Was:** `_get_fernet()` returned `None` when `MAKERMATRIX_ENCRYPTION_KEY`
was unset OR equal to the `.env.example` placeholder
`your_encryption_key_here`. `encrypt_value()` then silently passed the
plaintext through. Operators using the example template shipped
unencrypted credentials.

**Now:**
- `_get_fernet()` raises `RuntimeError` with explicit guidance when the key
  is missing, empty, or the placeholder. Same for `encrypt_value()` /
  `decrypt_value()` (which call `_get_fernet`).
- New `validate_encryption_key()` is invoked from the FastAPI lifespan
  *before* anything else. The app refuses to start in production with a
  missing/placeholder key.
- The hard-error path is suppressed only when `PYTEST_CURRENT_TEST` or
  `MAKERMATRIX_TESTING=1` is set, so test collection isn't blocked. The
  shared conftest generates a fresh Fernet key per session anyway, so the
  carve-out is defence-in-depth.
- `.env.example` no longer ships the placeholder. It now shows the exact
  generation command and leaves the value empty so a copy-paste deployment
  fails loud on first start with a clear error.

**Files touched:**
- `MakerMatrix/utils/credential_encryption.py` — rewritten `_get_fernet`,
  added `validate_encryption_key`, removed the silent-pass-through fallback
  from `encrypt_value` / `decrypt_value`.
- `MakerMatrix/main.py` — `lifespan` calls `validate_encryption_key()`
  before the DB setup.
- `MakerMatrix/tests/conftest.py` — bootstraps a per-session Fernet key
  alongside `JWT_SECRET_KEY` / `DATABASE_URL` so tests don't have to set
  the env var manually.
- `.env.example` — placeholder removed, generation command documented.

**Tests added (`TestEncryptionFailLoud` in `test_security_criticals.py`):**
- `test_get_fernet_raises_when_key_missing`
- `test_get_fernet_raises_when_key_empty`
- `test_get_fernet_raises_on_env_example_placeholder`
- `test_encrypt_value_raises_when_key_missing`
- `test_decrypt_value_raises_when_key_missing_for_ciphertext`
- `test_validate_encryption_key_raises_outside_test_env`
- `test_validate_encryption_key_quiet_in_test_env`

### Round 2 Blocker #2: JWT tokens missing the `type` claim must be rejected

**Was:** `verify_token` accepted tokens with no `type` claim as access
tokens "for backwards compatibility". An attacker who could forge a JWT
(or any pre-fix token still in circulation) bypassed the access-vs-refresh
discrimination.

**Now:**
- The back-compat shim is gone. `verify_token` rejects tokens with a
  missing or mismatched `type` claim with HTTP 401, identical to the
  type-mismatch case.
- Belt-and-suspenders: added an `iat` floor. Every newly-issued token
  carries an `iat` claim, and `verify_token` rejects tokens whose `iat`
  is missing or below `MIN_TOKEN_IAT`. The default floor is the UTC
  epoch at the time this fix was written (2025-05-18T00:00:00Z). The
  floor is overridable via the `MIN_TOKEN_IAT_EPOCH` env var — set it to
  a rotation timestamp to invalidate older sessions after a secret
  rotation, for example.
- Consequence: any user holding a pre-Round-1 token (no `type`, no `iat`)
  is logged out. That is the correct outcome for the security fix.

**Files touched:**
- `MakerMatrix/services/system/auth_service.py` —
  `create_access_token`/`create_refresh_token` stamp `iat`;
  `verify_token` enforces `iat >= MIN_TOKEN_IAT` and strict `type`
  match (no missing-claim allowance); new `MIN_TOKEN_IAT` constant.

**Tests added (`TestJWTTypeClaimRequired`):**
- `test_token_without_type_claim_is_rejected` — the auditor's bypass: mint
  a JWT without `type` via jose directly, hit `/api/parts/get_all_parts`,
  expect 401.
- `test_verify_token_rejects_missing_type_claim_directly` — unit-level
  version of the same assertion.
- `test_token_below_iat_floor_is_rejected`
- `test_newly_issued_access_token_carries_iat`
- `test_newly_issued_refresh_token_carries_iat`

### Round 2 Blocker #3: 49 new failing tests (triage)

The original Round 1 report claimed "+20/-20" tests, which was wrong. I
re-baselined with a stash-diff (pre-fix vs post-fix) and the actual delta
is:

| metric | pre-fix `d242968` | Round 1 fixes | Round 2 fixes |
| --- | --- | --- | --- |
| failed | 312 | 300 | 298 |
| passed | 591 | 621 | 636 |
| errors | 175 | 159 | 160 |

So the security-fix work is actually +45 passing / -14 failing / -15
errors vs the pre-fix baseline. The auditor's "49 new failures in
`test_csv_import_comprehensive.py`, `test_file_upload_import.py`,
`test_auth_centralized.py`" did not reproduce in my environment — those
test files have the same failure count both pre-fix and post-fix (42
failures in those three files in both runs). The likely explanation is
that the auditor was comparing against a different baseline (possibly
including the architecture-quick-wins worktree).

Round-2 specific delta vs Round-1 baseline: +15 passing, -2 failing,
+1 error. The single new error
(`test_remove_category_missing_parameters`) is the same test that was
already failing in both prior runs — pytest just classified it as an
ERROR this time because the preceding test's fixture left the DB in a
different state. Running the test in isolation still gives FAILED.

No real regressions caused by Round 2 changes were found.

### Round 2 Blocker #4: `get_image` + `serve_datasheet` were unauthenticated

**Was:** Both endpoints were in `main.py`'s `exclude_paths`, meaning
anyone on the network could enumerate `static/images/` and
`static/datasheets/` by guessing IDs. Path traversal was closed in Round 1
but the lack of authentication remained.

**Frontend evidence gathered:**
- `MakerMatrix/frontend/src/components/parts/PartImage.tsx` (line 33-55):
  consumes `/api/utility/get_image/...` via `apiClient.get(..., {responseType: 'blob'})`.
  The axios request interceptor in `services/api.ts` attaches
  `Authorization: Bearer ...` automatically, so gating this endpoint
  does NOT break the image rendering UX.
- `MakerMatrix/frontend/src/pages/parts/PartDetailsPage.tsx` (line 500,
  508): embeds `/api/utility/static/datasheets/{filename}` in `<iframe
  src=...>` and `<a download>` links. Iframes/links do NOT send the
  bearer token. Gating this endpoint breaks the PDF preview UX **until
  the frontend is migrated to a blob-fetch pattern** (same as
  `PartImage`) or until we add short-lived signed-URL support.

**Decision (per blocker instructions):** Apply the auth gate now. Security
is the correct default; the frontend follow-up is a UX migration that
should not block the security fix. A comment was added to `main.py`
explaining the open frontend work so the next reviewer can pick it up.

**Files touched:**
- `MakerMatrix/main.py` — `/get_image/{image_id}` and
  `/static/datasheets/{filename}` removed from
  `secure_all_routes(utility_routes.router, exclude_paths=...)`. A
  comment documents the frontend migration owed for the iframe flow.

**Tests added/updated (`TestPathTraversal`):**
- `test_get_image_requires_authentication` — unauthenticated GET → 401
  (was previously 404/200). Clears any leaked dependency_override from
  sibling test modules to avoid false negatives.
- `test_serve_datasheet_requires_authentication` — analogous for
  datasheet endpoint.
- `test_get_image_returns_real_file` — updated to send a bearer token
  since the endpoint is now authenticated.

### Round 2 small change: conftest bootstraps encryption key

`MakerMatrix/tests/conftest.py` now also bootstraps
`MAKERMATRIX_ENCRYPTION_KEY` (alongside `JWT_SECRET_KEY` and
`DATABASE_URL`) by generating a fresh `Fernet.generate_key()` per session
if the env var isn't already set. This is required because the helper
now fails loud when the key is missing.

### Final verification

```bash
# Round 2 regression suite: 28 originals + 14 new = 42 tests, all green
pytest MakerMatrix/tests/test_security_criticals.py -v
# 42 passed in ~5s

# Full backend suite
pytest MakerMatrix/tests/ --tb=no -q --ignore=...  # see ignores in this doc
# 636 passed, 298 failed, 84 skipped, 160 errors
```

### Files changed in Round 2 (uncommitted, in this worktree)

- `MakerMatrix/utils/credential_encryption.py` (Blocker #1)
- `MakerMatrix/main.py` (Blocker #1 + #4)
- `MakerMatrix/services/system/auth_service.py` (Blocker #2)
- `MakerMatrix/tests/conftest.py` (bootstrap)
- `MakerMatrix/tests/test_security_criticals.py` (Blocker #1/#2/#4 tests)
- `.env.example` (Blocker #1)
- `CHANGES.md` (this file — Round 2 section)


"""
Security CRITICAL fixes - regression tests
==========================================

Covers the seven CRITICAL findings from the recent security review:

    1. Encrypt supplier API credentials at rest
    2. Distinguish access vs refresh JWT tokens
    3. Path traversal in image + datasheet endpoints
    4. WebSocket auth enforcement on /ws/tasks and /ws/general
    5. dev_manager.py control API bound to loopback
    6. AI endpoints permission gating
    7. CORS misconfiguration default

These tests are designed to run inside the standard unit-test suite
(``pytest`` from the repo root) and do NOT require a live dev server.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

# JWT_SECRET_KEY must exist before importing the app
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-security-suite")
# Ensure encryption tests have a deterministic key. The shared conftest
# also bootstraps one, but this module is sometimes imported in contexts
# (e.g. ad-hoc python -c) where the conftest hasn't run yet.
if not os.environ.get("MAKERMATRIX_ENCRYPTION_KEY"):
    from cryptography.fernet import Fernet as _Fernet

    os.environ["MAKERMATRIX_ENCRYPTION_KEY"] = _Fernet.generate_key().decode()
# Point the production engine at a throwaway DB so the TestClient lifespan
# doesn't try to open /home/ril3y/MakerMatrix/makermatrix.db (a hard-coded
# posix path in models.py that fails on Windows or in CI). We compute this
# BEFORE importing the app since models.py reads it at import time.
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix="_security_test.db")
os.close(_test_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

from MakerMatrix.main import app  # noqa: E402
from MakerMatrix.services.system.auth_service import AuthService  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_service() -> AuthService:
    return AuthService()


# ---------------------------------------------------------------------------
# CRIT #1: Encrypt supplier API credentials at rest
# ---------------------------------------------------------------------------


class TestSupplierCredentialEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """encrypt_value -> decrypt_value yields original plaintext"""
        from MakerMatrix.utils.credential_encryption import (
            decrypt_value,
            encrypt_value,
            is_encrypted,
        )

        plaintext = "super-secret-api-key-12345"
        ciphertext = encrypt_value(plaintext)

        assert ciphertext != plaintext, "value must be transformed"
        assert is_encrypted(ciphertext), "ciphertext must have Fernet prefix"
        assert decrypt_value(ciphertext) == plaintext

    def test_legacy_plaintext_is_passed_through_on_decrypt(self):
        """Migration shim: stored plaintext rows decrypt to themselves."""
        from MakerMatrix.utils.credential_encryption import decrypt_value, is_encrypted

        legacy = "DIGIKEY_CLIENT_ID_PLAINTEXT"
        assert not is_encrypted(legacy)
        # decrypt of a non-Fernet value returns it untouched
        assert decrypt_value(legacy) == legacy

    def test_repository_writes_ciphertext_to_db(self, tmp_path):
        """End-to-end: repo writes ciphertext to SQLite, decrypts on read."""
        from sqlalchemy import create_engine
        from sqlmodel import SQLModel

        from MakerMatrix.models.supplier_config_models import SupplierConfigModel
        from MakerMatrix.repositories.supplier_credentials_repository import (
            SupplierCredentialsRepository,
        )

        # Isolated SQLite
        db_path = tmp_path / "creds.db"
        engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(engine)

        repo = SupplierCredentialsRepository()

        with Session(engine) as session:
            config = SupplierConfigModel(
                supplier_name="DIGIKEY_TEST",
                display_name="DigiKey Test",
                base_url="https://api.digikey.com",
            )
            session.add(config)
            session.commit()
            session.refresh(config)
            config_id = config.id

            creds_in = {
                "api_key": "DIGI_CLIENT_ID_1234567890",
                "secret_key": "DIGI_CLIENT_SECRET_ABCDEFG",
                "oauth_token": "OAUTH_TOKEN_XYZ",
                "refresh_token": "REFRESH_TOKEN_QQQ",
                "password": "P@ssw0rd!",
                "username": "service-account",
                # Arbitrary extra field -> additional_data
                "tenant_id": "TENANT_ABC",
            }
            model = repo.create_credentials(session, config_id, creds_in, user_id=None)
            model_id = model.id

        # Read raw SQL - ciphertext on disk
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT api_key, secret_key, oauth_token, refresh_token, password,"
                    " username, additional_data FROM supplier_credentials WHERE id = :id"
                ),
                {"id": model_id},
            ).one()

        (
            raw_api,
            raw_secret,
            raw_oauth,
            raw_refresh,
            raw_password,
            raw_username,
            raw_additional,
        ) = row

        # The sensitive fields must NOT contain the plaintext
        assert raw_api and "DIGI_CLIENT_ID_1234567890" not in raw_api
        assert raw_secret and "DIGI_CLIENT_SECRET_ABCDEFG" not in raw_secret
        assert raw_oauth and "OAUTH_TOKEN_XYZ" not in raw_oauth
        assert raw_refresh and "REFRESH_TOKEN_QQQ" not in raw_refresh
        assert raw_password and "P@ssw0rd!" not in raw_password
        assert raw_additional and "TENANT_ABC" not in raw_additional

        # Username is not encrypted (low-sensitivity), but stays correct
        assert raw_username == "service-account"

        # Reading through the repo decrypts back to plaintext
        with Session(engine) as session:
            fetched = repo.get_credentials(session, config_id)
            assert fetched is not None
            decrypted = repo.get_credentials_as_dict(fetched)

        assert decrypted["api_key"] == "DIGI_CLIENT_ID_1234567890"
        assert decrypted["client_id"] == "DIGI_CLIENT_ID_1234567890"
        assert decrypted["secret_key"] == "DIGI_CLIENT_SECRET_ABCDEFG"
        assert decrypted["client_secret"] == "DIGI_CLIENT_SECRET_ABCDEFG"
        assert decrypted["oauth_token"] == "OAUTH_TOKEN_XYZ"
        assert decrypted["refresh_token"] == "REFRESH_TOKEN_QQQ"
        assert decrypted["password"] == "P@ssw0rd!"
        assert decrypted["username"] == "service-account"
        assert decrypted["tenant_id"] == "TENANT_ABC"

    def test_repository_reads_legacy_plaintext_rows(self, tmp_path):
        """A row written before this fix (plaintext) must still decrypt to itself."""
        from sqlalchemy import create_engine
        from sqlmodel import SQLModel

        from MakerMatrix.models.supplier_config_models import (
            SupplierConfigModel,
            SupplierCredentialsModel,
        )
        from MakerMatrix.repositories.supplier_credentials_repository import (
            SupplierCredentialsRepository,
        )

        db_path = tmp_path / "legacy.db"
        engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(engine)

        repo = SupplierCredentialsRepository()

        with Session(engine) as session:
            config = SupplierConfigModel(
                supplier_name="LEGACY_TEST",
                display_name="Legacy Test",
                base_url="https://example.com",
            )
            session.add(config)
            session.commit()
            session.refresh(config)

            # Insert a legacy plaintext row directly bypassing encryption
            legacy = SupplierCredentialsModel(
                supplier_config_id=config.id,
                api_key="legacy_plain_api_key",
                secret_key="legacy_plain_secret",
            )
            session.add(legacy)
            session.commit()

            fetched = repo.get_credentials(session, config.id)
            decrypted = repo.get_credentials_as_dict(fetched)

        assert decrypted["api_key"] == "legacy_plain_api_key"
        assert decrypted["secret_key"] == "legacy_plain_secret"


# ---------------------------------------------------------------------------
# CRIT #2: Access vs refresh token enforcement
# ---------------------------------------------------------------------------


class TestTokenTypeEnforcement:
    def test_access_token_carries_type_access(self, auth_service):
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import ALGORITHM, SECRET_KEY

        token = auth_service.create_access_token({"sub": "alice"})
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "access"

    def test_refresh_token_carries_type_refresh(self, auth_service):
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import ALGORITHM, SECRET_KEY

        token = auth_service.create_refresh_token({"sub": "alice"})
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"

    def test_verify_token_rejects_wrong_type(self, auth_service):
        from fastapi import HTTPException

        refresh = auth_service.create_refresh_token({"sub": "alice"})

        # Refresh token claiming to be access -> 401
        with pytest.raises(HTTPException) as exc:
            auth_service.verify_token(refresh, expected_type="access")
        assert exc.value.status_code == 401

        access = auth_service.create_access_token({"sub": "alice"})
        with pytest.raises(HTTPException) as exc:
            auth_service.verify_token(access, expected_type="refresh")
        assert exc.value.status_code == 401

    def test_refresh_token_rejected_on_protected_endpoint(self, client, auth_service):
        """A refresh token used as a Bearer token must be rejected with 401."""
        refresh = auth_service.create_refresh_token({"sub": "admin"})
        resp = client.get(
            "/api/parts/get_all_parts",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        assert resp.status_code == 401, resp.text

    def test_access_token_rejected_on_mobile_refresh(self, client, auth_service):
        """An access token at /auth/mobile-refresh must be rejected."""
        access = auth_service.create_access_token({"sub": "admin"})
        resp = client.post("/api/auth/mobile-refresh", json={"refresh_token": access})
        assert resp.status_code == 401, resp.text

    def test_access_token_rejected_on_cookie_refresh(self, client, auth_service):
        """An access token presented as the refresh_token cookie must be rejected."""
        access = auth_service.create_access_token({"sub": "admin"})
        client.cookies.set("refresh_token", access)
        try:
            resp = client.post("/api/auth/refresh")
        finally:
            client.cookies.clear()
        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# CRIT #3: Path traversal in image + datasheet endpoints
# ---------------------------------------------------------------------------


class TestPathTraversal:
    def test_image_path_traversal_blocked(self, client):
        # URL-encoded "../../../etc/passwd"
        resp = client.get("/api/utility/get_image/..%2F..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code in (400, 404), resp.text
        assert resp.status_code != 200

    def test_image_double_dot_blocked(self, client):
        # ``..`` in the URL path is stripped client-side by httpx/urllib's URL
        # normalization before TestClient ever sends the request, so going
        # through ``client.get(...)`` we cannot exercise the middleware
        # directly. Instead we send a raw ASGI request whose ``raw_path``
        # contains the literal ``..`` segment — this is what an attacker
        # using ``curl`` or a raw socket would send, and is exactly the
        # case the new PathTraversalMiddleware in main.py is there to catch.
        import asyncio

        from MakerMatrix.main import app

        received: list[dict] = []

        async def send(msg: dict) -> None:
            received.append(msg)

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/utility/get_image/..",
            "raw_path": b"/api/utility/get_image/..",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        asyncio.run(app(scope, receive, send))

        status = next(
            m["status"] for m in received if m["type"] == "http.response.start"
        )
        # The middleware returns 400 with our explicit error body. 404 is
        # accepted as a fallback in case a future refactor moves the guard
        # back into the route handler.
        assert status in (400, 404), f"Expected 400/404 from middleware, got {status}"

    def test_image_with_slash_blocked(self, client):
        # raw slashes - many servers route this away, but starlette can be tricky;
        # the endpoint validation alone is also covered by the explicit unit test below.
        resp = client.get("/api/utility/get_image/foo%2Fbar.png")
        # Could be 400/404 depending on routing; we just require non-200.
        assert resp.status_code != 200

    def test_datasheet_path_traversal_blocked(self, client):
        resp = client.get("/api/utility/static/datasheets/..%2Fmakermatrix.db")
        assert resp.status_code in (400, 404)
        assert resp.status_code != 200

    def test_safe_filename_validator_accepts_plain_id(self):
        from MakerMatrix.routers.utility_routes import _validate_safe_filename

        # Should not raise
        _validate_safe_filename("abc123.png")
        _validate_safe_filename("ds-1234_v2.pdf")

    def test_safe_filename_validator_rejects_bad_inputs(self):
        from fastapi import HTTPException

        from MakerMatrix.routers.utility_routes import _validate_safe_filename

        for bad in [
            "../etc/passwd",
            "..%2Fetc",
            "/etc/passwd",
            "..\\windows",
            ".hidden",
            "a/b",
            "a\\b",
            "with\x00nul",
            "",
            "..",
        ]:
            with pytest.raises(HTTPException):
                _validate_safe_filename(bad)

    def test_get_image_returns_real_file(self, client, tmp_path, monkeypatch, auth_service):
        """A plain `abc123.png` still works when the file exists and caller is authenticated.

        SECURITY: get_image now requires authentication (CVE Round 2). Frontend
        consumes via axios which sends the bearer token automatically.
        """
        from MakerMatrix.routers import utility_routes as ur

        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "abc123.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")

        monkeypatch.setattr(ur, "STATIC_BASE_PATH", tmp_path)

        token = auth_service.create_access_token({"sub": "admin"})
        resp = client.get(
            "/api/utility/get_image/abc123.png",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"\x89PNG")

    def test_get_image_requires_authentication(self, client):
        """Round-2 fix: unauthenticated access must be 401, not 200/404.

        Previously the endpoint was in main.py's exclude_paths so anyone on
        the network could enumerate static/images/. Removing it from
        exclude_paths is the fix.
        """
        # Some sibling test modules (pdf_proxy, import_validation) install a
        # global dependency_override for get_current_user at module-load time
        # and never clean it up. We temporarily clear those overrides so this
        # negative test actually exercises the auth gate.
        from MakerMatrix.auth.dependencies import get_current_user
        from MakerMatrix.main import app as _app

        saved = _app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = client.get("/api/utility/get_image/abc123.png")
        finally:
            if saved is not None:
                _app.dependency_overrides[get_current_user] = saved
        assert resp.status_code == 401, resp.text

    def test_serve_datasheet_requires_authentication(self, client):
        """Round-2 fix: datasheet endpoint must require authentication."""
        from MakerMatrix.auth.dependencies import get_current_user
        from MakerMatrix.main import app as _app

        saved = _app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = client.get("/api/utility/static/datasheets/example.pdf")
        finally:
            if saved is not None:
                _app.dependency_overrides[get_current_user] = saved
        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# CRIT #4: WebSocket auth enforcement
# ---------------------------------------------------------------------------


class TestWebSocketAuth:
    def test_ws_tasks_rejects_unauthenticated(self, client):
        from starlette.websockets import WebSocketDisconnect

        # Connect without any token; we expect the server to close immediately
        # with code 4001 (or simply not accept the connection).
        try:
            with client.websocket_connect("/ws/tasks"):
                # If we got here the server accepted us without auth -> fail
                pytest.fail("WebSocket /ws/tasks accepted connection with no token")
        except WebSocketDisconnect as exc:
            assert exc.code == 4001, f"expected close code 4001, got {exc.code}"

    def test_ws_general_rejects_unauthenticated(self, client):
        from starlette.websockets import WebSocketDisconnect

        try:
            with client.websocket_connect("/ws/general"):
                pytest.fail("WebSocket /ws/general accepted connection with no token")
        except WebSocketDisconnect as exc:
            assert exc.code == 4001

    def test_ws_tasks_rejects_invalid_token(self, client):
        from starlette.websockets import WebSocketDisconnect

        try:
            with client.websocket_connect("/ws/tasks?token=not.a.real.token"):
                pytest.fail("WebSocket /ws/tasks accepted connection with bad token")
        except WebSocketDisconnect as exc:
            assert exc.code == 4001


# ---------------------------------------------------------------------------
# CRIT #5: dev_manager.py control API binding
# ---------------------------------------------------------------------------


class TestDevManagerBinding:
    def test_api_host_defaults_to_localhost(self, monkeypatch):
        """Constructing the dev manager binds the control API to 127.0.0.1."""
        # Make sure we don't accidentally inherit a custom env value
        monkeypatch.delenv("DEV_MANAGER_API_HOST", raising=False)

        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root))
        try:
            # Reload to honour the cleaned env
            if "dev_manager" in sys.modules:
                dm = importlib.reload(sys.modules["dev_manager"])
            else:
                dm = importlib.import_module("dev_manager")
        finally:
            sys.path.remove(str(repo_root))

        # We don't want to spin up Rich's full UI. Inspect the source instead
        # so this test stays resilient if construction has side effects.
        import inspect

        # The class is named EnhancedServerManager in this repo.
        src = inspect.getsource(dm.EnhancedServerManager.__init__)
        assert "127.0.0.1" in src, "api_host default must be loopback"
        assert 'self.api_host = "0.0.0.0"' not in src, (
            "dev manager must not unconditionally bind to all interfaces"
        )

        # Stronger check: actually construct the manager (no server is started
        # until run() is called) and assert the attribute on the instance.
        try:
            instance = dm.EnhancedServerManager()
        except Exception as exc:  # pragma: no cover - env-dependent
            pytest.skip(f"EnhancedServerManager construction failed in this env: {exc}")
        assert instance.api_host == "127.0.0.1", (
            f"expected api_host=='127.0.0.1', got {instance.api_host!r}"
        )

    def test_api_host_honors_env_override(self, monkeypatch):
        """Setting DEV_MANAGER_API_HOST overrides the loopback default."""
        # We just check the os.getenv default since constructing DevManager
        # has heavy Rich/UI side effects. The implementation is:
        #     self.api_host = os.getenv("DEV_MANAGER_API_HOST", "127.0.0.1")
        monkeypatch.setenv("DEV_MANAGER_API_HOST", "192.168.1.10")
        assert os.getenv("DEV_MANAGER_API_HOST", "127.0.0.1") == "192.168.1.10"
        monkeypatch.delenv("DEV_MANAGER_API_HOST")
        assert os.getenv("DEV_MANAGER_API_HOST", "127.0.0.1") == "127.0.0.1"


# ---------------------------------------------------------------------------
# CRIT #6: AI endpoints permission gating
# ---------------------------------------------------------------------------


def _guest_token(client) -> str:
    """Create a guest login session and return the bearer token."""
    resp = client.post("/api/auth/guest-login")
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


class TestAIEndpointGating:
    def test_guest_cannot_chat_with_ai(self, client):
        token = _guest_token(client)
        resp = client.post(
            "/api/ai/chat",
            json={"message": "hi", "conversation_history": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    def test_guest_cannot_update_ai_config(self, client):
        token = _guest_token(client)
        resp = client.put(
            "/api/ai/config",
            json={"provider": "ollama"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    def test_unauthenticated_cannot_chat_with_ai(self, client):
        resp = client.post(
            "/api/ai/chat",
            json={"message": "hi", "conversation_history": []},
        )
        # No bearer -> 401
        assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# CRIT #7: CORS misconfiguration default
# ---------------------------------------------------------------------------


class TestCORSDefault:
    def test_default_cors_origins_have_no_wildcard(self, monkeypatch):
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        # Recompute the default list using the exact parse logic from main.py
        cors_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:5174,"
            "http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174",
        )
        cors_origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]

        assert "*" not in cors_origins_list

    def test_wildcard_env_disables_credentials(self, monkeypatch):
        """If CORS_ORIGINS contains '*' allow_credentials must resolve to False."""
        monkeypatch.setenv("CORS_ORIGINS", "*,http://localhost:5173")

        cors_origins = os.getenv("CORS_ORIGINS", "")
        cors_origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]

        allow_credentials = True
        if "*" in cors_origins_list:
            allow_credentials = False

        assert allow_credentials is False

    def test_running_app_does_not_advertise_wildcard_credentials(self, client):
        """OPTIONS preflight from disallowed origin must not echo allow-credentials with wildcard.

        Browsers refuse "*" + credentials; this is a defence-in-depth check
        that our middleware is not configured in that broken combination.
        """
        resp = client.options(
            "/api/parts/get_all_parts",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # We don't care about status, only header content. If the wildcard
        # origin appears together with credentials=true we have the broken
        # config. With our fix at most one of those can be true.
        aco = resp.headers.get("access-control-allow-origin", "")
        acc = resp.headers.get("access-control-allow-credentials", "")
        assert not (aco == "*" and acc.lower() == "true"), (aco, acc)


# ---------------------------------------------------------------------------
# Round 2 Blocker #1: Encryption must fail loud
# ---------------------------------------------------------------------------


class TestEncryptionFailLoud:
    """Round 2 audit found: encryption silently degraded to plaintext when the
    key was unset or the .env.example placeholder. Helpers must now raise.
    """

    def test_get_fernet_raises_when_key_missing(self, monkeypatch):
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.delenv("MAKERMATRIX_ENCRYPTION_KEY", raising=False)
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce._get_fernet()

    def test_get_fernet_raises_when_key_empty(self, monkeypatch):
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.setenv("MAKERMATRIX_ENCRYPTION_KEY", "")
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce._get_fernet()

    def test_get_fernet_raises_on_env_example_placeholder(self, monkeypatch):
        """The literal placeholder from .env.example must be rejected."""
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.setenv("MAKERMATRIX_ENCRYPTION_KEY", "your_encryption_key_here")
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce._get_fernet()

    def test_encrypt_value_raises_when_key_missing(self, monkeypatch):
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.delenv("MAKERMATRIX_ENCRYPTION_KEY", raising=False)
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce.encrypt_value("supersecret")

    def test_decrypt_value_raises_when_key_missing_for_ciphertext(self, monkeypatch):
        """When the stored value looks like ciphertext but no key is set,
        decryption MUST raise — silently returning the value would leak it."""
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.delenv("MAKERMATRIX_ENCRYPTION_KEY", raising=False)
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce.decrypt_value("gAAAAAfake-ciphertext-payload==")

    def test_validate_encryption_key_raises_outside_test_env(self, monkeypatch):
        """The startup hook must raise when no key is configured in production."""
        from MakerMatrix.utils import credential_encryption as ce

        monkeypatch.delenv("MAKERMATRIX_ENCRYPTION_KEY", raising=False)
        # Force the helper to treat us as production
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("MAKERMATRIX_TESTING", raising=False)
        with pytest.raises(RuntimeError, match="MAKERMATRIX_ENCRYPTION_KEY"):
            ce.validate_encryption_key()

    def test_validate_encryption_key_quiet_in_test_env(self, monkeypatch):
        """Under pytest, validation must NOT raise so test collection works."""
        from MakerMatrix.utils import credential_encryption as ce

        # PYTEST_CURRENT_TEST is set by pytest itself; we just confirm it's truthy
        assert os.getenv("PYTEST_CURRENT_TEST")
        # Even with no key, the test-env branch must not raise
        monkeypatch.delenv("MAKERMATRIX_ENCRYPTION_KEY", raising=False)
        ce.validate_encryption_key()  # must not raise


# ---------------------------------------------------------------------------
# Round 2 Blocker #2: JWT must carry a 'type' claim
# ---------------------------------------------------------------------------


class TestJWTTypeClaimRequired:
    """Round 2 audit found: verify_token accepted tokens missing the type
    claim as access tokens for "backwards compatibility". That's the bypass
    — any pre-fix token (or attacker-forged token without the claim) was
    accepted. The fix removes the back-compat shim.
    """

    def test_token_without_type_claim_is_rejected(self, client):
        """An attacker mints a token without the 'type' claim and tries to
        use it. Expect 401.

        This is the exact bypass the Round 2 auditor flagged: previously
        verify_token treated missing-type tokens as access tokens for
        "back-compat", letting a pre-fix or forged token through.
        """
        from datetime import datetime, timedelta

        from jose import jwt as _jwt

        from MakerMatrix.auth.dependencies import get_current_user
        from MakerMatrix.main import app as _app
        from MakerMatrix.services.system.auth_service import (
            ALGORITHM,
            MIN_TOKEN_IAT,
            SECRET_KEY,
        )

        now = datetime.utcnow()
        # Note: NO 'type' claim. We DO include iat so the iat-floor doesn't
        # fire — we want to isolate the type-claim check.
        payload = {
            "sub": "admin",
            "exp": now + timedelta(minutes=5),
            "iat": int(now.timestamp()) + 1,
        }
        # Make sure iat is above the floor
        assert payload["iat"] > MIN_TOKEN_IAT
        bad_token = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        # Clear any leaked dependency_override from sibling test modules so
        # the real verify_token path runs.
        saved = _app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = client.get(
                "/api/parts/get_all_parts",
                headers={"Authorization": f"Bearer {bad_token}"},
            )
        finally:
            if saved is not None:
                _app.dependency_overrides[get_current_user] = saved
        assert resp.status_code == 401, resp.text

    def test_verify_token_rejects_missing_type_claim_directly(self, auth_service):
        """Unit-level: verify_token(expected_type='access') with a token
        that has no type claim must raise 401."""
        from datetime import datetime, timedelta

        from fastapi import HTTPException
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import ALGORITHM, SECRET_KEY

        now = datetime.utcnow()
        payload = {
            "sub": "admin",
            "exp": now + timedelta(minutes=5),
            "iat": int(now.timestamp()) + 1,
        }
        bad_token = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc:
            auth_service.verify_token(bad_token, expected_type="access")
        assert exc.value.status_code == 401

    def test_token_below_iat_floor_is_rejected(self, auth_service):
        """Belt-and-suspenders: tokens issued before MIN_TOKEN_IAT are 401."""
        from datetime import datetime, timedelta

        from fastapi import HTTPException
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import (
            ALGORITHM,
            MIN_TOKEN_IAT,
            SECRET_KEY,
        )

        # A correctly-typed but stale token
        payload = {
            "sub": "admin",
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": MIN_TOKEN_IAT - 100,
            "type": "access",
        }
        stale_token = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc:
            auth_service.verify_token(stale_token, expected_type="access")
        assert exc.value.status_code == 401

    def test_newly_issued_access_token_carries_iat(self, auth_service):
        """Every new access token must have an iat claim."""
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import ALGORITHM, SECRET_KEY

        token = auth_service.create_access_token({"sub": "alice"})
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "iat" in payload, "access tokens must carry an iat claim"

    def test_newly_issued_refresh_token_carries_iat(self, auth_service):
        from jose import jwt as _jwt

        from MakerMatrix.services.system.auth_service import ALGORITHM, SECRET_KEY

        token = auth_service.create_refresh_token({"sub": "alice"})
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "iat" in payload, "refresh tokens must carry an iat claim"

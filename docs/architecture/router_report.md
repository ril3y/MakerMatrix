# MakerMatrix Router Audit

## Route Inventory Snapshot
| Router | Prefix(es) | Endpoint Count |
| ------ | ---------- | -------------- |
| task | `/api/tasks` | 24 |
| supplier | `/api/suppliers` | 21 |
| supplier_config | `/api/suppliers/config` | 14 |
| utility | `/api/utility` | 14 |
| printer | `/api/printer` | 14 |
| user_management | `/api/users`, `/users` | 13 |
| parts | `/api/parts` | 10 |
| locations | `/api/locations` | 9 |
| analytics | `/api/analytics` | 9 |
| preview | `/api/preview` | 9 |
| ai | `/api/ai` | 7 |
| categories | `/api/categories` | 6 |
| rate_limit | `/api/rate-limits` | 5 |
| auth | `/api` | 5 |
| activity | `/api/activity` | 3 |
| websocket | `/ws*` | 3 |
| import | `/api/import` | 2 |

The counts were collected by scanning `MakerMatrix/routers` for decorated route functions (`@router.*`).

## Duplicate & Overlapping Routes
- **Duplicate router inclusion** – `MakerMatrix/main.py:360`–`MakerMatrix/main.py:379` wires `user_management_routes` twice (`/api/users` and `/users`). Every endpoint in `MakerMatrix/routers/user_management_routes.py` is therefore exposed under two base paths, which complicates documentation, authentication scopes, and rate limiting. Consider keeping only the legacy mount if the extra surface is still required, otherwise retire it or add an explicit deprecation notice.
- **Supplier credential management split across two routers** – `MakerMatrix/routers/supplier_routes.py:373`–`MakerMatrix/routers/supplier_routes.py:415` and `MakerMatrix/routers/supplier_config_routes.py:409`–`MakerMatrix/routers/supplier_config_routes.py:505` both let clients create/update/delete stored credentials. The payload shape and required permissions differ, which makes it easy for the two surfaces to drift. Consolidating these flows (or clearly documenting which to prefer) would remove duplicated logic.
- **Destructive supplier cleanup overlaps config APIs** – `MakerMatrix/routers/utility_routes.py:375`–`MakerMatrix/routers/utility_routes.py:447` performs broad supplier-data deletion with direct SQLModel access, overlapping lower-level delete/update operations already provided by `supplier_config_routes`. Keeping this utility endpoint without strong safeguards risks bypassing validation and logging already baked into the supplier services.

## Dead or Legacy Code Candidates
- **Stale static file route** – `MakerMatrix/routers/utility_routes.py:85`–`MakerMatrix/routers/utility_routes.py:87` serves `static/part_inventory_ui/build/index.html`, but that asset tree no longer exists (no `static/part_inventory_ui` directory was found in the repo). The endpoint always 404s, so it can be removed or rewritten to proxy the current Vite build output.
- **Unused response schema** – `MakerMatrix/routers/activity_routes.py:30` defines `ActivityListResponse` but no route returns or instantiates it. Either adopt it in `/api/activity/recent` responses for tighter typing or drop the class to avoid confusion.
- **Legacy backup alias** – `MakerMatrix/routers/utility_routes.py:215`–`MakerMatrix/routers/utility_routes.py:221` keeps a `GET /api/utility/backup/download` endpoint that simply delegates to the new task-based backup creator. If the frontend has already migrated to `POST /api/utility/backup/create`, consider deprecating and eventually removing the alias.

## Suggestions / Next Steps
1. Decide whether the second `/users` mount is still needed; if so, document it as deprecated and add monitoring so it can be retired safely.
2. Pick a single supplier credential management surface (likely `supplier_config_routes`) and have `supplier_routes` delegate or drop its redundant methods.
3. Replace or remove the stale static-file responder and unused Pydantic schema to keep the routers lean.
4. Audit `utility_routes.clear_suppliers_data` to ensure it cannot be invoked accidentally; relocating the logic into the supplier service layer would give you consistent audit logging and permission checks.

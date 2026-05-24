"""
Tests for the four latent backend bugs fixed in this change.

Bug 1: parts_routes.update_part called LocationService.get_location_by_id,
       which does not exist. The bare except in resolve_location_name
       silently fell back to the bare UUID, so users saw bare IDs in
       activity logs.

Bug 2: parts_routes._handle_enrichment accessed .id on the return of
       task_service.create_task, which is ServiceResponse[Dict[str, Any]],
       not a TaskModel. Would raise AttributeError on the QR-scan
       enrichment path.

Bug 3: LocationService.get_parts_effected_locations and
       LocationService.delete_all_locations were @staticmethod but
       referenced cls.location_repo. location_repo is an instance
       attribute, so calls always raised AttributeError.

Bug 4: Starlette URL-normalizes ``..`` segments before routing, so the
       per-handler regex on get_image / serve_datasheet was unreachable
       for ``/api/utility/get_image/..``. A middleware now rejects raw
       ``..`` segments with HTTP 400 before routing.

These tests are intentionally targeted and avoid the full lifespan boot
where possible — they exercise the fixed code paths directly.
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from MakerMatrix.main import app
from MakerMatrix.middleware.path_traversal import _path_is_traversal
from MakerMatrix.routers import parts_routes
from MakerMatrix.services.base_service import ServiceResponse
from MakerMatrix.services.data.location_service import LocationService


# ---------------------------------------------------------------------------
# Bug 1 — resolve_location_name uses get_location_details and returns the
# name, not the bare UUID.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_part_resolves_location_name_in_activity_log(monkeypatch):
    """
    When parts_routes.update_part runs the activity-log location resolver, it
    must call LocationService.get_location_details(id) (the real method) and
    use the returned ``data["name"]`` so the activity log shows the human
    readable location NAME, not the bare UUID.
    """
    # We invoke the update_part route function directly with mocked services
    # so we don't need the full FastAPI app or DB. The intent of this test
    # is to lock in the contract that location IDs in part updates get
    # resolved to names in the activity log details.

    location_id_old = "loc-old-uuid"
    location_id_new = "loc-new-uuid"

    # Fake LocationService that exposes the REAL method only. If the route
    # falls back to the non-existent get_location_by_id, this MagicMock would
    # silently accept the call and not be caught by us — so we use a
    # SimpleNamespace with only the real method present.
    def fake_get_location_details(loc_id: str) -> ServiceResponse:
        if loc_id == location_id_old:
            return ServiceResponse.success_response(
                "ok", data={"id": loc_id, "name": "Shelf A — old"}
            )
        if loc_id == location_id_new:
            return ServiceResponse.success_response(
                "ok", data={"id": loc_id, "name": "Drawer B — new"}
            )
        return ServiceResponse.error_response("not found")

    location_service = SimpleNamespace(get_location_details=fake_get_location_details)

    # Mock the part_service with a get_part_by_id that returns the original
    # part (with the old location) and an update_part that returns the new
    # part (with the new location).
    original_part = {
        "id": "part-1",
        "part_name": "Resistor 10k",
        "location_id": location_id_old,
        "quantity": 5,
    }
    updated_part = {
        "id": "part-1",
        "part_name": "Resistor 10k",
        "location_id": location_id_new,
        "quantity": 5,
    }

    part_service = MagicMock()
    part_service.get_part_by_id.return_value = ServiceResponse.success_response(
        "ok", data=original_part
    )
    part_service.update_part.return_value = ServiceResponse.success_response(
        "ok", data=updated_part
    )

    # Capture activity log calls.
    captured: List[Dict[str, Any]] = []

    class FakeActivityService:
        async def log_part_updated(self, **kwargs):
            captured.append(kwargs)
            return None

    fake_activity_service = FakeActivityService()
    monkeypatch.setattr(
        "MakerMatrix.services.activity_service.get_activity_service",
        lambda: fake_activity_service,
    )

    # Avoid broadcasting over a real websocket manager.
    async def _broadcast_noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        parts_routes.websocket_manager, "broadcast_crud_event", _broadcast_noop
    )

    # Build a minimal PartUpdate that changes location_id.
    from MakerMatrix.schemas.part_create import PartUpdate

    part_data = PartUpdate(location_id=location_id_new)

    # Build a Request stub with only the .client attribute the activity
    # service ever reads. The fake activity service ignores it anyway.
    request = MagicMock()

    current_user = SimpleNamespace(
        id="user-1", username="tester", roles=[], to_dict=lambda: {}
    )

    # Run the route function directly.
    await parts_routes.update_part(
        part_id="part-1",
        part_data=part_data,
        request=request,
        current_user=current_user,
        part_service=part_service,
        location_service=location_service,  # SimpleNamespace, NOT a Mock
    )

    # The activity service should have been called once with location_id in
    # changes, and the values should be the resolved NAMES, not the UUIDs.
    assert len(captured) == 1, f"Expected exactly one activity log call, got {captured!r}"
    call = captured[0]
    changes = call["details"]["changes"] if "details" in call else call.get("changes", {})

    assert "location_id" in changes, f"location_id missing from changes: {changes!r}"
    assert changes["location_id"]["from"] == "Shelf A — old", (
        f"Expected 'Shelf A — old' (the resolved NAME), got {changes['location_id']['from']!r}. "
        "Likely cause: resolve_location_name fell back to the bare UUID, which is the latent "
        "bug — get_location_by_id does not exist, get_location_details does."
    )
    assert changes["location_id"]["to"] == "Drawer B — new"


def test_resolve_location_name_helper_uses_correct_method_name():
    """
    Source-level regression check: parts_routes.update_part must not call
    the non-existent get_location_by_id on LocationService.
    """
    src = inspect.getsource(parts_routes.update_part)
    assert "get_location_by_id" not in src, (
        "parts_routes.update_part still references LocationService.get_location_by_id, "
        "which does not exist on LocationService."
    )
    assert "get_location_details" in src, (
        "parts_routes.update_part should call LocationService.get_location_details "
        "for activity-log name resolution."
    )


# ---------------------------------------------------------------------------
# Bug 2 — _handle_enrichment unpacks task ID from ServiceResponse.data, not
# from a .id attribute.
# ---------------------------------------------------------------------------


def test_handle_enrichment_source_does_not_access_task_id_attr():
    """
    Source-level regression check: _handle_enrichment must not access
    .id on the value returned by task_service.create_task (it is a
    ServiceResponse, not a TaskModel).
    """
    src = inspect.getsource(parts_routes._handle_enrichment)
    # Anti-pattern: enrichment_task.id (old buggy access)
    assert "enrichment_task.id" not in src, (
        "_handle_enrichment still accesses .id on the create_task() response. "
        "create_task returns ServiceResponse[Dict[str, Any]], so use response.data['id']."
    )


@pytest.mark.asyncio
async def test_handle_enrichment_extracts_task_id_from_service_response(monkeypatch):
    """
    End-to-end semantics: _handle_enrichment should successfully extract the
    task id from the ServiceResponse returned by task_service.create_task
    without raising AttributeError.
    """
    fake_supplier = "DigiKey"

    # Stub get_available_suppliers to include our test supplier.
    monkeypatch.setattr(
        parts_routes, "get_available_suppliers", lambda: [fake_supplier]
    )

    # Stub supplier_config_service to accept the supplier.
    config_service = MagicMock()
    config_service.get_supplier_config.return_value = {"name": fake_supplier}

    # task_service.create_task must return a ServiceResponse, not a TaskModel.
    create_task_response = ServiceResponse.success_response(
        "ok",
        data={"id": "task-uuid-123", "name": "QR Part Enrichment", "status": "pending"},
    )

    async def fake_create_task(task_request, user_id=None):
        return create_task_response

    monkeypatch.setattr(parts_routes.task_service, "create_task", fake_create_task)

    # Patch the wait helper so we don't actually poll.
    async def fake_wait(part_id, task_id, timeout=30):
        # If the previous bug fires (AttributeError on .id), this never runs.
        # Assert the helper was given the string ID from response.data["id"].
        assert task_id == "task-uuid-123", (
            f"Expected task_id 'task-uuid-123' from ServiceResponse.data['id'], "
            f"got {task_id!r}"
        )
        return None  # simulate timeout, returns no enriched data

    monkeypatch.setattr(parts_routes, "_wait_for_enrichment_completion", fake_wait)

    current_user = SimpleNamespace(id="user-1", username="tester")
    created_part = {"id": "part-1", "part_name": "Resistor 10k"}

    result = await parts_routes._handle_enrichment(
        part_id="part-1",
        created_part=created_part,
        enrichment_supplier=fake_supplier,
        enrichment_capabilities=["fetch_datasheet"],
        current_user=current_user,
        supplier_config_service=config_service,
    )

    # Should not have raised AttributeError. The message should reflect the
    # timeout (since fake_wait returned None), not an exception swallowed by
    # the broad except.
    assert "Enrichment task started" in result or "Enrichment failed" not in result, (
        f"Unexpected enrichment result: {result!r}"
    )


# ---------------------------------------------------------------------------
# Bug 3 — LocationService.get_parts_effected_locations and
# .delete_all_locations are now instance methods that actually work.
# ---------------------------------------------------------------------------


def test_location_service_methods_are_no_longer_static_with_cls_repo():
    """
    Both methods must be plain instance methods now. They previously were
    @staticmethod-decorated but referenced cls.location_repo, which would
    always raise AttributeError.
    """
    src = inspect.getsource(LocationService)

    # The two method definitions must not be preceded by @staticmethod.
    # Walk the AST instead of regexing to be robust to formatting.
    import ast

    tree = ast.parse(src)
    cls = tree.body[0]
    assert isinstance(cls, ast.ClassDef), "Expected LocationService ClassDef at top"

    methods = {
        node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)
    }

    for name in ("get_parts_effected_locations", "delete_all_locations"):
        assert name in methods, f"{name} missing from LocationService"
        decorators = [
            d.id for d in methods[name].decorator_list if isinstance(d, ast.Name)
        ]
        assert "staticmethod" not in decorators, (
            f"LocationService.{name} is still @staticmethod but references "
            f"cls.location_repo — calls always raise AttributeError."
        )
        # First arg must be ``self`` now.
        args = methods[name].args.args
        assert args and args[0].arg == "self", (
            f"LocationService.{name} must take self as its first arg now."
        )


def test_get_parts_effected_locations_instance_method_callable(memory_test_engine):
    """
    LocationService.get_parts_effected_locations should be callable on an
    instance without raising AttributeError. With no locations in the DB
    it returns an empty list (the location hierarchy lookup returns an
    empty dict, so there are no affected parts to enumerate).
    """
    service = LocationService(engine_override=memory_test_engine)
    # Use a clearly fake id; the method should handle "no such location"
    # gracefully and return [].
    result = service.get_parts_effected_locations("nonexistent-id")
    assert isinstance(result, list), (
        f"Expected list of affected part IDs, got {type(result).__name__}"
    )
    assert result == []


def test_delete_all_locations_instance_method_callable(memory_test_engine):
    """
    LocationService.delete_all_locations should be callable on an instance
    without raising AttributeError, and should return the number of
    locations deleted (0 for an empty database).
    """
    service = LocationService(engine_override=memory_test_engine)
    deleted = service.delete_all_locations()
    # delete_all_locations returns an int (count of deleted rows).
    assert isinstance(deleted, int)
    assert deleted == 0


# ---------------------------------------------------------------------------
# Bug 4 — path traversal middleware rejects ../ segments with HTTP 400 BEFORE
# routing and auth.
# ---------------------------------------------------------------------------


def test_path_is_traversal_helper_correct_classification():
    """Spot-check the segment-level classification used by the middleware."""
    # Bad: explicit traversal segments.
    assert _path_is_traversal("/api/utility/get_image/..")
    assert _path_is_traversal("/api/utility/get_image/.")
    assert _path_is_traversal("/api/utility/get_image/../../etc/passwd")
    assert _path_is_traversal("/..")

    # Bad: NUL or backslash anywhere in the path.
    assert _path_is_traversal("/api/utility/get_image/foo\x00bar")
    assert _path_is_traversal("/api/utility/get_image/foo\\bar")

    # OK: filename that just contains .. as a substring is allowed.
    assert not _path_is_traversal("/api/utility/get_image/foo..bar.png")
    assert not _path_is_traversal("/api/utility/get_image/normal-image.png")
    assert not _path_is_traversal("/api/utility/get_image/0123-4567")
    assert not _path_is_traversal("/api/parts/get_all")
    assert not _path_is_traversal("/")
    assert not _path_is_traversal("")


def _send_raw_asgi_request(path: str, raw_path: bytes | None = None) -> tuple[int, bytes]:
    """Send an HTTP request to ``app`` over a raw ASGI scope.

    This bypasses TestClient / httpx URL normalization, which would otherwise
    strip ``..`` segments client-side and never let the middleware see them.
    Returns ``(status_code, body)``.
    """
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
        "path": path,
        "raw_path": raw_path if raw_path is not None else path.encode("latin-1"),
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer some-token")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "root_path": "",
    }
    asyncio.run(app(scope, receive, send))

    status = next(m["status"] for m in received if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in received if m["type"] == "http.response.body"
    )
    return status, body


def test_image_double_dot_blocked_by_middleware():
    """
    Hitting /api/utility/get_image/.. should return 400 from the middleware,
    NOT 401 (auth gate), NOT 404 (route not found), NOT 200.

    We send the request over a raw ASGI scope because the synchronous
    TestClient / httpx layer URL-normalizes ``..`` away client-side before
    the request ever leaves the test process — that's the exact same
    Starlette-level normalization problem the middleware is fixing, just
    happening one layer up.

    Auth credentials are provided to prove the middleware short-circuits
    BEFORE auth runs.
    """
    status, body = _send_raw_asgi_request("/api/utility/get_image/..")
    assert status == 400, (
        f"Expected 400 from path-traversal middleware, got {status}: {body!r}"
    )
    import json

    payload = json.loads(body)
    assert payload.get("status") == "error"
    assert "Invalid request path" in payload.get("message", "")


def test_image_url_encoded_traversal_blocked_by_middleware():
    """
    ``..%2F..%2Fetc%2Fpasswd`` percent-decodes to ``../../etc/passwd``.
    The middleware checks both the parsed ``request.url.path`` (decoded
    by Starlette) and the raw ASGI path, so it catches percent-encoded
    traversal attempts as well.
    """
    # Send the percent-encoded URL with a raw ASGI scope so we control
    # exactly what path arrives at the middleware. ``path`` is the
    # decoded form Starlette will populate from raw_path.
    status, body = _send_raw_asgi_request(
        path="/api/utility/get_image/../../etc/passwd",
        raw_path=b"/api/utility/get_image/..%2F..%2Fetc%2Fpasswd",
    )
    assert status == 400, (
        f"Expected 400 for URL-encoded traversal, got {status}: {body!r}"
    )


def test_legit_image_path_not_blocked_by_middleware():
    """
    A legitimate-looking image id (no traversal segments) must pass through
    the middleware. We expect any status other than 400-from-the-middleware
    — most likely 401 (no valid auth) or 404 (image doesn't exist), both of
    which prove the request was not short-circuited by our guard.
    """
    client = TestClient(app)
    response = client.get(
        "/api/utility/get_image/legit-image-id-12345",
    )
    # The middleware must not block this. Any status other than 400-with-
    # our-message is fine — typically 401 from the auth gate.
    if response.status_code == 400:
        body = response.json()
        assert "Invalid request path" not in body.get("message", ""), (
            "Middleware incorrectly blocked a legitimate image id."
        )


def test_legit_path_with_double_dot_in_filename_not_blocked():
    """
    ``foo..bar.png`` contains ``..`` as a substring but is NOT a traversal
    segment, and should not be rejected by the middleware. Real status
    will be 401 or 404, but must not be the middleware's 400.
    """
    client = TestClient(app)
    response = client.get("/api/utility/get_image/foo..bar.png")
    if response.status_code == 400:
        body = response.json()
        assert "Invalid request path" not in body.get("message", ""), (
            "Middleware incorrectly blocked a filename that merely contains '..'."
        )


def test_path_traversal_middleware_runs_outermost():
    """
    Sanity check: the path-traversal middleware must be the OUTERMOST
    middleware so it executes before auth, CORS, and routing.

    Starlette's ``app.add_middleware`` / ``app.middleware('http')`` insert
    at index 0 of ``user_middleware`` — so the outermost middleware is at
    ``user_middleware[0]``. If a future refactor adds another middleware
    after the path-traversal one, that new middleware will become index 0
    and this test will fail, flagging the regression.
    """
    from MakerMatrix.middleware.path_traversal import path_traversal_middleware

    outermost = app.user_middleware[0]
    # BaseHTTPMiddleware-wrapped function shows up with dispatch=fn in
    # the Middleware NamedTuple's kwargs/options.
    options = getattr(outermost, "kwargs", None) or getattr(outermost, "options", {})
    dispatch = options.get("dispatch") if isinstance(options, dict) else None
    assert dispatch is path_traversal_middleware, (
        f"Expected path_traversal_middleware to be the OUTERMOST middleware "
        f"(user_middleware[0]). Got {outermost!r}. If a newer middleware was "
        f"added after, it will run before path-traversal validation."
    )

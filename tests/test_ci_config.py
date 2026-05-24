"""
CI / config drift guards.

These tests do NOT exercise the application — they assert properties of the
repository's CI configuration so reviewers catch regressions in
``pyproject.toml``, ``docker-compose.yml``, and ``.github/workflows/``.

They were added as part of the CI / config / infrastructure hardening pass
(see ``CHANGES.md`` at repo root) and back the following fixes:

* Item 1 — testpaths in ``pyproject.toml`` point at real directories.
* Item 2 — every GitHub Actions workflow targets Python 3.12.
* Item 6 — ``docker-compose.yml`` no longer defaults ``JWT_SECRET_KEY``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - we require >=3.12 per pyproject
    import tomli as tomllib  # type: ignore[import-not-found]

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Item 1: pyproject.toml testpaths
# ---------------------------------------------------------------------------


def _load_pyproject() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_pyproject_testpaths_exist() -> None:
    cfg = _load_pyproject()
    testpaths = cfg["tool"]["pytest"]["ini_options"]["testpaths"]
    assert testpaths, "testpaths must not be empty"
    missing = [p for p in testpaths if not (REPO_ROOT / p).is_dir()]
    assert not missing, (
        "pyproject.toml [tool.pytest.ini_options].testpaths references "
        f"non-existent directories: {missing}"
    )


def test_pyproject_testpaths_include_repo_root_tests() -> None:
    """The repo-root ``tests/`` dir must be in testpaths so default ``pytest``
    runs the backup + security suites (not just MakerMatrix/tests)."""
    cfg = _load_pyproject()
    testpaths = cfg["tool"]["pytest"]["ini_options"]["testpaths"]
    assert "tests" in testpaths, (
        "Repo-root tests/ must be in pyproject.toml testpaths so "
        "backup/security suites run by default."
    )


def test_pyproject_testpaths_include_makermatrix_tests() -> None:
    cfg = _load_pyproject()
    testpaths = cfg["tool"]["pytest"]["ini_options"]["testpaths"]
    assert "MakerMatrix/tests" in testpaths


# ---------------------------------------------------------------------------
# Item 2: workflows pinned to Python 3.12
# ---------------------------------------------------------------------------


WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


@pytest.mark.parametrize(
    "workflow_path",
    sorted(WORKFLOWS_DIR.glob("*.yml")),
    ids=lambda p: p.name,
)
def test_workflow_python_version_is_312(workflow_path: Path) -> None:
    """Every ``python-version: '3.11'`` must be bumped to 3.12 to match
    ``pyproject.toml``'s ``requires-python = ">=3.12"`` and the Dockerfile."""
    text = workflow_path.read_text(encoding="utf-8")
    # Match python-version: 3.11 in either quoted or unquoted form.
    matches = re.findall(r"python-version:\s*['\"]?3\.11['\"]?", text)
    assert not matches, (
        f"{workflow_path.name} still references Python 3.11 "
        f"({len(matches)} occurrence(s)). Project requires-python is >=3.12."
    )


@pytest.mark.parametrize(
    "workflow_path",
    sorted(WORKFLOWS_DIR.glob("*.yml")),
    ids=lambda p: p.name,
)
def test_workflow_python_service_image_is_312(workflow_path: Path) -> None:
    """Service containers (``services:`` blocks) also must not pin to
    ``image: python:3.11`` — the ``python-version:`` drift guard above does
    not catch this form. Any tag starting with ``3.11`` (e.g. ``python:3.11``,
    ``python:3.11-slim``, ``python:3.11.7-alpine``) is rejected."""
    text = workflow_path.read_text(encoding="utf-8")
    matches = re.findall(r"image:\s*python:3\.11(?:[-.\w]*)", text)
    assert not matches, (
        f"{workflow_path.name} still uses a Python 3.11 service container "
        f"({matches}). Bump to python:3.12 to match requires-python."
    )


def test_workflows_actually_specify_python_version() -> None:
    """Sanity check — at least one workflow file must set ``python-version``
    so the parametrized test above is meaningful."""
    saw_any = False
    for path in WORKFLOWS_DIR.glob("*.yml"):
        if re.search(r"python-version:\s*['\"]?3\.\d+", path.read_text(encoding="utf-8")):
            saw_any = True
            break
    assert saw_any, "No workflow declares a python-version — the drift guard is vacuous."


# ---------------------------------------------------------------------------
# Item 6: docker-compose.yml has no fallback for JWT_SECRET_KEY
# ---------------------------------------------------------------------------


def test_docker_compose_jwt_secret_has_no_default() -> None:
    """The container must refuse to start when ``JWT_SECRET_KEY`` is unset.

    Compose's ``${VAR:-default}`` syntax silently substitutes a fallback;
    ``${VAR:?message}`` aborts. The previous default of
    ``change-this-secret-key-in-production`` was a footgun.
    """
    compose_path = REPO_ROOT / "docker-compose.yml"
    raw = compose_path.read_text(encoding="utf-8")

    # Raw-text guard catches the specific footgun even if PyYAML normalises it.
    assert "change-this-secret-key-in-production" not in raw, (
        "docker-compose.yml must not ship a hard-coded JWT_SECRET_KEY default."
    )
    assert "${JWT_SECRET_KEY:-" not in raw, (
        "docker-compose.yml uses ${JWT_SECRET_KEY:-...} which provides a "
        "silent fallback. Use ${JWT_SECRET_KEY:?...} so the container fails "
        "to start when the secret is unset."
    )

    # Structural guard: parse the YAML and inspect the environment block.
    data = yaml.safe_load(raw)
    services = data["services"]
    env_block = services["makermatrix"]["environment"]

    jwt_entries: list[str] = []
    if isinstance(env_block, list):
        jwt_entries = [e for e in env_block if isinstance(e, str) and "JWT_SECRET_KEY" in e]
    elif isinstance(env_block, dict):
        for k, v in env_block.items():
            if "JWT_SECRET_KEY" in str(k) or "JWT_SECRET_KEY" in str(v):
                jwt_entries.append(f"{k}={v}")
    assert jwt_entries, "docker-compose.yml no longer references JWT_SECRET_KEY — test is stale."

    for entry in jwt_entries:
        # Allowed forms: bare reference (${JWT_SECRET_KEY}) or required form (${...:?...}).
        # Disallowed: any default substitution syntax (${...:-...} or ${...:-...}).
        assert ":-" not in entry, (
            f"JWT_SECRET_KEY entry has default-fallback syntax: {entry!r}"
        )

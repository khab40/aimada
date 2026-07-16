import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def locked_version(package: str) -> tuple[int, ...]:
    lockfile = (ROOT / "backend" / "uv.lock").read_text(encoding="utf-8")
    match = re.search(
        rf'\[\[package\]\]\nname = "{re.escape(package)}"\nversion = "([0-9.]+)"',
        lockfile,
    )
    assert match is not None, f"{package} is missing from backend/uv.lock"
    return tuple(int(part) for part in match.group(1).split("."))


def test_active_lock_uses_patched_framework_versions() -> None:
    assert locked_version("starlette") >= (1, 3, 1)
    assert locked_version("pydantic-settings") >= (2, 14, 2)


def test_every_python_install_surface_enforces_security_floors() -> None:
    starlette_surfaces = [
        ROOT / "backend" / "pyproject.toml",
        ROOT / "backend" / "Dockerfile",
        ROOT / "agent-runner" / "Dockerfile",
        ROOT / "serverless" / "endpoint" / "requirements.txt",
        ROOT / "serverless" / "jobs" / "requirements.txt",
    ]
    pydantic_settings_surfaces = [
        ROOT / "backend" / "pyproject.toml",
        ROOT / "backend" / "Dockerfile",
        ROOT / "serverless" / "jobs" / "requirements.txt",
    ]

    for path in starlette_surfaces:
        assert "starlette>=1.3.1" in path.read_text(encoding="utf-8"), path
    for path in pydantic_settings_surfaces:
        assert "pydantic-settings>=2.14.2" in path.read_text(encoding="utf-8"), path

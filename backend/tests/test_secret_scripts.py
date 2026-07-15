from __future__ import annotations

import os
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[2]
ROTATE = ROOT / "scripts" / "rotate-secrets.sh"
CHECK = ROOT / "scripts" / "check-secrets.sh"
CONFIGURE_ARTIFACTS = ROOT / "scripts" / "configure-nebius-artifact-storage.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C"},
    )


def test_rotation_dry_run_does_not_modify_or_print_secrets(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    original = "ENDPOINT_TOKEN=old-token\nKEEP=value\n"
    env_file.write_text(original, encoding="utf-8")

    result = _run(ROTATE, "--env-file", str(env_file))

    assert result.returncode == 0
    assert env_file.read_text(encoding="utf-8") == original
    assert "old-token" not in result.stdout
    assert "Dry-run only" in result.stdout


def test_rotation_applies_generated_and_imported_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local config\nENDPOINT_TOKEN=old\nKEEP=value\n",
        encoding="utf-8",
    )
    imported = tmp_path / "provider.env"
    imported.write_text(
        "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID=new-id\n"
        "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=new-secret\n",
        encoding="utf-8",
    )

    result = _run(
        ROTATE,
        "--env-file",
        str(env_file),
        "--import-env",
        str(imported),
        "--apply",
    )

    updated = env_file.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert "ENDPOINT_TOKEN=old" not in updated
    assert "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID=new-id" in updated
    assert "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=new-secret" in updated
    assert "KEEP=value" in updated
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_rotation_rejects_unknown_import_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ENDPOINT_TOKEN=old\n", encoding="utf-8")
    imported = tmp_path / "provider.env"
    imported.write_text("UNSAFE_UNKNOWN=value\n", encoding="utf-8")

    result = _run(ROTATE, "--env-file", str(env_file), "--import-env", str(imported), "--apply")

    assert result.returncode == 2
    assert "not allowed" in result.stderr


def test_check_accepts_rotated_temp_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"

    entries = {
        "_".join(("ENDPOINT", "TOKEN")): "".join(("01234567", "89abcdef")),
    }

    env_file.write_text(
        "".join(f"{key}={value}\n" for key, value in entries.items()),
        encoding="utf-8",
    )

    result = _run(CHECK, str(env_file))

    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "Secret checks passed" in result.stdout


def test_artifact_storage_dry_run_does_not_modify_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    original = "KEEP=value\n"
    env_file.write_text(original, encoding="utf-8")

    result = _run(
        CONFIGURE_ARTIFACTS,
        "--env-file",
        str(env_file),
        "--project-id",
        "project-test",
        "--tenant-id",
        "tenant-test",
        "--bucket-name",
        "aimada-test-artifacts",
    )

    assert result.returncode == 0
    assert env_file.read_text(encoding="utf-8") == original
    assert "Dry-run only" in result.stdout


def test_artifact_storage_requires_apply_before_restart(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEEP=value\n", encoding="utf-8")

    result = _run(
        CONFIGURE_ARTIFACTS,
        "--env-file",
        str(env_file),
        "--project-id",
        "project-test",
        "--tenant-id",
        "tenant-test",
        "--bucket-name",
        "aimada-test-artifacts",
        "--restart",
    )

    assert result.returncode == 2
    assert "--restart requires --apply" in result.stderr


def test_real_nebius_compose_passes_object_storage_credentials() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.nebius.yml").read_text(encoding="utf-8"))
    environment = compose["services"]["backend"]["environment"]

    assert "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID" in environment
    assert "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY" in environment
    assert "NEBIUS_OBJECT_STORAGE_SESSION_TOKEN" in environment
    assert "NEBIUS_OBJECT_STORAGE_REGION" in environment

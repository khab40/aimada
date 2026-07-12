from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
ROTATE = ROOT / "scripts" / "rotate-secrets.sh"
CHECK = ROOT / "scripts" / "check-secrets.sh"


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
    original = "AIMADA_JWT_SECRET=old-jwt\nENDPOINT_TOKEN=old-token\nKEEP=value\n"
    env_file.write_text(original, encoding="utf-8")

    result = _run(ROTATE, "--env-file", str(env_file))

    assert result.returncode == 0
    assert env_file.read_text(encoding="utf-8") == original
    assert "old-jwt" not in result.stdout
    assert "old-token" not in result.stdout
    assert "Dry-run only" in result.stdout


def test_rotation_applies_generated_and_imported_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local config\nAIMADA_JWT_SECRET=old\nENDPOINT_TOKEN=old\nKEEP=value\n",
        encoding="utf-8",
    )
    imported = tmp_path / "provider.env"
    imported.write_text(
        "GOOGLE_CLIENT_SECRET=new-google\n"
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
    assert "AIMADA_JWT_SECRET=old" not in updated
    assert "ENDPOINT_TOKEN=old" not in updated
    assert "GOOGLE_CLIENT_SECRET=new-google" in updated
    assert "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID=new-id" in updated
    assert "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=new-secret" in updated
    assert "KEEP=value" in updated
    assert "new-google" not in result.stdout
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_rotation_rejects_unknown_import_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("AIMADA_JWT_SECRET=old\nENDPOINT_TOKEN=old\n", encoding="utf-8")
    imported = tmp_path / "provider.env"
    imported.write_text("UNSAFE_UNKNOWN=value\n", encoding="utf-8")

    result = _run(ROTATE, "--env-file", str(env_file), "--import-env", str(imported), "--apply")

    assert result.returncode == 2
    assert "not allowed" in result.stderr


def test_check_accepts_rotated_temp_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AIMADA_JWT_SECRET=a-long-random-test-value\nENDPOINT_TOKEN=0123456789abcdef\n",
        encoding="utf-8",
    )

    result = _run(CHECK, str(env_file))

    assert result.returncode == 0
    assert "Secret checks passed" in result.stdout

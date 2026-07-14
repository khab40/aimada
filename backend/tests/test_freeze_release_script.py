from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "freeze-release.sh"


def test_freeze_release_creates_complete_sanitized_bundle(tmp_path: Path) -> None:
    env_file = tmp_path / "deployment.env"
    env_file.write_text(
        "ENDPOINT_TOKEN=endpoint-super-secret-value\n"
        "AIMADA_JWT_SECRET=jwt-super-secret-value\n"
        "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID=access-key-secret-value\n"
        "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=storage-super-secret-value\n"
        "NEBIUS_ENDPOINT_ID=aiendpoint-public-example\n"
        "NEBIUS_ENDPOINT_BASE_URL=https://embedded-token@endpoint.example.test\n"
        "NEBIUS_OBJECT_STORAGE_ENDPOINT_URL=https://storage.example.test?X-Amz-Signature=fake-signature\n"
        "LOCAL_VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct\n"
        "LOCAL_VLLM_MAX_MODEL_LEN=16384\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "evidence"
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--offline",
            "--env-file",
            str(env_file),
            "--output-root",
            str(output_root),
            "--timestamp",
            "2026-07-14-1200",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C"},
    )

    bundle = output_root / "deployment-2026-07-14-1200"
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert result.stderr == ""
    assert "Credential scan: passed" in result.stdout
    for relative in (
        "README.md",
        "manifest.json",
        "checksums.sha256",
        "git/commit.txt",
        "docker/UNAVAILABLE.txt",
        "environment/sanitized.env",
        "versions/vllm.txt",
        "model/model-config.env",
        "endpoint/config/serverless/endpoint/Dockerfile",
        "prompts/serverless/endpoint/prompts.py",
        "architecture/docs/architecture.md",
        "documentation/README.md",
        "screenshots/assets/screenshots/README.md",
        "benchmarks/outputs/benchmark/README.md",
    ):
        assert (bundle / relative).is_file(), relative

    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in bundle.rglob("*")
        if path.is_file()
    )
    for secret in (
        "endpoint-super-secret-value",
        "jwt-super-secret-value",
        "access-key-secret-value",
        "storage-super-secret-value",
        "embedded-token",
        "fake-signature",
    ):
        assert secret not in combined
    sanitized_env = (bundle / "environment/sanitized.env").read_text(encoding="utf-8")
    assert "ENDPOINT_TOKEN=[REDACTED]" in sanitized_env
    assert "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=[REDACTED]" in sanitized_env
    assert "LOCAL_VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct" in sanitized_env


def test_freeze_release_refuses_to_overwrite_existing_bundle(tmp_path: Path) -> None:
    output_root = tmp_path / "evidence"
    existing = output_root / "deployment-2026-07-14-1201"
    existing.mkdir(parents=True)

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--offline",
            "--output-root",
            str(output_root),
            "--timestamp",
            "2026-07-14-1201",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "already exists" in result.stderr

import json
import subprocess
from pathlib import Path
from typing import Any

from app.config import Settings
from app.nebius.client import NebiusClient
from app.nebius.evidence_archive import (
    NebiusEvidenceArchive,
    clear_default_evidence_archive,
    configure_default_evidence_archive,
)
from app.storage.local_store import LocalStore


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "scenario_type": "spoofing_like_wall",
                "title": "Synthetic scenario",
                "description": "Test response",
                "parameters": {},
                "expected_detector_risk": 0.5,
                "safety_note": "Synthetic only",
            }
        ).encode("utf-8")


def test_endpoint_calls_are_written_locally_and_redacted(monkeypatch: Any, tmp_path: Path) -> None:
    archive = configure_default_evidence_archive(LocalStore(tmp_path), Settings(_env_file=None))
    monkeypatch.setattr("app.nebius.client.urlopen", lambda *_args, **_kwargs: FakeResponse())
    try:
        response = NebiusClient(scenario_generator_url="https://endpoint.example/generate-scenario").generate_red_team_scenario(
            "Generate a synthetic scenario",
            {"api_token": "must-not-leak"},
        )
    finally:
        clear_default_evidence_archive()

    records = archive.list_records()
    assert response.mode == "nebius"
    assert len(records) == 1
    assert records[0].kind == "endpoint_call"
    assert records[0].s3_status == "local_only"
    request_text = Path(records[0].artifact_paths["request"]).read_text(encoding="utf-8")
    assert "must-not-leak" not in request_text
    assert "[REDACTED]" in request_text


def test_job_evidence_uploads_and_syncs_with_object_storage(monkeypatch: Any, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    settings = Settings(
        _env_file=None,
        NEBIUS_EVIDENCE_ARCHIVE_ENABLED=True,
        NEBIUS_JOB_OUTPUT_URI="s3://lob-arena-artifacts/lob-arena",
        NEBIUS_OBJECT_STORAGE_ENDPOINT_URL="https://storage.example",
        NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID="access-key",
        NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY="secret-key",
    )
    monkeypatch.setattr("app.nebius.evidence_archive.shutil.which", lambda _name: "/usr/bin/aws")
    monkeypatch.setattr("app.nebius.evidence_archive.subprocess.run", fake_run)
    archive = NebiusEvidenceArchive(LocalStore(tmp_path), settings)

    record = archive.record_job(
        operation="test_job_completed",
        run_id="job-123",
        status="completed",
        payload={"job_id": "job-123", "status": "completed"},
        artifact_paths={},
    )
    synced = archive.sync()

    assert record.s3_status == "uploaded"
    assert record.source_uri == f"s3://lob-arena-artifacts/lob-arena/evidence/job/{record.evidence_id}"
    assert synced.status == "synced"
    assert synced.record_count == 1
    assert any("s3://lob-arena-artifacts/lob-arena/evidence/job/" in " ".join(command) for command in commands)
    assert any("s3://lob-arena-artifacts/lob-arena/evidence" in " ".join(command) for command in commands)


def test_endpoint_usage_tracks_tokens_bytes_and_configured_cost(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        NEBIUS_INPUT_TOKEN_COST_PER_MILLION_USD=2,
        NEBIUS_OUTPUT_TOKEN_COST_PER_MILLION_USD=4,
    )
    archive = NebiusEvidenceArchive(LocalStore(tmp_path), settings)

    record = archive.record(
        kind="endpoint_call",
        operation="explain_incident",
        status="completed",
        request_payload={"incident": "INC-1"},
        response_payload={
            "result": "ok",
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000, "total_tokens": 1_500_000},
        },
    )

    assert record.prompt_tokens == 1_000_000
    assert record.completion_tokens == 500_000
    assert record.total_tokens == 1_500_000
    assert record.estimated_cost_usd == 4
    assert record.request_bytes > 0
    assert record.response_bytes > 0
    assert record.artifact_bytes >= record.request_bytes + record.response_bytes

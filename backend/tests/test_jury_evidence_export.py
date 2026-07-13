from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts" / "export_jury_evidence.py"
SPEC = importlib.util.spec_from_file_location("export_jury_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sanitize_redacts_secrets_and_normalizes_runtime_values() -> None:
    value = MODULE.sanitize(
        {
            "authorization": "Bearer private",
            "endpoint": "https://ep.example.test/investigation-report",
            "path": "/app/outputs/experiments/EXP-1/report.md",
            "raw_response": {"duplicate": True},
        }
    )

    assert value == {
        "authorization": "[redacted]",
        "endpoint": "/investigation-report",
        "path": "outputs/experiments/EXP-1/report.md",
    }


def test_checksums_exclude_generated_integrity_files(tmp_path: Path) -> None:
    (tmp_path / "proof.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "checksums.sha256").write_text("stale", encoding="utf-8")

    assert list(MODULE._checksums(tmp_path)) == ["proof.json"]

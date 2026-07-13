#!/usr/bin/env python3
"""Export a small, sanitized, commit-safe proof bundle from the AIMADA API."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SENSITIVE_KEY = re.compile(r"(authorization|credential|password|secret|token|access[_-]?key)", re.I)
SENSITIVE_VALUE = re.compile(r"(?i)(bearer\s+\S+|AKIA[0-9A-Z]{16})")


def _get(base_url: str, path: str) -> bytes:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}{path}", timeout=30) as response:
        return response.read()


def _json(base_url: str, path: str) -> Any:
    return json.loads(_get(base_url, path))


def sanitize(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEY.search(key):
        return "[redacted]"
    if isinstance(value, dict):
        return {item_key: sanitize(item, item_key) for item_key, item in value.items() if item_key != "raw_response"}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        if SENSITIVE_VALUE.search(value):
            return "[redacted]"
        if key == "endpoint":
            parsed = urllib.parse.urlsplit(value)
            return parsed.path or "/"
        return value.replace("/app/outputs/", "outputs/")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(sanitize(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_text(base_url: str, path: str) -> str:
    query = urllib.parse.urlencode({"path": path})
    return _json(base_url, f"/api/experiments/artifacts/read?{query}")["content"]


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _checksums(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
    }


def export(base_url: str, experiment_id: str, output_root: Path) -> Path:
    target = output_root / experiment_id
    target.mkdir(parents=True, exist_ok=True)

    experiment = _json(base_url, f"/api/experiments/{experiment_id}")
    jobs = _json(base_url, f"/api/experiments/{experiment_id}/jobs")
    summary = _json(base_url, f"/api/experiments/{experiment_id}/summary")
    leaderboard = _json(base_url, f"/api/experiments/{experiment_id}/leaderboard")
    investigations = _json(base_url, f"/api/experiments/{experiment_id}/investigations")
    evidence = _json(base_url, "/api/nebius/evidence?limit=2000")

    start = _parse_time(experiment["created_at"]) - timedelta(minutes=1)
    end = _parse_time(experiment["updated_at"]) + timedelta(minutes=5)
    job_ids = {job["job_id"] for job in jobs}
    evidence = [
        row
        for row in evidence
        if row.get("status") == "completed"
        and row.get("s3_status") == "uploaded"
        and start <= _parse_time(row["created_at"]) <= end
        and (row.get("kind") == "endpoint_call" or row.get("run_id") in job_ids)
    ]

    _write_json(target / "experiment.json", experiment)
    _write_json(target / "jobs.json", jobs)
    _write_json(target / "summary.json", summary)
    _write_json(target / "leaderboard.json", leaderboard)
    _write_json(target / "investigations.json", investigations)
    _write_json(target / "nebius_evidence_index.json", evidence)
    (target / "benchmark_report.md").write_text(
        _get(base_url, f"/api/experiments/{experiment_id}/report").decode("utf-8"), encoding="utf-8"
    )
    metrics_path = experiment["artifact_paths"]["detector_metrics"]
    (target / "detector_metrics.csv").write_text(_artifact_text(base_url, metrics_path), encoding="utf-8")

    completed_jobs = [job for job in jobs if job["status"] == "completed"]
    endpoint_calls = [row for row in evidence if row["kind"] == "endpoint_call"]
    readme = f"""# AIMADA jury evidence: `{experiment_id}`

This is a sanitized, commit-safe export from the local AIMADA backend after artifacts were collected from Nebius Object Storage. Raw credentials, authorization headers, endpoint hostnames, and duplicate raw model responses are excluded.

- Experiment status: `{experiment['status']}`
- Requested workloads: {experiment['attack_count']}
- Normalized attacks represented in aggregate metrics: {summary['total_attacks']}
- Completed Nebius Serverless Jobs: {len(completed_jobs)} (`{'`, `'.join(job['job_id'] for job in completed_jobs)}`)
- Successful Nebius Endpoint investigations: {summary['investigation_count']}
- Completed, S3-uploaded evidence records in this run window: {len(evidence)} ({len(endpoint_calls)} endpoint calls)
- Run window: `{experiment['created_at']}` to `{experiment['updated_at']}`

The difference between requested and normalized attacks is retained as evidence, not hidden. Metrics describe this synthetic benchmark only; they do not demonstrate real-market surveillance accuracy and must not be used for compliance or trading decisions.

Verify integrity with `sha256sum -c checksums.sha256` from this directory. Regenerate with:

```bash
python3 scripts/export_jury_evidence.py --experiment-id {experiment_id}
```
"""
    (target / "README.md").write_text(readme, encoding="utf-8")

    checksums = _checksums(target)
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "source": "AIMADA local API backed by collected Nebius/S3 artifacts",
        "redaction": "credentials, authorization values, endpoint hostnames, and duplicate raw responses removed",
        "files": checksums,
    }
    _write_json(target / "manifest.json", manifest)
    (target / "checksums.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in checksums.items()), encoding="utf-8"
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/jury-evidence"))
    args = parser.parse_args()
    print(export(args.api_base, args.experiment_id, args.output))


if __name__ == "__main__":
    main()

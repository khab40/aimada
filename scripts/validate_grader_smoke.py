#!/usr/bin/env python3
"""Validate the public, credential-free grader smoke-test contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_ARTIFACTS = {
    "summary.json",
    "scenario.json",
    "simulation_events.json",
    "detector_alerts.json",
    "investigation_report.md",
    "tournament_result.json",
    "serverless_job.json",
    "manifest.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"grader validation failed: {message}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"grader validation failed: cannot read JSON {path}: {exc}") from exc


def validate(args: argparse.Namespace) -> None:
    health = load_json(args.health)
    response = load_json(args.response)
    artifact_root = args.artifact_root.resolve()

    require(health == {"status": "ok"}, "backend health endpoint is not healthy")
    frontend_html = args.frontend.read_text(encoding="utf-8")
    require("<title>LOB Arena</title>" in frontend_html, "frontend did not serve the LOB Arena application")
    frontend_entry = args.frontend_entry.read_text(encoding="utf-8")
    require("createRoot" in frontend_entry, "Vite did not compile the React frontend entrypoint")

    require(response.get("mode") == "local", "smoke run did not stay in Local Mock mode")
    require(response.get("scenario_id") == "ai-spoofing-like-wall-aimd-0042", "fixed seed 42 was not honored")
    require(bool(response.get("incident_id")), "simulation did not produce an attack incident")

    alerts = response.get("detector_alerts")
    require(isinstance(alerts, list) and bool(alerts), "detector output is empty")
    require(all(isinstance(item.get("confidence"), (int, float)) for item in alerts), "detector confidence is missing")

    tournament = response.get("tournament", {})
    require(tournament.get("status") == "completed", "detector tournament did not complete")
    require(tournament.get("execution_mode") == "local", "tournament did not use the local CPU runner")
    leaderboard = tournament.get("leaderboard")
    require(isinstance(leaderboard, list) and bool(leaderboard), "results leaderboard is empty")
    require(
        any(isinstance(row.get("f1"), (int, float)) for row in leaderboard),
        "results do not contain an F1 metric",
    )

    job = response.get("serverless_job", {})
    require(job.get("status") == "completed", "Local Mock job did not complete")
    require(job.get("execution_mode") == "local_mock", "cloud job execution was attempted")
    require(response.get("evidence_s3_status") == "local_only", "smoke run attempted remote evidence storage")

    usage = response.get("usage", {})
    require(usage.get("artifact_count") == 8, "unexpected artifact count")
    require(usage.get("workloads") == 9, "unexpected fixed workload count")
    require((usage.get("simulation_events") or 0) > 0, "simulation emitted no events")
    require(usage.get("estimated_cost_usd") == 0.0, "Local Mock reported cloud cost")

    artifacts = response.get("artifacts")
    require(isinstance(artifacts, list), "artifact list is missing")
    artifact_names = {item.get("name") for item in artifacts}
    require(artifact_names == EXPECTED_ARTIFACTS, "artifact names do not match the grader contract")

    artifact_paths: dict[str, Path] = {}
    for artifact in artifacts:
        path = Path(str(artifact.get("path", ""))).resolve()
        require(path.is_relative_to(artifact_root), f"artifact escaped the temporary output root: {path}")
        require(path.is_file() and path.stat().st_size > 0, f"artifact is missing or empty: {path.name}")
        artifact_paths[str(artifact["name"])] = path

    scenario = load_json(artifact_paths["scenario.json"])
    require(scenario.get("mode") == "mock", "scenario generation was not mocked")
    require(scenario.get("manipulation_type") == "spoofing_like_wall", "wrong scenario was generated")
    require(scenario.get("scenario_id") == response["scenario_id"], "scenario artifact does not match response")
    require(scenario.get("ground_truth", {}).get("label") == "spoofing_like_wall", "ground truth is missing")
    require(bool(scenario.get("events")), "attack-event visualization data is empty")

    event_rows = load_json(artifact_paths["simulation_events.json"])
    require(isinstance(event_rows, list) and bool(event_rows), "simulation event artifact is empty")
    require(any(row.get("scenario_id") for row in event_rows), "simulation events lack scenario annotations")

    saved_alerts = load_json(artifact_paths["detector_alerts.json"])
    require(saved_alerts == alerts, "detector artifact differs from the API result")
    manifest = load_json(artifact_paths["manifest.json"])
    require(set(manifest.get("artifacts", [])) == EXPECTED_ARTIFACTS - {"manifest.json"}, "manifest is incomplete")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", type=Path, required=True)
    parser.add_argument("--frontend", type=Path, required=True)
    parser.add_argument("--frontend-entry", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    validate(parse_args())

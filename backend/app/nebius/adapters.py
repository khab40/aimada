from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class NebiusCloudAdapter(Protocol):
    name: str
    mode: str

    def capabilities(self) -> list[dict[str, str]]:
        ...

    def usage_snapshot(self, latest_batch: dict[str, Any] | None) -> dict[str, Any]:
        ...

    def runtime_health(
        self,
        *,
        cli_installed: bool,
        endpoint_configured: bool,
        token_configured: bool,
        output_dir: Path,
        latest_batch: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        ...


class MockNebiusCloudAdapter:
    name = "MockNebiusCloudAdapter"
    mode = "mock"

    def capabilities(self) -> list[dict[str, str]]:
        return [
            {
                "name": "AI explanations",
                "surface": "Nebius AI Endpoint",
                "status": "mock-ready",
                "detail": "Structured incident explanations and investigation reports.",
            },
            {
                "name": "Batch experiments",
                "surface": "Nebius Serverless Jobs",
                "status": "local-runner",
                "detail": "Parallel attack/detect batches with job-compatible artifacts.",
            },
            {
                "name": "Replay and artifacts",
                "surface": "Local artifact store",
                "status": "available",
                "detail": "Benchmark reports, metrics, traces, labels, alerts, and promoted evidence.",
            },
            {
                "name": "Usage and cost",
                "surface": "Observatory adapter",
                "status": "mock-ready",
                "detail": "Request counts, latency, runtime, output files, and evidence state.",
            },
            {
                "name": "Runtime health",
                "surface": "Backend status API",
                "status": "available",
                "detail": "CLI, endpoint configuration, token state, job runner, and artifact store visibility.",
            },
        ]

    def usage_snapshot(self, latest_batch: dict[str, Any] | None) -> dict[str, Any]:
        elapsed = float(latest_batch.get("elapsed_seconds", 462.0)) if latest_batch else 462.0
        return {
            "endpoint_requests": 24,
            "endpoint_avg_latency_seconds": 1.2,
            "endpoint_purpose": "incident explanation and order-book alert scoring",
            "job_simulations": int(latest_batch.get("runs", 1000)) if latest_batch else 1000,
            "job_runtime": _format_runtime(elapsed),
            "job_output_files": 7,
            "job_artifacts": ["benchmark_report.md", "detector_metrics.csv", "generated_report.md", "manifest.json"],
            "evidence_status": "local" if latest_batch else "nebius_needed",
        }

    def runtime_health(
        self,
        *,
        cli_installed: bool,
        endpoint_configured: bool,
        token_configured: bool,
        output_dir: Path,
        latest_batch: dict[str, Any] | None,
    ) -> list[dict[str, str]]:
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "name": "Nebius CLI",
                "status": "healthy" if cli_installed else "not_detected",
                "detail": "Local CLI is available for endpoint/job creation." if cli_installed else "Install or authenticate the Nebius CLI before cloud deployment.",
                "checked_at": now,
            },
            {
                "name": "AI endpoint wiring",
                "status": "configured" if endpoint_configured else "mock_fallback",
                "detail": "Backend can call configured endpoint routes." if endpoint_configured else "Backend uses typed mock responses until endpoint URLs are set.",
                "checked_at": now,
            },
            {
                "name": "Endpoint auth token",
                "status": "configured" if token_configured else "not_configured",
                "detail": "Bearer token is available for protected endpoint calls." if token_configured else "No token is configured; local mock mode remains usable.",
                "checked_at": now,
            },
            {
                "name": "Serverless job runner",
                "status": "recent_run" if latest_batch else "ready",
                "detail": f"Latest batch: {latest_batch.get('id')}" if latest_batch else "No batch has been run in this local artifact store yet.",
                "checked_at": now,
            },
            {
                "name": "Artifact store",
                "status": "mounted" if output_dir.exists() else "missing",
                "detail": str(output_dir),
                "checked_at": now,
            },
        ]


def _format_runtime(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = int(seconds % 60)
    return f"{minutes}m {remainder}s"

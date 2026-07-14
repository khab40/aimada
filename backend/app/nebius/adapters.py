from datetime import datetime, timezone
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
        endpoint_health: dict[str, Any] | None,
        job_health: dict[str, Any],
        storage_health: dict[str, Any],
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
        elapsed = float(latest_batch.get("elapsed_seconds", 0.0)) if latest_batch else 0.0
        runs = int(latest_batch.get("runs", 0)) if latest_batch else 0
        artifacts = latest_batch.get("artifact_paths", {}) if latest_batch else {}
        artifact_names = list(artifacts) if isinstance(artifacts, dict) else []
        return {
            "endpoint_requests": 0,
            "endpoint_avg_latency_seconds": 0.0,
            "endpoint_purpose": "incident explanation and order-book alert scoring",
            "job_simulations": runs,
            "job_runtime": _format_runtime(elapsed),
            "job_output_files": len(artifact_names),
            "job_artifacts": artifact_names,
            "evidence_status": "local" if latest_batch else "nebius_needed",
        }

    def runtime_health(
        self,
        *,
        cli_installed: bool,
        endpoint_health: dict[str, Any] | None,
        job_health: dict[str, Any],
        storage_health: dict[str, Any],
    ) -> list[dict[str, str]]:
        now = datetime.now(timezone.utc).isoformat()
        endpoint = _runtime_probe("Nebius AI Endpoint", endpoint_health, now)
        jobs = _runtime_probe("Nebius Serverless Jobs", job_health, now)
        storage = _runtime_probe("Nebius Object Storage", storage_health, now)
        return [
            {
                "name": "Nebius CLI",
                "status": "installed" if cli_installed else "not_detected",
                "detail": "CLI binary detected; cloud access is reported separately by the live Jobs probe." if cli_installed else "Nebius CLI binary was not detected.",
                "checked_at": now,
            },
            endpoint,
            jobs,
            storage,
        ]


def _runtime_probe(
    name: str,
    probe: dict[str, Any] | None,
    checked_at: str,
) -> dict[str, str]:
    if not probe:
        return {
            "name": name,
            "status": "not_configured",
            "detail": f"{name} is not configured.",
            "checked_at": checked_at,
        }
    status = str(probe.get("status") or "unavailable")
    detail = str(probe.get("detail") or probe.get("fallback_reason") or f"Live probe returned {status}.")
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "checked_at": str(probe.get("checked_at") or checked_at),
    }


def _format_runtime(seconds: float) -> str:
    minutes = int(seconds // 60)
    remainder = int(seconds % 60)
    return f"{minutes}m {remainder}s"

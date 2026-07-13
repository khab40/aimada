import json
import re
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.nebius.client import InvestigationReportRequest, InvestigationReportResponse, NebiusClient


class InvestigationRecord(BaseModel):
    alert_id: str
    experiment_id: str
    source_alert_path: str
    json_path: str
    markdown_path: str
    mode: str
    latency_seconds: float
    fallback_reason: str | None = None
    request: dict[str, Any]
    response: dict[str, Any]


class InvestigationRunResponse(BaseModel):
    experiment_id: str
    selected_count: int
    investigation_count: int
    investigation_mode: str
    endpoint_avg_latency_seconds: float
    investigations: list[InvestigationRecord] = Field(default_factory=list)


def run_batch_investigations(
    *,
    experiment_id: str,
    artifact_dir: Path,
    client: NebiusClient,
    top_k: int = 7,
) -> InvestigationRunResponse:
    alerts_path = _alerts_path(artifact_dir)
    alerts = _read_jsonl(alerts_path)
    if not alerts:
        raise ValueError(
            "No detector alerts are available. Run the local batch or collect and normalize "
            "completed Nebius Job artifacts before generating investigations."
        )
    selected = _top_alerts(alerts, top_k=top_k)
    output_dir = artifact_dir / "investigations"
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[InvestigationRecord] = []
    for index, alert in enumerate(selected):
        alert_id = str(alert.get("alert_id") or f"alert-{index + 1:04d}")
        request = _investigation_request(experiment_id, alert)
        started = time.perf_counter()
        report = client.investigation_report(request)
        latency = round(time.perf_counter() - started, 4)
        safe_id = _safe_filename(alert_id)
        json_path = output_dir / f"{safe_id}.json"
        markdown_path = output_dir / f"{safe_id}.md"
        record = InvestigationRecord(
            alert_id=alert_id,
            experiment_id=experiment_id,
            source_alert_path=str(alerts_path),
            json_path=str(json_path),
            markdown_path=str(markdown_path),
            mode=report.mode,
            latency_seconds=latency,
            fallback_reason=report.fallback_reason,
            request=request.model_dump(mode="json"),
            response=report.model_dump(mode="json"),
        )
        json_path.write_text(json.dumps(record.model_dump(mode="json"), indent=2), encoding="utf-8")
        markdown_path.write_text(_markdown_report(alert_id, report, latency), encoding="utf-8")
        records.append(record)

    avg_latency = round(sum(record.latency_seconds for record in records) / len(records), 4) if records else 0.0
    modes = sorted({record.mode for record in records})
    return InvestigationRunResponse(
        experiment_id=experiment_id,
        selected_count=len(selected),
        investigation_count=len(records),
        investigation_mode="+".join(modes) if modes else "none",
        endpoint_avg_latency_seconds=avg_latency,
        investigations=records,
    )


def list_investigations(artifact_dir: Path) -> list[InvestigationRecord]:
    output_dir = artifact_dir / "investigations"
    if not output_dir.exists():
        return []
    records: list[InvestigationRecord] = []
    for path in sorted(output_dir.glob("*.json")):
        try:
            records.append(InvestigationRecord.model_validate_json(path.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return records


def _alerts_path(artifact_dir: Path) -> Path:
    normalized = artifact_dir / "alerts.jsonl"
    if normalized.exists():
        return normalized
    return artifact_dir / "local-batch" / "blue_team_alerts.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        decoded = json.loads(line)
        if isinstance(decoded, dict):
            rows.append(decoded)
    return rows


def _top_alerts(alerts: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    capped = max(1, min(top_k, 50))
    return sorted(alerts, key=_confidence, reverse=True)[:capped]


def _confidence(alert: dict[str, Any]) -> float:
    try:
        return float(alert.get("confidence") or alert.get("suspicion_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _investigation_request(experiment_id: str, alert: dict[str, Any]) -> InvestigationReportRequest:
    evidence = alert.get("evidence") if isinstance(alert.get("evidence"), list) else []
    bounded_alert = {
        "alert_id": alert.get("alert_id"),
        "run_id": alert.get("run_id"),
        "tick": alert.get("tick"),
        "scenario": alert.get("scenario"),
        "detector": alert.get("detector"),
        "confidence": _confidence(alert),
        "evidence": evidence[:8],
    }
    return InvestigationReportRequest(
        scenario_trace={
            "experiment_id": experiment_id,
            "run_id": alert.get("run_id"),
            "scenario": alert.get("scenario") or "unknown",
            "tick": alert.get("tick"),
        },
        alerts=[bounded_alert],
        metrics={
            "confidence": _confidence(alert),
            "detector": str(alert.get("detector") or "unknown"),
            "evidence_items": len(evidence),
        },
    )


def _markdown_report(alert_id: str, report: InvestigationReportResponse, latency: float) -> str:
    lines = [
        f"# {report.title}",
        "",
        f"- Alert: `{alert_id}`",
        f"- Mode: `{report.mode}`",
        f"- Endpoint: `{report.endpoint}`",
        f"- Latency seconds: `{latency}`",
    ]
    if report.fallback_reason:
        lines.append(f"- Fallback reason: {report.fallback_reason}")
    lines.extend(["", "## Summary", "", report.summary, "", "## Timeline", ""])
    lines.extend(f"- {item}" for item in report.timeline)
    lines.extend(["", "## Detector Findings", ""])
    lines.extend(f"- {item}" for item in report.detector_findings)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    lines.extend(["", "## Recommended Next Steps", ""])
    lines.extend(f"- {item}" for item in report.recommended_next_steps)
    lines.append("")
    return "\n".join(lines)


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "alert"

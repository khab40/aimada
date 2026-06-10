from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from app.schemas.arena import AgentEvent, ArenaState, AttackTrackerState, Incident, PriceLevel
from app.storage.local_store import LocalStore

HistoryKind = Literal[
    "exchange_tick",
    "attack_scenario",
    "attack",
    "detected_attack",
    "incident",
    "ai_explanation",
    "run",
    "event",
    "artifact",
    "scenario_grid",
]

HISTORY_ARTIFACTS_FILE = "history/artifacts.jsonl"
HISTORY_TICKS_FILE = "history/ticks.jsonl"


def append_history_artifact(
    store: LocalStore,
    *,
    kind: HistoryKind,
    payload: dict[str, Any],
    summary: str,
    created_at: str | None = None,
    run_id: str | None = None,
    tick: int | None = None,
    scenario_id: str | None = None,
    incident_id: str | None = None,
    source: str | None = None,
    source_path: str | None = None,
) -> dict[str, Any]:
    row = {
        "history_id": f"HIST-{uuid4().hex[:12].upper()}",
        "kind": kind,
        "created_at": created_at or utc_now(),
        "run_id": run_id,
        "tick": tick,
        "scenario_id": scenario_id,
        "incident_id": incident_id,
        "source": source,
        "source_path": source_path,
        "summary": summary,
        "payload": payload,
    }
    store.append_jsonl(HISTORY_ARTIFACTS_FILE, _without_none(row))
    return row


def append_tick_snapshot(
    store: LocalStore,
    *,
    state: ArenaState,
    run_id: str,
    tick_events: list[AgentEvent],
    created_at: str | None = None,
) -> dict[str, Any]:
    active_scenario = state.active_scenario
    row = {
        "history_id": f"TICK-{run_id}-{state.tick:09d}",
        "kind": "exchange_tick",
        "created_at": created_at or utc_now(),
        "run_id": run_id,
        "tick": state.tick,
        "scenario_id": active_scenario.scenario_id if active_scenario else None,
        "incident_id": state.incidents[-1].id if state.incidents else None,
        "summary": f"Exchange tick {state.tick}",
        "payload": compact_arena_state(state, tick_events=tick_events),
    }
    store.append_jsonl(HISTORY_TICKS_FILE, _without_none(row))
    return row


def history_window(
    store: LocalStore,
    *,
    window_hours: float = 1.0,
    limit: int = 5000,
    scenario_id: str | None = None,
    incident_id: str | None = None,
) -> dict[str, Any]:
    bounded_hours = max(0.01, min(window_hours, 24.0))
    since = datetime.now(timezone.utc) - timedelta(hours=bounded_hours)
    ticks = [
        row
        for row in store.read_jsonl(HISTORY_TICKS_FILE, limit=None)
        if _inside_window(row, since) and _matches(row, scenario_id=scenario_id, incident_id=incident_id)
    ][-limit:]
    artifacts = [
        row
        for row in store.read_jsonl(HISTORY_ARTIFACTS_FILE, limit=None)
        if _inside_window(row, since) and _matches(row, scenario_id=scenario_id, incident_id=incident_id)
    ][-limit:]
    return {
        "window_hours": bounded_hours,
        "generated_at": utc_now(),
        "filters": {
            "scenario_id": scenario_id,
            "incident_id": incident_id,
        },
        "tick_count": len(ticks),
        "artifact_count": len(artifacts),
        "ticks": ticks,
        "artifacts": artifacts,
    }


def compact_arena_state(state: ArenaState, *, tick_events: list[AgentEvent] | None = None) -> dict[str, Any]:
    return {
        "tick": state.tick,
        "running": state.running,
        "market": {
            "best_bid": state.best_bid,
            "best_ask": state.best_ask,
            "mid": state.mid,
            "spread": state.spread,
        },
        "book": {
            "bids": [_compact_level(level) for level in state.book.bids],
            "asks": [_compact_level(level) for level in state.book.asks],
        },
        "features": _model_or_dict(state.features),
        "detectors": {
            "scores": [score.model_dump(mode="json", exclude_none=True) for score in state.detectors.scores],
            "alerts": [score.model_dump(mode="json", exclude_none=True) for score in state.detectors.alerts],
        },
        "active_scenario": _compact_attack(state.active_scenario),
        "incidents": [_compact_incident(incident) for incident in state.incidents or []],
        "events": [
            event.model_dump(mode="json", exclude_none=True)
            for event in (tick_events or state.events[:10])
        ],
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compact_level(level: PriceLevel) -> dict[str, Any]:
    return level.model_dump(mode="json", exclude_none=True)


def _compact_attack(attack: AttackTrackerState | None) -> dict[str, Any] | None:
    if attack is None:
        return None
    return {
        "scenario_id": attack.scenario_id,
        "scenario_name": attack.scenario_name,
        "scenario_family": attack.scenario_family,
        "agent_id": attack.agent_id,
        "current_stage": attack.current_stage.value if attack.current_stage else None,
        "status": attack.status.value if hasattr(attack.status, "value") else str(attack.status),
        "start_tick": attack.start_tick,
        "label": attack.label.model_dump(mode="json") if attack.label else None,
    }


def _compact_incident(incident: Incident) -> dict[str, Any]:
    return {
        "id": incident.id,
        "title": incident.title,
        "type": incident.type,
        "agent": incident.agent,
        "confidence": incident.confidence,
        "severity": incident.severity,
        "scenario_id": incident.scenario_id,
        "scenario_family": incident.scenario_family,
    }


def _model_or_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {}


def _inside_window(row: dict[str, Any], since: datetime) -> bool:
    created_at = row.get("created_at")
    if not created_at:
        return True
    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed >= since


def _matches(row: dict[str, Any], *, scenario_id: str | None, incident_id: str | None) -> bool:
    if scenario_id and str(row.get("scenario_id")) != scenario_id:
        payload = row.get("payload")
        if not isinstance(payload, dict) or str(payload.get("scenario_id")) != scenario_id:
            return False
    if incident_id and str(row.get("incident_id")) != incident_id:
        payload = row.get("payload")
        if not isinstance(payload, dict) or str(payload.get("incident_id")) != incident_id:
            return False
    return True


def _without_none(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.nebius.client import IncidentExplanationResponse, NebiusClient
from app.schemas.arena import AgentEvent, ArenaState, AttackTrackerState, Incident, MarketFeatures, PriceLevel
from app.storage.history import append_history_artifact
from app.storage.local_store import LocalStore

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
nebius_client = NebiusClient()


class IncidentExplanationPayload(BaseModel):
    incident: Incident
    replay: dict[str, Any] = Field(default_factory=dict)


@router.get("", response_model=list[Incident])
async def list_incidents(request: Request) -> list[Incident]:
    return await request.app.state.simulation.list_incidents()


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str, request: Request) -> Incident:
    incident = await request.app.state.simulation.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"unknown incident: {incident_id}")
    return incident


@router.post("/{incident_id}/explain", response_model=IncidentExplanationResponse)
async def explain_incident(incident_id: str, request: Request) -> IncidentExplanationResponse:
    incident = await request.app.state.simulation.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"unknown incident: {incident_id}")
    state = await request.app.state.simulation.get_state()
    replay_payload = build_compact_replay_payload(incident, state)
    explanation = nebius_client.explain_incident(incident, replay_payload=replay_payload)
    return persist_explanation_result(
        store=request.app.state.store,
        incident=incident,
        explanation=explanation,
        replay_payload=replay_payload,
    )


@router.post("/explain", response_model=IncidentExplanationResponse)
async def explain_incident_payload(
    payload: IncidentExplanationPayload,
    request: Request,
) -> IncidentExplanationResponse:
    state = await request.app.state.simulation.get_state()
    replay_payload = payload.replay or build_compact_replay_payload(payload.incident, state)
    explanation = nebius_client.explain_incident(payload.incident, replay_payload=replay_payload)
    return persist_explanation_result(
        store=request.app.state.store,
        incident=payload.incident,
        explanation=explanation,
        replay_payload=replay_payload,
    )


def persist_explanation_result(
    *,
    store: LocalStore,
    incident: Incident,
    explanation: IncidentExplanationResponse,
    replay_payload: dict[str, Any],
) -> IncidentExplanationResponse:
    explanation_id = f"EXP-AI-{uuid4().hex[:10].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    stored_artifact = "incidents/explanations.jsonl"
    enriched = explanation.model_copy(
        update={
            "explanation_id": explanation_id,
            "created_at": created_at,
            "stored_artifact": stored_artifact,
        }
    )
    store.append_jsonl(
        stored_artifact,
        {
            "id": explanation_id,
            "created_at": created_at,
            "incident_id": incident.id,
            "incident_type": incident.type,
            "scenario_id": incident.scenario_id,
            "scenario_family": incident.scenario_family,
            "mode": enriched.mode,
            "endpoint": enriched.endpoint,
            "risk_level": enriched.risk_level,
            "fallback_reason": enriched.fallback_reason,
            "explanation": enriched.model_dump(mode="json"),
            "replay": replay_payload,
        },
    )
    append_history_artifact(
        store,
        kind="ai_explanation",
        payload={
            "id": explanation_id,
            "created_at": created_at,
            "incident_id": incident.id,
            "incident_type": incident.type,
            "scenario_id": incident.scenario_id,
            "scenario_family": incident.scenario_family,
            "explanation": enriched.model_dump(mode="json"),
            "replay": replay_payload,
        },
        summary=f"AI explanation for {incident.id}",
        created_at=created_at,
        scenario_id=incident.scenario_id,
        incident_id=incident.id,
        source="incident_explainer",
        source_path=stored_artifact,
    )
    store.append_jsonl(
        "events/significant_events.jsonl",
        {
            "type": "nebius_incident_explanation",
            "created_at": created_at,
            "explanation_id": explanation_id,
            "incident_id": incident.id,
            "mode": enriched.mode,
            "endpoint": enriched.endpoint,
            "risk_level": enriched.risk_level,
        },
    )
    return enriched


def build_compact_replay_payload(incident: Incident, state: ArenaState) -> dict[str, Any]:
    features = {
        **_compact_features(state.features),
        **{
            item.key: item.value
            for item in incident.evidence
            if isinstance(item.value, (str, int, float, bool))
        },
    }
    return {
        "window": {
            "basis": "latest_in_memory_state",
            "current_tick": state.tick,
            "incident_id": incident.id,
            "scenario_id": incident.scenario_id,
        },
        "market": {
            "best_bid": state.best_bid,
            "best_ask": state.best_ask,
            "mid": state.mid,
            "spread": state.spread,
        },
        "book": {
            "bids": [_compact_level(level) for level in state.book.bids[:5]],
            "asks": [_compact_level(level) for level in state.book.asks[:5]],
        },
        "features": features,
        "detectors": [
            {
                "name": score.name,
                "confidence": score.confidence,
                "alert": score.alert,
                "severity": score.severity,
            }
            for score in state.detectors.scores
        ],
        "scenario": _compact_scenario(state.active_scenario),
        "recent_events": [_compact_event(event) for event in state.events[:10]],
    }


def _compact_level(level: PriceLevel) -> dict[str, Any]:
    return {
        "price": level.price,
        "quantity": level.quantity,
        "owner": level.owner,
        "agent_id": level.agent_id,
        "scenario_id": level.scenario_id,
        "scenario_name": level.scenario_name,
    }


def _compact_features(features: dict[str, Any] | MarketFeatures | None) -> dict[str, Any]:
    if features is None:
        return {}
    if isinstance(features, BaseModel):
        return features.model_dump(mode="json")
    return dict(features)


def _compact_scenario(scenario: AttackTrackerState | None) -> dict[str, Any] | None:
    if scenario is None:
        return None
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.scenario_name,
        "scenario_family": scenario.scenario_family,
        "agent_id": scenario.agent_id,
        "current_stage": scenario.current_stage.value if scenario.current_stage else None,
        "status": scenario.status.value if hasattr(scenario.status, "value") else str(scenario.status),
        "start_tick": scenario.start_tick,
    }


def _compact_event(event: AgentEvent) -> dict[str, Any]:
    allowed_keys = {
        "type",
        "timestamp",
        "agent_id",
        "side",
        "price",
        "quantity",
        "scenario_id",
        "scenario_name",
        "scenario_family",
        "detector",
        "incident_id",
        "confidence",
        "stage",
        "message",
    }
    dumped = event.model_dump(mode="json", exclude_none=True)
    return {key: value for key, value in dumped.items() if key in allowed_keys}

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.nebius.client import IncidentExplanationResponse, NebiusClient
from app.schemas.arena import AgentEvent, ArenaState, AttackTrackerState, Incident, MarketFeatures, PriceLevel

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
nebius_client = NebiusClient()


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
    return nebius_client.explain_incident(incident, replay_payload=replay_payload)


def build_compact_replay_payload(incident: Incident, state: ArenaState) -> dict[str, Any]:
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
        "features": _compact_features(state.features),
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

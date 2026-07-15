from fastapi import APIRouter, HTTPException, Request

from app.schemas.arena import AttackTrackerState
from app.scenarios.catalog import ScenarioType

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.post("/spoofing-like", response_model=AttackTrackerState)
async def start_spoofing_like(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, ScenarioType.SPOOFING_LIKE_WALL)


@router.post("/layering-like", response_model=AttackTrackerState)
async def start_layering_like(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, ScenarioType.LAYERING_LIKE)


@router.post("/quote-stuffing", response_model=AttackTrackerState)
async def start_quote_stuffing(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, ScenarioType.QUOTE_STUFFING)


@router.post("/liquidity-evaporation", response_model=AttackTrackerState)
async def start_liquidity_evaporation(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, ScenarioType.LIQUIDITY_EVAPORATION)


async def _start_scenario(request: Request, scenario_name: ScenarioType) -> AttackTrackerState:
    try:
        return await request.app.state.simulation.start_scenario(scenario_name.value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

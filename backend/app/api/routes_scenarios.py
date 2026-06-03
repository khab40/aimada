from fastapi import APIRouter, HTTPException, Request

from app.schemas.arena import AttackTrackerState

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.post("/spoofing-like", response_model=AttackTrackerState)
async def start_spoofing_like(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, "spoofing-like")


@router.post("/layering-like", response_model=AttackTrackerState)
async def start_layering_like(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, "layering-like")


@router.post("/quote-stuffing", response_model=AttackTrackerState)
async def start_quote_stuffing(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, "quote-stuffing")


@router.post("/liquidity-evaporation", response_model=AttackTrackerState)
async def start_liquidity_evaporation(request: Request) -> AttackTrackerState:
    return await _start_scenario(request, "liquidity-evaporation")


async def _start_scenario(request: Request, scenario_name: str) -> AttackTrackerState:
    try:
        return await request.app.state.simulation.start_scenario(scenario_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

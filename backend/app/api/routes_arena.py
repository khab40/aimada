from fastapi import APIRouter, Query, Request

from app.schemas.arena import ArenaState, ExchangeEventReplay

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/state", response_model=ArenaState)
async def get_arena_state(request: Request) -> ArenaState:
    return await request.app.state.simulation.get_state()


@router.get("/exchange-events", response_model=ExchangeEventReplay)
async def get_exchange_events(
    request: Request,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> ExchangeEventReplay:
    return await request.app.state.simulation.replay_exchange_events(
        after_sequence=after_sequence,
        limit=limit,
    )

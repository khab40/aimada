from fastapi import APIRouter, Request

from app.schemas.arena import ArenaState

router = APIRouter(prefix="/api/arena", tags=["arena"])


@router.get("/state", response_model=ArenaState)
async def get_arena_state(request: Request) -> ArenaState:
    return await request.app.state.simulation.get_state()

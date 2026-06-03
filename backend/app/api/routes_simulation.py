from fastapi import APIRouter, Request

from app.schemas.arena import ArenaState

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.post("/start", response_model=ArenaState)
async def start_simulation(request: Request) -> ArenaState:
    return await request.app.state.simulation.start()


@router.post("/pause", response_model=ArenaState)
async def pause_simulation(request: Request) -> ArenaState:
    return await request.app.state.simulation.pause()


@router.post("/reset", response_model=ArenaState)
async def reset_simulation(request: Request) -> ArenaState:
    return await request.app.state.simulation.reset()

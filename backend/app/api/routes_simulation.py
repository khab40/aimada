from fastapi import APIRouter, Request

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/start")
async def start_simulation(request: Request) -> dict[str, object]:
    state = await request.app.state.runtime.start()
    return {"running": True, "state": state}


@router.post("/stop")
async def stop_simulation(request: Request) -> dict[str, object]:
    state = await request.app.state.runtime.pause()
    return {"running": False, "state": state}


@router.post("/pause")
async def pause_simulation(request: Request) -> dict[str, object]:
    state = await request.app.state.runtime.pause()
    return {"running": False, "state": state}


@router.post("/reset")
async def reset_simulation(request: Request) -> dict[str, object]:
    state = await request.app.state.runtime.reset()
    return {"running": False, "state": state}


@router.post("/scenario/{scenario_name}")
async def launch_scenario(scenario_name: str, request: Request) -> dict[str, object]:
    return {"accepted": False, "error": f"scenario runtime is implemented in Phase 2: {scenario_name}"}


@router.get("/snapshot")
async def snapshot(request: Request) -> dict[str, object]:
    state = await request.app.state.runtime.snapshot()
    return {"running": state["running"], "state": state}

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_benchmark import router as benchmark_router
from app.api.routes_explain import router as explain_router
from app.api.routes_health import router as health_router
from app.api.routes_simulation import router as simulation_router
from app.arena.live_runtime import LiveArenaRuntime
from app.websocket.broadcaster import Broadcaster

app = FastAPI(title="Nebius Market Abuse Arena")
app.state.broadcaster = Broadcaster()
app.state.runtime = LiveArenaRuntime(app.state.broadcaster)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(simulation_router)
app.include_router(explain_router)
app.include_router(benchmark_router)


@app.on_event("shutdown")
async def shutdown_runtime() -> None:
    await app.state.runtime.stop()


@app.websocket("/ws/arena")
async def arena_websocket(websocket: WebSocket) -> None:
    state = await app.state.runtime.snapshot()
    await app.state.broadcaster.connect(websocket, {"type": "arena_state", "payload": state})

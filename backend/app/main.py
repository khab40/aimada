from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.routes_arena import router as arena_router
from app.api.routes_auth import router as auth_router
from app.api.routes_experiments import router as experiments_router
from app.api.routes_health import router as health_router
from app.api.routes_incidents import router as incidents_router
from app.api.routes_nebius import nebius_client, router as nebius_router
from app.api.routes_red_team import router as red_team_router
from app.api.routes_scenarios import router as scenarios_router
from app.api.routes_simulation import router as simulation_router
from app.arena.engine import SimulationEngine
from app.auth.store import AuthStore
from app.config import get_settings
from app.nebius.evidence_archive import configure_default_evidence_archive
from app.storage.local_store import LocalStore
from app.storage.retention import cleanup_output_data
from app.websocket.manager import WebSocketManager
from app.websocket.routes import router as websocket_router

app = FastAPI(title="LOB Arena")
settings = get_settings()
app.state.store = LocalStore(settings.arena_output_dir)
app.state.nebius_evidence = (
    configure_default_evidence_archive(app.state.store, settings)
    if settings.nebius_evidence_archive_enabled
    else None
)
app.state.retention_cleanup = cleanup_output_data(app.state.store.output_dir, settings.arena_data_retention_days)
app.state.auth_store = AuthStore(settings.arena_output_dir / "auth" / "auth.db")
app.state.settings = settings
app.state.simulation = SimulationEngine(
    store=app.state.store,
    normal_agent_count=settings.arena_agent_count,
    agent_decision_timeout_seconds=settings.arena_agent_decision_timeout_seconds,
    remote_agent_urls=settings.remote_agent_url_list,
    remote_agent_timeout_seconds=settings.arena_remote_agent_timeout_seconds,
    baseline_liquidity_levels=settings.arena_baseline_liquidity_levels,
    baseline_liquidity_base_size=settings.arena_baseline_liquidity_base_size,
    baseline_liquidity_tick_size=settings.arena_baseline_liquidity_tick_size,
    baseline_liquidity_reference_price=settings.arena_baseline_liquidity_reference_price,
    max_agent_quote_size=settings.arena_max_agent_quote_size,
    tick_history_interval=settings.arena_tick_history_interval,
    persist_all_events=settings.arena_persist_all_events,
)
app.state.websocket_manager = WebSocketManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(arena_router)
app.include_router(simulation_router)
app.include_router(experiments_router)
app.include_router(scenarios_router)
app.include_router(incidents_router)
app.include_router(nebius_router)
app.include_router(red_team_router)
app.include_router(websocket_router)


@app.get("/api/status", tags=["status"])
def api_status() -> dict[str, object]:
    return {
        "service": "lob-arena-backend",
        "status": "ok",
        "nebius": nebius_client.integration_status().model_dump(mode="json"),
    }


@app.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> PlainTextResponse:
    state = await request.app.state.simulation.get_state()
    incidents = await request.app.state.simulation.list_incidents()
    websocket_clients = request.app.state.websocket_manager.client_count
    lines = [
        "# HELP arena_tick Current simulation tick.",
        "# TYPE arena_tick gauge",
        f"arena_tick {state.tick}",
        "# HELP arena_running Whether the simulation loop is running.",
        "# TYPE arena_running gauge",
        f"arena_running {1 if state.running else 0}",
        "# HELP arena_incidents_total Number of in-memory incidents.",
        "# TYPE arena_incidents_total gauge",
        f"arena_incidents_total {len(incidents)}",
        "# HELP arena_websocket_clients Current websocket client count.",
        "# TYPE arena_websocket_clients gauge",
        f"arena_websocket_clients {websocket_clients}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.on_event("shutdown")
async def shutdown_simulation() -> None:
    await app.state.simulation.stop()

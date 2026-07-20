import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.agents.runtime import AgentManager, MarketSnapshot, build_heavy_agents, build_prefixed_normal_agents
from app.metrics import PrometheusTextRegistry, Timer
from langgraph_agents import build_langgraph_agents


class DecideRequest(BaseModel):
    snapshot: dict[str, Any]


class DecideResponse(BaseModel):
    runner_id: str
    agent_ids: list[str]
    intents: list[dict[str, Any]] = Field(default_factory=list)


def _env_int(name: str, default: int, *, minimum: int, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw is not None and raw.strip() else default
    except ValueError:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


REQUESTED_AGENT_COUNT = _env_int("AGENT_RUNNER_AGENT_COUNT", 24, minimum=0)
REQUESTED_HEAVY_AGENT_COUNT = _env_int("AGENT_RUNNER_HEAVY_AGENT_COUNT", 0, minimum=0)
REQUESTED_HEAVY_AGENT_WORKERS = _env_int("AGENT_RUNNER_HEAVY_AGENT_WORKERS", 1, minimum=1)
REQUESTED_LANGGRAPH_AGENT_COUNT = _env_int("AGENT_RUNNER_LANGGRAPH_AGENT_COUNT", 0, minimum=0)
MAX_AGENT_COUNT = _env_int("AGENT_RUNNER_MAX_AGENT_COUNT", 48, minimum=0)
MAX_HEAVY_AGENT_COUNT = _env_int("AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT", 2, minimum=0)
MAX_HEAVY_AGENT_WORKERS = _env_int("AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS", 1, minimum=1)
MAX_LANGGRAPH_AGENT_COUNT = _env_int("AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT", 4, minimum=0)
AGENT_COUNT = min(REQUESTED_AGENT_COUNT, MAX_AGENT_COUNT)
HEAVY_AGENT_COUNT = min(REQUESTED_HEAVY_AGENT_COUNT, MAX_HEAVY_AGENT_COUNT)
HEAVY_AGENT_COMPLEXITY = _env_int("AGENT_RUNNER_HEAVY_AGENT_COMPLEXITY", 20000, minimum=100, maximum=50000)
HEAVY_AGENT_WORKERS = min(REQUESTED_HEAVY_AGENT_WORKERS, MAX_HEAVY_AGENT_WORKERS)
LANGGRAPH_AGENT_COUNT = min(REQUESTED_LANGGRAPH_AGENT_COUNT, MAX_LANGGRAPH_AGENT_COUNT)
LANGGRAPH_STRATEGY = os.getenv("AGENT_RUNNER_LANGGRAPH_STRATEGY", "liquidity_rebalancer")
AGENT_PREFIX = os.getenv("AGENT_RUNNER_AGENT_ID_PREFIX", "REMOTE")
RUNNER_ID = os.getenv("AGENT_RUNNER_ID", AGENT_PREFIX.lower())
DECISION_TIMEOUT_SECONDS = float(os.getenv("AGENT_RUNNER_DECISION_TIMEOUT_SECONDS", "0.05"))

heavy_executor = ProcessPoolExecutor(max_workers=max(1, HEAVY_AGENT_WORKERS)) if HEAVY_AGENT_COUNT > 0 else None
manager = AgentManager(
    [
        *build_prefixed_normal_agents(AGENT_COUNT, AGENT_PREFIX),
        *build_heavy_agents(
            HEAVY_AGENT_COUNT,
            AGENT_PREFIX,
            complexity=HEAVY_AGENT_COMPLEXITY,
            executor=heavy_executor,
        ),
        *build_langgraph_agents(
            LANGGRAPH_AGENT_COUNT,
            AGENT_PREFIX,
            strategy=LANGGRAPH_STRATEGY,
        ),
    ],
    decision_timeout_seconds=DECISION_TIMEOUT_SECONDS,
)
app = FastAPI(title="LOB Arena Agent Runner")
metrics_registry = PrometheusTextRegistry()
metrics_registry.counter("agent_runner_decide_requests_total", "Agent runner /decide requests.", ("runner_id", "outcome"))
metrics_registry.histogram(
    "agent_runner_decide_duration_seconds",
    "Agent runner /decide request latency.",
    ("runner_id", "outcome"),
)
metrics_registry.histogram(
    "agent_runner_intents_returned",
    "Agent intents returned per /decide request.",
    ("runner_id",),
    buckets=(0, 1, 5, 10, 25, 50, 100, 250),
)
metrics_registry.gauge("agent_runner_agents", "Configured agent count by type.", ("runner_id", "agent_type"))
metrics_registry.gauge("agent_runner_up", "Agent runner process health.", ("runner_id",))
metrics_registry.gauge("agent_runner_uptime_seconds", "Agent runner uptime.", ("runner_id",))
metrics_registry.set("agent_runner_agents", AGENT_COUNT, runner_id=RUNNER_ID, agent_type="normal")
metrics_registry.set("agent_runner_agents", HEAVY_AGENT_COUNT, runner_id=RUNNER_ID, agent_type="heavy")
metrics_registry.set("agent_runner_agents", LANGGRAPH_AGENT_COUNT, runner_id=RUNNER_ID, agent_type="langgraph")
metrics_registry.set("agent_runner_up", 1, runner_id=RUNNER_ID)
STARTED_AT = time.time()


@app.on_event("shutdown")
def shutdown_executor() -> None:
    if heavy_executor is not None:
        heavy_executor.shutdown(cancel_futures=True)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "runner_id": RUNNER_ID,
        "agent_count": len(manager.agent_ids),
        "normal_agent_count": AGENT_COUNT,
        "heavy_agent_count": HEAVY_AGENT_COUNT,
        "heavy_agent_workers": HEAVY_AGENT_WORKERS if heavy_executor is not None else 0,
        "langgraph_agent_count": LANGGRAPH_AGENT_COUNT,
        "langgraph_strategy": LANGGRAPH_STRATEGY,
        "requested_agent_count": REQUESTED_AGENT_COUNT,
        "requested_heavy_agent_count": REQUESTED_HEAVY_AGENT_COUNT,
        "requested_langgraph_agent_count": REQUESTED_LANGGRAPH_AGENT_COUNT,
        "max_agent_count": MAX_AGENT_COUNT,
        "max_heavy_agent_count": MAX_HEAVY_AGENT_COUNT,
        "max_langgraph_agent_count": MAX_LANGGRAPH_AGENT_COUNT,
    }


@app.get("/agents")
def agents() -> dict[str, object]:
    return {"runner_id": RUNNER_ID, "agent_ids": manager.agent_ids}


@app.get("/metrics", include_in_schema=False)
def metrics() -> PlainTextResponse:
    uptime = time.time() - STARTED_AT
    metrics_registry.set("agent_runner_uptime_seconds", uptime, runner_id=RUNNER_ID)
    return PlainTextResponse(metrics_registry.render() + "\n", media_type="text/plain; version=0.0.4")


@app.post("/decide", response_model=DecideResponse)
async def decide(payload: DecideRequest) -> DecideResponse:
    timer = Timer()
    outcome = "completed"
    try:
        snapshot = MarketSnapshot(**payload.snapshot)
        intents = await manager.collect_intents(snapshot)
        metrics_registry.observe("agent_runner_intents_returned", len(intents), runner_id=RUNNER_ID)
        return DecideResponse(
            runner_id=RUNNER_ID,
            agent_ids=manager.agent_ids,
            intents=[asdict(intent) for intent in intents],
        )
    except Exception:
        outcome = "error"
        raise
    finally:
        metrics_registry.inc("agent_runner_decide_requests_total", runner_id=RUNNER_ID, outcome=outcome)
        metrics_registry.observe("agent_runner_decide_duration_seconds", timer.elapsed(), runner_id=RUNNER_ID, outcome=outcome)

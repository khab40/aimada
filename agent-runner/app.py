import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agents.runtime import AgentManager, MarketSnapshot, build_heavy_agents, build_prefixed_normal_agents
from langgraph_agents import build_langgraph_agents


class DecideRequest(BaseModel):
    snapshot: dict[str, Any]


class DecideResponse(BaseModel):
    runner_id: str
    agent_ids: list[str]
    intents: list[dict[str, Any]] = Field(default_factory=list)


AGENT_COUNT = int(os.getenv("AGENT_RUNNER_AGENT_COUNT", "200"))
HEAVY_AGENT_COUNT = int(os.getenv("AGENT_RUNNER_HEAVY_AGENT_COUNT", "8"))
HEAVY_AGENT_COMPLEXITY = int(os.getenv("AGENT_RUNNER_HEAVY_AGENT_COMPLEXITY", "20000"))
HEAVY_AGENT_WORKERS = int(os.getenv("AGENT_RUNNER_HEAVY_AGENT_WORKERS", "2"))
LANGGRAPH_AGENT_COUNT = int(os.getenv("AGENT_RUNNER_LANGGRAPH_AGENT_COUNT", "16"))
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
app = FastAPI(title="AI Market Abuse Detection Arena Agent Runner")


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
    }


@app.get("/agents")
def agents() -> dict[str, object]:
    return {"runner_id": RUNNER_ID, "agent_ids": manager.agent_ids}


@app.post("/decide", response_model=DecideResponse)
async def decide(payload: DecideRequest) -> DecideResponse:
    snapshot = MarketSnapshot(**payload.snapshot)
    intents = await manager.collect_intents(snapshot)
    return DecideResponse(
        runner_id=RUNNER_ID,
        agent_ids=manager.agent_ids,
        intents=[asdict(intent) for intent in intents],
    )

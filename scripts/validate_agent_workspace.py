from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
importlib.import_module("app.agents.runtime")
sys.path.insert(0, str(ROOT / "agent-runner"))

os.environ.update(
    AGENT_RUNNER_AGENT_COUNT="2",
    AGENT_RUNNER_MAX_AGENT_COUNT="2",
    AGENT_RUNNER_HEAVY_AGENT_COUNT="0",
    AGENT_RUNNER_LANGGRAPH_AGENT_COUNT="1",
    AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT="1",
)


def _load_runner():
    path = ROOT / "agent-runner" / "app.py"
    spec = importlib.util.spec_from_file_location("aimada_agent_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load agent workspace: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _validate_decision(runner) -> None:
    request = runner.DecideRequest(
        snapshot={
            "tick": 7,
            "bids": [{"price": 99.0, "quantity": 2.0}],
            "asks": [{"price": 101.0, "quantity": 1.5}],
            "best_bid": 99.0,
            "best_ask": 101.0,
            "mid": 100.0,
            "spread": 2.0,
        }
    )
    response = await runner.decide(request)
    if not response.intents:
        raise ValueError("agent workspace returned no intents")
    if any(intent.get("tick") != 7 for intent in response.intents):
        raise ValueError("agent workspace returned an intent for the wrong tick")


def main() -> None:
    runner = _load_runner()
    health = runner.health()
    if health.get("status") != "ok":
        raise ValueError(f"agent workspace health failed: {health}")
    if health.get("agent_count") != 3:
        raise ValueError(f"unexpected agent workspace count: {health}")
    asyncio.run(_validate_decision(runner))
    print("Agent workspace import, health, and deterministic decision checks passed.")


if __name__ == "__main__":
    main()

import asyncio
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.runtime import AgentIntent, MarketSnapshot, RuntimeAgent


class LangGraphAgentState(TypedDict):
    snapshot: dict[str, Any]
    agent_id: str
    offset: int
    strategy: str
    intents: list[dict[str, Any]]


@dataclass(frozen=True)
class LangGraphAgentConfig:
    agent_id: str
    offset: int = 0
    strategy: str = "liquidity_rebalancer"


class GenericLangGraphAgent:
    def __init__(self, config: LangGraphAgentConfig) -> None:
        self.agent_id = config.agent_id
        self.offset = config.offset
        self.strategy = config.strategy
        self.graph = _build_agent_graph()

    async def decide(self, snapshot: MarketSnapshot) -> list[AgentIntent]:
        state: LangGraphAgentState = {
            "snapshot": {
                "tick": snapshot.tick,
                "bids": snapshot.bids,
                "asks": snapshot.asks,
                "best_bid": snapshot.best_bid,
                "best_ask": snapshot.best_ask,
                "mid": snapshot.mid,
                "spread": snapshot.spread,
            },
            "agent_id": self.agent_id,
            "offset": self.offset,
            "strategy": self.strategy,
            "intents": [],
        }
        result = await asyncio.to_thread(self.graph.invoke, state)
        return [AgentIntent(**item) for item in result.get("intents", [])]


def build_langgraph_agents(count: int, prefix: str, *, strategy: str = "liquidity_rebalancer") -> list[RuntimeAgent]:
    normalized = prefix.strip().upper() or "LG"
    return [
        GenericLangGraphAgent(
            LangGraphAgentConfig(
                agent_id=f"{normalized}_LANGGRAPH_{index:03d}",
                offset=index,
                strategy=strategy,
            )
        )
        for index in range(1, max(0, count) + 1)
    ]


def _build_agent_graph():
    builder = StateGraph(LangGraphAgentState)
    builder.add_node("observe", _observe_node)
    builder.add_node("decide", _decide_node)
    builder.add_edge(START, "observe")
    builder.add_edge("observe", "decide")
    builder.add_edge("decide", END)
    return builder.compile()


def _observe_node(state: LangGraphAgentState) -> dict[str, Any]:
    snapshot = state["snapshot"]
    bids = snapshot.get("bids") or []
    asks = snapshot.get("asks") or []
    bid_depth = sum(float(level.get("quantity", 0.0)) for level in bids[:5])
    ask_depth = sum(float(level.get("quantity", 0.0)) for level in asks[:5])
    total_depth = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total_depth if total_depth else 0.0
    return {
        "snapshot": {
            **snapshot,
            "bid_depth_top5": bid_depth,
            "ask_depth_top5": ask_depth,
            "imbalance": imbalance,
        }
    }


def _decide_node(state: LangGraphAgentState) -> dict[str, Any]:
    snapshot = state["snapshot"]
    bids = snapshot.get("bids") or []
    asks = snapshot.get("asks") or []
    if not bids or not asks:
        return {"intents": []}

    tick = int(snapshot["tick"])
    offset = int(state["offset"])
    agent_id = state["agent_id"]
    strategy = state["strategy"]
    imbalance = float(snapshot.get("imbalance", 0.0))

    if strategy == "liquidity_rebalancer":
        side = "bid" if imbalance < 0 else "ask"
    elif strategy == "contrarian_depth":
        side = "ask" if (tick + offset) % 2 else "bid"
    else:
        side = "bid" if (tick + offset + len(agent_id)) % 2 else "ask"

    levels = bids if side == "bid" else asks
    level = levels[(tick + offset) % min(len(levels), 5)]
    price = float(level["price"])
    quantity = 0.35 + ((tick + offset) % 6) * 0.05
    if side == "ask" and imbalance > 0.15:
        quantity += 0.15
    if side == "bid" and imbalance < -0.15:
        quantity += 0.15

    return {
        "intents": [
            {
                "tick": tick,
                "agent_id": agent_id,
                "kind": "set_level",
                "sequence": 0,
                "latency_bucket": 20 + (offset % 17),
                "event_type": "normal",
                "side": side,
                "price": price,
                "quantity": round(quantity, 3),
                "message": f"langgraph {strategy} decision",
            }
        ]
    }

from app.agents.base import Agent
from app.agents.liquidity_taker import LiquidityTakerAgent
from app.agents.market_maker import MarketMakerAgent
from app.agents.noise_trader import NoiseTraderAgent
from app.arena.clock import SimulationClock
from app.detectors.aggregate_score import aggregate_detector_scores
from app.exchange.event_log import EventLog
from app.exchange.matching_engine import MatchingEngine


class ArenaEngine:
    def __init__(self, agents: list[Agent] | None = None) -> None:
        self.clock = SimulationClock()
        self.matching_engine = MatchingEngine()
        self.event_log = EventLog()
        self.agents = agents or [
            MarketMakerAgent("MM_01"),
            NoiseTraderAgent("NOISE_01"),
            LiquidityTakerAgent("TAKER_01"),
        ]

    def step(self) -> dict[str, object]:
        timestamp = self.clock.step()
        events: list[dict[str, object]] = []
        for agent in self.agents:
            for order in agent.act(timestamp):
                events.extend(self.matching_engine.process_event(order))
        for event in events:
            self.event_log.append(event)
        detector_result = aggregate_detector_scores(events)
        book = self.matching_engine.snapshot()
        return {
            "tick": timestamp,
            "running": True,
            "events": events,
            "detectors": detector_result,
            "book": book,
            "best_bid": book["best_bid"],
            "best_ask": book["best_ask"],
            "mid": book["mid"],
            "spread": book["spread"],
            "active_agents": [agent.agent_id for agent in self.agents],
        }

    def snapshot(self, running: bool = False) -> dict[str, object]:
        book = self.matching_engine.snapshot()
        return {
            "tick": self.clock.tick,
            "running": running,
            "events": self.event_log.tail(20),
            "detectors": aggregate_detector_scores([]),
            "book": book,
            "best_bid": book["best_bid"],
            "best_ask": book["best_ask"],
            "mid": book["mid"],
            "spread": book["spread"],
            "active_agents": [agent.agent_id for agent in self.agents],
        }

from app.agents.base import Agent
from app.exchange.schemas import Order


class MarketMakerAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        drift = (timestamp % 10 - 5) * 0.01
        mid = 100.0 + drift
        return [
            Order(f"{self.agent_id}-{timestamp}-bid", self.agent_id, "buy", 24, round(mid - 0.05, 2), timestamp=timestamp),
            Order(f"{self.agent_id}-{timestamp}-ask", self.agent_id, "sell", 24, round(mid + 0.05, 2), timestamp=timestamp),
        ]


MarketMaker = MarketMakerAgent

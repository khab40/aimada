from app.agents.base import Agent
from app.exchange.schemas import Order


class QuoteStuffingLikeAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        return [
            Order(f"{self.agent_id}-{timestamp}-{index}", self.agent_id, "buy" if index % 2 else "sell", 1, 100.0, timestamp=timestamp)
            for index in range(30)
        ]

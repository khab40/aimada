from app.agents.base import Agent
from app.exchange.schemas import Order


class LayeringLikeAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        return [
            Order(f"{self.agent_id}-{timestamp}-{level}", self.agent_id, "sell", 120, 101.0 + level * 0.1, timestamp=timestamp)
            for level in range(3)
        ]

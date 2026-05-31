from app.agents.base import Agent
from app.exchange.schemas import Order


class SpoofingLikeAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        order_id = f"{self.agent_id}-spoof-{timestamp}"
        if timestamp % 3 == 0:
            return [Order(order_id, self.agent_id, "buy", 500, 98.0, order_type="cancel", timestamp=timestamp)]
        return [Order(order_id, self.agent_id, "buy", 500, 98.0, timestamp=timestamp)]

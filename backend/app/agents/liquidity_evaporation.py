from app.agents.base import Agent
from app.exchange.schemas import Order


class LiquidityEvaporationAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        return [Order(f"{self.agent_id}-cancel-{timestamp}-{index}", self.agent_id, "sell", 1, order_type="cancel", timestamp=timestamp) for index in range(10)]

from app.agents.base import Agent
from app.exchange.schemas import Order


class PanicSelloffAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        return [Order(f"{self.agent_id}-{timestamp}", self.agent_id, "sell", 50, order_type="market", timestamp=timestamp)]

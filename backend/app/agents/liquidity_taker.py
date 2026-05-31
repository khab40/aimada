from app.agents.base import Agent
from app.exchange.schemas import Order


class LiquidityTakerAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        if timestamp % 4:
            return []
        side = "buy" if timestamp % 8 == 0 else "sell"
        return [Order(f"{self.agent_id}-{timestamp}", self.agent_id, side, 8, order_type="market", timestamp=timestamp)]


LiquidityTaker = LiquidityTakerAgent

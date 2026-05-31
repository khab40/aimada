from app.agents.base import Agent
from app.exchange.schemas import Order


class NoiseTraderAgent(Agent):
    def act(self, timestamp: int) -> list[Order]:
        side = "buy" if timestamp % 2 else "sell"
        price = 100.0 - (timestamp % 3) * 0.1 if side == "buy" else 100.0 + (timestamp % 3) * 0.1
        return [Order(f"{self.agent_id}-{timestamp}", self.agent_id, side, 1, price, timestamp=timestamp)]


NoiseTrader = NoiseTraderAgent

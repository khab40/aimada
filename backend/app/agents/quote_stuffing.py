from app.agents.base import Agent
from app.exchange.schemas import Order


class QuoteStuffingAgent(Agent):
    scenario_family = "quote_stuffing"
    scenario_name = "quote_stuffing"

    def __init__(self, agent_id: str, scenario_id: str | None = None) -> None:
        super().__init__(agent_id)
        self.scenario_id = scenario_id or f"{self.scenario_family}-{agent_id}"
        self.age = 0
        self.previous_order_ids: list[str] = []

    def act(self, timestamp: int) -> list[Order]:
        self.age += 1
        if self.age > 6:
            return []

        cancels = [
            Order(
                order_id,
                self.agent_id,
                "buy",
                1,
                order_type="cancel",
                timestamp=timestamp,
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                scenario_family=self.scenario_family,
            )
            for order_id in self.previous_order_ids
        ]
        new_orders = [
            Order(
                f"{self.scenario_id}-{timestamp}-{index}",
                self.agent_id,
                "buy" if index % 2 else "sell",
                1,
                99.5 if index % 2 else 100.5,
                timestamp=timestamp,
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                scenario_family=self.scenario_family,
            )
            for index in range(12)
        ]
        self.previous_order_ids = [order.order_id for order in new_orders]
        return cancels + new_orders

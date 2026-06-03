from app.agents.base import Agent
from app.exchange.schemas import Order


class LayeringLikeAgent(Agent):
    scenario_family = "layering_like"
    scenario_name = "layering-like"

    def __init__(self, agent_id: str, scenario_id: str | None = None) -> None:
        super().__init__(agent_id)
        self.scenario_id = scenario_id or f"{self.scenario_family}-{agent_id}"
        self.age = 0
        self.layer_order_ids = [f"{self.scenario_id}-layer-{level}" for level in range(4)]

    def act(self, timestamp: int) -> list[Order]:
        self.age += 1
        if self.age == 1:
            return [
                Order(
                    self.layer_order_ids[level],
                    self.agent_id,
                    "sell",
                    120,
                    100.25 + level * 0.05,
                    timestamp=timestamp,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
                for level in range(4)
            ]
        if self.age == 5:
            return [
                Order(
                    order_id,
                    self.agent_id,
                    "sell",
                    120,
                    order_type="cancel",
                    timestamp=timestamp,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
                for order_id in self.layer_order_ids
            ]
        return []

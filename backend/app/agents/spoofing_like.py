from app.agents.base import Agent
from app.exchange.schemas import Order


class SpoofingLikeAgent(Agent):
    scenario_family = "spoofing_like_wall"
    scenario_name = "spoofing_like_wall"

    def __init__(self, agent_id: str, scenario_id: str | None = None) -> None:
        super().__init__(agent_id)
        self.scenario_id = scenario_id or f"{self.scenario_family}-{agent_id}"
        self.age = 0
        self.wall_order_id = f"{self.scenario_id}-wall"

    def act(self, timestamp: int) -> list[Order]:
        self.age += 1
        if self.age == 1:
            return [
                Order(
                    self.wall_order_id,
                    self.agent_id,
                    "sell",
                    480,
                    100.35,
                    timestamp=timestamp,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
            ]
        if self.age == 4:
            return [
                Order(
                    self.wall_order_id,
                    self.agent_id,
                    "sell",
                    480,
                    order_type="cancel",
                    timestamp=timestamp,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
            ]
        return []

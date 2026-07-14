from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage
from app.scenarios.base import ScenarioBase


class SpoofingLikeScenario(ScenarioBase):
    scenario_name = "spoofing-like"
    scenario_family = "spoofing_like"
    agent_id = "ABUSER_01"

    def __init__(self, scenario_id: str, start_tick: int, seed: int = 0) -> None:
        super().__init__(scenario_id, start_tick, seed)
        self.wall_price: float | None = None
        self.wall_order_id = f"{scenario_id}-wall"

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        if stage == AttackStage.WALL_PLACED:
            best_ask = book.best_ask()
            if best_ask is None:
                return []
            self.wall_price = best_ask + 2.0
            book.update_agent_level(
                "ask",
                self.wall_price,
                48.0,
                agent_id=self.agent_id,
                owner="abuser",
                order_id=self.wall_order_id,
                timestamp=tick,
                scenario_id=self.scenario_id,
                scenario_name=self.scenario_name,
                scenario_family=self.scenario_family,
            )
            return [
                self._event(
                    tick,
                    "large ask wall placed away from mid",
                    stage=stage,
                    side="sell",
                    price=self.wall_price,
                    quantity=48.0,
                    order_id=self.wall_order_id,
                )
            ]

        if stage == AttackStage.PRESSURE_PHASE:
            if self.wall_price is not None:
                book.update_agent_level(
                    "ask",
                    self.wall_price,
                    52.0,
                    agent_id=self.agent_id,
                    owner="abuser",
                    order_id=self.wall_order_id,
                    timestamp=tick,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
            return [
                self._event(
                    tick,
                    "visible wall replenishment maintained",
                    stage=stage,
                    side="sell",
                    price=self.wall_price,
                    quantity=52.0,
                    order_id=self.wall_order_id,
                )
            ]

        if stage == AttackStage.WALL_CANCELLED:
            if self.wall_price is not None:
                book.cancel_order(self.wall_order_id)
            return [
                self._event(
                    tick,
                    "ask wall cancelled before execution",
                    stage=stage,
                    side="sell",
                    price=self.wall_price,
                    order_id=self.wall_order_id,
                )
            ]

        if stage == AttackStage.INCIDENT_CONFIRMED:
            return [self._event(tick, "spoofing-like wall incident confirmed", stage=stage, confidence=0.91)]

        return super().on_stage_enter(book, tick, stage)

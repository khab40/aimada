from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage
from app.scenarios.base import ScenarioBase


class LayeringLikeScenario(ScenarioBase):
    scenario_name = "layering_like"
    scenario_family = "layering_like"
    agent_id = "ABUSER_02"

    def __init__(self, scenario_id: str, start_tick: int, seed: int = 0) -> None:
        super().__init__(scenario_id, start_tick, seed)
        self.layer_prices: list[float] = []
        self.layer_order_ids = [f"{scenario_id}-layer-{index}" for index in range(3)]
        self.book_side = "ask" if seed % 2 == 0 else "bid"
        self.event_side = "sell" if self.book_side == "ask" else "buy"

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        if stage == AttackStage.WALL_PLACED:
            touch = book.best_ask() if self.book_side == "ask" else book.best_bid()
            if touch is None:
                return []
            direction = 1.0 if self.book_side == "ask" else -1.0
            self.layer_prices = [touch + direction * offset for offset in (2.0, 3.0, 4.0)]
            for index, price in enumerate(self.layer_prices):
                book.update_agent_level(
                    self.book_side,
                    price,
                    22.0 + index * 4,
                    agent_id=self.agent_id,
                    owner="abuser",
                    order_id=self.layer_order_ids[index],
                    timestamp=tick,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
            return [
                self._event(
                    tick,
                    f"same-side {self.book_side} layer placed",
                    stage=stage,
                    side=self.event_side,
                    price=price,
                    quantity=22.0 + index * 4,
                    order_id=self.layer_order_ids[index],
                )
                for index, price in enumerate(self.layer_prices)
            ]

        if stage == AttackStage.PRESSURE_PHASE:
            for index, price in enumerate(self.layer_prices):
                book.update_agent_level(
                    self.book_side,
                    price,
                    26.0 + index * 4,
                    agent_id=self.agent_id,
                    owner="abuser",
                    order_id=self.layer_order_ids[index],
                    timestamp=tick,
                    scenario_id=self.scenario_id,
                    scenario_name=self.scenario_name,
                    scenario_family=self.scenario_family,
                )
            return [
                self._event(
                    tick,
                    f"layered {self.book_side} replenishment maintained",
                    stage=stage,
                    side=self.event_side,
                    price=price,
                    quantity=26.0 + index * 4,
                    order_id=self.layer_order_ids[index],
                )
                for index, price in enumerate(self.layer_prices)
            ]

        if stage == AttackStage.WALL_CANCELLED:
            for order_id in self.layer_order_ids:
                book.cancel_order(order_id)
            return [
                self._event(
                    tick,
                    f"layered {self.book_side} liquidity cancelled",
                    stage=stage,
                    side=self.event_side,
                    price=price,
                    order_id=self.layer_order_ids[index],
                )
                for index, price in enumerate(self.layer_prices)
            ]

        if stage == AttackStage.INCIDENT_CONFIRMED:
            return [self._event(tick, "layering-like pattern incident confirmed", stage=stage, confidence=0.86)]

        return super().on_stage_enter(book, tick, stage)

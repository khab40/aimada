from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage
from app.scenarios.base import ScenarioBase


class LayeringLikeScenario(ScenarioBase):
    scenario_name = "layering-like"
    scenario_family = "layering_like"
    agent_id = "ABUSER_02"

    def __init__(self, scenario_id: str, start_tick: int) -> None:
        super().__init__(scenario_id, start_tick)
        self.layer_prices: list[float] = []

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        if stage == AttackStage.WALL_PLACED:
            best_ask = book.best_ask()
            if best_ask is None:
                return []
            self.layer_prices = [best_ask + offset for offset in (2.0, 3.0, 4.0)]
            for index, price in enumerate(self.layer_prices):
                book.update_level("ask", price, 22.0 + index * 4, owner="abuser")
            return [self._event(tick, "same-side ask layers placed", stage=stage, quantity=3)]

        if stage == AttackStage.PRESSURE_PHASE:
            for index, price in enumerate(self.layer_prices):
                book.update_level("ask", price, 26.0 + index * 4, owner="abuser")
            return [self._event(tick, "layered ask pressure maintained", stage=stage)]

        if stage == AttackStage.WALL_CANCELLED:
            for price in self.layer_prices:
                book.remove_level("ask", price)
            return [self._event(tick, "layered ask liquidity cancelled", stage=stage)]

        if stage == AttackStage.INCIDENT_CONFIRMED:
            return [self._event(tick, "layering-like pattern incident confirmed", stage=stage, confidence=0.86)]

        return super().on_stage_enter(book, tick, stage)

from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage
from app.scenarios.base import ScenarioBase


class QuoteStuffingLikeScenario(ScenarioBase):
    scenario_name = "quote-stuffing"
    scenario_family = "quote_stuffing"
    agent_id = "ABUSER_03"

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        if stage == AttackStage.WALL_PLACED:
            return [self._event(tick, "quote stuffing burst armed", stage=stage)]
        if stage == AttackStage.PRESSURE_PHASE:
            return [self._event(tick, "high message-rate quote burst active", stage=stage, confidence=0.76)]
        if stage == AttackStage.WALL_CANCELLED:
            return [self._event(tick, "quote stuffing burst stopped", stage=stage)]
        if stage == AttackStage.INCIDENT_CONFIRMED:
            return [self._event(tick, "quote-stuffing-like incident confirmed", stage=stage, confidence=0.94)]
        return super().on_stage_enter(book, tick, stage)

    def on_tick(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        if self.current_stage != AttackStage.PRESSURE_PHASE:
            return []

        best_ask = book.best_ask()
        if best_ask is not None:
            for index in range(3):
                price = best_ask + 5.0 + index
                book.update_level("ask", price, 0.5 + index * 0.1, owner="abuser")
                book.remove_level("ask", price)

        return [
            self._event(
                tick,
                "rapid place/cancel quote update",
                stage=AttackStage.PRESSURE_PHASE,
                update_index=index,
            )
            for index in range(8)
        ]

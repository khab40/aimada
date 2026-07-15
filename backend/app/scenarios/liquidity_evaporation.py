from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage
from app.scenarios.base import ScenarioBase


class LiquidityEvaporationScenario(ScenarioBase):
    scenario_name = "liquidity_evaporation"
    scenario_family = "liquidity_evaporation"
    agent_id = "SHOCK_01"

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        if stage == AttackStage.WALL_PLACED:
            return [self._event(tick, "liquidity shock armed", stage=stage)]

        if stage == AttackStage.PRESSURE_PHASE:
            self._thin_top_of_book(book)
            return [self._event(tick, "top-of-book depth collapsed", stage=stage, confidence=0.73)]

        if stage == AttackStage.WALL_CANCELLED:
            self._widen_spread(book)
            return [self._event(tick, "spread widened after depth collapse", stage=stage)]

        if stage == AttackStage.INCIDENT_CONFIRMED:
            return [self._event(tick, "liquidity evaporation incident confirmed", stage=stage, confidence=0.88)]

        return super().on_stage_enter(book, tick, stage)

    def on_tick(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        if self.current_stage != AttackStage.PRESSURE_PHASE:
            return []
        self._thin_top_of_book(book)
        return [self._event(tick, "liquidity remains thin", stage=AttackStage.PRESSURE_PHASE)]

    def _thin_top_of_book(self, book: OrderBook) -> None:
        for side in ("bid", "ask"):
            levels = book.bids if side == "bid" else book.asks
            prices = sorted(levels, reverse=side == "bid")[:3]
            for price in prices:
                current = book._level_quantity(side, price)
                book.update_level(side, price, max(0.2, round(current * 0.35, 3)), owner="normal")

    def _widen_spread(self, book: OrderBook) -> None:
        best_bid = book.best_bid()
        best_ask = book.best_ask()
        if best_bid is not None:
            book.remove_level("bid", best_bid)
        if best_ask is not None:
            book.remove_level("ask", best_ask)

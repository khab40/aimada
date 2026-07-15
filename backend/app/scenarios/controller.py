from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackTrackerState
from app.scenarios.base import ScenarioBase
from app.scenarios.catalog import ScenarioType, parse_scenario_type
from app.scenarios.layering_like import LayeringLikeScenario
from app.scenarios.liquidity_evaporation import LiquidityEvaporationScenario
from app.scenarios.quote_stuffing import QuoteStuffingScenario
from app.scenarios.spoofing_like import SpoofingLikeScenario


class ScenarioController:
    def __init__(self) -> None:
        self.active: ScenarioBase | None = None
        self._counter = 0

    def start(
        self,
        scenario_name: str,
        tick: int,
        *,
        run_id: str = "RUN-000042",
        seed: int = 42,
    ) -> AttackTrackerState:
        scenario_class = self._scenario_class(scenario_name)
        self._counter += 1
        scenario_id = f"{scenario_class.scenario_family}-{self._counter:04d}"
        self.active = scenario_class(scenario_id=scenario_id, start_tick=tick + 1, seed=seed)
        return self.active.tracker_state(run_id=run_id, seed=seed)

    def advance(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        if self.active is None:
            return []
        return self.active.apply(book, tick)

    def tracker_state(self, *, run_id: str = "RUN-000042", seed: int = 42) -> AttackTrackerState | None:
        if self.active is None:
            return None
        return self.active.tracker_state(run_id=run_id, seed=seed)

    def reset(self) -> None:
        self.active = None

    def _scenario_class(self, scenario_name: str) -> type[ScenarioBase]:
        scenario_type = parse_scenario_type(scenario_name)
        scenarios: dict[ScenarioType, type[ScenarioBase]] = {
            ScenarioType.SPOOFING_LIKE_WALL: SpoofingLikeScenario,
            ScenarioType.LAYERING_LIKE: LayeringLikeScenario,
            ScenarioType.QUOTE_STUFFING: QuoteStuffingScenario,
            ScenarioType.LIQUIDITY_EVAPORATION: LiquidityEvaporationScenario,
        }
        return scenarios[scenario_type]

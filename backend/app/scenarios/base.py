import time
from dataclasses import dataclass

from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, AttackStage, AttackStageSnapshot, AttackTrackerState, ScenarioLabel


STAGE_SEQUENCE = [
    AttackStage.ARMED,
    AttackStage.WALL_PLACED,
    AttackStage.PRESSURE_PHASE,
    AttackStage.WALL_CANCELLED,
    AttackStage.INCIDENT_CONFIRMED,
    AttackStage.DONE,
]


STAGE_LABELS = {
    AttackStage.ARMED: "Armed",
    AttackStage.WALL_PLACED: "Wall Placed",
    AttackStage.PRESSURE_PHASE: "Pressure Phase",
    AttackStage.WALL_CANCELLED: "Wall Cancelled",
    AttackStage.INCIDENT_CONFIRMED: "Incident Confirmed",
    AttackStage.DONE: "Done",
}


@dataclass(frozen=True)
class StageRule:
    stage: AttackStage
    at_tick: int
    confidence: float


class ScenarioBase:
    scenario_name = "scenario"
    scenario_family = "scenario"
    agent_id = "ABUSER_00"
    stage_rules = [
        StageRule(AttackStage.ARMED, 0, 0.05),
        StageRule(AttackStage.WALL_PLACED, 1, 0.25),
        StageRule(AttackStage.PRESSURE_PHASE, 3, 0.55),
        StageRule(AttackStage.WALL_CANCELLED, 6, 0.72),
        StageRule(AttackStage.INCIDENT_CONFIRMED, 7, 0.9),
        StageRule(AttackStage.DONE, 9, 0.95),
    ]

    def __init__(self, scenario_id: str, start_tick: int) -> None:
        self.scenario_id = scenario_id
        self.start_tick = start_tick
        self.current_stage = AttackStage.ARMED
        self.stage_ticks: dict[AttackStage, int] = {AttackStage.ARMED: start_tick}
        self.stage_timestamps: dict[AttackStage, float] = {AttackStage.ARMED: self._now_ms()}
        self._applied_stages: set[AttackStage] = set()

    @property
    def done(self) -> bool:
        return self.current_stage == AttackStage.DONE

    def apply(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        previous_stage = self.current_stage
        self.current_stage = self._stage_for_tick(tick)
        if self.current_stage != previous_stage:
            self.stage_ticks.setdefault(self.current_stage, tick)
            self.stage_timestamps.setdefault(self.current_stage, self._now_ms())

        events = self._apply_stage_once(book, tick)
        events.extend(self.on_tick(book, tick))
        return events

    def label_record(self, *, run_id: str, seed: int) -> ScenarioLabel:
        final_rule = self.stage_rules[-1]
        return ScenarioLabel(
            label_id=f"LABEL-{self.scenario_id}",
            run_id=run_id,
            scenario_id=self.scenario_id,
            scenario_family=self.scenario_family,
            scenario_name=self.scenario_name,
            seed=seed,
            start_tick=self.start_tick,
            expected_end_tick=self.start_tick + final_rule.at_tick,
            actual_end_tick=self.stage_ticks.get(AttackStage.DONE),
            agent_ids=[self.agent_id],
            parameters={"scenario_name": self._label_scenario_name()},
        )

    def tracker_state(self, *, run_id: str = "RUN-000042", seed: int = 42) -> AttackTrackerState:
        return AttackTrackerState(
            scenario_id=self.scenario_id,
            scenario_name=self.scenario_name,
            scenario_family=self.scenario_family,
            agent_id=self.agent_id,
            current_stage=self.current_stage,
            start_tick=self.start_tick,
            stages=self._stage_snapshots(),
            status=self.current_stage,
            label=self.label_record(run_id=run_id, seed=seed),
        )

    def on_tick(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        return []

    def on_stage_enter(self, book: OrderBook, tick: int, stage: AttackStage) -> list[AgentEvent]:
        return [self._event(tick, f"{self.scenario_name} entered {stage.value}", stage=stage)]

    def _apply_stage_once(self, book: OrderBook, tick: int) -> list[AgentEvent]:
        if self.current_stage in self._applied_stages:
            return []
        self._applied_stages.add(self.current_stage)
        return self.on_stage_enter(book, tick, self.current_stage)

    def _stage_for_tick(self, tick: int) -> AttackStage:
        elapsed = max(0, tick - self.start_tick)
        stage = self.stage_rules[0].stage
        for rule in self.stage_rules:
            if elapsed >= rule.at_tick:
                stage = rule.stage
        return stage

    def _stage_snapshots(self) -> list[AttackStageSnapshot]:
        current_index = STAGE_SEQUENCE.index(self.current_stage)
        snapshots: list[AttackStageSnapshot] = []
        for index, stage in enumerate(STAGE_SEQUENCE):
            status = "completed" if index < current_index else "active" if index == current_index else "pending"
            rule = next(rule for rule in self.stage_rules if rule.stage == stage)
            snapshots.append(
                AttackStageSnapshot(
                    detector_confidence=rule.confidence if status != "pending" else None,
                    label=STAGE_LABELS[stage],
                    stage=stage,
                    status=status,
                    tick=self.stage_ticks.get(stage),
                    timestamp=self.stage_timestamps.get(stage),
                )
            )
        return snapshots

    def _event(self, tick: int, message: str, *, stage: AttackStage | None = None, **extra: object) -> AgentEvent:
        return AgentEvent(
            type="red_team",
            timestamp=self._now_ms(),
            agent_id=self.agent_id,
            scenario_id=self.scenario_id,
            scenario_name=self.scenario_name,
            scenario_family=self.scenario_family,
            tick=tick,
            stage=(stage or self.current_stage).value,
            message=message,
            **extra,
        )

    def _label_scenario_name(self) -> str:
        names = {
            "spoofing_like": "Spoofing-like Wall",
            "layering_like": "Layering-like",
            "quote_stuffing": "Quote Stuffing",
            "liquidity_evaporation": "Liquidity Evaporation",
        }
        return names.get(self.scenario_family, self.scenario_name)

    def _now_ms(self) -> float:
        return time.time() * 1000

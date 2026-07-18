import asyncio
from collections import deque
from contextlib import suppress

from app.agents.runtime import AgentIntent, MarketSnapshot, build_agent_manager
from app.arena.clock import SimulationClock
from app.arena.state import (
    arena_state_from_book,
    order_book_snapshot_from_dict,
)
from app.detectors.aggregate import AggregateDetectorEngine, flatten_evidence
from app.detectors.features import extract_features
from app.exchange.matching_engine import MatchingEngine
from app.exchange.event_log import EventLog
from app.exchange.order_book import OrderBook
from app.exchange.schemas import ExecuteOrderEvent, Order
from app.exchange.sources import SimulationEventSource
from app.schemas.arena import (
    AgentEvent,
    ArenaState,
    AttackTrackerState,
    DetectorScore,
    EvidenceItem,
    ExchangeEventRecord,
    ExchangeEventReplay,
    Incident,
)
from app.scenarios.controller import ScenarioController
from app.storage.history import append_exchange_event, append_history_artifact, append_tick_snapshot
from app.storage.local_store import LocalStore


class SimulationEngine:
    def __init__(
        self,
        tick_interval_seconds: float = 0.5,
        seed: int = 7,
        store: LocalStore | None = None,
        normal_agent_count: int = 3,
        agent_decision_timeout_seconds: float = 0.05,
        remote_agent_urls: list[str] | None = None,
        remote_agent_timeout_seconds: float | None = None,
        baseline_liquidity_levels: int = 12,
        baseline_liquidity_base_size: float = 1.5,
        baseline_liquidity_tick_size: float = 1.0,
        baseline_liquidity_reference_price: float = 68_125.0,
        max_agent_quote_size: float = 25.0,
        tick_history_interval: int = 1,
        persist_all_events: bool = True,
        exchange_snapshot_depth: int = 12,
        exchange_event_window: int = 100,
    ) -> None:
        self.tick_interval_seconds = tick_interval_seconds
        self.seed = seed
        self.run_id = f"RUN-{seed:06d}"
        self._exchange_stream_generation = 0
        self.exchange_stream_id = self._new_exchange_stream_id()
        self._persisted_exchange_sequence = 0
        self.clock = SimulationClock(tick_interval_ms=int(tick_interval_seconds * 1000))
        self.baseline_liquidity_levels = max(0, baseline_liquidity_levels)
        self.baseline_liquidity_base_size = max(0.0, baseline_liquidity_base_size)
        self.baseline_liquidity_tick_size = max(0.01, baseline_liquidity_tick_size)
        self.baseline_liquidity_reference_price = baseline_liquidity_reference_price
        self.max_agent_quote_size = max(0.0, max_agent_quote_size)
        self.tick_history_interval = max(1, tick_history_interval)
        self.persist_all_events = persist_all_events
        self.exchange_snapshot_depth = max(1, exchange_snapshot_depth)
        self.exchange_event_window = max(1, exchange_event_window)
        self.normal_agent_count = normal_agent_count
        self.agent_decision_timeout_seconds = agent_decision_timeout_seconds
        self.remote_agent_urls = remote_agent_urls or []
        self.remote_agent_timeout_seconds = remote_agent_timeout_seconds
        self.agent_manager = build_agent_manager(
            local_agent_count=normal_agent_count,
            remote_agent_urls=self.remote_agent_urls,
            decision_timeout_seconds=agent_decision_timeout_seconds,
            remote_timeout_seconds=remote_agent_timeout_seconds,
        )
        self.matching_engine = self._new_matching_engine()
        self.order_book = self.matching_engine.book
        self.exchange_event_source = SimulationEventSource(self.exchange_event_log)
        self.events: deque[AgentEvent] = deque(maxlen=20)
        self.scenarios = ScenarioController()
        self.detectors = AggregateDetectorEngine()
        self.incidents: list[Incident] = []
        self._incident_counter = 0
        self._incident_keys: set[tuple[str, str]] = set()
        self._persisted_label_payloads: dict[str, dict[str, object]] = {}
        self._order_first_seen_ticks: dict[str, int] = {}
        self.running = False
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self.store = store
        self.state = self._build_state(running=False)

    def _new_order_book(self) -> OrderBook:
        return OrderBook(
            mid_price=self.baseline_liquidity_reference_price,
            levels=self.baseline_liquidity_levels,
            tick_size=self.baseline_liquidity_tick_size,
            base_size=self.baseline_liquidity_base_size,
        )

    def _new_matching_engine(self) -> MatchingEngine:
        return MatchingEngine(symbol="LOB", venue="SIM", source="simulation", book=self._new_order_book())

    def _new_exchange_stream_id(self) -> str:
        return f"{self.run_id}-STREAM-{self._exchange_stream_generation:03d}"

    @property
    def exchange_event_log(self) -> EventLog:
        return self.matching_engine.event_log

    async def start(self) -> ArenaState:
        async with self._lock:
            self.running = True
            self.state = self._build_state(running=True)
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
            return self.state

    async def pause(self) -> ArenaState:
        async with self._lock:
            self.running = False
            self.state = self._build_state(running=False)
            return self.state

    async def reset(self) -> ArenaState:
        async with self._lock:
            self.running = False
            self.clock.reset()
            self._exchange_stream_generation += 1
            self.exchange_stream_id = self._new_exchange_stream_id()
            self._persisted_exchange_sequence = 0
            self.matching_engine = self._new_matching_engine()
            self.order_book = self.matching_engine.book
            self.exchange_event_source = SimulationEventSource(self.exchange_event_log)
            self.agent_manager = build_agent_manager(
                local_agent_count=self.normal_agent_count,
                remote_agent_urls=self.remote_agent_urls,
                decision_timeout_seconds=self.agent_decision_timeout_seconds,
                remote_timeout_seconds=self.remote_agent_timeout_seconds,
            )
            self.events.clear()
            self.scenarios.reset()
            self.incidents.clear()
            self._incident_counter = 0
            self._incident_keys.clear()
            self._persisted_label_payloads.clear()
            self._order_first_seen_ticks.clear()
            self.state = self._build_state(running=False)
            return self.state

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def get_state(self) -> ArenaState:
        async with self._lock:
            return self.state

    async def replay_exchange_events(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventReplay:
        async with self._lock:
            batch = self.exchange_event_source.read(after_sequence=after_sequence, limit=limit)
            return ExchangeEventReplay(
                events=[ExchangeEventRecord.model_validate(event.to_dict()) for event in batch.events],
                after_sequence=batch.after_sequence,
                next_after_sequence=batch.next_after_sequence,
                latest_sequence=batch.latest_sequence,
                has_more=batch.has_more,
            )

    async def list_incidents(self) -> list[Incident]:
        async with self._lock:
            return list(self.incidents)

    async def get_incident(self, incident_id: str) -> Incident | None:
        async with self._lock:
            return next((incident for incident in self.incidents if incident.id == incident_id), None)

    async def start_scenario(self, scenario_name: str) -> AttackTrackerState:
        async with self._lock:
            tracker = self._start_scenario_locked(scenario_name)
            self.running = True
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
            self.state = self._build_state(running=True)
            return tracker

    def step(self) -> dict[str, object]:
        self._advance_tick(running=True)
        return self.state.model_dump(mode="json")

    def launch_scenario(self, scenario_name: str) -> dict[str, object]:
        try:
            tracker = self._start_scenario_locked(scenario_name)
        except ValueError as exc:
            return {"accepted": False, "error": str(exc)}
        self.state = self._build_state(running=self.running)
        return {"accepted": True, "scenario": tracker.model_dump(mode="json")}

    def _start_scenario_locked(self, scenario_name: str) -> AttackTrackerState:
        tracker = self.scenarios.start(scenario_name, self.clock.tick, run_id=self.run_id, seed=self.seed)
        event = AgentEvent(
            type="red_team",
            timestamp=tracker.stages[0].timestamp if tracker.stages else None,
            agent_id=tracker.agent_id,
            scenario_id=tracker.scenario_id,
            scenario_name=tracker.scenario_name,
            scenario_family=tracker.scenario_family,
            tick=self.clock.tick,
            stage=tracker.current_stage.value if tracker.current_stage else "armed",
            message=f"{tracker.scenario_name} scenario armed",
        )
        self.events.appendleft(event)
        self._persist_attack(tracker)
        self._persist_event(event, significant=True)
        return tracker

    def snapshot(self, running: bool | None = None) -> dict[str, object]:
        if running is not None:
            self.state = self._build_state(running=running)
        return self.state.model_dump(mode="json")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.tick_interval_seconds)
            if not self.running:
                continue
            async with self._lock:
                await self._advance_tick_async(running=True)

    def _advance_tick(self, running: bool) -> None:
        tick = self.clock.step()
        previous_depth_top_n = self._top_depth()
        with self.matching_engine.mutation_context(tick=tick):
            tick_events = self._apply_agent_intents(
                self.agent_manager.collect_intents_sync(self._market_snapshot(tick))
            )
        scenario = self.scenarios.tracker_state(run_id=self.run_id, seed=self.seed)
        with self.matching_engine.mutation_context(
            tick=tick,
            scenario_id=scenario.scenario_id if scenario else None,
            scenario_name=scenario.scenario_name if scenario else None,
            scenario_family=scenario.scenario_family if scenario else None,
        ):
            tick_events.extend(self.scenarios.advance(self.order_book, tick))
        with self.matching_engine.mutation_context(tick=tick):
            self._maintain_baseline_liquidity()
        scenario = self.scenarios.tracker_state(run_id=self.run_id, seed=self.seed)
        self.matching_engine.record_snapshot(
            tick=tick,
            depth=self.exchange_snapshot_depth,
            scenario_id=scenario.scenario_id if scenario else None,
            scenario_name=scenario.scenario_name if scenario else None,
            scenario_family=scenario.scenario_family if scenario else None,
        )
        self._persist_exchange_stream()

        for event in tick_events:
            self.events.appendleft(event)
            is_significant = event.type in {"red_team", "detector", "nebius"} or event.scenario_id is not None
            self._persist_event(event, significant=is_significant)

        self.state = self._build_state(
            running=running,
            current_events=tick_events,
            previous_depth_top_n=previous_depth_top_n,
        )
        self._persist_tick_snapshot(tick_events)

    async def _advance_tick_async(self, running: bool) -> None:
        tick = self.clock.step()
        previous_depth_top_n = self._top_depth()
        with self.matching_engine.mutation_context(tick=tick):
            tick_events = self._apply_agent_intents(
                await self.agent_manager.collect_intents(self._market_snapshot(tick))
            )
        scenario = self.scenarios.tracker_state(run_id=self.run_id, seed=self.seed)
        with self.matching_engine.mutation_context(
            tick=tick,
            scenario_id=scenario.scenario_id if scenario else None,
            scenario_name=scenario.scenario_name if scenario else None,
            scenario_family=scenario.scenario_family if scenario else None,
        ):
            tick_events.extend(self.scenarios.advance(self.order_book, tick))
        with self.matching_engine.mutation_context(tick=tick):
            self._maintain_baseline_liquidity()
        scenario = self.scenarios.tracker_state(run_id=self.run_id, seed=self.seed)
        self.matching_engine.record_snapshot(
            tick=tick,
            depth=self.exchange_snapshot_depth,
            scenario_id=scenario.scenario_id if scenario else None,
            scenario_name=scenario.scenario_name if scenario else None,
            scenario_family=scenario.scenario_family if scenario else None,
        )
        self._persist_exchange_stream()

        for event in tick_events:
            self.events.appendleft(event)
            is_significant = event.type in {"red_team", "detector", "nebius"} or event.scenario_id is not None
            self._persist_event(event, significant=is_significant)

        self.state = self._build_state(
            running=running,
            current_events=tick_events,
            previous_depth_top_n=previous_depth_top_n,
        )
        self._persist_tick_snapshot(tick_events)

    def _market_snapshot(self, tick: int) -> MarketSnapshot:
        snapshot = self.order_book.get_l2_snapshot(depth=12)
        return MarketSnapshot(
            tick=tick,
            bids=list(snapshot["bids"]),
            asks=list(snapshot["asks"]),
            best_bid=snapshot["best_bid"],
            best_ask=snapshot["best_ask"],
            mid=snapshot["mid"],
            spread=snapshot["spread"],
        )

    def _apply_agent_intents(self, intents: list[AgentIntent]) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        for intent in intents:
            event = self._apply_agent_intent(intent)
            if event is not None:
                events.append(event)
        return events

    def _apply_agent_intent(self, intent: AgentIntent) -> AgentEvent | None:
        if intent.kind == "set_level":
            if intent.side is None or intent.price is None:
                return None
            book_side = "bid" if intent.side in {"bid", "buy"} else "ask"
            quantity = min(max(0.0, intent.quantity), self.max_agent_quote_size)
            self.order_book.update_agent_level(
                book_side,
                intent.price,
                quantity,
                agent_id=intent.agent_id,
                owner="normal",
                timestamp=intent.tick,
            )
            return AgentEvent(
                type=intent.event_type,
                timestamp=intent.tick,
                agent_id=intent.agent_id,
                runtime_source=intent.runtime_source,
                side="buy" if book_side == "bid" else "sell",
                price=intent.price,
                quantity=intent.quantity,
                message=intent.message or "updated visible depth",
            )

        if intent.kind == "market":
            order = intent.to_order()
            exchange_events = self.matching_engine.submit(order)
            executions = [event for event in exchange_events if isinstance(event, ExecuteOrderEvent)]
            traded_quantity = sum(event.quantity for event in executions)
            trade_price = executions[0].price if executions else None
            return AgentEvent(
                type=intent.event_type,
                timestamp=intent.tick,
                agent_id=intent.agent_id,
                runtime_source=intent.runtime_source,
                side=order.side,
                price=trade_price,
                quantity=traded_quantity,
                message=intent.message or "submitted market order",
            )

        if intent.kind == "limit":
            order = intent.to_order()
            self.matching_engine.submit(order)
            return AgentEvent(
                type=intent.event_type,
                timestamp=intent.tick,
                order_id=order.order_id,
                agent_id=order.agent_id,
                runtime_source=intent.runtime_source,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                message=intent.message or "submitted limit order",
            )

        if intent.kind == "cancel" and intent.order_id:
            resting = self.order_book.orders.get(intent.order_id)
            if resting is None:
                return None
            request = Order(
                order_id=resting.order_id,
                agent_id=intent.agent_id,
                side=resting.side,
                quantity=0.0,
                order_type="cancel",
                timestamp=intent.tick,
            )
            exchange_events = self.matching_engine.submit(request)
            if not exchange_events:
                return None
            return AgentEvent(
                type=intent.event_type,
                timestamp=intent.tick,
                order_id=resting.order_id,
                agent_id=intent.agent_id,
                runtime_source=intent.runtime_source,
                side=resting.side,
                price=resting.price,
                quantity=resting.quantity,
                message=intent.message or "cancelled resting order",
            )
        return AgentEvent(
            type=intent.event_type,
            timestamp=intent.tick,
            agent_id=intent.agent_id,
            runtime_source=intent.runtime_source,
            message=intent.message or "agent intent ignored",
        )

    def _maintain_baseline_liquidity(self) -> None:
        if self.baseline_liquidity_levels <= 0 or self.baseline_liquidity_base_size <= 0:
            return

        reference = self.baseline_liquidity_reference_price
        for index in range(self.baseline_liquidity_levels):
            distance = index + 1
            target_size = round(self.baseline_liquidity_base_size + index, 6)
            bid_price = round(reference - distance * self.baseline_liquidity_tick_size, 8)
            ask_price = round(reference + distance * self.baseline_liquidity_tick_size, 8)
            self.order_book.ensure_level_minimum(
                "bid",
                bid_price,
                target_size,
                agent_id="BASELINE_MM",
                owner="normal",
            )
            self.order_book.ensure_level_minimum(
                "ask",
                ask_price,
                target_size,
                agent_id="BASELINE_MM",
                owner="normal",
            )

    def _build_state(
        self,
        *,
        running: bool,
        current_events: list[AgentEvent] | None = None,
        previous_depth_top_n: float | None = None,
    ) -> ArenaState:
        book = order_book_snapshot_from_dict(self.order_book.get_l2_snapshot(depth=12))
        active_scenario = self.scenarios.tracker_state(run_id=self.run_id, seed=self.seed)
        features = extract_features(
            book=book,
            events=current_events or [],
            previous_depth_top_n=previous_depth_top_n,
            tick_interval_seconds=self.tick_interval_seconds,
            active_scenario=active_scenario,
            current_tick=self.clock.tick,
            order_first_seen_ticks=self._order_first_seen_ticks,
        )
        detector_scores = self.detectors.detect(features)
        evidence = flatten_evidence(detector_scores)
        active_agents = self.agent_manager.agent_ids
        if active_scenario is not None:
            active_agents.append(active_scenario.agent_id)
            active_scenario = active_scenario.model_copy(update={"evidence": evidence})
            self._persist_label(active_scenario)
            self._maybe_create_incident(active_scenario, detector_scores.scores)
        return arena_state_from_book(
            tick=self.clock.tick,
            running=running,
            book=book,
            events=list(self.events),
            exchange_events=[
                ExchangeEventRecord.model_validate(event.to_dict())
                for event in self.exchange_event_log.tail(self.exchange_event_window)
            ],
            features=features.to_arena_features(),
            active_agents=active_agents,
            active_scenario=active_scenario,
            detectors=detector_scores,
            incidents=list(self.incidents),
        )

    def _top_depth(self, depth: int = 5) -> float:
        snapshot = self.order_book.get_l2_snapshot(depth=depth)
        return sum(level["quantity"] for level in snapshot["bids"]) + sum(level["quantity"] for level in snapshot["asks"])

    def _maybe_create_incident(self, scenario: AttackTrackerState, scores: list[DetectorScore]) -> None:
        for score in scores:
            evidence = score.evidence or []
            incident_key = (scenario.scenario_id, score.name)
            if score.confidence < 0.80 or len(evidence) < 2 or incident_key in self._incident_keys:
                continue

            self._incident_counter += 1
            incident = Incident(
                id=f"INC-{self._incident_counter:06d}",
                title=f"{_format_detector_name(score.name)} detected",
                type=score.name,
                agent=scenario.agent_id,
                confidence=score.confidence,
                severity=_incident_severity(score),
                evidence=_confirmed_evidence(evidence),
                explanation="Mock Nebius AI explanation pending.",
                scenario_id=scenario.scenario_id,
                scenario_family=scenario.scenario_family,
            )
            self.incidents.append(incident)
            self._incident_keys.add(incident_key)
            self._persist_incident(incident)
            event = AgentEvent(
                type="detector",
                timestamp=self.clock.tick,
                agent_id="DETECTOR_ENGINE",
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.scenario_name,
                scenario_family=scenario.scenario_family,
                detector=score.name,
                incident_id=incident.id,
                confidence=score.confidence,
                message=f"{incident.id} created from {score.name} confidence {score.confidence:.2f}",
            )
            self.events.appendleft(event)
            self._persist_event(event, significant=True)

    def _persist_event(self, event: AgentEvent, *, significant: bool) -> None:
        if self.store is None:
            return
        payload = event.model_dump(mode="json", exclude_none=True)
        payload.setdefault("tick", self.clock.tick)
        if self.persist_all_events or significant:
            self.store.append_jsonl("events/events.jsonl", payload)
        if significant:
            self.store.append_jsonl("events/significant_events.jsonl", payload)
            append_history_artifact(
                self.store,
                kind="event",
                payload=payload,
                summary=str(payload.get("message") or payload.get("type") or "Significant event"),
                run_id=self.run_id,
                tick=int(payload.get("tick", self.clock.tick)),
                scenario_id=payload.get("scenario_id"),
                incident_id=payload.get("incident_id"),
                source="simulation_engine",
                source_path="events/significant_events.jsonl",
            )

    def _persist_exchange_stream(self) -> None:
        if self.store is None:
            return
        pending = self.exchange_event_log.replay_events(after_sequence=self._persisted_exchange_sequence)
        for event in pending:
            append_exchange_event(
                self.store,
                event=event,
                run_id=self.run_id,
                stream_id=self.exchange_stream_id,
            )
            self._persisted_exchange_sequence = event.sequence or self._persisted_exchange_sequence

    def _persist_attack(self, tracker: AttackTrackerState) -> None:
        if self.store is None:
            return
        payload = tracker.model_dump(mode="json")
        self.store.append_jsonl("attacks/attacks.jsonl", payload)
        append_history_artifact(
            self.store,
            kind="attack",
            payload=payload,
            summary=f"{tracker.scenario_name} armed",
            run_id=self.run_id,
            tick=tracker.start_tick,
            scenario_id=tracker.scenario_id,
            source="simulation_engine",
            source_path="attacks/attacks.jsonl",
        )
        self._persist_label(tracker)

    def _persist_label(self, tracker: AttackTrackerState) -> None:
        if self.store is None or tracker.label is None:
            return
        payload = tracker.label.model_dump(mode="json")
        previous_payload = self._persisted_label_payloads.get(tracker.label.label_id)
        if previous_payload == payload:
            return
        self._persisted_label_payloads[tracker.label.label_id] = payload
        self.store.append_jsonl("labels/scenario_labels.jsonl", payload)

    def _persist_incident(self, incident: Incident) -> None:
        if self.store is None:
            return
        payload = incident.model_dump(mode="json")
        self.store.append_jsonl("incidents/incidents.jsonl", payload)
        append_history_artifact(
            self.store,
            kind="incident",
            payload=payload,
            summary=incident.title,
            run_id=self.run_id,
            tick=self.clock.tick,
            scenario_id=incident.scenario_id,
            incident_id=incident.id,
            source="simulation_engine",
            source_path="incidents/incidents.jsonl",
        )
        append_history_artifact(
            self.store,
            kind="detected_attack",
            payload=payload,
            summary=f"{incident.type} detected for {incident.scenario_id or incident.agent}",
            run_id=self.run_id,
            tick=self.clock.tick,
            scenario_id=incident.scenario_id,
            incident_id=incident.id,
            source="detector_engine",
            source_path="incidents/incidents.jsonl",
        )

    def _persist_tick_snapshot(self, tick_events: list[AgentEvent]) -> None:
        if self.store is None:
            return
        has_significant_event = any(
            event.type in {"red_team", "detector", "nebius"} or event.scenario_id is not None
            for event in tick_events
        )
        if self.clock.tick % self.tick_history_interval != 0 and not has_significant_event:
            return
        append_tick_snapshot(
            self.store,
            state=self.state,
            run_id=self.run_id,
            tick_events=tick_events,
        )


def _format_detector_name(name: str) -> str:
    return name.replace("_", " ").title()


def _incident_severity(score: DetectorScore) -> str:
    if score.severity == "critical":
        return "Critical"
    if score.severity == "high" or score.confidence >= 0.80:
        return "High"
    if score.severity == "medium":
        return "Medium"
    return "Low"


def _confirmed_evidence(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return [
        item.model_copy(
            update={
                "interpretation": item.interpretation or "Confirmed by deterministic detector threshold.",
            }
        )
        for item in evidence
    ]


ArenaEngine = SimulationEngine

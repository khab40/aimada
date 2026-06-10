import asyncio
import random
from collections import deque
from contextlib import suppress

from app.arena.clock import SimulationClock
from app.arena.state import (
    arena_state_from_book,
    order_book_snapshot_from_dict,
)
from app.detectors.aggregate import AggregateDetectorEngine, flatten_evidence
from app.detectors.features import extract_features
from app.exchange.order_book import OrderBook
from app.schemas.arena import AgentEvent, ArenaState, AttackTrackerState, DetectorScore, EvidenceItem, Incident
from app.scenarios.controller import ScenarioController
from app.storage.history import append_history_artifact, append_tick_snapshot
from app.storage.local_store import LocalStore


class SimulationEngine:
    def __init__(self, tick_interval_seconds: float = 0.5, seed: int = 7, store: LocalStore | None = None) -> None:
        self.tick_interval_seconds = tick_interval_seconds
        self.seed = seed
        self.run_id = f"RUN-{seed:06d}"
        self.clock = SimulationClock(tick_interval_ms=int(tick_interval_seconds * 1000))
        self.random = random.Random(seed)
        self.order_book = self._new_order_book()
        self.events: deque[AgentEvent] = deque(maxlen=20)
        self.scenarios = ScenarioController()
        self.detectors = AggregateDetectorEngine()
        self.incidents: list[Incident] = []
        self._incident_counter = 0
        self._incident_keys: set[tuple[str, str]] = set()
        self._persisted_label_payloads: dict[str, dict[str, object]] = {}
        self.running = False
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self.store = store
        self.state = self._build_state(running=False)

    def _new_order_book(self) -> OrderBook:
        return OrderBook(mid_price=68_125.0, levels=12, tick_size=1.0, base_size=1.5)

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
            self.order_book = self._new_order_book()
            self.events.clear()
            self.scenarios.reset()
            self.incidents.clear()
            self._incident_counter = 0
            self._incident_keys.clear()
            self._persisted_label_payloads.clear()
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
                self._advance_tick(running=True)

    def _advance_tick(self, running: bool) -> None:
        tick = self.clock.step()
        previous_depth_top_n = self._top_depth()
        tick_events = [
            self._market_maker_refresh(tick),
            self._noise_trader_update(tick),
        ]
        taker_event = self._liquidity_taker_update(tick)
        if taker_event is not None:
            tick_events.append(taker_event)
        tick_events.extend(self.scenarios.advance(self.order_book, tick))

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

    def _market_maker_refresh(self, tick: int) -> AgentEvent:
        best_bid = self.order_book.best_bid()
        best_ask = self.order_book.best_ask()
        if best_bid is None or best_ask is None:
            return AgentEvent(type="market_maker", timestamp=tick, agent_id="MM_01")

        bid_size = round(2.0 + (tick % 5) * 0.25, 3)
        ask_size = round(2.1 + ((tick + 2) % 5) * 0.25, 3)
        self.order_book.update_level("bid", best_bid, bid_size, owner="normal")
        self.order_book.update_level("ask", best_ask, ask_size, owner="normal")
        return AgentEvent(
            type="market_maker",
            timestamp=tick,
            agent_id="MM_01",
            price=(best_bid + best_ask) / 2,
            quantity=round(bid_size + ask_size, 3),
            message="refreshed best bid/ask depth",
        )

    def _noise_trader_update(self, tick: int) -> AgentEvent:
        side = "bid" if tick % 2 else "ask"
        levels = self.order_book.bids if side == "bid" else self.order_book.asks
        prices = sorted(levels, reverse=side == "bid")
        level_index = min((tick + 2) % 5, len(prices) - 1)
        price = prices[level_index]
        current_size = self.order_book._level_quantity(side, price)
        delta = self.random.choice([-0.35, -0.2, 0.2, 0.35])
        next_size = max(0.25, round(current_size + delta, 3))
        self.order_book.update_level(side, price, next_size, owner="normal")
        return AgentEvent(
            type="normal",
            timestamp=tick,
            agent_id="NOISE_01",
            side="buy" if side == "bid" else "sell",
            price=price,
            quantity=next_size,
            message="small visible depth changed",
        )

    def _liquidity_taker_update(self, tick: int) -> AgentEvent | None:
        if tick % 4 != 0:
            return None

        side = "buy" if (tick // 4) % 2 else "sell"
        quantity = 0.5
        trades = self.order_book.apply_market_order(side, quantity)
        traded_quantity = sum(float(trade["quantity"]) for trade in trades)
        trade_price = trades[0]["price"] if trades else None
        return AgentEvent(
            type="normal",
            timestamp=tick,
            agent_id="TAKER_01",
            side=side,
            price=trade_price,
            quantity=traded_quantity,
            message="consumed small top-of-book quantity",
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
        )
        detector_scores = self.detectors.detect(features)
        evidence = flatten_evidence(detector_scores)
        active_agents = ["MM_01", "NOISE_01", "TAKER_01"]
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

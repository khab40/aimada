from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field
from app.scenarios.catalog import SCENARIO_LABELS, ScenarioType


ManipulationType = Literal["spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"]
ScenarioDifficulty = Literal["easy", "medium", "hard", "adversarial"]
LiquidityRegime = Literal["thin", "normal", "deep"]
VolatilityRegime = Literal["low", "medium", "high"]
ScenarioEventType = Literal["place_order", "cancel_order", "trade", "quote_update"]


class MarketAbuseScenarioGenerationRequest(BaseModel):
    manipulation_type: ManipulationType = "spoofing_like_wall"
    difficulty: ScenarioDifficulty = "medium"
    symbol: str = Field(default="AIMD", min_length=1, max_length=16)
    duration_ticks: int = Field(default=120, ge=30, le=600)
    liquidity_regime: LiquidityRegime = "thin"
    volatility_regime: VolatilityRegime = "high"
    seed: int | None = None


class ScenarioEvent(BaseModel):
    event_id: str
    tick: int = Field(ge=0)
    event_type: ScenarioEventType
    type: str
    agent_id: str
    symbol: str
    scenario_id: str
    scenario_name: str
    scenario_family: str
    stage: str
    message: str
    side: Literal["buy", "sell"] | None = None
    price: float | None = None
    quantity: float | None = None
    order_id: str | None = None
    aggressor_order_id: str | None = None
    resting_order_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManipulationWindow(BaseModel):
    start_tick: int = Field(ge=0)
    end_tick: int = Field(ge=0)


class ScenarioGroundTruth(BaseModel):
    label: ManipulationType
    manipulation_windows: list[ManipulationWindow]
    manipulator_agent_ids: list[str]
    expected_detector_targets: list[str]
    positive_event_ids: list[str]


class ExpectedDetectorBehavior(BaseModel):
    primary_signals: list[str]
    expected_risk_score: float = Field(ge=0.0, le=1.0)
    false_positive_risk: Literal["low", "medium", "high"]


class CanonicalMarketAbuseScenario(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    scenario_id: str
    title: str
    description: str
    manipulation_type: ManipulationType
    difficulty: ScenarioDifficulty
    symbol: str
    duration_ticks: int
    liquidity_regime: LiquidityRegime
    volatility_regime: VolatilityRegime
    ground_truth: ScenarioGroundTruth
    events: list[ScenarioEvent]
    expected_detector_behavior: ExpectedDetectorBehavior
    explanation: str
    replay: dict[str, Any]
    source: dict[str, Any] = Field(default_factory=dict)
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class MarketAbuseScenarioClient(Protocol):
    def generate_market_abuse_scenario(
        self,
        request: MarketAbuseScenarioGenerationRequest,
    ) -> CanonicalMarketAbuseScenario:
        ...


def generate_with_client(
    client: MarketAbuseScenarioClient,
    request: MarketAbuseScenarioGenerationRequest,
) -> CanonicalMarketAbuseScenario:
    return client.generate_market_abuse_scenario(prepare_payload(request))


def prepare_payload(request: MarketAbuseScenarioGenerationRequest) -> MarketAbuseScenarioGenerationRequest:
    return MarketAbuseScenarioGenerationRequest.model_validate(request.model_dump(mode="json"))


def normalize_response(
    response: dict[str, Any],
    *,
    request: MarketAbuseScenarioGenerationRequest,
    endpoint: str,
    mode: Literal["nebius", "mock"] = "nebius",
    fallback_reason: str | None = None,
) -> CanonicalMarketAbuseScenario:
    fallback = mock_response(request, reason=fallback_reason or "deterministic normalization fallback")
    scenario_id = str(response.get("scenario_id") or fallback.scenario_id)
    manipulation_type = _manipulation_type(response.get("manipulation_type"), request.manipulation_type)
    duration_ticks = _bounded_int(response.get("duration_ticks"), request.duration_ticks, 30, 600)
    source = response.get("source") if isinstance(response.get("source"), dict) else {}
    source = {
        **source,
        "provider": source.get("provider") or "nebius_serverless",
        "endpoint": source.get("endpoint") or endpoint,
    }
    if response.get("model_mode"):
        source["model_mode"] = response.get("model_mode")
    if response.get("model"):
        source["model"] = response.get("model")
    events = _scenario_events(response.get("events"), fallback.events, scenario_id=scenario_id)
    ground_truth = _ground_truth(
        response.get("ground_truth"),
        fallback.ground_truth,
        manipulation_type=manipulation_type,
        positive_event_ids=[event.event_id for event in events[:2]] or fallback.ground_truth.positive_event_ids,
    )
    detector_behavior = _detector_behavior(response.get("expected_detector_behavior"), fallback.expected_detector_behavior)
    return CanonicalMarketAbuseScenario(
        mode=mode,
        endpoint=endpoint,
        scenario_id=scenario_id,
        title=str(response.get("title") or fallback.title),
        description=str(response.get("description") or fallback.description),
        manipulation_type=manipulation_type,
        difficulty=_difficulty(response.get("difficulty"), request.difficulty),
        symbol=str(response.get("symbol") or request.symbol).upper(),
        duration_ticks=duration_ticks,
        liquidity_regime=_liquidity(response.get("liquidity_regime"), request.liquidity_regime),
        volatility_regime=_volatility(response.get("volatility_regime"), request.volatility_regime),
        ground_truth=ground_truth,
        events=events,
        expected_detector_behavior=detector_behavior,
        explanation=str(response.get("explanation") or fallback.explanation),
        replay=_replay_payload(scenario_id, manipulation_type, duration_ticks, response.get("replay")),
        source=source,
        fallback_reason=fallback_reason,
        raw_response=response if mode == "nebius" else None,
    )


def mock_response(request: MarketAbuseScenarioGenerationRequest, *, reason: str) -> CanonicalMarketAbuseScenario:
    symbol = request.symbol.upper()
    seed = request.seed if request.seed is not None else _stable_seed(request)
    scenario_id = f"ai-{request.manipulation_type.replace('_', '-')}-{symbol.lower()}-{seed % 10000:04d}"
    start_tick = max(10, request.duration_ticks // 6)
    end_tick = min(request.duration_ticks, max(start_tick + 12, request.duration_ticks - request.duration_ticks // 5))
    agent_id = _agent_id(request.manipulation_type)
    route = _replay_route(request.manipulation_type)
    signals = _signals(request.manipulation_type)
    risk = _risk_score(request.difficulty, request.volatility_regime)
    events = _events_for(request, scenario_id=scenario_id, agent_id=agent_id, start_tick=start_tick)
    return CanonicalMarketAbuseScenario(
        mode="mock",
        endpoint="mock Nebius /generate-market-abuse-scenario",
        scenario_id=scenario_id,
        title=_title(request.manipulation_type, symbol),
        description=_description(request),
        manipulation_type=request.manipulation_type,
        difficulty=request.difficulty,
        symbol=symbol,
        duration_ticks=request.duration_ticks,
        liquidity_regime=request.liquidity_regime,
        volatility_regime=request.volatility_regime,
        ground_truth=ScenarioGroundTruth(
            label=request.manipulation_type,
            manipulation_windows=[ManipulationWindow(start_tick=start_tick, end_tick=end_tick)],
            manipulator_agent_ids=[agent_id],
            expected_detector_targets=signals,
            positive_event_ids=[event.event_id for event in events[:2]],
        ),
        events=events,
        expected_detector_behavior=ExpectedDetectorBehavior(
            primary_signals=signals,
            expected_risk_score=risk,
            false_positive_risk="high" if request.difficulty == "adversarial" else "medium" if request.difficulty == "hard" else "low",
        ),
        explanation=_explanation(request),
        replay={
            "mode": "attack_scenario_projection",
            "route": route,
            "supported": True,
            "note": "Replay uses the existing Arena named-scenario injection path.",
        },
        source={
            "mode": "mock",
            "provider": "nebius_serverless",
            "endpoint": "/generate-market-abuse-scenario",
            "model": "deterministic-template",
        },
        fallback_reason=reason,
    )


def project_attack_scenario(scenario: CanonicalMarketAbuseScenario) -> dict[str, Any]:
    attack_type = _attack_type_for_projection(scenario.manipulation_type)
    target_side = "both" if scenario.manipulation_type in {"layering_like", "liquidity_evaporation"} else "sell"
    real_trade_side = "buy" if target_side != "buy" else "sell"
    return {
        "id": scenario.scenario_id,
        "name": scenario.title,
        "attackType": attack_type,
        "targetSide": target_side,
        "objective": _objective_for(scenario.manipulation_type),
        "marketRegime": f"{scenario.liquidity_regime}_{scenario.volatility_regime}",
        "redTeamAgents": scenario.ground_truth.manipulator_agent_ids,
        "startTick": scenario.ground_truth.manipulation_windows[0].start_tick if scenario.ground_truth.manipulation_windows else 20,
        "durationTicks": scenario.duration_ticks,
        "fakeOrderLevels": 8 if scenario.manipulation_type == "quote_stuffing" else 4,
        "fakeOrderSizeMultiplier": 6 if scenario.difficulty in {"easy", "medium"} else 10,
        "cancelDelayTicks": 4 if scenario.manipulation_type == "quote_stuffing" else 12,
        "realTradeSide": real_trade_side,
        "realTradeSize": 120 if scenario.difficulty == "easy" else 240,
        "stealthLevel": "subtle" if scenario.difficulty == "adversarial" else "medium" if scenario.difficulty in {"medium", "hard"} else "obvious",
        "expectedDetectorDifficulty": "hard" if scenario.difficulty == "adversarial" else scenario.difficulty,
        "expectedSignals": scenario.expected_detector_behavior.primary_signals,
        "planSteps": [
            event.message for event in scenario.events[:5]
        ] or [scenario.explanation],
        "source": {
            **scenario.source,
            "canonical_scenario_id": scenario.scenario_id,
            "canonical_manipulation_type": scenario.manipulation_type,
            "ground_truth": scenario.ground_truth.model_dump(mode="json"),
            "event_count": len(scenario.events),
            "replay": scenario.replay,
        },
    }


def _events_for(
    request: MarketAbuseScenarioGenerationRequest,
    *,
    scenario_id: str,
    agent_id: str,
    start_tick: int,
) -> list[ScenarioEvent]:
    side: Literal["buy", "sell"] = "buy" if request.manipulation_type == "spoofing_like_wall" else "sell"
    base_price = 100.0 + (_stable_seed(request) % 250) / 100.0
    size = 250.0 if request.liquidity_regime == "thin" else 500.0 if request.liquidity_regime == "normal" else 800.0
    spread = 0.05 if request.volatility_regime == "low" else 0.15 if request.volatility_regime == "medium" else 0.35
    order_id = f"ord-{scenario_id}-{start_tick}"
    templates = {
        "spoofing_like_wall": [
            ("place_order", "wall_placed", "Place large visible synthetic liquidity wall.", order_id, side, size),
            ("cancel_order", "wall_cancelled", "Cancel wall before execution.", order_id, side, size),
            ("trade", "incident_confirmed", "Submit small opposite-side trade after book reaction.", None, "sell" if side == "buy" else "buy", size / 8),
        ],
        "layering_like": [
            ("place_order", "pressure_phase", "Layer synthetic orders across adjacent price levels.", order_id, side, size / 2),
            ("place_order", "pressure_phase", "Add second layer to deepen visible imbalance.", f"{order_id}-b", side, size / 3),
            ("cancel_order", "cancelled", "Cancel layered orders as price pressure appears.", order_id, side, size / 2),
        ],
        "liquidity_evaporation": [
            ("quote_update", "pressure_phase", "Thin visible depth across the top three book levels.", None, None, None),
            ("quote_update", "pressure_phase", "Maintain reduced two-sided top-of-book liquidity.", None, None, None),
            ("quote_update", "incident_confirmed", "Widen the synthetic spread after depth collapse.", None, None, None),
        ],
        "quote_stuffing": [
            ("place_order", "pressure_phase", "Burst submit synthetic quotes at high message rate.", order_id, side, size / 10),
            ("cancel_order", "cancelled", "Rapidly cancel burst quotes.", order_id, side, size / 10),
            ("quote_update", "incident_confirmed", "Record temporary spread and message-rate distortion.", None, None, None),
        ],
    }
    rows = templates[request.manipulation_type]
    events: list[ScenarioEvent] = []
    for index, (event_type, stage, message, oid, event_side, quantity) in enumerate(rows):
        tick = start_tick + index * max(2, min(12, request.duration_ticks // 16))
        price_offset = (index + 1) * spread * (1 if event_side == "sell" else -1)
        events.append(
            ScenarioEvent(
                event_id=f"evt-{tick:04d}-{event_type.replace('_', '-')}",
                tick=tick,
                event_type=event_type,  # type: ignore[arg-type]
                type=event_type,
                agent_id=agent_id,
                symbol=request.symbol.upper(),
                scenario_id=scenario_id,
                scenario_name=_title(request.manipulation_type, request.symbol.upper()),
                scenario_family=request.manipulation_type,
                stage=stage,
                message=message,
                side=event_side,  # type: ignore[arg-type]
                price=round(base_price + price_offset, 4) if event_side else None,
                quantity=round(quantity, 4) if quantity else None,
                order_id=oid,
                metadata={
                    "difficulty": request.difficulty,
                    "liquidity_regime": request.liquidity_regime,
                    "volatility_regime": request.volatility_regime,
                },
            )
        )
    return events


def _scenario_events(value: Any, fallback: list[ScenarioEvent], *, scenario_id: str) -> list[ScenarioEvent]:
    if not isinstance(value, list):
        return fallback
    events: list[ScenarioEvent] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        payload = {
            **item,
            "event_id": item.get("event_id") or f"evt-{index + 1:04d}",
            "type": item.get("type") or item.get("event_type") or "quote_update",
            "scenario_id": item.get("scenario_id") or scenario_id,
            "scenario_name": item.get("scenario_name") or "AI generated scenario",
            "scenario_family": item.get("scenario_family") or item.get("manipulation_type") or "spoofing_like_wall",
            "stage": item.get("stage") or "pressure_phase",
            "message": item.get("message") or "Synthetic scenario event.",
        }
        try:
            events.append(ScenarioEvent.model_validate(payload))
        except ValueError:
            continue
    return events or fallback


def _ground_truth(
    value: Any,
    fallback: ScenarioGroundTruth,
    *,
    manipulation_type: ManipulationType,
    positive_event_ids: list[str],
) -> ScenarioGroundTruth:
    if not isinstance(value, dict):
        return fallback.model_copy(update={"label": manipulation_type, "positive_event_ids": positive_event_ids})
    try:
        return ScenarioGroundTruth.model_validate(
            {
                **value,
                "label": manipulation_type,
                "positive_event_ids": value.get("positive_event_ids") or positive_event_ids,
            }
        )
    except ValueError:
        return fallback.model_copy(update={"label": manipulation_type, "positive_event_ids": positive_event_ids})


def _detector_behavior(value: Any, fallback: ExpectedDetectorBehavior) -> ExpectedDetectorBehavior:
    if not isinstance(value, dict):
        return fallback
    try:
        return ExpectedDetectorBehavior.model_validate(value)
    except ValueError:
        return fallback


def _replay_payload(
    scenario_id: str,
    manipulation_type: ManipulationType,
    duration_ticks: int,
    value: Any,
) -> dict[str, Any]:
    replay = value if isinstance(value, dict) else {}
    return {
        "mode": replay.get("mode") or "attack_scenario_projection",
        "route": replay.get("route") or _replay_route(manipulation_type),
        "supported": replay.get("supported", True),
        "scenario_id": scenario_id,
        "duration_ticks": duration_ticks,
    }


def _stable_seed(request: MarketAbuseScenarioGenerationRequest) -> int:
    raw = "|".join(
        [
            request.manipulation_type,
            request.difficulty,
            request.symbol.upper(),
            str(request.duration_ticks),
            request.liquidity_regime,
            request.volatility_regime,
        ]
    )
    return int(sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _manipulation_type(value: Any, fallback: ManipulationType) -> ManipulationType:
    normalized = str(value or fallback).lower().replace("-", "_").replace(" ", "_")
    if normalized in {"spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"}:
        return normalized  # type: ignore[return-value]
    return fallback


def _difficulty(value: Any, fallback: ScenarioDifficulty) -> ScenarioDifficulty:
    normalized = str(value or fallback).lower()
    if normalized in {"easy", "medium", "hard", "adversarial"}:
        return normalized  # type: ignore[return-value]
    return fallback


def _liquidity(value: Any, fallback: LiquidityRegime) -> LiquidityRegime:
    normalized = str(value or fallback).lower()
    if normalized in {"thin", "normal", "deep"}:
        return normalized  # type: ignore[return-value]
    return fallback


def _volatility(value: Any, fallback: VolatilityRegime) -> VolatilityRegime:
    normalized = str(value or fallback).lower()
    if normalized in {"low", "medium", "high"}:
        return normalized  # type: ignore[return-value]
    return fallback


def _bounded_int(value: Any, fallback: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return fallback


def _risk_score(difficulty: ScenarioDifficulty, volatility: VolatilityRegime) -> float:
    base = {"easy": 0.52, "medium": 0.68, "hard": 0.82, "adversarial": 0.91}[difficulty]
    adjustment = {"low": -0.04, "medium": 0.0, "high": 0.04}[volatility]
    return round(max(0.0, min(0.97, base + adjustment)), 4)


def _signals(manipulation_type: ManipulationType) -> list[str]:
    return {
        "spoofing_like_wall": ["wall_size_ratio", "cancel_to_trade_ratio", "order_lifetime_ms"],
        "layering_like": ["depth_imbalance", "rapid_cancel_cluster", "multi_level_pressure"],
        "quote_stuffing": ["message_rate", "cancel_to_trade_ratio", "spread_widening"],
        "liquidity_evaporation": ["depth_change_pct", "spread_bps", "replenishment_rate"],
    }[manipulation_type]


def _agent_id(manipulation_type: ManipulationType) -> str:
    return {
        "spoofing_like_wall": "AI-SPOOF-001",
        "layering_like": "AI-LAYER-001",
        "quote_stuffing": "AI-STUFF-001",
        "liquidity_evaporation": "AI-LIQUIDITY-001",
    }[manipulation_type]


def _title(manipulation_type: ManipulationType, symbol: str) -> str:
    return f"{symbol} {SCENARIO_LABELS[ScenarioType(manipulation_type)]}"


def _description(request: MarketAbuseScenarioGenerationRequest) -> str:
    return (
        f"Synthetic {request.manipulation_type.replace('_', ' ')} workload for {request.symbol.upper()} "
        f"over {request.duration_ticks} ticks in {request.liquidity_regime} liquidity and "
        f"{request.volatility_regime} volatility."
    )


def _explanation(request: MarketAbuseScenarioGenerationRequest) -> str:
    return (
        f"The generated scenario is a bounded {request.difficulty} synthetic workload. "
        "It preserves simulator labels, detector targets, and replay projection metadata."
    )


def _replay_route(manipulation_type: ManipulationType) -> str:
    return {
        "spoofing_like_wall": "spoofing_like_wall",
        "layering_like": "layering_like",
        "quote_stuffing": "quote_stuffing",
        "liquidity_evaporation": "liquidity_evaporation",
    }[manipulation_type]


def _attack_type_for_projection(manipulation_type: ManipulationType) -> ManipulationType:
    return manipulation_type


def _objective_for(manipulation_type: ManipulationType) -> str:
    return {
        "spoofing_like_wall": "Distort visible liquidity and measure detector response",
        "layering_like": "Stress multi-level depth imbalance detectors",
        "quote_stuffing": "Stress message-rate and cancellation detectors",
        "liquidity_evaporation": "Stress depth-collapse and spread-widening detectors",
    }[manipulation_type]

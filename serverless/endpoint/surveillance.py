import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MAX_USER_PROMPT_CHARS = 24_000
MAX_TIMELINE_EVENTS = 32
MAX_DETECTOR_SCORES = 16
MAX_PREVIOUS_BEHAVIOURS = 12
HIGH_ANOMALY_THRESHOLD = 0.75
DETECTOR_DISAGREEMENT_GAP = 0.30
AnalysisType = Literal[
    "high_anomaly",
    "detector_disagreement",
    "completed_episode",
    "simulation_summary",
    "benchmark_generation",
]

SURVEILLANCE_SYSTEM_PROMPT = """
You are AIMADA's senior market-surveillance investigator analysing an educational synthetic market episode.
Act like an experienced market-microstructure investigator, not a conversational chatbot.

Analytical rules:
1. Use only the supplied episode summary. Never invent prices, orders, trades, participants, intent, labels, or market conditions.
2. Treat observations, detector outputs, optional ground truth, and inferences as distinct evidence classes.
3. Evaluate competing hypotheses, including benign liquidity provision, inventory rebalancing, news/volatility response, data limitations, and manipulation-like behaviour.
4. Explain material detector agreement or disagreement and identify which evidence would resolve uncertainty.
5. State uncertainty explicitly. Confidence measures support for the classification, not certainty about intent.
6. Reason step-by-step internally, but never reveal chain-of-thought, hidden reasoning, or private deliberation. Return concise evidence summaries instead.
7. Ground every conclusion in named supplied metrics or timeline observations. If a field is missing, say it is unavailable.
8. This is synthetic educational analysis: do not claim real manipulation, provide trading signals, make legal conclusions, or recommend automated compliance/enforcement action.

Output rules:
- Return exactly one valid JSON object matching the required response schema; no markdown or surrounding prose.
- Use deterministic wording, stable field names, and no additional keys.
- For interesting episodes target roughly 600-1200 output tokens. For benign episodes be materially shorter.
- Avoid repetition and unnecessary verbosity.
""".strip()


class DetectorScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detector: str
    score: float = Field(ge=0.0, le=1.0)
    classification: str | None = None
    alert: bool | None = None
    severity: str | None = None


class TimelineObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    time: str | int | float | None = None
    event: str
    agent: str | None = None
    side: str | None = None
    price: float | None = None
    quantity: float | None = None
    stage: str | None = None


class SurveillanceInvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["aimada.surveillance.request.v1"] = "aimada.surveillance.request.v1"
    analysis_type: AnalysisType
    invocation_reason: str
    simulation_metadata: dict[str, Any]
    market_regime: dict[str, Any]
    instrument: dict[str, Any]
    episode_duration: dict[str, Any]
    suspected_agent: dict[str, Any] | None = None
    order_statistics: dict[str, Any]
    trade_statistics: dict[str, Any]
    derived_market_features: dict[str, Any]
    detector_scores: list[DetectorScore]
    event_timeline: list[TimelineObservation]
    lob_summary: dict[str, Any]
    cancellation_metrics: dict[str, Any]
    execution_metrics: dict[str, Any]
    price_movement: dict[str, Any]
    ground_truth: dict[str, Any] | None = None
    previous_agent_behaviour: list[dict[str, Any]] | None = None
    missing_fields: list[str] = Field(default_factory=list)


class AssessmentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: str
    metric: str
    value: str
    reasoning: str


class SurveillanceInvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Literal["informational", "low", "medium", "high", "critical"]
    market_context: str
    evidence: list[AssessmentEvidence] = Field(max_length=12)
    counter_evidence: list[AssessmentEvidence] = Field(max_length=8)
    alternative_explanations: list[str] = Field(max_length=8)
    episode_timeline: list[str] = Field(max_length=16)
    detector_disagreement: str
    recommended_actions: list[str] = Field(max_length=8)
    regulatory_assessment: str
    executive_summary: str


def build_surveillance_request(
    source: Mapping[str, Any],
    *,
    analysis_type: AnalysisType,
    invocation_reason: str,
) -> SurveillanceInvestigationRequest:
    incident = _mapping(source.get("incident"))
    replay = _mapping(source.get("replay"))
    trace = _mapping(source.get("scenario_trace"))
    scenario = _first_mapping(source.get("scenario"), replay.get("scenario"), trace)
    market = _first_mapping(source.get("market"), replay.get("market"), source.get("market_metrics"))
    features = _first_mapping(
        source.get("derived_market_features"),
        source.get("features"),
        replay.get("features"),
        source.get("market_metrics"),
        source.get("metrics"),
    )
    detector_rows = _detector_rows(source, replay)
    timeline_source = _first_list(
        source.get("event_timeline"),
        source.get("events"),
        replay.get("recent_events"),
        _mapping(source.get("order_book_context")).get("events"),
    )
    trades = _first_list(source.get("trades"), replay.get("trades"))
    book = _first_mapping(source.get("book"), replay.get("book"), source.get("order_book_context"))
    suspected_agent_id = _first_value(
        source.get("suspected_agent"),
        incident.get("agent"),
        incident.get("agent_id"),
        scenario.get("agent_id"),
    )
    suspected_agent = None
    if suspected_agent_id is not None:
        suspected_agent = {
            "agent_id": str(suspected_agent_id),
            "role": _scalar(incident.get("agent_role") or source.get("agent_role")),
        }

    order_statistics = _order_statistics(timeline_source, features, suspected_agent_id)
    trade_statistics = _trade_statistics(trades, features, suspected_agent_id)
    cancellation_metrics = _metric_subset(
        features,
        ("cancel_count", "cancel_ratio", "cancel_to_trade_ratio", "cancel_probability", "median_order_lifetime_ms"),
    )
    if "cancel_count" in order_statistics:
        cancellation_metrics.setdefault("cancel_count", order_statistics["cancel_count"])
    execution_metrics = _metric_subset(
        features,
        ("execution_count", "execution_ratio", "fill_ratio", "executed_quantity", "trade_count"),
    )
    if "trade_count" in trade_statistics:
        execution_metrics.setdefault("trade_count", trade_statistics["trade_count"])

    request = SurveillanceInvestigationRequest(
        analysis_type=analysis_type,
        invocation_reason=invocation_reason,
        simulation_metadata=_clean_mapping(
            {
                "simulation_id": _first_value(source.get("simulation_id"), trace.get("experiment_id")),
                "episode_id": _first_value(incident.get("incident_id"), incident.get("id"), source.get("episode_id")),
                "scenario_id": _first_value(incident.get("scenario_id"), scenario.get("scenario_id"), trace.get("run_id")),
                "scenario_family": _first_value(incident.get("scenario_family"), scenario.get("scenario_family"), trace.get("scenario")),
                "status": _first_value(source.get("episode_status"), scenario.get("status"), source.get("status")),
                "seed": _first_value(source.get("seed"), scenario.get("seed")),
            }
        ),
        market_regime=_clean_mapping(
            {
                "liquidity": _first_value(source.get("liquidity_regime"), scenario.get("liquidity_regime"), features.get("liquidity_regime")),
                "volatility": _first_value(source.get("volatility_regime"), scenario.get("volatility_regime"), features.get("volatility_regime")),
                "session": _first_value(source.get("session"), features.get("session")),
            }
        ),
        instrument=_clean_mapping(
            {
                "symbol": _first_value(source.get("symbol"), incident.get("symbol"), scenario.get("symbol"), market.get("symbol")),
                "tick_size": _first_value(source.get("tick_size"), market.get("tick_size")),
                "currency": _first_value(source.get("currency"), market.get("currency")),
            }
        ),
        episode_duration=_clean_mapping(
            {
                "start_tick": _first_value(source.get("start_tick"), scenario.get("start_tick")),
                "end_tick": _first_value(source.get("end_tick"), incident.get("tick"), replay.get("window", {}).get("current_tick") if isinstance(replay.get("window"), dict) else None),
                "duration_ticks": _first_value(source.get("duration_ticks"), scenario.get("duration_ticks")),
                "duration_ms": source.get("duration_ms"),
            }
        ),
        suspected_agent=suspected_agent,
        order_statistics=order_statistics,
        trade_statistics=trade_statistics,
        derived_market_features=_clean_mapping(features, limit=32),
        detector_scores=detector_rows,
        event_timeline=_timeline(timeline_source),
        lob_summary=_lob_summary(source, replay, book, market),
        cancellation_metrics=cancellation_metrics,
        execution_metrics=execution_metrics,
        price_movement=_price_movement(source, market, features),
        ground_truth=_optional_clean_mapping(_first_mapping(source.get("ground_truth"), scenario.get("ground_truth"))),
        previous_agent_behaviour=_previous_behaviour(source, replay),
    )
    missing = [
        field
        for field in (
            "market_regime",
            "instrument",
            "episode_duration",
            "suspected_agent",
            "order_statistics",
            "trade_statistics",
            "detector_scores",
            "event_timeline",
            "lob_summary",
        )
        if not getattr(request, field)
    ]
    return request.model_copy(update={"missing_fields": missing})


def build_user_prompt(request: SurveillanceInvestigationRequest) -> dict[str, Any]:
    payload = {
        "task": "Assess the summarized synthetic market episode and return the required professional surveillance JSON.",
        "episode_summary": request.model_dump(mode="json", exclude_none=True),
        "required_response_schema": SurveillanceInvestigationResponse.model_json_schema(),
    }
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    if len(encoded) > MAX_USER_PROMPT_CHARS:
        episode = payload["episode_summary"]
        episode["event_timeline"] = episode.get("event_timeline", [])[:12]
        episode["previous_agent_behaviour"] = episode.get("previous_agent_behaviour", [])[:4]
        episode["derived_market_features"] = dict(list(episode.get("derived_market_features", {}).items())[:16])
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    if len(encoded) > MAX_USER_PROMPT_CHARS:
        raise ValueError("summarized surveillance prompt exceeds the 24,000-character budget")
    return payload


def parse_surveillance_response(payload: dict[str, Any] | None) -> SurveillanceInvestigationResponse | None:
    if payload is None:
        return None
    try:
        return SurveillanceInvestigationResponse.model_validate(payload)
    except ValueError:
        return None


def choose_analysis_type(source: Mapping[str, Any], *, operation: str) -> tuple[AnalysisType | None, str]:
    if operation == "simulation_summary":
        return "simulation_summary", "simulation summary requested"
    if operation == "benchmark_generation":
        return "benchmark_generation", "benchmark report generation requested"
    score = _maximum_score(source)
    if score >= HIGH_ANOMALY_THRESHOLD:
        return "high_anomaly", f"maximum anomaly or detector score {score:.3f} crossed {HIGH_ANOMALY_THRESHOLD:.2f}"
    disagreement = _detector_disagreement(source)
    if disagreement:
        return "detector_disagreement", disagreement
    if _episode_completed(source) and _manipulation_episode(source):
        return "completed_episode", "labelled or suspected manipulation episode completed"
    return None, "no LLM trigger: no high anomaly, detector disagreement, completed manipulation, or aggregate task"


def output_token_budget(request: SurveillanceInvestigationRequest) -> int:
    maximum = max((row.score for row in request.detector_scores), default=0.0)
    if maximum < 0.35 and request.analysis_type in {"simulation_summary", "benchmark_generation"}:
        return 500
    return 1200


def _detector_rows(source: Mapping[str, Any], replay: Mapping[str, Any]) -> list[DetectorScore]:
    rows = _first_list(source.get("detector_scores"), source.get("detector_outputs"), source.get("alerts"), replay.get("detectors"))
    output: list[DetectorScore] = []
    for index, item in enumerate(rows[:MAX_DETECTOR_SCORES]):
        if not isinstance(item, Mapping):
            continue
        score = _bounded_score(item.get("score", item.get("confidence", item.get("suspicion_score", 0.0))))
        output.append(
            DetectorScore(
                detector=str(item.get("detector") or item.get("name") or f"detector_{index + 1}"),
                score=score,
                classification=_optional_string(item.get("classification") or item.get("detected_pattern")),
                alert=item.get("alert") if isinstance(item.get("alert"), bool) else None,
                severity=_optional_string(item.get("severity")),
            )
        )
    return output


def _timeline(rows: list[Any]) -> list[TimelineObservation]:
    output: list[TimelineObservation] = []
    for sequence, item in enumerate(rows[:MAX_TIMELINE_EVENTS], start=1):
        if not isinstance(item, Mapping):
            output.append(TimelineObservation(sequence=sequence, event=str(item)[:300]))
            continue
        output.append(
            TimelineObservation(
                sequence=sequence,
                time=_scalar(item.get("tick", item.get("timestamp", item.get("time")))),
                event=str(item.get("message") or item.get("event") or item.get("type") or "episode event")[:300],
                agent=_optional_string(item.get("agent_id") or item.get("agent")),
                side=_optional_string(item.get("side")),
                price=_optional_float(item.get("price")),
                quantity=_optional_float(item.get("quantity")),
                stage=_optional_string(item.get("stage")),
            )
        )
    return output


def _order_statistics(events: list[Any], features: Mapping[str, Any], suspected_agent: Any) -> dict[str, Any]:
    counts = {"placement_count": 0, "cancel_count": 0, "modification_count": 0}
    sides = {"buy": 0, "sell": 0}
    quantities: list[float] = []
    for item in events[:2000]:
        if not isinstance(item, Mapping):
            continue
        if suspected_agent is not None and item.get("agent_id") not in {None, suspected_agent, str(suspected_agent)}:
            continue
        kind = str(item.get("type") or item.get("event_type") or "").lower()
        if "cancel" in kind:
            counts["cancel_count"] += 1
        elif "modify" in kind or "replace" in kind:
            counts["modification_count"] += 1
        elif "order" in kind or "place" in kind:
            counts["placement_count"] += 1
        side = str(item.get("side") or "").lower()
        if side in sides:
            sides[side] += 1
        quantity = _optional_float(item.get("quantity"))
        if quantity is not None:
            quantities.append(quantity)
    result: dict[str, Any] = {}
    if events:
        result.update({**counts, "buy_events": sides["buy"], "sell_events": sides["sell"]})
    if quantities:
        result.update({"total_order_quantity": round(sum(quantities), 6), "max_order_quantity": max(quantities)})
    result.update(_metric_subset(features, ("order_count", "order_lifetime_ms", "replenishment_count", "side_switch_count")))
    return result


def _trade_statistics(trades: list[Any], features: Mapping[str, Any], suspected_agent: Any) -> dict[str, Any]:
    prices: list[float] = []
    quantities: list[float] = []
    buy_count = 0
    sell_count = 0
    count = 0
    for item in trades[:2000]:
        if not isinstance(item, Mapping):
            continue
        participants = {item.get("agent_id"), item.get("buyer_id"), item.get("seller_id")}
        if suspected_agent is not None and suspected_agent not in participants and str(suspected_agent) not in participants:
            continue
        count += 1
        price = _optional_float(item.get("price"))
        quantity = _optional_float(item.get("quantity"))
        if price is not None:
            prices.append(price)
        if quantity is not None:
            quantities.append(quantity)
        side = str(item.get("side") or "").lower()
        buy_count += side == "buy"
        sell_count += side == "sell"
    result: dict[str, Any] = {}
    if trades:
        result.update({"trade_count": count, "buy_trades": buy_count, "sell_trades": sell_count})
    if quantities:
        result["total_executed_quantity"] = round(sum(quantities), 6)
    if prices:
        result.update({"min_trade_price": min(prices), "max_trade_price": max(prices)})
    result.update(_metric_subset(features, ("trade_count", "trade_volume", "vwap", "buy_volume", "sell_volume")))
    return result


def _lob_summary(
    source: Mapping[str, Any],
    replay: Mapping[str, Any],
    book: Mapping[str, Any],
    market: Mapping[str, Any],
) -> dict[str, Any]:
    supplied = _first_mapping(source.get("lob_summary"), replay.get("lob_summary"))
    if supplied:
        return {
            phase: _clean_mapping(_mapping(supplied.get(phase)), limit=16)
            for phase in ("before", "during", "after")
            if isinstance(supplied.get(phase), Mapping)
        }
    phased_book = _first_mapping(source.get("order_book_context"), replay.get("order_book_context"))
    phased = {
        phase: _summarize_book(_mapping(phased_book.get(phase)), market)
        for phase in ("before", "during", "after")
        if isinstance(phased_book.get(phase), Mapping)
    }
    if phased:
        return phased
    during = _summarize_book(book, market)
    return {"during": during} if during else {}


def _summarize_book(book: Mapping[str, Any], market: Mapping[str, Any]) -> dict[str, Any]:
    bids = book.get("bids") if isinstance(book.get("bids"), list) else []
    asks = book.get("asks") if isinstance(book.get("asks"), list) else []
    bid_depth = sum(_optional_float(row.get("quantity")) or 0.0 for row in bids if isinstance(row, Mapping))
    ask_depth = sum(_optional_float(row.get("quantity")) or 0.0 for row in asks if isinstance(row, Mapping))
    best_bid = _first_value(market.get("best_bid"), _level_value(bids, 0, "price"))
    best_ask = _first_value(market.get("best_ask"), _level_value(asks, 0, "price"))
    return _clean_mapping(
        {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": market.get("mid"),
            "spread": market.get("spread"),
            "bid_depth_top_levels": round(bid_depth, 6),
            "ask_depth_top_levels": round(ask_depth, 6),
            "depth_imbalance": round((bid_depth - ask_depth) / (bid_depth + ask_depth), 6) if bid_depth + ask_depth else None,
            "levels_summarized": {"bids": len(bids), "asks": len(asks)},
        }
    )


def _price_movement(source: Mapping[str, Any], market: Mapping[str, Any], features: Mapping[str, Any]) -> dict[str, Any]:
    return _clean_mapping(
        {
            "mid_before": _first_value(source.get("mid_before"), features.get("mid_before")),
            "mid_during": _first_value(source.get("mid_during"), market.get("mid")),
            "mid_after": _first_value(source.get("mid_after"), features.get("mid_after")),
            "absolute_change": _first_value(source.get("price_change"), features.get("price_change")),
            "change_bps": _first_value(source.get("price_change_bps"), features.get("price_change_bps")),
            "reversion_bps": _first_value(source.get("price_reversion_bps"), features.get("price_reversion_bps")),
        }
    )


def _previous_behaviour(source: Mapping[str, Any], replay: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    rows = _first_list(source.get("previous_agent_behaviour"), replay.get("previous_agent_behaviour"))
    output = [_clean_mapping(item, limit=12) for item in rows[:MAX_PREVIOUS_BEHAVIOURS] if isinstance(item, Mapping)]
    return output or None


def _maximum_score(source: Mapping[str, Any]) -> float:
    values = [source.get("anomaly_score"), source.get("confidence"), source.get("suspicion_score")]
    incident = _mapping(source.get("incident"))
    values.extend((incident.get("confidence"), incident.get("anomaly_score")))
    for item in _trigger_detector_rows(source):
        if isinstance(item, Mapping):
            values.extend((item.get("score"), item.get("confidence"), item.get("suspicion_score")))
    return max((_bounded_score(value) for value in values), default=0.0)


def _detector_disagreement(source: Mapping[str, Any]) -> str | None:
    rows = _trigger_detector_rows(source)
    scores: list[float] = []
    classifications: set[str] = set()
    alerts: set[bool] = set()
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        scores.append(_bounded_score(item.get("score", item.get("confidence", item.get("suspicion_score", 0.0)))))
        classification = item.get("classification") or item.get("detected_pattern")
        if classification:
            classifications.add(str(classification))
        if isinstance(item.get("alert"), bool):
            alerts.add(item["alert"])
    if len(classifications) > 1:
        return f"detectors produced {len(classifications)} competing classifications"
    if len(alerts) > 1:
        return "detectors disagree on whether the episode crosses the alert threshold"
    if len(scores) >= 2 and max(scores) - min(scores) >= DETECTOR_DISAGREEMENT_GAP:
        return f"detector score spread {max(scores) - min(scores):.3f} exceeds {DETECTOR_DISAGREEMENT_GAP:.2f}"
    return None


def _episode_completed(source: Mapping[str, Any]) -> bool:
    values = [source.get("episode_complete"), source.get("completed"), source.get("episode_status"), source.get("status")]
    incident = _mapping(source.get("incident"))
    scenario = _mapping(source.get("scenario"))
    values.extend((incident.get("status"), scenario.get("status"), scenario.get("current_stage")))
    return any(value is True or str(value).lower() in {"completed", "complete", "finished", "resolved"} for value in values)


def _manipulation_episode(source: Mapping[str, Any]) -> bool:
    incident = _mapping(source.get("incident"))
    scenario = _mapping(source.get("scenario"))
    ground_truth = _first_mapping(source.get("ground_truth"), scenario.get("ground_truth"))
    explicit = _first_value(source.get("is_manipulation"), ground_truth.get("is_manipulation"))
    if isinstance(explicit, bool):
        return explicit
    labels = (
        source.get("manipulation_type"),
        source.get("scenario_hint"),
        incident.get("type"),
        incident.get("scenario_family"),
        scenario.get("manipulation_type"),
        scenario.get("scenario_family"),
        ground_truth.get("label"),
        ground_truth.get("manipulation_type"),
    )
    benign = {"", "none", "normal", "normal_market", "benign", "market_making", "unknown"}
    return any(value is not None and str(value).strip().lower() not in benign for value in labels)


def _trigger_detector_rows(source: Mapping[str, Any]) -> list[Any]:
    replay = _mapping(source.get("replay"))
    return _first_list(
        source.get("detector_scores"),
        source.get("detector_outputs"),
        source.get("alerts"),
        replay.get("detectors"),
    )


def _clean_mapping(value: Mapping[str, Any], *, limit: int = 24) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, item in list(value.items())[:limit]:
        if item is None:
            continue
        if isinstance(item, (str, int, float, bool)):
            output[str(key)] = item[:500] if isinstance(item, str) else item
        elif isinstance(item, Mapping):
            output[str(key)] = _clean_mapping(item, limit=12)
        elif isinstance(item, list) and all(isinstance(part, (str, int, float, bool)) for part in item[:12]):
            output[str(key)] = item[:12]
    return output


def _metric_subset(source: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return _clean_mapping({key: source.get(key) for key in keys})


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_mapping(*values: Any) -> Mapping[str, Any]:
    return next((_mapping(value) for value in values if isinstance(value, Mapping) and value), {})


def _optional_clean_mapping(value: Mapping[str, Any]) -> dict[str, Any] | None:
    cleaned = _clean_mapping(value, limit=20)
    return cleaned or None


def _first_list(*values: Any) -> list[Any]:
    return next((value for value in values if isinstance(value, list) and value), [])


def _first_value(*values: Any) -> Any:
    return next((value for value in values if value is not None and value != ""), None)


def _scalar(value: Any) -> str | int | float | bool | None:
    return value if isinstance(value, (str, int, float, bool)) else None


def _optional_string(value: Any) -> str | None:
    return str(value)[:200] if value is not None and str(value).strip() else None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _bounded_score(value: Any) -> float:
    number = _optional_float(value) or 0.0
    return max(0.0, min(1.0, number))


def _level_value(rows: list[Any], index: int, key: str) -> Any:
    if len(rows) <= index or not isinstance(rows[index], Mapping):
        return None
    return rows[index].get(key)

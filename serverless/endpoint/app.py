import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI
from pydantic import BaseModel, Field

from prompts import INCIDENT_EXPLANATION_SYSTEM_PROMPT, SCENARIO_GENERATOR_SYSTEM_PROMPT

DISCLAIMER = (
    "Educational synthetic simulation only. This does not detect real market manipulation, "
    "does not provide trading signals, and must not be used for compliance decisions."
)

app = FastAPI(title="Nebius Market Abuse Arena Serverless Endpoint")


class EvidenceItem(BaseModel):
    key: str
    label: str
    value: str | int | float | bool
    unit: str | None = None
    interpretation: str | None = None


class IncidentExplanationRequest(BaseModel):
    incident_id: str
    title: str
    type: str
    agent: str
    confidence: float = Field(ge=0.0, le=1.0)
    severity: str
    scenario_id: str | None = None
    scenario_family: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    replay: dict[str, Any] | None = None


class IncidentExplanationResponse(BaseModel):
    incident_id: str
    risk_level: str
    plain_english_summary: str
    evidence: list[str]
    recommended_action: str
    disclaimer: str = DISCLAIMER


class ScenarioGenerationRequest(BaseModel):
    prompt: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class ScenarioGenerationResponse(BaseModel):
    scenario_type: str
    title: str
    description: str
    parameters: dict[str, Any]
    expected_detector_risk: float = Field(ge=0.0, le=1.0)
    safety_note: str = DISCLAIMER


class L2Level(BaseModel):
    price: float
    quantity: float
    owner: str | None = None
    agent_id: str | None = None
    scenario_id: str | None = None
    scenario_name: str | None = None


class OrderBookWindow(BaseModel):
    bids: list[L2Level] = Field(default_factory=list)
    asks: list[L2Level] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    scenario_hint: str | None = None
    tick: int | None = None


class OrderBookAlertResponse(BaseModel):
    suspicion_score: float = Field(ge=0.0, le=1.0)
    detected_pattern: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    recommended_action: str
    model_mode: str
    disclaimer: str = DISCLAIMER


class InvestigationReportRequest(BaseModel):
    scenario_trace: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class InvestigationReportResponse(BaseModel):
    title: str
    summary: str
    timeline: list[str]
    detector_findings: list[str]
    limitations: list[str]
    recommended_next_steps: list[str]
    disclaimer: str = DISCLAIMER


class ExplainPayload(BaseModel):
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "nebius-market-abuse-arena-endpoint",
        "model_mode": "ai_studio" if _model_enabled() else "deterministic_fallback",
    }


@app.post("/orderbook-alert", response_model=OrderBookAlertResponse)
def orderbook_alert(request: OrderBookWindow) -> OrderBookAlertResponse:
    fallback = _deterministic_orderbook_alert(request)
    model_response = _call_model_json(
        system_prompt=(
            "Return JSON with suspicion_score, detected_pattern, confidence, reasons, "
            "and recommended_action for a synthetic educational L2 order-book window. "
            "Never claim real market surveillance capability."
        ),
        user_payload=request.model_dump(mode="json"),
    )
    if model_response is None:
        return fallback
    return _merge_alert_response(fallback, model_response)


@app.post("/investigation-report", response_model=InvestigationReportResponse)
def investigation_report(request: InvestigationReportRequest) -> InvestigationReportResponse:
    fallback = _deterministic_investigation_report(request)
    model_response = _call_model_json(
        system_prompt=(
            "Return a JSON market-abuse case report for an educational synthetic trace. "
            "Required keys: title, summary, timeline, detector_findings, limitations, "
            "recommended_next_steps. Avoid real-world enforcement or trading advice."
        ),
        user_payload=request.model_dump(mode="json"),
    )
    if model_response is None:
        return fallback
    return _merge_report_response(fallback, model_response)


@app.post("/explain-event", response_model=IncidentExplanationResponse)
def explain_event(request: IncidentExplanationRequest) -> IncidentExplanationResponse:
    fallback = _deterministic_explanation(request)
    model_response = _call_model_json(
        system_prompt=INCIDENT_EXPLANATION_SYSTEM_PROMPT,
        user_payload=request.model_dump(mode="json"),
    )
    if model_response is None:
        return fallback
    return _merge_explanation_response(request, fallback, model_response)


@app.post("/explain-simulation")
def explain_simulation(request: ExplainPayload) -> dict[str, Any]:
    summary = _call_model_json(
        system_prompt=INCIDENT_EXPLANATION_SYSTEM_PROMPT,
        user_payload={"task": "explain_simulation", **request.payload},
    )
    if summary is not None:
        return {"summary": summary, "disclaimer": DISCLAIMER}
    return {
        "summary": "Synthetic simulation completed with deterministic detector outputs and bounded scenario labels.",
        "payload": request.payload,
        "disclaimer": DISCLAIMER,
    }


@app.post("/generate-report")
@app.post("/generate-incident-report")
def generate_incident_report(request: ExplainPayload) -> dict[str, Any]:
    summary = _call_model_json(
        system_prompt=INCIDENT_EXPLANATION_SYSTEM_PROMPT,
        user_payload={"task": "generate_report", **request.payload},
    )
    if summary is not None:
        return {"report": summary, "disclaimer": DISCLAIMER}
    return {
        "report": "Synthetic incident report generated from deterministic evidence. Review detector scores, replay window, and labels.",
        "payload": request.payload,
        "disclaimer": DISCLAIMER,
    }


@app.post("/generate-scenario", response_model=ScenarioGenerationResponse)
def generate_scenario(request: ScenarioGenerationRequest) -> ScenarioGenerationResponse:
    fallback = _deterministic_scenario(request)
    model_response = _call_model_json(
        system_prompt=SCENARIO_GENERATOR_SYSTEM_PROMPT,
        user_payload=request.model_dump(mode="json"),
    )
    if model_response is None:
        return fallback
    return _merge_scenario_response(fallback, model_response)


@app.post("/generate-smart-scenario", response_model=ScenarioGenerationResponse)
def generate_smart_scenario(request: ScenarioGenerationRequest) -> ScenarioGenerationResponse:
    return generate_scenario(request)


def _model_enabled() -> bool:
    return bool(os.environ.get("NEBIUS_API_KEY")) and os.environ.get("NEBIUS_ENDPOINT_MODE", "mock") == "ai"


def _call_model_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any] | None:
    if not _model_enabled():
        return None

    api_key = os.environ["NEBIUS_API_KEY"]
    base_url = os.environ.get("NEBIUS_AI_STUDIO_BASE_URL", "https://api.studio.nebius.com/v1")
    model = os.environ.get("NEBIUS_AI_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    temperature = float(os.environ.get("NEBIUS_TEMPERATURE", "0.2"))
    max_tokens = int(os.environ.get("NEBIUS_MAX_TOKENS", "800"))
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, separators=(",", ":"))},
        ],
    }
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=float(os.environ.get("NEBIUS_REQUEST_TIMEOUT_SECONDS", "12"))) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    try:
        content = decoded["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def _deterministic_explanation(request: IncidentExplanationRequest) -> IncidentExplanationResponse:
    evidence = [
        f"{item.label}: {item.value}{f' {item.unit}' if item.unit else ''}"
        for item in request.evidence
    ]
    replay = request.replay or {}
    market = replay.get("market", {}) if isinstance(replay, dict) else {}
    market_summary = ""
    if market:
        market_summary = (
            f" Current replay context has mid={market.get('mid')} and spread={market.get('spread')}."
        )
    return IncidentExplanationResponse(
        incident_id=request.incident_id,
        risk_level=request.severity.lower(),
        plain_english_summary=(
            f"{request.title} was flagged in the synthetic arena with detector confidence "
            f"{request.confidence:.2f}.{market_summary}"
        ),
        evidence=evidence,
        recommended_action="Flag this synthetic interval for manual review in the demo replay.",
    )


def _merge_explanation_response(
    request: IncidentExplanationRequest,
    fallback: IncidentExplanationResponse,
    response: dict[str, Any],
) -> IncidentExplanationResponse:
    evidence = response.get("evidence", fallback.evidence)
    if isinstance(evidence, str):
        evidence = [evidence]
    if not isinstance(evidence, list):
        evidence = fallback.evidence
    return IncidentExplanationResponse(
        incident_id=str(response.get("incident_id") or request.incident_id),
        risk_level=str(response.get("risk_level") or fallback.risk_level),
        plain_english_summary=str(response.get("plain_english_summary") or fallback.plain_english_summary),
        evidence=[str(item) for item in evidence],
        recommended_action=str(response.get("recommended_action") or fallback.recommended_action),
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )


def _deterministic_orderbook_alert(request: OrderBookWindow) -> OrderBookAlertResponse:
    features = request.features
    wall_size_ratio = _float_feature(features, "wall_size_ratio")
    message_rate = _float_feature(features, "message_rate")
    cancel_to_trade_ratio = _float_feature(features, "cancel_to_trade_ratio")
    depth_change_pct = _float_feature(features, "depth_change_pct")
    imbalance = abs(_float_feature(features, "imbalance"))
    scenario_hint = (request.scenario_hint or "").lower().replace("-", "_")

    pattern = "normal_market"
    score = 0.12
    reasons = ["No dominant synthetic abuse-like pattern crossed the alert threshold."]

    if scenario_hint in {"spoofing", "spoofing_like", "spoofing_like_wall"} or wall_size_ratio >= 5.0:
        pattern = "spoofing_like_wall"
        score = min(0.98, 0.48 + wall_size_ratio / 12.0 + imbalance / 3.0)
        reasons = [
            f"Wall size ratio is {wall_size_ratio:.2f}.",
            f"Top-of-book imbalance magnitude is {imbalance:.2f}.",
        ]
    elif scenario_hint in {"layering", "layering_like"} or depth_change_pct >= 0.45:
        pattern = "layering_like"
        score = min(0.95, 0.44 + depth_change_pct + message_rate / 80.0)
        reasons = [
            f"Depth changed by {depth_change_pct:.2f}.",
            f"Message rate is {message_rate:.2f} events/sec.",
        ]
    elif scenario_hint in {"quote_stuffing", "quote_stuffing_like"} or message_rate >= 18.0:
        pattern = "quote_stuffing"
        score = min(0.97, 0.40 + message_rate / 45.0 + cancel_to_trade_ratio / 15.0)
        reasons = [
            f"Message rate is {message_rate:.2f} events/sec.",
            f"Cancel-to-trade ratio is {cancel_to_trade_ratio:.2f}.",
        ]
    elif scenario_hint in {"pump_and_cancel", "pump_cancel"} or cancel_to_trade_ratio >= 8.0:
        pattern = "pump_and_cancel"
        score = min(0.94, 0.42 + cancel_to_trade_ratio / 16.0 + depth_change_pct / 2.0)
        reasons = [
            f"Cancel-to-trade ratio is {cancel_to_trade_ratio:.2f}.",
            f"Depth changed by {depth_change_pct:.2f}.",
        ]

    confidence = max(0.05, min(1.0, score))
    return OrderBookAlertResponse(
        suspicion_score=round(confidence, 4),
        detected_pattern=pattern,
        confidence=round(confidence, 4),
        reasons=reasons,
        recommended_action="Keep this synthetic interval in the demo investigation queue.",
        model_mode="deterministic_fallback",
    )


def _merge_alert_response(
    fallback: OrderBookAlertResponse,
    response: dict[str, Any],
) -> OrderBookAlertResponse:
    reasons = response.get("reasons", fallback.reasons)
    if isinstance(reasons, str):
        reasons = [reasons]
    if not isinstance(reasons, list):
        reasons = fallback.reasons
    suspicion_score = _bounded_float(response.get("suspicion_score"), fallback.suspicion_score)
    confidence = _bounded_float(response.get("confidence"), suspicion_score)
    return OrderBookAlertResponse(
        suspicion_score=suspicion_score,
        detected_pattern=str(response.get("detected_pattern") or fallback.detected_pattern),
        confidence=confidence,
        reasons=[str(item) for item in reasons],
        recommended_action=str(response.get("recommended_action") or fallback.recommended_action),
        model_mode="ai_studio",
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )


def _deterministic_investigation_report(request: InvestigationReportRequest) -> InvestigationReportResponse:
    trace = request.scenario_trace
    scenario = str(trace.get("scenario") or trace.get("scenario_name") or "synthetic scenario")
    alert_count = len(request.alerts)
    metric_bits = [
        f"{key}={value}"
        for key, value in sorted(request.metrics.items())
        if key in {"precision", "recall", "f1", "avg_detection_latency_ms", "runtime_seconds"}
    ]
    return InvestigationReportResponse(
        title=f"Synthetic investigation report: {scenario}",
        summary=(
            f"The trace contains {alert_count} alert(s) for {scenario}. "
            "Detector evidence is suitable for educational replay and benchmark review only."
        ),
        timeline=[
            "Scenario generated inside the synthetic order-book simulator.",
            "Detector confidence crossed the configured alert threshold.",
            "Evidence and labels were archived as benchmark artifacts.",
        ],
        detector_findings=metric_bits or ["Structured detector metrics were included in the artifact bundle."],
        limitations=[
            "Synthetic labels are generated by scenario injection, not by real surveillance review.",
            "Results must not be interpreted as real-world market abuse detection performance.",
        ],
        recommended_next_steps=[
            "Open the replay drawer and compare alert timing with scenario labels.",
            "Archive Nebius job logs, endpoint logs, metrics, and generated artifacts for submission.",
        ],
    )


def _merge_report_response(
    fallback: InvestigationReportResponse,
    response: dict[str, Any],
) -> InvestigationReportResponse:
    return InvestigationReportResponse(
        title=str(response.get("title") or fallback.title),
        summary=str(response.get("summary") or fallback.summary),
        timeline=_string_list(response.get("timeline"), fallback.timeline),
        detector_findings=_string_list(response.get("detector_findings"), fallback.detector_findings),
        limitations=_string_list(response.get("limitations"), fallback.limitations),
        recommended_next_steps=_string_list(
            response.get("recommended_next_steps"),
            fallback.recommended_next_steps,
        ),
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )


def _deterministic_scenario(request: ScenarioGenerationRequest) -> ScenarioGenerationResponse:
    constraints = request.constraints
    scenario_family = str(constraints.get("scenario_family") or constraints.get("scenario_type") or "spoofing_like_wall")
    scenario_type = _normalize_scenario_type(scenario_family)
    goal = str(constraints.get("goal") or "obvious")
    market_regime = str(constraints.get("market_regime") or "calm")
    risk = 0.82 if goal == "obvious" else 0.68 if goal == "stealth" else 0.58
    return ScenarioGenerationResponse(
        scenario_type=scenario_type,
        title=f"{scenario_type.replace('_', ' ').title()} draft",
        description=(
            f"Bounded {scenario_type.replace('_', ' ')} scenario for a {market_regime} synthetic market, "
            f"optimized for goal={goal}."
        ),
        parameters={
            "market_regime": market_regime,
            "goal": goal,
            "wall_size_multiplier": constraints.get("wall_size_multiplier", 8),
            "lifetime_seconds": constraints.get("lifetime_seconds", 5),
            "distance_from_mid_bps": constraints.get("distance_from_mid_bps", 12),
        },
        expected_detector_risk=risk,
    )


def _merge_scenario_response(
    fallback: ScenarioGenerationResponse,
    response: dict[str, Any],
) -> ScenarioGenerationResponse:
    parameters = response.get("parameters", fallback.parameters)
    if not isinstance(parameters, dict):
        parameters = fallback.parameters
    risk = response.get("expected_detector_risk", fallback.expected_detector_risk)
    try:
        risk_float = max(0.0, min(1.0, float(risk)))
    except (TypeError, ValueError):
        risk_float = fallback.expected_detector_risk
    return ScenarioGenerationResponse(
        scenario_type=_normalize_scenario_type(str(response.get("scenario_type") or fallback.scenario_type)),
        title=str(response.get("title") or fallback.title),
        description=str(response.get("description") or fallback.description),
        parameters=parameters,
        expected_detector_risk=risk_float,
        safety_note=str(response.get("safety_note") or DISCLAIMER),
    )


def _normalize_scenario_type(value: str) -> str:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "spoofing": "spoofing_like_wall",
        "spoofing_like": "spoofing_like_wall",
        "spoofing_like_wall": "spoofing_like_wall",
        "layering": "layering_like",
        "layering_like": "layering_like",
        "quote_stuffing": "quote_stuffing",
        "quote_stuffing_like": "quote_stuffing",
        "liquidity_evaporation": "liquidity_evaporation",
        "liquidity_shock": "liquidity_evaporation",
    }
    return mapping.get(normalized, "spoofing_like_wall")


def _float_feature(features: dict[str, Any], key: str) -> float:
    try:
        return float(features.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bounded_float(value: Any, fallback: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return fallback


def _string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return fallback

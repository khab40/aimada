import json
import os
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI
from pydantic import BaseModel, Field

from prompts import SCENARIO_GENERATOR_SYSTEM_PROMPT
from surveillance import (
    SURVEILLANCE_SYSTEM_PROMPT,
    SurveillanceInvestigationResponse,
    build_surveillance_request,
    build_user_prompt,
    choose_analysis_type,
    output_token_budget,
    parse_surveillance_response,
)

import logging

logger = logging.getLogger("aimada-endpoint")

JSON_ONLY_INSTRUCTION = (
    "Return ONLY valid JSON. Do not use markdown. Do not wrap the JSON in code fences. "
    "Do not add explanatory text before or after the JSON. "
)

DISCLAIMER = (
    "Educational synthetic simulation only. This does not detect real market manipulation, "
    "does not provide trading signals, and must not be used for compliance decisions."
)
DEFAULT_LOCAL_VLLM_HOST = "127.0.0.1"
DEFAULT_LOCAL_VLLM_PORT = "8001"
DEFAULT_LOCAL_VLLM_MODEL = "Qwen/Qwen2.5-14B-Instruct"
DEFAULT_ENDPOINT_MODEL = DEFAULT_LOCAL_VLLM_MODEL


app = FastAPI(
    title="AI Market Abuse Detection Arena Serverless Endpoint",
)


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
    model_mode: str = "deterministic_fallback"
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
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
    model_mode: str = "deterministic_fallback"
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
    safety_note: str = DISCLAIMER


class MarketAbuseScenarioGenerationRequest(BaseModel):
    manipulation_type: Literal["spoofing", "layering", "wash_trading", "quote_stuffing"] = "spoofing"
    difficulty: Literal["easy", "medium", "hard", "adversarial"] = "medium"
    symbol: str = Field(default="AIMD", min_length=1, max_length=16)
    duration_ticks: int = Field(default=120, ge=30, le=600)
    liquidity_regime: Literal["thin", "normal", "deep"] = "thin"
    volatility_regime: Literal["low", "medium", "high"] = "high"
    seed: int | None = None


class ScenarioEvent(BaseModel):
    event_id: str
    tick: int = Field(ge=0)
    event_type: Literal["place_order", "cancel_order", "trade", "quote_update"]
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
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketAbuseScenarioResponse(BaseModel):
    scenario_id: str
    title: str
    description: str
    manipulation_type: str
    difficulty: str
    symbol: str
    duration_ticks: int
    liquidity_regime: str
    volatility_regime: str
    ground_truth: dict[str, Any]
    events: list[ScenarioEvent]
    expected_detector_behavior: dict[str, Any]
    explanation: str
    replay: dict[str, Any]
    source: dict[str, Any]
    model_mode: str = "deterministic_fallback"
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
    disclaimer: str = DISCLAIMER


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
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
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
    model_mode: str = "deterministic_fallback"
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
    disclaimer: str = DISCLAIMER


class TeamEvidenceItem(BaseModel):
    key: str
    label: str
    value: str | int | float | bool
    source: str | None = None


class EvidenceTimelineItem(BaseModel):
    sequence: int
    event: str
    tick: int | str | None = None
    source: str | None = None
    significance: str | None = None


class AgentFinding(BaseModel):
    name: str
    role: str
    finding: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[TeamEvidenceItem] = Field(default_factory=list)


class AIInvestigationTeamRequest(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)
    detector_outputs: list[dict[str, Any]] = Field(default_factory=list)
    order_book_context: dict[str, Any] = Field(default_factory=dict)
    trades: list[dict[str, Any]] = Field(default_factory=list)
    market_metrics: dict[str, Any] = Field(default_factory=dict)


class AIInvestigationTeamResponse(BaseModel):
    investigation_id: str
    manipulation_type: str
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    agents: list[AgentFinding]
    consensus: str
    evidence_timeline: list[EvidenceTimelineItem]
    recommended_action: str
    executive_summary: str
    model_mode: str = "deterministic_fallback"
    model: str = DEFAULT_ENDPOINT_MODEL
    latency_ms: float = 0.0
    fallback_reason: str | None = None
    disclaimer: str = DISCLAIMER


class ExplainPayload(BaseModel):
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "ai-market-abuse-detection-arena-endpoint",
        "endpoint_mode": _endpoint_mode(),
        "model_mode": _active_model_mode(),
        "model": _active_model_name(),
        "local_vllm_base_url": _local_vllm_base_url(),
        "local_vllm_model": _local_vllm_model(),
        "credentials_configured": _credentials_configured(),
    }


@app.get("/ready")
def ready() -> dict[str, str | bool]:
    return {
        "status": "ready",
        "service": "ai-market-abuse-detection-arena-endpoint",
        "endpoint_mode": _endpoint_mode(),
        "model_mode": _active_model_mode(),
        "model": _active_model_name(),
        "local_vllm_base_url": _local_vllm_base_url(),
        "local_vllm_model": _local_vllm_model(),
        "credentials_configured": _credentials_configured(),
    }


@app.post("/orderbook-alert", response_model=OrderBookAlertResponse)
def orderbook_alert(request: OrderBookWindow) -> OrderBookAlertResponse:
    fallback = _deterministic_orderbook_alert(request)
    model_response, assessment = _call_surveillance_analysis(
        {
            "anomaly_score": fallback.suspicion_score,
            "book": {"bids": request.model_dump(mode="json")["bids"], "asks": request.model_dump(mode="json")["asks"]},
            "detector_scores": [
                {
                    "alert": fallback.suspicion_score >= 0.75,
                    "classification": fallback.detected_pattern,
                    "detector": "deterministic_orderbook_screen",
                    "score": fallback.suspicion_score,
                }
            ],
            "events": request.events,
            "features": request.features,
            "scenario": {"scenario_family": request.scenario_hint},
            "end_tick": request.tick,
        },
        operation="event_screening",
    )
    if assessment is None:
        _log_fallback("orderbook_alert", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    payload = _assessment_to_alert(assessment, fallback)
    return _merge_alert_response(fallback, payload, model_response)


@app.post("/investigation-report", response_model=InvestigationReportResponse)
def investigation_report(request: InvestigationReportRequest) -> InvestigationReportResponse:
    fallback = _deterministic_investigation_report(request)
    model_response, assessment = _call_surveillance_analysis(
        request.model_dump(mode="json"),
        operation="benchmark_generation",
    )
    if assessment is None:
        _log_fallback("investigation_report", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    payload = _assessment_to_report(assessment)
    return _merge_report_response(fallback, payload, model_response)


@app.post("/investigation-team", response_model=AIInvestigationTeamResponse)
def investigation_team(request: AIInvestigationTeamRequest) -> AIInvestigationTeamResponse:
    fallback = _deterministic_investigation_team(request)
    model_response, assessment = _call_surveillance_analysis(
        request.model_dump(mode="json"),
        operation="episode_analysis",
    )
    if assessment is None:
        _log_fallback("investigation_team", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    payload = _assessment_to_investigation_team(assessment, fallback)
    return _merge_investigation_team_response(fallback, payload, model_response)


@app.post("/explain-event", response_model=IncidentExplanationResponse)
def explain_event(request: IncidentExplanationRequest) -> IncidentExplanationResponse:
    fallback = _deterministic_explanation(request)
    source = request.model_dump(mode="json")
    source["incident"] = {
        "agent": request.agent,
        "confidence": request.confidence,
        "id": request.incident_id,
        "scenario_family": request.scenario_family,
        "scenario_id": request.scenario_id,
        "severity": request.severity,
        "title": request.title,
        "type": request.type,
    }
    model_response, assessment = _call_surveillance_analysis(
        source,
        operation="episode_analysis",
    )
    if assessment is None:
        _log_fallback("explain_event", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    payload = _assessment_to_explanation(assessment)
    return _merge_explanation_response(request, fallback, payload, model_response)


@app.post("/explain-simulation")
def explain_simulation(request: ExplainPayload) -> dict[str, Any]:
    summary, assessment = _call_surveillance_analysis(
        request.payload,
        operation="simulation_summary",
    )
    if assessment is not None:
        return {
            "summary": assessment.model_dump(mode="json"),
            "model_mode": summary.model_mode,
            "model": summary.model,
            "latency_ms": summary.latency_ms,
            "fallback_reason": summary.fallback_reason,
            "disclaimer": DISCLAIMER,
        }
    _log_fallback("explain_simulation", summary)
    return {
        "summary": "Synthetic simulation completed with deterministic detector outputs and bounded scenario labels.",
        "payload": request.payload,
        "model_mode": summary.model_mode,
        "model": summary.model,
        "latency_ms": summary.latency_ms,
        "fallback_reason": summary.fallback_reason,
        "disclaimer": DISCLAIMER,
    }


@app.post("/generate-report")
@app.post("/generate-incident-report")
def generate_incident_report(request: ExplainPayload) -> dict[str, Any]:
    summary, assessment = _call_surveillance_analysis(
        request.payload,
        operation="benchmark_generation",
    )
    if assessment is not None:
        return {
            "report": assessment.model_dump(mode="json"),
            "model_mode": summary.model_mode,
            "model": summary.model,
            "latency_ms": summary.latency_ms,
            "fallback_reason": summary.fallback_reason,
            "disclaimer": DISCLAIMER,
        }
    _log_fallback("generate_incident_report", summary)
    return {
        "report": "Synthetic incident report generated from deterministic evidence. Review detector scores, replay window, and labels.",
        "payload": request.payload,
        "model_mode": summary.model_mode,
        "model": summary.model,
        "latency_ms": summary.latency_ms,
        "fallback_reason": summary.fallback_reason,
        "disclaimer": DISCLAIMER,
    }


@app.post("/generate-scenario", response_model=ScenarioGenerationResponse)
def generate_scenario(request: ScenarioGenerationRequest) -> ScenarioGenerationResponse:
    fallback = _deterministic_scenario(request)
    model_response = _call_model_json(
        system_prompt=(
            JSON_ONLY_INSTRUCTION
            + SCENARIO_GENERATOR_SYSTEM_PROMPT
            + " Return a JSON object with exactly these keys: scenario_type, title, description, parameters, expected_detector_risk. "
            "scenario_type, title, and description must be strings. "
            "parameters must be an object. expected_detector_risk must be a number between 0 and 1."
        ),
        user_payload=request.model_dump(mode="json"),
    )
    payload = _validated_model_payload(
        model_response,
        {
            "scenario_type": str,
            "title": str,
            "description": str,
            "parameters": dict,
            "expected_detector_risk": "number",
        },
    )
    if payload is None:
        _log_fallback("generate_scenario", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    return _merge_scenario_response(fallback, payload, model_response)


@app.post("/generate-market-abuse-scenario", response_model=MarketAbuseScenarioResponse)
def generate_market_abuse_scenario(request: MarketAbuseScenarioGenerationRequest) -> MarketAbuseScenarioResponse:
    fallback = _deterministic_market_abuse_scenario(request)
    model_response = _call_model_json(
        system_prompt=(
            JSON_ONLY_INSTRUCTION
            + "You explain a bounded educational synthetic market-abuse scenario for an order-book simulator. "
            "Return a compact JSON object with exactly these string keys: title, description, explanation. "
            "The simulator, labels, event schedule, replay route, and detector targets are supplied separately "
            "by deterministic code and must not be recreated. "
            "Use synthetic educational data only and do not provide real manipulation instructions."
        ),
        user_payload={
            "task": "Describe the bounded synthetic scenario without changing its deterministic contract.",
            "scenario": request.model_dump(mode="json"),
        },
    )
    payload = _validated_model_payload(
        model_response,
        {
            "title": str,
            "description": str,
            "explanation": str,
        },
    )
    if payload is None:
        _log_fallback("generate_market_abuse_scenario", model_response)
        return _with_model_metadata(fallback, _fallback_model_result(model_response))
    return _merge_market_abuse_scenario_response(fallback, payload, model_response)


@app.post("/generate-smart-scenario", response_model=ScenarioGenerationResponse)
def generate_smart_scenario(request: ScenarioGenerationRequest) -> ScenarioGenerationResponse:
    return generate_scenario(request)


@dataclass(frozen=True)
class ModelCallResult:
    payload: dict[str, Any] | None
    model_mode: str
    model: str
    latency_ms: float = 0.0
    fallback_reason: str | None = None


def _call_surveillance_analysis(
    source: dict[str, Any],
    *,
    operation: str,
) -> tuple[ModelCallResult, SurveillanceInvestigationResponse | None]:
    analysis_type, reason = choose_analysis_type(source, operation=operation)
    if analysis_type is None:
        return (
            ModelCallResult(
                payload=None,
                model_mode="deterministic_fallback",
                model=_active_model_name(),
                fallback_reason="llm_not_triggered",
            ),
            None,
        )
    try:
        prompt_request = build_surveillance_request(
            source,
            analysis_type=analysis_type,
            invocation_reason=reason,
        )
        user_prompt = build_user_prompt(prompt_request)
    except ValueError:
        logger.exception("Surveillance prompt construction failed")
        return (
            ModelCallResult(
                payload=None,
                model_mode="deterministic_fallback",
                model=_active_model_name(),
                fallback_reason="prompt_budget_exceeded",
            ),
            None,
        )
    result = _call_model_json(
        system_prompt=SURVEILLANCE_SYSTEM_PROMPT,
        user_payload=user_prompt,
        max_tokens=output_token_budget(prompt_request),
    )
    return result, parse_surveillance_response(result.payload)


def _assessment_to_alert(
    assessment: SurveillanceInvestigationResponse,
    fallback: OrderBookAlertResponse,
) -> dict[str, Any]:
    reasons = [
        f"{item.observation} Metric {item.metric}={item.value}. {item.reasoning}"
        for item in assessment.evidence[:5]
    ]
    reasons.extend(f"Counter-evidence: {item.observation}" for item in assessment.counter_evidence[:2])
    return {
        "suspicion_score": max(fallback.suspicion_score, assessment.confidence),
        "detected_pattern": assessment.classification,
        "confidence": assessment.confidence,
        "reasons": reasons or [assessment.executive_summary],
        "recommended_action": assessment.recommended_actions[0]
        if assessment.recommended_actions
        else fallback.recommended_action,
    }


def _assessment_to_report(assessment: SurveillanceInvestigationResponse) -> dict[str, Any]:
    return {
        "title": f"Synthetic episode assessment: {assessment.classification}",
        "summary": assessment.executive_summary,
        "timeline": assessment.episode_timeline,
        "detector_findings": [
            f"{item.observation} ({item.metric}={item.value}): {item.reasoning}"
            for item in assessment.evidence
        ] + [assessment.detector_disagreement],
        "limitations": [
            *(f"Counter-evidence: {item.observation}" for item in assessment.counter_evidence),
            *(f"Alternative: {item}" for item in assessment.alternative_explanations),
            assessment.regulatory_assessment,
        ],
        "recommended_next_steps": assessment.recommended_actions,
    }


def _assessment_to_explanation(assessment: SurveillanceInvestigationResponse) -> dict[str, Any]:
    return {
        "risk_level": assessment.severity,
        "plain_english_summary": assessment.executive_summary,
        "evidence": [
            f"{item.observation} ({item.metric}={item.value}): {item.reasoning}"
            for item in assessment.evidence
        ],
        "recommended_action": assessment.recommended_actions[0]
        if assessment.recommended_actions
        else "Review the synthetic episode and retain the summarized evidence.",
    }


def _assessment_to_investigation_team(
    assessment: SurveillanceInvestigationResponse,
    fallback: AIInvestigationTeamResponse,
) -> dict[str, Any]:
    evidence = [
        {
            "key": f"assessment_{index}",
            "label": item.metric,
            "value": item.value,
            "source": "professional_surveillance_assessment",
        }
        for index, item in enumerate(assessment.evidence[:5], start=1)
    ]
    findings = [
        assessment.market_context,
        assessment.executive_summary,
        assessment.detector_disagreement,
        assessment.regulatory_assessment,
        f"Classification {assessment.classification}; confidence {assessment.confidence:.2f}.",
    ]
    agents = []
    for index, agent in enumerate(fallback.agents):
        agents.append(
            {
                "name": agent.name,
                "role": agent.role,
                "finding": findings[index],
                "confidence": assessment.confidence,
                "evidence": evidence,
            }
        )
    return {
        "investigation_id": fallback.investigation_id,
        "manipulation_type": assessment.classification,
        "risk_score": _severity_score(assessment.severity),
        "confidence": assessment.confidence,
        "agents": agents,
        "consensus": assessment.executive_summary,
        "evidence_timeline": [
            {
                "sequence": index,
                "event": item,
                "tick": None,
                "source": "professional_surveillance_assessment",
                "significance": "episode reconstruction",
            }
            for index, item in enumerate(assessment.episode_timeline, start=1)
        ],
        "recommended_action": assessment.recommended_actions[0]
        if assessment.recommended_actions
        else fallback.recommended_action,
        "executive_summary": assessment.executive_summary,
    }


def _severity_score(severity: str) -> float:
    return {
        "informational": 0.1,
        "low": 0.25,
        "medium": 0.5,
        "high": 0.75,
        "critical": 0.95,
    }.get(severity, 0.5)


def _endpoint_mode() -> str:
    return os.environ.get("NEBIUS_ENDPOINT_MODE", "mock").strip().lower() or "mock"


def _credentials_configured() -> bool:
    return False


def _active_model_mode() -> str:
    if _local_vllm_enabled():
        return "local_vllm"
    return "deterministic_fallback"


def _local_vllm_enabled() -> bool:
    return _endpoint_mode() == "local_vllm"


def _active_model_name() -> str:
    if _local_vllm_enabled():
        return _local_vllm_model()
    return DEFAULT_ENDPOINT_MODEL


def _call_model_json(
    system_prompt: str,
    user_payload: dict[str, Any],
    *,
    max_tokens: int = 400,
) -> ModelCallResult:
    if _local_vllm_enabled():
        return _call_local_vllm_json(system_prompt, user_payload, max_tokens=max_tokens)
    return ModelCallResult(
        payload=None,
        model_mode="deterministic_fallback",
        model=DEFAULT_ENDPOINT_MODEL,
        fallback_reason="mock_mode" if _endpoint_mode() == "mock" else "unsupported_endpoint_mode",
    )


def _call_local_vllm_json(
    system_prompt: str,
    user_payload: dict[str, Any],
    *,
    max_tokens: int,
) -> ModelCallResult:
    return _call_openai_compatible_json(
        base_url=_local_vllm_base_url(),
        model=_local_vllm_model(),
        model_mode="local_vllm",
        failure_reason="local_vllm_failed",
        temperature=0.0,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        user_payload=user_payload,
        headers={"Content-Type": "application/json"},
    )


def _call_openai_compatible_json(
    *,
    base_url: str,
    model: str,
    model_mode: str,
    failure_reason: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
    user_payload: dict[str, Any],
    headers: dict[str, str],
) -> ModelCallResult:
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "temperature": temperature,
        "seed": _int_env("NEBIUS_PROMPT_SEED", 42),
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, separators=(",", ":"))},
        ],
    }
    request = Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    started = perf_counter()
    try:
        with urlopen(request, timeout=_float_env("NEBIUS_REQUEST_TIMEOUT_SECONDS", 180.0)) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as ex:
        logger.exception("OpenAI-compatible model call failed: mode=%s url=%s error=%s", model_mode, url, ex)
        return ModelCallResult(
            payload=None,
            model_mode="deterministic_fallback",
            model=model,
            latency_ms=_elapsed_ms(started),
            fallback_reason=failure_reason,
        )

    parsed = _parse_chat_completion_json(decoded)
    if parsed is None:
        logger.warning("Model returned invalid JSON response: %s", json.dumps(decoded)[:4000])
        return ModelCallResult(
            payload=None,
            model_mode="deterministic_fallback",
            model=model,
            latency_ms=_elapsed_ms(started),
            fallback_reason="invalid_model_json",
        )
    return ModelCallResult(
        payload=parsed,
        model_mode=model_mode,
        model=model,
        latency_ms=_elapsed_ms(started),
    )


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _parse_chat_completion_json(decoded: Any) -> dict[str, Any] | None:
    if not isinstance(decoded, dict):
        return None
    choices = decoded.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return _parse_json_object_text(content)


def _parse_json_object_text(content: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for candidate_text in _json_text_candidates(content):
        try:
            parsed = json.loads(candidate_text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

        for index, char in enumerate(candidate_text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(candidate_text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                return candidate

    logger.warning("Model content does not contain a JSON object: %s", content[:4000])
    return None


def _json_text_candidates(content: str) -> list[str]:
    stripped = content.strip()
    candidates = [stripped]

    fence_parts = stripped.split("```")
    if len(fence_parts) >= 3:
        for part in fence_parts[1::2]:
            block = part.strip()
            if block.lower().startswith("json"):
                block = block[4:].strip()
            if block:
                candidates.append(block)

    first_brace = stripped.find("{")
    last_brace = stripped.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(stripped[first_brace : last_brace + 1])

    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _validated_model_payload(
    result: ModelCallResult,
    schema: dict[str, type | tuple[type, ...] | str],
) -> dict[str, Any] | None:
    if result.payload is None:
        return None
    for key, expected_type in schema.items():
        if key not in result.payload or not _matches_expected_type(result.payload[key], expected_type):
            return None
    return result.payload


def _matches_expected_type(value: Any, expected_type: type | tuple[type, ...] | str) -> bool:
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, expected_type)


def _with_model_metadata(response: BaseModel, result: ModelCallResult) -> Any:
    return response.model_copy(
        update={
            "model_mode": result.model_mode,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "fallback_reason": result.fallback_reason,
        }
    )



def _fallback_model_result(result: ModelCallResult) -> ModelCallResult:
    if result.model_mode == "deterministic_fallback":
        return result
    return ModelCallResult(
        payload=None,
        model_mode="deterministic_fallback",
        model=result.model,
        latency_ms=result.latency_ms,
        fallback_reason="invalid_model_json",
    )


# Helper to log fallback events for all routes
def _log_fallback(route: str, result: ModelCallResult) -> None:
    logger.warning(
        "%s falling back to deterministic response: mode=%s reason=%s latency_ms=%s",
        route,
        result.model_mode,
        result.fallback_reason,
        result.latency_ms,
    )


def _local_vllm_base_url() -> str:
    configured = os.environ.get("LOCAL_VLLM_BASE_URL")
    if configured and configured.strip():
        return configured.strip()
    host = os.environ.get("LOCAL_VLLM_HOST", DEFAULT_LOCAL_VLLM_HOST).strip() or DEFAULT_LOCAL_VLLM_HOST
    port = os.environ.get("LOCAL_VLLM_PORT", DEFAULT_LOCAL_VLLM_PORT).strip() or DEFAULT_LOCAL_VLLM_PORT
    return f"http://{host}:{port}/v1"


def _local_vllm_model() -> str:
    return os.environ.get("LOCAL_VLLM_MODEL", DEFAULT_LOCAL_VLLM_MODEL).strip() or DEFAULT_LOCAL_VLLM_MODEL


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
    model_result: ModelCallResult,
) -> IncidentExplanationResponse:
    evidence = response.get("evidence", fallback.evidence)
    if isinstance(evidence, str):
        evidence = [evidence]
    if not isinstance(evidence, list):
        evidence = fallback.evidence
    merged = IncidentExplanationResponse(
        incident_id=str(response.get("incident_id") or request.incident_id),
        risk_level=str(response.get("risk_level") or fallback.risk_level),
        plain_english_summary=str(response.get("plain_english_summary") or fallback.plain_english_summary),
        evidence=[str(item) for item in evidence],
        recommended_action=str(response.get("recommended_action") or fallback.recommended_action),
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )
    return _with_model_metadata(merged, model_result)


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
    model_result: ModelCallResult,
) -> OrderBookAlertResponse:
    reasons = response.get("reasons", fallback.reasons)
    if isinstance(reasons, str):
        reasons = [reasons]
    if not isinstance(reasons, list):
        reasons = fallback.reasons
    suspicion_score = _bounded_float(response.get("suspicion_score"), fallback.suspicion_score)
    confidence = _bounded_float(response.get("confidence"), suspicion_score)
    merged = OrderBookAlertResponse(
        suspicion_score=suspicion_score,
        detected_pattern=str(response.get("detected_pattern") or fallback.detected_pattern),
        confidence=confidence,
        reasons=[str(item) for item in reasons],
        recommended_action=str(response.get("recommended_action") or fallback.recommended_action),
        model_mode=model_result.model_mode,
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )
    return _with_model_metadata(merged, model_result)


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
    model_result: ModelCallResult,
) -> InvestigationReportResponse:
    merged = InvestigationReportResponse(
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
    return _with_model_metadata(merged, model_result)


def _deterministic_investigation_team(request: AIInvestigationTeamRequest) -> AIInvestigationTeamResponse:
    incident = request.incident
    metrics = request.market_metrics
    detector_outputs = request.detector_outputs
    manipulation_type = _manipulation_type(incident, detector_outputs)
    risk_score = _investigation_risk_score(incident, detector_outputs, metrics)
    confidence = _bounded_float(
        max([_float_feature(row, "confidence") for row in detector_outputs] or [risk_score]),
        risk_score,
    )
    evidence = _investigation_evidence(metrics, detector_outputs)
    timeline = _investigation_timeline(incident, request.order_book_context, request.trades)
    return AIInvestigationTeamResponse(
        investigation_id=str(incident.get("incident_id") or incident.get("id") or "INV-MOCK-001"),
        manipulation_type=manipulation_type,
        risk_score=risk_score,
        confidence=confidence,
        agents=[
            AgentFinding(
                name="OrderBookExpertAgent",
                role="Order book microstructure reviewer",
                finding=f"Order-book state is consistent with {manipulation_type}.",
                confidence=_bounded_float(risk_score + 0.04, risk_score),
                evidence=evidence[:3],
            ),
            AgentFinding(
                name="TradePatternAgent",
                role="Trade and cancellation pattern reviewer",
                finding="Trade/event cadence supports replay review.",
                confidence=_bounded_float(confidence - 0.05, confidence),
                evidence=[TeamEvidenceItem(key="trade_count", label="Trade count", value=len(request.trades)), *evidence[:2]],
            ),
            AgentFinding(
                name="StatisticsAgent",
                role="Metric anomaly reviewer",
                finding="Submitted metrics crossed deterministic anomaly thresholds.",
                confidence=risk_score,
                evidence=evidence,
            ),
            AgentFinding(
                name="ComplianceAgent",
                role="Synthetic compliance framing reviewer",
                finding="Escalate for demo review only; not real enforcement.",
                confidence=0.89,
                evidence=[
                    TeamEvidenceItem(key="synthetic_simulation", label="Synthetic simulation", value=True),
                    TeamEvidenceItem(key="real_market_data", label="Real market data", value=False),
                ],
            ),
            AgentFinding(
                name="LeadInvestigatorAgent",
                role="Consensus owner",
                finding=f"Consensus: {manipulation_type} risk is {risk_score:.2f}.",
                confidence=_bounded_float((risk_score + confidence) / 2, risk_score),
                evidence=[
                    TeamEvidenceItem(key=f"timeline_{item.sequence}", label="Timeline", value=item.event, source=item.source)
                    for item in timeline[:3]
                ],
            ),
        ],
        consensus=f"{manipulation_type} synthetic incident with risk {risk_score:.2f}.",
        evidence_timeline=timeline,
        recommended_action="Queue this synthetic interval for replay, artifact capture, and detector-threshold review.",
        executive_summary=(
            f"AI Investigation Team reviewed incident {incident.get('incident_id') or incident.get('id') or 'unknown'} "
            f"and found {manipulation_type} evidence at risk {risk_score:.2f}."
        ),
    )


def _merge_investigation_team_response(
    fallback: AIInvestigationTeamResponse,
    response: dict[str, Any],
    model_result: ModelCallResult,
) -> AIInvestigationTeamResponse:
    merged = AIInvestigationTeamResponse(
        investigation_id=str(response.get("investigation_id") or fallback.investigation_id),
        manipulation_type=str(response.get("manipulation_type") or fallback.manipulation_type),
        risk_score=_bounded_float(response.get("risk_score"), fallback.risk_score),
        confidence=_bounded_float(response.get("confidence"), fallback.confidence),
        agents=_agent_findings(response.get("agents"), fallback.agents),
        consensus=str(response.get("consensus") or fallback.consensus),
        evidence_timeline=_timeline_items(response.get("evidence_timeline"), fallback.evidence_timeline),
        recommended_action=str(response.get("recommended_action") or fallback.recommended_action),
        executive_summary=str(response.get("executive_summary") or fallback.executive_summary),
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )
    return _with_model_metadata(merged, model_result)


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
    model_result: ModelCallResult,
) -> ScenarioGenerationResponse:
    parameters = response.get("parameters", fallback.parameters)
    if not isinstance(parameters, dict):
        parameters = fallback.parameters
    risk = response.get("expected_detector_risk", fallback.expected_detector_risk)
    try:
        risk_float = max(0.0, min(1.0, float(risk)))
    except (TypeError, ValueError):
        risk_float = fallback.expected_detector_risk
    merged = ScenarioGenerationResponse(
        scenario_type=_normalize_scenario_type(str(response.get("scenario_type") or fallback.scenario_type)),
        title=str(response.get("title") or fallback.title),
        description=str(response.get("description") or fallback.description),
        parameters=parameters,
        expected_detector_risk=risk_float,
        safety_note=str(response.get("safety_note") or DISCLAIMER),
    )
    return _with_model_metadata(merged, model_result)


def _deterministic_market_abuse_scenario(
    request: MarketAbuseScenarioGenerationRequest,
) -> MarketAbuseScenarioResponse:
    symbol = request.symbol.upper()
    seed = request.seed if request.seed is not None else _stable_market_abuse_seed(request)
    scenario_id = f"ai-{request.manipulation_type.replace('_', '-')}-{symbol.lower()}-{seed % 10000:04d}"
    start_tick = max(10, request.duration_ticks // 6)
    end_tick = min(request.duration_ticks, max(start_tick + 12, request.duration_ticks - request.duration_ticks // 5))
    title = _market_abuse_title(request.manipulation_type, symbol)
    events = _market_abuse_events(request, scenario_id=scenario_id, title=title, start_tick=start_tick)
    signals = _market_abuse_signals(request.manipulation_type)
    route = {
        "spoofing": "spoofing-like",
        "layering": "layering-like",
        "quote_stuffing": "quote-stuffing",
        "wash_trading": "spoofing-like",
    }[request.manipulation_type]
    return MarketAbuseScenarioResponse(
        scenario_id=scenario_id,
        title=title,
        description=(
            f"Synthetic {request.manipulation_type.replace('_', ' ')} workload for {symbol} "
            f"over {request.duration_ticks} ticks."
        ),
        manipulation_type=request.manipulation_type,
        difficulty=request.difficulty,
        symbol=symbol,
        duration_ticks=request.duration_ticks,
        liquidity_regime=request.liquidity_regime,
        volatility_regime=request.volatility_regime,
        ground_truth={
            "label": request.manipulation_type,
            "manipulation_windows": [{"start_tick": start_tick, "end_tick": end_tick}],
            "manipulator_agent_ids": [_market_abuse_agent(request.manipulation_type)],
            "expected_detector_targets": signals,
            "positive_event_ids": [event.event_id for event in events[:2]],
        },
        events=events,
        expected_detector_behavior={
            "primary_signals": signals,
            "expected_risk_score": _market_abuse_risk(request.difficulty, request.volatility_regime),
            "false_positive_risk": "high" if request.difficulty == "adversarial" else "medium" if request.difficulty == "hard" else "low",
        },
        explanation=(
            "Deterministic template generated a bounded synthetic workload with preserved labels, "
            "detector targets, and Arena replay projection."
        ),
        replay={
            "mode": "attack_scenario_projection",
            "route": route,
            "supported": True,
            "scenario_id": scenario_id,
            "duration_ticks": request.duration_ticks,
        },
        source={
            "mode": "mock",
            "provider": "nebius_serverless",
            "endpoint": "/generate-market-abuse-scenario",
            "model": "deterministic-template",
        },
    )


def _merge_market_abuse_scenario_response(
    fallback: MarketAbuseScenarioResponse,
    response: dict[str, Any],
    model_result: ModelCallResult,
) -> MarketAbuseScenarioResponse:
    merged = MarketAbuseScenarioResponse(
        scenario_id=fallback.scenario_id,
        title=str(response.get("title") or fallback.title),
        description=str(response.get("description") or fallback.description),
        manipulation_type=fallback.manipulation_type,
        difficulty=fallback.difficulty,
        symbol=fallback.symbol,
        duration_ticks=fallback.duration_ticks,
        liquidity_regime=fallback.liquidity_regime,
        volatility_regime=fallback.volatility_regime,
        ground_truth=fallback.ground_truth,
        events=fallback.events,
        expected_detector_behavior=fallback.expected_detector_behavior,
        explanation=str(response.get("explanation") or fallback.explanation),
        replay=fallback.replay,
        source={
            "mode": "nebius",
            "provider": "nebius_serverless",
            "endpoint": "/generate-market-abuse-scenario",
            "model": model_result.model,
            "model_mode": model_result.model_mode,
        },
        disclaimer=str(response.get("disclaimer") or DISCLAIMER),
    )
    return _with_model_metadata(merged, model_result)


def _market_abuse_events(
    request: MarketAbuseScenarioGenerationRequest,
    *,
    scenario_id: str,
    title: str,
    start_tick: int,
) -> list[ScenarioEvent]:
    agent_id = _market_abuse_agent(request.manipulation_type)
    side: Literal["buy", "sell"] = "buy" if request.manipulation_type in {"spoofing", "wash_trading"} else "sell"
    price = 100.0 + (_stable_market_abuse_seed(request) % 250) / 100.0
    size = 250.0 if request.liquidity_regime == "thin" else 500.0 if request.liquidity_regime == "normal" else 800.0
    order_id = f"ord-{scenario_id}-{start_tick}"
    templates = {
        "spoofing": [
            ("place_order", "wall_placed", "Place large visible synthetic liquidity wall.", order_id, side, size),
            ("cancel_order", "wall_cancelled", "Cancel wall before execution.", order_id, side, size),
            ("trade", "incident_confirmed", "Submit small opposite-side trade after book reaction.", None, "sell", size / 8),
        ],
        "layering": [
            ("place_order", "pressure_phase", "Layer synthetic orders across adjacent price levels.", order_id, side, size / 2),
            ("place_order", "pressure_phase", "Add second visible layer to deepen imbalance.", f"{order_id}-b", side, size / 3),
            ("cancel_order", "cancelled", "Cancel layered orders as price pressure appears.", order_id, side, size / 2),
        ],
        "wash_trading": [
            ("trade", "pressure_phase", "Cross synthetic accounts inside simulator labels.", None, "buy", size / 10),
            ("trade", "pressure_phase", "Reverse synthetic cross-trade to preserve net position.", None, "sell", size / 10),
            ("quote_update", "incident_confirmed", "Mark repeated self-crossing pattern for detector review.", None, None, None),
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
        events.append(
            ScenarioEvent(
                event_id=f"evt-{tick:04d}-{event_type.replace('_', '-')}",
                tick=tick,
                event_type=event_type,  # type: ignore[arg-type]
                type=event_type,
                agent_id=agent_id,
                symbol=request.symbol.upper(),
                scenario_id=scenario_id,
                scenario_name=title,
                scenario_family=request.manipulation_type,
                stage=stage,
                message=message,
                side=event_side,  # type: ignore[arg-type]
                price=round(price + (index * 0.05), 4) if event_side else None,
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


def _market_abuse_signals(manipulation_type: str) -> list[str]:
    return {
        "spoofing": ["wall_size_ratio", "cancel_to_trade_ratio", "order_lifetime_ms"],
        "layering": ["depth_imbalance", "rapid_cancel_cluster", "multi_level_pressure"],
        "wash_trading": ["self_trade_ratio", "round_trip_volume", "matched_agent_pairs"],
        "quote_stuffing": ["message_rate", "cancel_to_trade_ratio", "spread_widening"],
    }.get(manipulation_type, ["cancel_to_trade_ratio"])


def _market_abuse_agent(manipulation_type: str) -> str:
    return {
        "spoofing": "AI-SPOOF-001",
        "layering": "AI-LAYER-001",
        "wash_trading": "AI-WASH-001",
        "quote_stuffing": "AI-STUFF-001",
    }.get(manipulation_type, "AI-SCENARIO-001")


def _market_abuse_title(manipulation_type: str, symbol: str) -> str:
    return {
        "spoofing": f"{symbol} Spoofing Pressure Near Mid",
        "layering": f"{symbol} Layered Depth Pressure",
        "wash_trading": f"{symbol} Wash Trading Loop",
        "quote_stuffing": f"{symbol} Quote Stuffing Burst",
    }.get(manipulation_type, f"{symbol} Synthetic Scenario")


def _market_abuse_risk(difficulty: str, volatility: str) -> float:
    base = {"easy": 0.52, "medium": 0.68, "hard": 0.82, "adversarial": 0.91}.get(difficulty, 0.68)
    adjustment = {"low": -0.04, "medium": 0.0, "high": 0.04}.get(volatility, 0.0)
    return round(max(0.0, min(0.97, base + adjustment)), 4)


def _stable_market_abuse_seed(request: MarketAbuseScenarioGenerationRequest) -> int:
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


def _agent_findings(value: Any, fallback: list[AgentFinding]) -> list[AgentFinding]:
    if not isinstance(value, list):
        return fallback
    findings: list[AgentFinding] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        findings.append(
            AgentFinding(
                name=str(item.get("name") or f"InvestigationAgent{index + 1}"),
                role=str(item.get("role") or "Investigation reviewer"),
                finding=str(item.get("finding") or "No finding provided."),
                confidence=_bounded_float(item.get("confidence"), 0.5),
                evidence=_team_evidence_items(item.get("evidence")),
            )
        )
    return findings or fallback


def _team_evidence_items(value: Any) -> list[TeamEvidenceItem]:
    if isinstance(value, str):
        return [TeamEvidenceItem(key="evidence", label="Evidence", value=value)]
    if not isinstance(value, list):
        return []
    items: list[TeamEvidenceItem] = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            items.append(
                TeamEvidenceItem(
                    key=str(item.get("key") or f"evidence_{index + 1}"),
                    label=str(item.get("label") or item.get("key") or "Evidence"),
                    value=_evidence_value(item.get("value") if "value" in item else item.get("text") or item),
                    source=str(item["source"]) if item.get("source") is not None else None,
                )
            )
        else:
            items.append(TeamEvidenceItem(key=f"evidence_{index + 1}", label="Evidence", value=str(item)))
    return items


def _timeline_items(value: Any, fallback: list[EvidenceTimelineItem]) -> list[EvidenceTimelineItem]:
    if isinstance(value, str):
        return [EvidenceTimelineItem(sequence=1, event=value)]
    if not isinstance(value, list):
        return fallback
    items: list[EvidenceTimelineItem] = []
    for index, item in enumerate(value):
        sequence = index + 1
        if isinstance(item, dict):
            items.append(
                EvidenceTimelineItem(
                    sequence=int(item.get("sequence") or sequence),
                    event=str(item.get("event") or item.get("description") or item),
                    tick=item.get("tick"),
                    source=str(item["source"]) if item.get("source") is not None else None,
                    significance=str(item["significance"]) if item.get("significance") is not None else None,
                )
            )
        else:
            items.append(EvidenceTimelineItem(sequence=sequence, event=str(item)))
    return items or fallback


def _manipulation_type(incident: dict[str, Any], detector_outputs: list[dict[str, Any]]) -> str:
    candidates = [
        incident.get("manipulation_type"),
        incident.get("type"),
        incident.get("scenario"),
        incident.get("scenario_family"),
    ]
    candidates.extend(row.get("detected_pattern") or row.get("detector") for row in detector_outputs)
    for candidate in candidates:
        if candidate:
            return str(candidate).lower().replace("-", "_").replace(" ", "_")
    return "unknown"


def _investigation_risk_score(
    incident: dict[str, Any],
    detector_outputs: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> float:
    confidence_values = [_float_feature(row, "confidence") for row in detector_outputs]
    suspicion_values = [_float_feature(row, "suspicion_score") for row in detector_outputs]
    metric_values = [
        _float_feature(metrics, "wall_size_ratio") / 10,
        _float_feature(metrics, "cancel_to_trade_ratio") / 12,
        _float_feature(metrics, "message_rate") / 40,
        _float_feature(metrics, "depth_change_pct"),
        _float_feature(metrics, "imbalance"),
    ]
    incident_confidence = _float_feature(incident, "confidence")
    return _bounded_float(max([incident_confidence, *confidence_values, *suspicion_values, *metric_values, 0.42]), 0.42)


def _investigation_evidence(metrics: dict[str, Any], detector_outputs: list[dict[str, Any]]) -> list[TeamEvidenceItem]:
    evidence = [
        TeamEvidenceItem(key=key, label=key.replace("_", " "), value=_evidence_value(value), source="market_metrics")
        for key, value in sorted(metrics.items())
        if key in {"wall_size_ratio", "cancel_to_trade_ratio", "message_rate", "depth_change_pct", "imbalance"}
    ]
    for row in detector_outputs[:3]:
        detector = row.get("detector") or row.get("detected_pattern") or "detector"
        confidence = row.get("confidence") or row.get("suspicion_score")
        evidence.append(
            TeamEvidenceItem(
                key=str(detector),
                label=str(detector),
                value=_evidence_value(confidence),
                source="detector_outputs",
            )
        )
    return evidence or [TeamEvidenceItem(key="detector_evidence", label="Detector evidence", value="available")]


def _investigation_timeline(
    incident: dict[str, Any],
    order_book_context: dict[str, Any],
    trades: list[dict[str, Any]],
) -> list[EvidenceTimelineItem]:
    tick = incident.get("tick") or incident.get("created_at") or "unknown"
    events = order_book_context.get("events")
    event_count = len(events) if isinstance(events, list) else 0
    return [
        EvidenceTimelineItem(sequence=1, event=f"Incident observed at tick/time {tick}.", tick=tick, source="incident"),
        EvidenceTimelineItem(sequence=2, event=f"Order-book context supplied with {event_count} event(s).", source="order_book_context"),
        EvidenceTimelineItem(sequence=3, event=f"Trade context supplied with {len(trades)} trade(s).", source="trades"),
        EvidenceTimelineItem(sequence=4, event="AI Investigation Team produced consensus from specialist findings.", source="investigation_team"),
    ]


def _evidence_value(value: Any) -> str | int | float | bool:
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

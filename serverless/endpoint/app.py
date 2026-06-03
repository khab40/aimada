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


class ExplainPayload(BaseModel):
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "nebius-market-abuse-arena-endpoint",
        "model_mode": "ai_studio" if _model_enabled() else "deterministic_fallback",
    }


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

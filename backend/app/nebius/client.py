import json
import shutil
import subprocess
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from app.config import get_settings
from app.nebius.investigation_team import (
    AIInvestigationAgentFinding,
    AIInvestigationTeamRequest,
    AIInvestigationTeamResponse,
    AgentFinding,
    EvidenceItem,
    EvidenceTimelineItem,
    mock_response as mock_investigation_team_response,
    normalize_response as normalize_investigation_team_response,
    prepare_payload as prepare_investigation_team_payload,
)
from app.nebius.scenario_generator import (
    CanonicalMarketAbuseScenario,
    MarketAbuseScenarioGenerationRequest,
    mock_response as mock_market_abuse_scenario_response,
    normalize_response as normalize_market_abuse_scenario_response,
    prepare_payload as prepare_market_abuse_scenario_payload,
)
from app.schemas.arena import Incident


class IncidentEvidencePayload(BaseModel):
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
    evidence: list[IncidentEvidencePayload]
    replay: dict[str, Any] | None = None


class IncidentExplanationResponse(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    incident_id: str
    explanation_id: str | None = None
    created_at: str | None = None
    stored_artifact: str | None = None
    risk_level: str
    plain_english_summary: str
    evidence: list[str]
    recommended_action: str
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class RedTeamScenarioRequest(BaseModel):
    prompt: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class RedTeamScenarioResponse(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    scenario_type: str
    title: str
    description: str
    parameters: dict[str, Any]
    expected_detector_risk: float = Field(ge=0.0, le=1.0)
    safety_note: str
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class OrderBookAlertRequest(BaseModel):
    bids: list[dict[str, Any]] = Field(default_factory=list)
    asks: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    scenario_hint: str | None = None
    tick: int | None = None


class OrderBookAlertResponse(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    suspicion_score: float = Field(ge=0.0, le=1.0)
    detected_pattern: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    recommended_action: str
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class InvestigationReportRequest(BaseModel):
    scenario_trace: dict[str, Any] = Field(default_factory=dict)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class InvestigationReportResponse(BaseModel):
    mode: Literal["nebius", "mock"]
    endpoint: str
    title: str
    summary: str
    timeline: list[str]
    detector_findings: list[str]
    limitations: list[str]
    recommended_next_steps: list[str]
    fallback_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class NebiusIntegrationStatus(BaseModel):
    tenant_id_configured: bool
    incident_explainer_configured: bool
    scenario_generator_configured: bool
    orderbook_alert_configured: bool
    investigation_report_configured: bool
    investigation_team_configured: bool
    market_abuse_scenario_configured: bool
    endpoint_token_configured: bool
    endpoint_mode: str
    endpoint_base_url: str | None = None
    endpoint_base_url_configured: bool
    endpoint_health: dict[str, Any] | None = None
    job_image: str
    job_submit_template_configured: bool
    cli_installed: bool
    cli_path: str | None = None
    cli_version: str | None = None


class NebiusClient:
    def __init__(
        self,
        incident_explainer_url: str | None = None,
        scenario_generator_url: str | None = None,
        orderbook_alert_url: str | None = None,
        investigation_report_url: str | None = None,
        investigation_team_url: str | None = None,
        market_abuse_scenario_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        settings = get_settings()
        self.incident_explainer_url = (
            incident_explainer_url
            if incident_explainer_url is not None
            else settings.nebius_explain_endpoint_url
        )
        self.scenario_generator_url = (
            scenario_generator_url
            if scenario_generator_url is not None
            else settings.nebius_scenario_endpoint_url
        )
        self.orderbook_alert_url = (
            orderbook_alert_url
            if orderbook_alert_url is not None
            else settings.nebius_orderbook_alert_endpoint_url
        )
        self.investigation_report_url = (
            investigation_report_url
            if investigation_report_url is not None
            else settings.nebius_investigation_report_endpoint_url
        )
        self.investigation_team_url = (
            investigation_team_url
            if investigation_team_url is not None
            else settings.nebius_investigation_team_endpoint_url
        )
        self.market_abuse_scenario_url = (
            market_abuse_scenario_url
            if market_abuse_scenario_url is not None
            else settings.nebius_market_abuse_scenario_endpoint_url
        )
        self.api_key = api_key if api_key is not None else settings.endpoint_token
        self.timeout_seconds = timeout_seconds

    def explain_incident(
        self,
        incident: Incident,
        replay_payload: dict[str, Any] | None = None,
    ) -> IncidentExplanationResponse:
        payload = self._incident_payload(incident, replay_payload=replay_payload)
        if not self.incident_explainer_url:
            return self._mock_explanation(
                incident,
                reason="NEBIUS_INCIDENT_EXPLAINER_URL is not configured",
            )

        try:
            response = self._post_json(self.incident_explainer_url, payload.model_dump(mode="json"))
            return self._parse_explanation_response(incident, response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_explanation(incident, reason=f"Nebius incident explainer fallback: {exc}")

    def generate_red_team_scenario(
        self,
        prompt: str,
        constraints: dict[str, Any] | None = None,
    ) -> RedTeamScenarioResponse:
        request = RedTeamScenarioRequest(prompt=prompt, constraints=constraints or {})
        if not self.scenario_generator_url:
            return self._mock_red_team_scenario(
                request,
                reason="NEBIUS_SCENARIO_GENERATOR_URL is not configured",
            )

        try:
            response = self._post_json(self.scenario_generator_url, request.model_dump(mode="json"))
            return self._parse_red_team_response(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_red_team_scenario(
                request,
                reason=f"Nebius scenario generator fallback: {exc}",
            )

    def detect_orderbook_alert(self, request: OrderBookAlertRequest) -> OrderBookAlertResponse:
        if not self.orderbook_alert_url:
            return self._mock_orderbook_alert(
                request,
                reason="NEBIUS_ORDERBOOK_ALERT_URL or NEBIUS_ENDPOINT_BASE_URL is not configured",
            )
        try:
            response = self._post_json(self.orderbook_alert_url, request.model_dump(mode="json"))
            return self._parse_orderbook_alert_response(response, endpoint=self.orderbook_alert_url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_orderbook_alert(request, reason=f"Nebius order-book alert fallback: {exc}")

    def investigation_report(self, request: InvestigationReportRequest) -> InvestigationReportResponse:
        if not self.investigation_report_url:
            return self._mock_investigation_report(
                request,
                reason="NEBIUS_INVESTIGATION_REPORT_URL or NEBIUS_ENDPOINT_BASE_URL is not configured",
            )
        try:
            response = self._post_json(self.investigation_report_url, request.model_dump(mode="json"))
            return self._parse_investigation_report_response(
                response,
                endpoint=self.investigation_report_url,
            )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_investigation_report(
                request,
                reason=f"Nebius investigation report fallback: {exc}",
            )

    def analyze_investigation_team(self, request: AIInvestigationTeamRequest) -> AIInvestigationTeamResponse:
        payload = prepare_investigation_team_payload(request)
        if not self.investigation_team_url:
            return self._mock_investigation_team(
                payload,
                reason="NEBIUS_INVESTIGATION_TEAM_URL or NEBIUS_ENDPOINT_BASE_URL is not configured",
            )
        try:
            response = self._post_json(self.investigation_team_url, payload.model_dump(mode="json"))
            return self._parse_investigation_team_response(response, endpoint=self.investigation_team_url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_investigation_team(
                payload,
                reason=f"Nebius investigation team fallback: {exc}",
            )

    def generate_market_abuse_scenario(
        self,
        request: MarketAbuseScenarioGenerationRequest,
    ) -> CanonicalMarketAbuseScenario:
        payload = prepare_market_abuse_scenario_payload(request)
        if not self.market_abuse_scenario_url:
            return self._mock_market_abuse_scenario(
                payload,
                reason="NEBIUS_MARKET_ABUSE_SCENARIO_URL or NEBIUS_ENDPOINT_BASE_URL is not configured",
            )
        try:
            response = self._post_json(self.market_abuse_scenario_url, payload.model_dump(mode="json"))
            return self._parse_market_abuse_scenario_response(
                response,
                request=payload,
                endpoint=self.market_abuse_scenario_url,
            )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return self._mock_market_abuse_scenario(
                payload,
                reason=f"Nebius market-abuse scenario generator fallback: {exc}",
            )

    def integration_status(self) -> NebiusIntegrationStatus:
        settings = get_settings()
        cli_path = shutil.which("nebius")
        cli_version = None
        if cli_path:
            try:
                completed = subprocess.run(
                    [cli_path, "version"],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=2.0,
                )
                cli_version = (completed.stdout or completed.stderr).strip() or None
            except (OSError, subprocess.SubprocessError, TimeoutError):
                cli_version = None

        return NebiusIntegrationStatus(
            tenant_id_configured=bool(settings.nebius_tenant_id),
            incident_explainer_configured=bool(settings.nebius_explain_endpoint_url),
            scenario_generator_configured=bool(settings.nebius_scenario_endpoint_url),
            orderbook_alert_configured=bool(settings.nebius_orderbook_alert_endpoint_url),
            investigation_report_configured=bool(settings.nebius_investigation_report_endpoint_url),
            investigation_team_configured=bool(settings.nebius_investigation_team_endpoint_url),
            market_abuse_scenario_configured=bool(settings.nebius_market_abuse_scenario_endpoint_url),
            endpoint_token_configured=bool(settings.endpoint_token),
            endpoint_mode=settings.nebius_endpoint_mode,
            endpoint_base_url=settings.nebius_endpoint_base_url,
            endpoint_base_url_configured=bool(settings.nebius_endpoint_base_url),
            endpoint_health=self.endpoint_health(),
            job_image=settings.nebius_job_image,
            job_submit_template_configured=bool(settings.nebius_job_submit_command_template),
            cli_installed=bool(cli_path),
            cli_path=cli_path,
            cli_version=cli_version,
        )

    def endpoint_health(self) -> dict[str, Any] | None:
        settings = get_settings()
        if not settings.nebius_endpoint_base_url:
            return None
        health_url = settings.nebius_endpoint_url("/health")
        if not health_url:
            return None
        try:
            return self._get_json(health_url, timeout_seconds=settings.nebius_health_timeout_seconds)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return {
                "status": "unreachable",
                "url_configured": True,
                "fallback_reason": f"endpoint health probe failed: {exc}",
            }

    def _get_json(self, url: str, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=timeout_seconds or self.timeout_seconds) as response:
            body = response.read().decode("utf-8")
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise ValueError("Nebius endpoint returned a non-object JSON response")
            return decoded

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")
            decoded = json.loads(body)
            if not isinstance(decoded, dict):
                raise ValueError("Nebius endpoint returned a non-object JSON response")
            return decoded

    def _incident_payload(
        self,
        incident: Incident,
        *,
        replay_payload: dict[str, Any] | None = None,
    ) -> IncidentExplanationRequest:
        return IncidentExplanationRequest(
            incident_id=incident.id,
            title=incident.title,
            type=incident.type,
            agent=incident.agent,
            confidence=incident.confidence,
            severity=incident.severity,
            scenario_id=incident.scenario_id,
            scenario_family=incident.scenario_family,
            evidence=[
                IncidentEvidencePayload(
                    key=item.key,
                    label=item.label,
                    value=item.value,
                    unit=item.unit,
                    interpretation=item.interpretation,
                )
                for item in incident.evidence
            ],
            replay=replay_payload,
        )

    def _parse_explanation_response(
        self,
        incident: Incident,
        response: dict[str, Any],
    ) -> IncidentExplanationResponse:
        evidence = response.get("evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence]
        if not isinstance(evidence, list):
            evidence = []

        return IncidentExplanationResponse(
            mode="nebius",
            endpoint="Nebius Serverless AI Endpoint",
            incident_id=str(response.get("incident_id") or incident.id),
            risk_level=str(response.get("risk_level") or incident.severity.lower()),
            plain_english_summary=str(
                response.get("plain_english_summary")
                or response.get("summary")
                or "Nebius endpoint returned an explanation without a summary field."
            ),
            evidence=[str(item) for item in evidence],
            recommended_action=str(
                response.get("recommended_action")
                or "Flag this simulated interval for manual review."
            ),
            raw_response=response,
        )

    def _parse_red_team_response(self, response: dict[str, Any]) -> RedTeamScenarioResponse:
        parameters = response.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        risk = response.get("expected_detector_risk", response.get("risk", 0.65))
        try:
            expected_detector_risk = max(0.0, min(1.0, float(risk)))
        except (TypeError, ValueError):
            expected_detector_risk = 0.65

        return RedTeamScenarioResponse(
            mode="nebius",
            endpoint="Nebius Serverless AI Endpoint",
            scenario_type=str(response.get("scenario_type") or "spoofing_like_wall"),
            title=str(response.get("title") or "Generated red-team scenario"),
            description=str(response.get("description") or "Nebius generated a synthetic scenario."),
            parameters=parameters,
            expected_detector_risk=expected_detector_risk,
            safety_note=str(
                response.get("safety_note")
                or "Educational synthetic scenario only. Do not use as trading or compliance guidance."
            ),
            raw_response=response,
        )

    def _parse_orderbook_alert_response(
        self,
        response: dict[str, Any],
        *,
        endpoint: str,
    ) -> OrderBookAlertResponse:
        reasons = response.get("reasons", [])
        if isinstance(reasons, str):
            reasons = [reasons]
        if not isinstance(reasons, list):
            reasons = []
        suspicion_score = _bounded_float(response.get("suspicion_score"), 0.0)
        confidence = _bounded_float(response.get("confidence"), suspicion_score)
        return OrderBookAlertResponse(
            mode="nebius",
            endpoint=endpoint,
            suspicion_score=suspicion_score,
            detected_pattern=str(response.get("detected_pattern") or "unknown"),
            confidence=confidence,
            reasons=[str(item) for item in reasons],
            recommended_action=str(response.get("recommended_action") or "Review the synthetic interval."),
            raw_response=response,
        )

    def _parse_investigation_report_response(
        self,
        response: dict[str, Any],
        *,
        endpoint: str,
    ) -> InvestigationReportResponse:
        return InvestigationReportResponse(
            mode="nebius",
            endpoint=endpoint,
            title=str(response.get("title") or "Synthetic investigation report"),
            summary=str(response.get("summary") or "Nebius endpoint returned a report."),
            timeline=_string_list(response.get("timeline")),
            detector_findings=_string_list(response.get("detector_findings")),
            limitations=_string_list(response.get("limitations")),
            recommended_next_steps=_string_list(response.get("recommended_next_steps")),
            raw_response=response,
        )

    def _parse_investigation_team_response(
        self,
        response: dict[str, Any],
        *,
        endpoint: str,
    ) -> AIInvestigationTeamResponse:
        return normalize_investigation_team_response(response, endpoint=endpoint, mode="nebius")

    def _parse_market_abuse_scenario_response(
        self,
        response: dict[str, Any],
        *,
        request: MarketAbuseScenarioGenerationRequest,
        endpoint: str,
    ) -> CanonicalMarketAbuseScenario:
        source = response.get("source") if isinstance(response.get("source"), dict) else {}
        mode = "mock" if source.get("mode") == "mock" or response.get("model_mode") == "deterministic_fallback" else "nebius"
        return normalize_market_abuse_scenario_response(response, request=request, endpoint=endpoint, mode=mode)

    def _mock_explanation(self, incident: Incident, *, reason: str) -> IncidentExplanationResponse:
        return IncidentExplanationResponse(
            mode="mock",
            endpoint="mock Nebius AI explanation",
            fallback_reason=reason,
            incident_id=incident.id,
            risk_level=incident.severity.lower(),
            plain_english_summary=(
                f"{incident.title} was generated by deterministic detectors in this educational "
                "synthetic market simulation."
            ),
            evidence=[
                f"{item.label}: {item.value}{f' {item.unit}' if item.unit else ''}"
                for item in incident.evidence
            ],
            recommended_action=(
                "Flag this simulated interval for manual review. Do not use it for compliance decisions."
            ),
        )

    def _mock_red_team_scenario(
        self,
        request: RedTeamScenarioRequest,
        *,
        reason: str,
    ) -> RedTeamScenarioResponse:
        scenario_type = str(request.constraints.get("scenario_type") or "spoofing_like_wall")
        return RedTeamScenarioResponse(
            mode="mock",
            endpoint="mock Nebius scenario generator",
            fallback_reason=reason,
            scenario_type=scenario_type,
            title="Synthetic red-team scenario draft",
            description=(
                "Create a short-lived, visible liquidity pattern in the synthetic order book "
                "with bounded size and lifetime for detector demonstration."
            ),
            parameters={
                "wall_size_multiplier": request.constraints.get("wall_size_multiplier", 8),
                "lifetime_seconds": request.constraints.get("lifetime_seconds", 5),
                "distance_from_mid_bps": request.constraints.get("distance_from_mid_bps", 12),
                "prompt": request.prompt,
            },
            expected_detector_risk=0.72,
            safety_note=(
                "Educational synthetic scenario only. It must remain inside the simulator and "
                "must not be used against real markets."
            ),
        )

    def _mock_orderbook_alert(
        self,
        request: OrderBookAlertRequest,
        *,
        reason: str,
    ) -> OrderBookAlertResponse:
        features = request.features
        wall = _feature_float(features, "wall_size_ratio")
        message_rate = _feature_float(features, "message_rate")
        cancel_ratio = _feature_float(features, "cancel_to_trade_ratio")
        score = min(0.95, max(0.12, wall / 10 + message_rate / 80 + cancel_ratio / 30))
        pattern = request.scenario_hint or (
            "quote_stuffing" if message_rate >= 18 else "spoofing_like_wall" if wall >= 5 else "normal_market"
        )
        return OrderBookAlertResponse(
            mode="mock",
            endpoint="mock Nebius /orderbook-alert",
            fallback_reason=reason,
            suspicion_score=round(score, 4),
            detected_pattern=pattern,
            confidence=round(score, 4),
            reasons=[
                f"wall_size_ratio={wall:.2f}",
                f"message_rate={message_rate:.2f}",
                f"cancel_to_trade_ratio={cancel_ratio:.2f}",
            ],
            recommended_action="Queue the synthetic interval for replay and benchmark review.",
        )

    def _mock_investigation_report(
        self,
        request: InvestigationReportRequest,
        *,
        reason: str,
    ) -> InvestigationReportResponse:
        scenario = str(request.scenario_trace.get("scenario") or "synthetic scenario")
        return InvestigationReportResponse(
            mode="mock",
            endpoint="mock Nebius /investigation-report",
            fallback_reason=reason,
            title=f"Synthetic investigation report: {scenario}",
            summary=(
                f"{len(request.alerts)} alert(s) were generated for {scenario}. "
                "This is a bounded educational report."
            ),
            timeline=[
                "Synthetic scenario generated.",
                "Order-book window scored by detector endpoint.",
                "Alerts and metrics archived for the demo.",
            ],
            detector_findings=[f"{key}: {value}" for key, value in request.metrics.items()],
            limitations=[
                "Synthetic simulator labels are not real surveillance labels.",
                "Do not use these outputs for trading, compliance, or enforcement decisions.",
            ],
            recommended_next_steps=[
                "Capture real Nebius endpoint and job logs.",
                "Archive benchmark artifacts with the submission.",
            ],
        )

    def _mock_investigation_team(
        self,
        request: AIInvestigationTeamRequest,
        *,
        reason: str,
    ) -> AIInvestigationTeamResponse:
        return mock_investigation_team_response(request, reason=reason)

    def _mock_market_abuse_scenario(
        self,
        request: MarketAbuseScenarioGenerationRequest,
        *,
        reason: str,
    ) -> CanonicalMarketAbuseScenario:
        return mock_market_abuse_scenario_response(request, reason=reason)


NebiusAIClient = NebiusClient


def _feature_float(features: dict[str, Any], key: str) -> float:
    try:
        return float(features.get(key) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bounded_float(value: Any, fallback: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []

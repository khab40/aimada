import json
import shutil
import subprocess
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from app.config import get_settings
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


class NebiusIntegrationStatus(BaseModel):
    tenant_id_configured: bool
    incident_explainer_configured: bool
    scenario_generator_configured: bool
    api_key_configured: bool
    cli_installed: bool
    cli_path: str | None = None
    cli_version: str | None = None


class NebiusClient:
    def __init__(
        self,
        incident_explainer_url: str | None = None,
        scenario_generator_url: str | None = None,
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
        self.api_key = api_key if api_key is not None else settings.nebius_api_key
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
            api_key_configured=bool(settings.nebius_api_key),
            cli_installed=bool(cli_path),
            cli_path=cli_path,
            cli_version=cli_version,
        )

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


NebiusAIClient = NebiusClient

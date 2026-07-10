import json

import pytest

import app as endpoint_app
from app import (
    AIInvestigationTeamRequest,
    IncidentExplanationRequest,
    InvestigationReportRequest,
    MarketAbuseScenarioGenerationRequest,
    OrderBookWindow,
    ScenarioGenerationRequest,
    explain_event,
    generate_market_abuse_scenario,
    generate_scenario,
    health,
    investigation_team,
    investigation_report,
    orderbook_alert,
    ready,
)


@pytest.fixture(autouse=True)
def endpoint_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "NEBIUS_ENDPOINT_MODE",
        "LOCAL_VLLM_BASE_URL",
        "LOCAL_VLLM_MODEL",
        "LOCAL_VLLM_HOST",
        "LOCAL_VLLM_PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NEBIUS_ENDPOINT_MODE", "mock")


class FakeModelResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeModelResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _chat_completion(content: str) -> dict[str, object]:
    return {"choices": [{"message": {"content": content}}]}


def test_health_and_ready_use_fallback_mode_by_default() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["endpoint_mode"] == "mock"
    assert response["model_mode"] == "deterministic_fallback"
    assert response["credentials_configured"] is False
    assert "api_key" not in json.dumps(response).lower()

    ready_response = ready()

    assert ready_response["status"] == "ready"
    assert ready_response["model_mode"] == "deterministic_fallback"


def test_explain_event_returns_backend_compatible_json() -> None:
    response = explain_event(
        IncidentExplanationRequest(
            incident_id="INC-000001",
            title="Quote Stuffing detected",
            type="quote_stuffing",
            agent="ABUSER_01",
            confidence=0.91,
            severity="High",
            evidence=[
                {
                    "key": "message_rate",
                    "label": "Message rate",
                    "value": 42,
                    "unit": "events/sec",
                }
            ],
            replay={"market": {"mid": 68125, "spread": 2}},
        )
    )

    assert response.incident_id == "INC-000001"
    assert response.risk_level == "high"
    assert response.evidence
    assert response.recommended_action
    assert response.model_mode == "deterministic_fallback"
    assert response.model


def test_generate_scenario_returns_backend_compatible_json() -> None:
    response = generate_scenario(
        ScenarioGenerationRequest(
            prompt="Generate a bounded quote stuffing scenario.",
            constraints={
                "scenario_family": "quote_stuffing",
                "market_regime": "volatile",
                "goal": "hard_to_detect",
            },
        )
    )

    assert response.scenario_type == "quote_stuffing"
    assert response.expected_detector_risk >= 0
    assert response.parameters["market_regime"] == "volatile"
    assert response.model_mode == "deterministic_fallback"


def test_generate_market_abuse_scenario_returns_ground_truth_contract() -> None:
    response = generate_market_abuse_scenario(
        MarketAbuseScenarioGenerationRequest(
            manipulation_type="quote_stuffing",
            difficulty="hard",
            symbol="NBS",
            duration_ticks=150,
            liquidity_regime="thin",
            volatility_regime="high",
        )
    )

    assert response.manipulation_type == "quote_stuffing"
    assert response.ground_truth["label"] == "quote_stuffing"
    assert response.events
    assert response.replay["route"] == "quote-stuffing"
    assert response.model_mode == "deterministic_fallback"
    assert response.source["endpoint"] == "/generate-market-abuse-scenario"


def test_orderbook_alert_returns_detector_contract() -> None:
    response = orderbook_alert(
        OrderBookWindow(
            bids=[{"price": 68120, "quantity": 12.4, "owner": "abuser"}],
            asks=[{"price": 68130, "quantity": 1.8, "owner": "normal"}],
            features={
                "wall_size_ratio": 8.2,
                "message_rate": 21,
                "cancel_to_trade_ratio": 5.4,
                "imbalance": 0.72,
            },
            scenario_hint="spoofing",
        )
    )

    assert response.detected_pattern == "spoofing_like_wall"
    assert response.suspicion_score >= 0.75
    assert response.reasons
    assert response.model_mode == "deterministic_fallback"
    assert response.latency_ms == 0.0


def test_investigation_report_returns_case_report_contract() -> None:
    response = investigation_report(
        InvestigationReportRequest(
            scenario_trace={"scenario": "quote_stuffing"},
            alerts=[{"detector": "quote_stuffing", "confidence": 0.91}],
            metrics={"precision": 0.9, "recall": 0.86, "f1": 0.88},
        )
    )

    assert "quote_stuffing" in response.title
    assert response.timeline
    assert response.detector_findings
    assert response.model_mode == "deterministic_fallback"


def test_investigation_team_returns_agent_contract() -> None:
    response = investigation_team(
        AIInvestigationTeamRequest(
            incident={"incident_id": "INC-1", "type": "spoofing", "confidence": 0.88, "tick": 12},
            detector_outputs=[{"detected_pattern": "spoofing_like_wall", "confidence": 0.91}],
            order_book_context={"events": [{"type": "quote"}]},
            trades=[{"price": 100.0}],
            market_metrics={"wall_size_ratio": 8.2, "cancel_to_trade_ratio": 5.4},
        )
    )

    assert response.investigation_id == "INC-1"
    assert response.manipulation_type == "spoofing"
    assert response.risk_score == 0.91
    assert response.model_mode == "deterministic_fallback"
    assert [agent.name for agent in response.agents] == [
        "OrderBookExpertAgent",
        "TradePatternAgent",
        "StatisticsAgent",
        "ComplianceAgent",
        "LeadInvestigatorAgent",
    ]
    assert response.evidence_timeline


def test_local_vllm_mode_uses_local_openai_compatible_endpoint_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_MODE", "local_vllm")
    monkeypatch.setenv("LOCAL_VLLM_BASE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("LOCAL_VLLM_MODEL", "test-local-vllm-model")
    captured: dict[str, str | None] = {}

    def fake_urlopen(request: object, timeout: float) -> FakeModelResponse:
        captured["authorization"] = request.get_header("Authorization")  # type: ignore[attr-defined]
        captured["url"] = request.full_url  # type: ignore[attr-defined]
        return FakeModelResponse(
            _chat_completion(
                json.dumps(
                    {
                        "suspicion_score": 0.91,
                        "detected_pattern": "spoofing_like_wall",
                        "confidence": 0.88,
                        "reasons": ["Local vLLM returned structured synthetic JSON."],
                        "recommended_action": "Review the synthetic replay window.",
                    }
                )
            )
        )

    monkeypatch.setattr(endpoint_app, "urlopen", fake_urlopen)

    response = orderbook_alert(
        OrderBookWindow(
            bids=[{"price": 68120, "quantity": 12.4}],
            asks=[{"price": 68130, "quantity": 1.8}],
            features={"wall_size_ratio": 8.2},
            scenario_hint="spoofing",
        )
    )

    assert response.model_mode == "local_vllm"
    assert response.model == "test-local-vllm-model"
    assert captured["url"] == "http://127.0.0.1:8001/v1/chat/completions"
    assert captured["authorization"] is None


def test_local_vllm_base_url_defaults_to_configured_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCAL_VLLM_BASE_URL", raising=False)
    monkeypatch.setenv("LOCAL_VLLM_HOST", "127.0.0.1")
    monkeypatch.setenv("LOCAL_VLLM_PORT", "8001")

    assert endpoint_app._local_vllm_base_url() == "http://127.0.0.1:8001/v1"


def test_invalid_model_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_MODE", "local_vllm")
    monkeypatch.setenv("LOCAL_VLLM_MODEL", "test-model")

    def fake_urlopen(request: object, timeout: float) -> FakeModelResponse:
        return FakeModelResponse(_chat_completion("{not-json"))

    monkeypatch.setattr(endpoint_app, "urlopen", fake_urlopen)

    response = orderbook_alert(
        OrderBookWindow(
            bids=[{"price": 68120, "quantity": 12.4}],
            asks=[{"price": 68130, "quantity": 1.8}],
            features={"wall_size_ratio": 8.2},
            scenario_hint="spoofing",
        )
    )

    assert response.model_mode == "deterministic_fallback"
    assert response.model == "test-model"
    assert response.detected_pattern == "spoofing_like_wall"
    assert response.fallback_reason == "invalid_model_json"


def test_wrong_shaped_model_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_MODE", "local_vllm")
    monkeypatch.setenv("LOCAL_VLLM_MODEL", "test-model")

    def fake_urlopen(request: object, timeout: float) -> FakeModelResponse:
        return FakeModelResponse(_chat_completion(json.dumps({"unexpected": "shape"})))

    monkeypatch.setattr(endpoint_app, "urlopen", fake_urlopen)

    response = orderbook_alert(
        OrderBookWindow(
            bids=[{"price": 68120, "quantity": 12.4}],
            asks=[{"price": 68130, "quantity": 1.8}],
            features={"wall_size_ratio": 8.2},
            scenario_hint="spoofing",
        )
    )

    assert response.model_mode == "deterministic_fallback"
    assert response.model == "test-model"
    assert response.detected_pattern == "spoofing_like_wall"
    assert response.reasons != ["unexpected"]
    assert response.fallback_reason == "invalid_model_json"


def test_unknown_endpoint_mode_falls_back_without_http_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_MODE", "unsupported")

    def fail_urlopen(request: object, timeout: float) -> FakeModelResponse:
        raise AssertionError("HTTP model call should not run for unsupported endpoint mode")

    monkeypatch.setattr(endpoint_app, "urlopen", fail_urlopen)

    response = orderbook_alert(
        OrderBookWindow(
            bids=[{"price": 68120, "quantity": 12.4}],
            asks=[{"price": 68130, "quantity": 1.8}],
            features={"wall_size_ratio": 8.2},
            scenario_hint="spoofing",
        )
    )

    assert response.model_mode == "deterministic_fallback"
    assert response.model == "Qwen/Qwen2.5-1.5B-Instruct"
    assert response.latency_ms == 0.0
    assert response.fallback_reason == "unsupported_endpoint_mode"


def test_model_json_parser_extracts_fenced_object() -> None:
    parsed = endpoint_app._parse_json_object_text(
        "Model output:\n```json\n{\"status\":\"ok\",\"value\":1}\n```\nTrailing text."
    )

    assert parsed == {"status": "ok", "value": 1}

from app import IncidentExplanationRequest, ScenarioGenerationRequest, explain_event, generate_scenario, health


def test_health_uses_fallback_mode_by_default() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["model_mode"] == "deterministic_fallback"


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

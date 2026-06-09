from app import (
    IncidentExplanationRequest,
    InvestigationReportRequest,
    OrderBookWindow,
    ScenarioGenerationRequest,
    explain_event,
    generate_scenario,
    health,
    investigation_report,
    orderbook_alert,
)


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

import json
from pathlib import Path

from surveillance import (
    MAX_DETECTOR_SCORES,
    MAX_TIMELINE_EVENTS,
    MAX_USER_PROMPT_CHARS,
    SURVEILLANCE_SYSTEM_PROMPT,
    SurveillanceInvestigationRequest,
    SurveillanceInvestigationResponse,
    build_surveillance_request,
    build_user_prompt,
    choose_analysis_type,
    output_token_budget,
    parse_surveillance_response,
)


def _assessment() -> dict[str, object]:
    return {
        "classification": "spoofing_like",
        "confidence": 0.86,
        "severity": "high",
        "market_context": "Synthetic thin-liquidity episode.",
        "evidence": [
            {
                "observation": "Displayed pressure was cancelled.",
                "metric": "cancel_ratio",
                "value": "0.91",
                "reasoning": "The supplied ratio is elevated.",
            }
        ],
        "counter_evidence": [],
        "alternative_explanations": ["Temporary legitimate liquidity provision."],
        "episode_timeline": ["Pressure appeared.", "Orders were cancelled."],
        "detector_disagreement": "No material disagreement.",
        "recommended_actions": ["Review the synthetic replay summary."],
        "regulatory_assessment": "Educational triage only.",
        "executive_summary": "Evidence supports a spoofing-like synthetic classification.",
    }


def test_prompt_builder_summarizes_raw_episode_and_stays_below_budget() -> None:
    events = [
        {
            "type": "cancel_order" if index % 2 else "place_order",
            "tick": index,
            "agent_id": "A-7",
            "side": "sell",
            "price": 100.0 + index / 100,
            "quantity": 50 + index,
            "message": "bounded synthetic order event " + "x" * 500,
        }
        for index in range(5000)
    ]
    levels = [{"price": 100 + index / 100, "quantity": index + 1, "owner": "A-7"} for index in range(1000)]
    source = {
        "incident": {"id": "INC-7", "agent": "A-7", "confidence": 0.92, "type": "spoofing"},
        "replay": {
            "book": {"bids": levels, "asks": levels},
            "detectors": [
                {"name": f"detector-{index}", "confidence": index / 20, "alert": index > 14}
                for index in range(20)
            ],
            "features": {"cancel_ratio": 0.91, "wall_size_ratio": 8.4},
            "market": {"best_bid": 99.9, "best_ask": 100.1, "mid": 100.0, "spread": 0.2},
            "recent_events": events,
        },
    }
    request = build_surveillance_request(
        source,
        analysis_type="high_anomaly",
        invocation_reason="test anomaly",
    )
    prompt = build_user_prompt(request)
    encoded = json.dumps(prompt, separators=(",", ":"))

    assert len(encoded) <= MAX_USER_PROMPT_CHARS
    assert len(request.event_timeline) == MAX_TIMELINE_EVENTS
    assert len(request.detector_scores) == MAX_DETECTOR_SCORES
    assert request.lob_summary["during"]["levels_summarized"] == {"bids": 1000, "asks": 1000}
    assert "bids" not in request.lob_summary["during"]
    assert "asks" not in request.lob_summary["during"]
    assert request.order_statistics["cancel_count"] > 0
    assert prompt["episode_summary"]["schema_version"] == "aimada.surveillance.request.v1"


def test_llm_invocation_policy_uses_only_professional_analysis_triggers() -> None:
    assert choose_analysis_type({"anomaly_score": 0.9}, operation="event_screening")[0] == "high_anomaly"
    assert choose_analysis_type(
        {"detector_scores": [{"score": 0.2}, {"score": 0.7}]},
        operation="event_screening",
    )[0] == "detector_disagreement"
    assert choose_analysis_type(
        {"episode_status": "completed", "ground_truth": {"label": "spoofing"}},
        operation="episode_analysis",
    )[0] == "completed_episode"
    assert choose_analysis_type(
        {"episode_status": "completed", "ground_truth": {"label": "benign"}},
        operation="episode_analysis",
    )[0] is None
    assert choose_analysis_type({}, operation="simulation_summary")[0] == "simulation_summary"
    assert choose_analysis_type({}, operation="benchmark_generation")[0] == "benchmark_generation"
    assert choose_analysis_type({"anomaly_score": 0.2}, operation="event_screening")[0] is None


def test_professional_response_parser_is_strict_and_bounded() -> None:
    parsed = parse_surveillance_response(_assessment())

    assert isinstance(parsed, SurveillanceInvestigationResponse)
    assert parsed.classification == "spoofing_like"
    assert parse_surveillance_response({**_assessment(), "invented_extra_field": True}) is None
    assert parse_surveillance_response({"classification": "spoofing_like"}) is None


def test_prompt_policy_hides_chain_of_thought_and_adjusts_benign_budget() -> None:
    assert "never reveal chain-of-thought" in SURVEILLANCE_SYSTEM_PROMPT
    assert "Never invent" in SURVEILLANCE_SYSTEM_PROMPT
    request = build_surveillance_request(
        {"detector_scores": [{"detector": "baseline", "score": 0.2}]},
        analysis_type="benchmark_generation",
        invocation_reason="benchmark",
    )

    assert output_token_budget(request) == 500


def test_missing_episode_data_is_not_presented_as_observed_zero() -> None:
    request = build_surveillance_request(
        {"anomaly_score": 0.8},
        analysis_type="high_anomaly",
        invocation_reason="test",
    )

    assert request.order_statistics == {}
    assert request.trade_statistics == {}
    assert request.cancellation_metrics == {}
    assert request.execution_metrics == {}
    assert "order_statistics" in request.missing_fields
    assert "trade_statistics" in request.missing_fields


def test_structured_episode_summary_is_promoted_into_the_prompt_contract() -> None:
    request = build_surveillance_request(
        {
            "incident": {"id": "INC-42", "confidence": 0.91},
            "detector_outputs": [{"detector": "spoofing_like", "score": 0.91, "alert": True}],
            "order_book_context": {"events": [{"type": "cancel", "agent_id": "A1"}]},
            "trades": [{"trade_id": "T1", "quantity": 2.0}],
            "market_metrics": {"cancel_to_trade_ratio": 7.0},
            "episode_summary": {
                "simulation_metadata": {"episode_id": "INC-42", "scenario_family": "spoofing"},
                "market_regime": {"liquidity": "thin", "volatility": "low"},
                "instrument": {"symbol": "AIMD"},
                "event_timeline": [{"sequence": 1, "event": "wall placed"}],
                "lob_summary": {"during": {"mid": 100.0}},
                "cancellation_metrics": {"cancel_probability": 0.96},
                "execution_metrics": {"execution_ratio": 0.04},
            },
        },
        analysis_type="high_anomaly",
        invocation_reason="structured context test",
    )

    assert request.market_regime["liquidity"] == "thin"
    assert request.instrument["symbol"] == "AIMD"
    assert request.event_timeline[0].event == "wall placed"
    assert request.cancellation_metrics["cancel_probability"] == 0.96
    assert request.execution_metrics["execution_ratio"] == 0.04


def test_committed_json_schemas_match_runtime_contracts() -> None:
    schema_dir = Path(__file__).with_name("schemas")
    request_schema = json.loads((schema_dir / "surveillance-request.schema.json").read_text(encoding="utf-8"))
    response_schema = json.loads((schema_dir / "surveillance-response.schema.json").read_text(encoding="utf-8"))
    runtime_response = SurveillanceInvestigationResponse.model_json_schema()

    assert request_schema["properties"]["schema_version"]["const"] == "aimada.surveillance.request.v1"
    assert request_schema["properties"]["event_timeline"]["maxItems"] == MAX_TIMELINE_EVENTS
    assert request_schema["properties"]["detector_scores"]["maxItems"] == MAX_DETECTOR_SCORES
    assert set(response_schema["required"]) == set(runtime_response["required"])
    assert set(response_schema["properties"]) == set(runtime_response["properties"])


def test_committed_examples_validate_against_runtime_contracts() -> None:
    example_dir = Path(__file__).with_name("examples")

    for name in ("spoofing", "layering", "benign-market-making", "uncertain"):
        example = json.loads((example_dir / f"{name}.json").read_text(encoding="utf-8"))
        request = SurveillanceInvestigationRequest.model_validate(example["request"])
        response = SurveillanceInvestigationResponse.model_validate(example["response"])

        assert request.schema_version == "aimada.surveillance.request.v1"
        assert response.classification

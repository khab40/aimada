from app.detectors.aggregate_score import aggregate_detector_scores
from app.arena.engine import SimulationEngine


def test_aggregate_score_flags_large_order() -> None:
    result = aggregate_detector_scores([{"type": "limit_order", "quantity": 500, "price": 98.0}])

    assert result["alerts"]
    assert result["alerts"][0]["name"] == "spoofing_like"


def test_live_detector_engine_adds_scores_features_and_evidence() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("spoofing-like")
    for _ in range(4):
        state = engine.step()

    spoofing = next(score for score in state["detectors"]["scores"] if score["name"] == "spoofing_like")

    assert state["features"]["wall_size_ratio"] > 1.0
    assert state["features"]["message_rate_per_sec"] > 0
    assert spoofing["evidence"]
    assert state["active_scenario"]["evidence"]


def test_quote_stuffing_detector_scores_message_rate() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("quote-stuffing")
    for _ in range(5):
        state = engine.step()

    quote = next(score for score in state["detectors"]["scores"] if score["name"] == "quote_stuffing")

    assert state["features"]["message_rate_per_sec"] >= 18
    assert quote["confidence"] >= 0.75
    assert quote["alert"] is True

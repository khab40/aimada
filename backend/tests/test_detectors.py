from dataclasses import replace

from app.detectors.aggregate_score import aggregate_detector_scores
from app.detectors.aggregate import aggregate_detector_scores_from_features
from app.detectors.features import DetectorFeatures
from app.arena.engine import SimulationEngine


def normal_market_features() -> DetectorFeatures:
    return DetectorFeatures(
        spread_bps=0.15,
        order_book_imbalance=0.02,
        top_n_bid_depth=100.0,
        top_n_ask_depth=102.0,
        depth_change_pct=1.0,
        wall_size_ratio=1.0,
        order_lifetime_ms=12_000.0,
        cancel_to_trade_ratio=0.3,
        message_rate_per_sec=4.0,
    )


def test_aggregate_score_flags_large_order() -> None:
    result = aggregate_detector_scores([{"type": "limit_order", "quantity": 500, "price": 98.0}])

    assert result["alerts"]
    assert result["alerts"][0]["name"] == "spoofing_like"


def test_live_detector_engine_adds_scores_features_and_evidence() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("spoofing_like_wall")
    for _ in range(4):
        state = engine.step()

    spoofing = next(score for score in state["detectors"]["scores"] if score["name"] == "spoofing_like")

    assert state["features"]["wall_size_ratio"] > 1.0
    assert state["features"]["message_rate_per_sec"] > 0
    assert spoofing["evidence"]
    assert state["active_scenario"]["evidence"]


def test_quote_stuffing_detector_scores_message_rate() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("quote_stuffing")
    for _ in range(5):
        state = engine.step()

    quote = next(score for score in state["detectors"]["scores"] if score["name"] == "quote_stuffing")

    assert state["features"]["message_rate_per_sec"] >= 18
    assert quote["confidence"] >= 0.75
    assert quote["alert"] is True


def test_aggregate_detector_does_not_alert_on_normal_market_making() -> None:
    scores = aggregate_detector_scores_from_features(normal_market_features())

    assert scores.alerts == []
    assert all(score.confidence < 0.75 for score in scores.scores)


def test_spoofing_like_features_trigger_spoofing_alert_only() -> None:
    scores = aggregate_detector_scores_from_features(
        DetectorFeatures(
            spread_bps=0.2,
            order_book_imbalance=-0.45,
            top_n_bid_depth=80.0,
            top_n_ask_depth=170.0,
            depth_change_pct=3.0,
            wall_size_ratio=8.5,
            order_lifetime_ms=1_500.0,
            cancel_to_trade_ratio=4.0,
            message_rate_per_sec=8.0,
        )
    )

    alerts = {score.name for score in scores.alerts}
    assert "spoofing_like" in alerts
    assert "quote_stuffing" not in alerts


def test_layering_like_features_trigger_layering_alert() -> None:
    scores = aggregate_detector_scores_from_features(
        DetectorFeatures(
            spread_bps=0.2,
            order_book_imbalance=-0.38,
            top_n_bid_depth=70.0,
            top_n_ask_depth=150.0,
            depth_change_pct=5.0,
            wall_size_ratio=5.5,
            order_lifetime_ms=8_000.0,
            cancel_to_trade_ratio=1.0,
            message_rate_per_sec=6.0,
            large_level_count=3,
        )
    )

    layering = next(score for score in scores.scores if score.name == "layering_like")
    assert layering.alert is True
    assert layering.confidence >= 0.75


def test_quote_stuffing_requires_more_than_message_rate_noise() -> None:
    scores = aggregate_detector_scores_from_features(
        replace(normal_market_features(), message_rate_per_sec=12.0)
    )

    quote = next(score for score in scores.scores if score.name == "quote_stuffing")
    assert quote.alert is False
    assert quote.confidence < 0.75

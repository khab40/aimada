from app.detectors.aggregate_score import aggregate_detector_scores


def test_aggregate_score_flags_large_order() -> None:
    result = aggregate_detector_scores([{"type": "limit_order", "quantity": 500, "price": 98.0}])

    assert result["alerts"]
    assert result["alerts"][0]["name"] == "spoofing_like"

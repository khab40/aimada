from app.detectors.layering_detector import LayeringDetector
from app.detectors.liquidity_shock_detector import LiquidityShockDetector
from app.detectors.quote_stuffing_detector import QuoteStuffingDetector
from app.detectors.spoofing_detector import SpoofingDetector


def aggregate_detector_scores(events: list[dict[str, object]]) -> dict[str, object]:
    scores = [
        SpoofingDetector().score(events),
        LayeringDetector().score(events),
        QuoteStuffingDetector().score(events),
        LiquidityShockDetector().score(events),
    ]
    return {
        "scores": scores,
        "alerts": [score for score in scores if score["alert"]],
    }

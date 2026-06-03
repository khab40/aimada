from app.detectors.features import DetectorFeatures
from app.detectors.layering_like_detector import LayeringLikeDetector
from app.detectors.liquidity_shock_detector import LiquidityShockDetector
from app.detectors.quote_stuffing_detector import QuoteStuffingDetector
from app.detectors.spoofing_like_detector import SpoofingLikeDetector
from app.schemas.arena import DetectorScores, EvidenceItem


class AggregateDetectorEngine:
    def __init__(self) -> None:
        self.detectors = [
            SpoofingLikeDetector(),
            LayeringLikeDetector(),
            QuoteStuffingDetector(),
            LiquidityShockDetector(),
        ]

    def detect(self, features: DetectorFeatures) -> DetectorScores:
        scores = [detector.detect(features) for detector in self.detectors]
        return DetectorScores(
            scores=scores,
            alerts=[score for score in scores if score.alert],
        )


def aggregate_detector_scores_from_features(features: DetectorFeatures) -> DetectorScores:
    return AggregateDetectorEngine().detect(features)


def flatten_evidence(scores: DetectorScores) -> list[EvidenceItem]:
    evidence: dict[str, EvidenceItem] = {}
    for score in scores.scores:
        for item in score.evidence or []:
            evidence.setdefault(item.key, item)
    return list(evidence.values())

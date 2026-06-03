from app.detectors.features import DetectorFeatures
from app.schemas.arena import DetectorScore, EvidenceItem


class LayeringLikeDetector:
    name = "layering_like"

    def detect(self, features: DetectorFeatures) -> DetectorScore:
        wall_component = min(features.wall_size_ratio / 5.0, 1.0)
        imbalance_component = min(abs(features.order_book_imbalance) / 0.35, 1.0)
        depth_component = 1.0 if features.top_n_ask_depth > features.top_n_bid_depth * 1.4 else 0.35
        confidence = round(wall_component * 0.45 + imbalance_component * 0.3 + depth_component * 0.25, 4)
        return DetectorScore(
            name=self.name,
            confidence=min(confidence, 1.0),
            alert=confidence >= 0.75,
            severity=_severity(confidence),
            evidence=[
                EvidenceItem(
                    key="top_n_ask_depth",
                    label="Top ask depth",
                    value=features.top_n_ask_depth,
                    interpretation="Same-side visible depth is elevated across nearby ask levels.",
                ),
                EvidenceItem(
                    key="order_book_imbalance",
                    label="Order-book imbalance",
                    value=features.order_book_imbalance,
                    interpretation="Depth distribution shifted toward one side of the book.",
                ),
            ],
        )


def _severity(confidence: float) -> str:
    if confidence >= 0.9:
        return "critical"
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"

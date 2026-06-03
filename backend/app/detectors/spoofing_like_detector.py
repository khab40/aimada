from app.detectors.features import DetectorFeatures
from app.schemas.arena import DetectorScore, EvidenceItem


class SpoofingLikeDetector:
    name = "spoofing_like"

    def detect(self, features: DetectorFeatures) -> DetectorScore:
        wall_component = min(features.wall_size_ratio / 8.0, 1.0)
        lifetime_component = 1.0 if 500 <= features.order_lifetime_ms <= 5_000 else 0.25
        cancel_component = min(features.cancel_to_trade_ratio / 3.0, 1.0)
        imbalance_component = min(abs(features.order_book_imbalance) / 0.5, 1.0)
        confidence = round(max(wall_component * 0.6 + lifetime_component * 0.2 + cancel_component * 0.1 + imbalance_component * 0.1, 0.0), 4)
        return DetectorScore(
            name=self.name,
            confidence=min(confidence, 1.0),
            alert=confidence >= 0.75,
            severity=_severity(confidence),
            evidence=[
                EvidenceItem(
                    key="wall_size_ratio",
                    label="Visible wall ratio",
                    value=features.wall_size_ratio,
                    interpretation="Large abuser-owned visible liquidity relative to nearby depth.",
                ),
                EvidenceItem(
                    key="order_lifetime_ms",
                    label="Order lifetime",
                    value=features.order_lifetime_ms,
                    unit="ms",
                    interpretation="Short-lived visible pressure is consistent with spoofing-like behavior.",
                ),
                EvidenceItem(
                    key="cancel_to_trade_ratio",
                    label="Cancel/trade ratio",
                    value=features.cancel_to_trade_ratio,
                    interpretation="Cancellation activity is elevated relative to executions.",
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

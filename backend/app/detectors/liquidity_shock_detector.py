from app.detectors.features import DetectorFeatures, count_events
from app.schemas.arena import DetectorScore, EvidenceItem


class LiquidityShockDetector:
    name = "liquidity_shock"

    def detect(self, features: DetectorFeatures) -> DetectorScore:
        depth_component = min(abs(min(features.depth_change_pct, 0.0)) / 45.0, 1.0)
        spread_component = min(features.spread_bps / 1.0, 1.0)
        imbalance_component = min(abs(features.order_book_imbalance) / 0.55, 1.0)
        confidence = round(depth_component * 0.45 + spread_component * 0.35 + imbalance_component * 0.2, 4)
        return DetectorScore(
            name=self.name,
            confidence=min(confidence, 1.0),
            alert=confidence >= 0.75,
            severity=_severity(confidence),
            evidence=[
                EvidenceItem(
                    key="depth_change_pct",
                    label="Depth change",
                    value=features.depth_change_pct,
                    unit="%",
                    interpretation="Top-of-book depth changed abruptly versus the previous tick.",
                ),
                EvidenceItem(
                    key="spread_bps",
                    label="Spread",
                    value=features.spread_bps,
                    unit="bps",
                    interpretation="Spread widening indicates weaker visible liquidity.",
                ),
            ],
        )

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(count_events(events, "cancel") / 10, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}


def _severity(confidence: float) -> str:
    if confidence >= 0.9:
        return "critical"
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"

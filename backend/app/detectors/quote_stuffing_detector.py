from app.detectors.features import DetectorFeatures
from app.schemas.arena import DetectorScore, EvidenceItem


class QuoteStuffingDetector:
    name = "quote_stuffing"

    def detect(self, features: DetectorFeatures) -> DetectorScore:
        message_component = min(features.message_rate_per_sec / 18.0, 1.0)
        cancel_component = min(features.cancel_to_trade_ratio / 8.0, 1.0)
        confidence = round(message_component * 0.75 + cancel_component * 0.25, 4)
        return DetectorScore(
            name=self.name,
            confidence=min(confidence, 1.0),
            alert=confidence >= 0.75,
            severity=_severity(confidence),
            evidence=[
                EvidenceItem(
                    key="message_rate_per_sec",
                    label="Message rate",
                    value=features.message_rate_per_sec,
                    unit="events/sec",
                    interpretation="High update throughput in the current tick window.",
                ),
                EvidenceItem(
                    key="cancel_to_trade_ratio",
                    label="Cancel/trade ratio",
                    value=features.cancel_to_trade_ratio,
                    interpretation="Most updates do not result in execution.",
                ),
            ],
        )

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(len(events) / 30, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}


def _severity(confidence: float) -> str:
    if confidence >= 0.9:
        return "critical"
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"

from app.detectors.features import DetectorFeatures
from app.schemas.arena import DetectorScore, EvidenceItem


class LayeringLikeDetector:
    name = "layering_like"

    def detect(self, features: DetectorFeatures) -> DetectorScore:
        wall_component = min(features.wall_size_ratio / 5.0, 1.0)
        imbalance_component = min(abs(features.order_book_imbalance) / 0.35, 1.0)
        dominant_depth = max(features.top_n_ask_depth, features.top_n_bid_depth)
        opposite_depth = min(features.top_n_ask_depth, features.top_n_bid_depth)
        depth_component = 1.0 if dominant_depth > opposite_depth * 1.4 else 0.35
        replenishment_component = min(features.replenishment_rate, 1.0)
        multi_level_component = 1.0 if features.large_level_count >= 3 else 0.0
        confidence = round(
            wall_component * 0.15
            + imbalance_component * 0.15
            + depth_component * 0.2
            + replenishment_component * 0.15
            + multi_level_component * 0.35,
            4,
        )
        return DetectorScore(
            name=self.name,
            confidence=min(confidence, 1.0),
            alert=confidence >= 0.75,
            severity=_severity(confidence),
            evidence=[
                EvidenceItem(
                    key="dominant_side_depth",
                    label="Dominant-side depth",
                    value=dominant_depth,
                    interpretation="Visible depth is evaluated symmetrically on bid and ask sides.",
                ),
                EvidenceItem(
                    key="order_book_imbalance",
                    label="Order-book imbalance",
                    value=features.order_book_imbalance,
                    interpretation="Depth distribution shifted toward one side of the book.",
                ),
                EvidenceItem(
                    key="large_level_count",
                    label="Large nearby levels",
                    value=features.large_level_count,
                    interpretation="Layering requires multiple unusually large same-side levels, not one wall.",
                ),
                EvidenceItem(
                    key="replenishment_rate",
                    label="Replenishment pattern",
                    value=features.replenishment_rate,
                    interpretation="Repeated updates at linked visible levels strengthen multi-level evidence.",
                ),
                EvidenceItem(
                    key="side_switching_rate",
                    label="Side switching",
                    value=features.side_switching_rate,
                    interpretation="Participant-side changes are measured when event linkage is available.",
                ),
                EvidenceItem(
                    key="linked_order_ids",
                    label="Linked orders",
                    value=",".join(features.linked_order_ids) or "unavailable",
                    interpretation="Linked order identifiers are derived from observable events, not scenario labels.",
                ),
                EvidenceItem(
                    key="linked_participant_ids",
                    label="Linked participants",
                    value=",".join(features.linked_participant_ids) or "unavailable",
                    interpretation="Participant linkage is included only when present in observable events.",
                ),
                EvidenceItem(
                    key="linked_event_ids",
                    label="Linked events",
                    value=",".join(features.linked_event_ids) or "unavailable",
                    interpretation="Event attribution links alerts to observable event identifiers.",
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

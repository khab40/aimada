from app.detectors.base import Detector
from app.detectors.features import unique_price_levels


class LayeringDetector(Detector):
    name = "layering_like"

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(unique_price_levels(events) / 3, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}

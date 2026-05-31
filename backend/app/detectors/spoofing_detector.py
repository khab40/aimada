from app.detectors.base import Detector
from app.detectors.features import max_quantity


class SpoofingDetector(Detector):
    name = "spoofing_like"

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(max_quantity(events) / 500, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}

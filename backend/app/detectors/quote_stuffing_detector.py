from app.detectors.base import Detector


class QuoteStuffingDetector(Detector):
    name = "quote_stuffing_like"

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(len(events) / 30, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}

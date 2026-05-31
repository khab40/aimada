from app.detectors.base import Detector
from app.detectors.features import count_events


class LiquidityShockDetector(Detector):
    name = "liquidity_shock"

    def score(self, events: list[dict[str, object]]) -> dict[str, object]:
        confidence = min(count_events(events, "cancel") / 10, 1.0)
        return {"name": self.name, "confidence": confidence, "alert": confidence >= 0.8}

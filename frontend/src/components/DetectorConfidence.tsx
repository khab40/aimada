import type { DetectorScore, DetectorScores } from "@/types/arena";

type DetectorMeter = {
  label: string;
  match: (score: DetectorScore) => boolean;
};

type Severity = "normal" | "watch" | "warning" | "critical";

const detectorMeters: DetectorMeter[] = [
  { label: "Spoofing-like", match: (score) => score.name.toLowerCase().includes("spoof") },
  { label: "Layering-like", match: (score) => score.name.toLowerCase().includes("layer") },
  { label: "Quote stuffing", match: (score) => score.name.toLowerCase().includes("quote") },
  { label: "Liquidity shock", match: (score) => score.name.toLowerCase().includes("liquidity") }
];

export function DetectorConfidence({ detectors }: { detectors: DetectorScores }) {
  const hasScores = detectors.scores.length > 0;

  return (
    <section className="detector-confidence-panel">
      <h2>Detector Confidence</h2>
      {!hasScores ? <div className="empty-state">Waiting for detector scores.</div> : null}
      <div className="detector-meter-list">
        {detectorMeters.map((meter) => {
          const score = detectors.scores.find(meter.match);
          const confidence = score?.confidence ?? 0;
          const severity = getSeverity(confidence);
          const highlighted = Boolean(score?.alert);

          return (
            <div className={`detector-meter ${severity} ${highlighted ? "highlighted" : ""}`} key={meter.label}>
              <div className="detector-meter-header">
                <span>{meter.label}</span>
                <div className="detector-meter-value">
                  {highlighted ? <em>High confidence</em> : null}
                  <strong>{confidence.toFixed(2)}</strong>
                </div>
              </div>
              <div className="detector-meter-track" aria-label={`${meter.label} confidence ${confidence.toFixed(2)}`}>
                <div style={{ width: `${Math.min(confidence, 1) * 100}%` }} />
              </div>
              <span className="detector-severity">{severity}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function getSeverity(confidence: number): Severity {
  if (confidence >= 0.9) {
    return "critical";
  }
  if (confidence >= 0.75) {
    return "warning";
  }
  if (confidence >= 0.45) {
    return "watch";
  }
  return "normal";
}

import type { BattlefieldFrame } from "../types";

export function DetectionPanel({ frame }: { frame: BattlefieldFrame }) {
  const probability = frame.spoofingProbability;
  const severity = probability > 0.82 ? "critical" : probability > 0.62 ? "warning" : probability > 0.35 ? "watch" : "normal";

  return (
    <section className="battlefield-detection panel">
      <div className="section-heading-row">
        <h2>Blue-Team Detection</h2>
        <span className={`battlefield-risk ${severity}`}>{severity}</span>
      </div>
      <div className="battlefield-probability">
        <strong>{Math.round(probability * 100)}%</strong>
        <span>Spoofing probability</span>
        <div className="detector-meter-track">
          <div style={{ width: `${probability * 100}%` }} />
        </div>
      </div>
      <ul className="battlefield-signal-list">
        <li><span>Order-to-trade ratio spike</span><strong>{probability > 0.58 ? "observed" : "pending"}</strong></li>
        <li><span>Cancellation burst</span><strong>{probability > 0.88 ? "confirmed" : "watching"}</strong></li>
        <li><span>Liquidity wall disappeared</span><strong>{frame.tick > 36 ? "confirmed" : "pending"}</strong></li>
        <li><span>Price moved after fake depth</span><strong>{frame.tick > 30 ? "observed" : "pending"}</strong></li>
      </ul>
    </section>
  );
}

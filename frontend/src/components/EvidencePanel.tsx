import type { ArenaState } from "@/types/arena";

type EvidenceStatus = "pending" | "observed" | "confirmed";

type EvidenceRow = {
  explanation: string;
  label: string;
  status: EvidenceStatus;
  value: string;
};

export function EvidencePanel({ state }: { state: ArenaState }) {
  const rows = buildEvidenceRows(state);
  const hasEvidence = rows.some((row) => row.status !== "pending");

  return (
    <section className="evidence-panel">
      <h2>Evidence</h2>
      {hasEvidence ? (
        <div className="evidence-item-list">
          {rows.map((row) => (
            <article className={`evidence-item ${row.status}`} key={row.label}>
              <div className="evidence-item-header">
                <h3>{row.label}</h3>
                <span>{row.status}</span>
              </div>
              <strong>{row.value}</strong>
              <p>{row.explanation}</p>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">No evidence collected yet.</div>
      )}
    </section>
  );
}

function buildEvidenceRows(state: ArenaState): EvidenceRow[] {
  const features = state.features;
  const scenario = state.active_scenario?.scenario_name;
  const hasIncident = state.detectors.alerts.length > 0;
  const currentStage = state.active_scenario?.current_stage ?? state.active_scenario?.status;

  return [
    {
      explanation: "Visible ask-side depth is large relative to normal top-of-book liquidity.",
      label: "Large wall detected",
      status: features && (features.wall_size_ratio ?? 0) >= 5 ? "observed" : "pending",
      value: `${formatNumber(features?.wall_size_ratio)}x wall ratio`
    },
    {
      explanation: "Top-level bid/ask depth moved meaningfully toward one side of the book.",
      label: "Imbalance shifted",
      status: features && Math.abs(features.imbalance ?? 0) >= 0.35 ? "observed" : "pending",
      value: formatNumber(features?.imbalance)
    },
    {
      explanation: "Synthetic scenario reached the cancel phase after placing visible pressure.",
      label: "Cancellation before execution",
      status: currentStage === "wall_cancelled" || currentStage === "cancelled" || currentStage === "incident_confirmed" ? "confirmed" : scenario ? "observed" : "pending",
      value: currentStage === "wall_cancelled" || currentStage === "cancelled" || currentStage === "incident_confirmed" ? "cancel observed" : "waiting"
    },
    {
      explanation: "Spread and mid-price behavior show the market reacted during the scenario window.",
      label: "Price impact confirmed",
      status: hasIncident || Math.abs(features?.depth_change_pct ?? 0) >= 50 ? "confirmed" : scenario ? "observed" : "pending",
      value: `${formatNumber(features?.depth_change_pct)}% depth change`
    },
    {
      explanation: "Cancel activity is elevated versus trades, especially during quote-stuffing-like flow.",
      label: "High cancel/trade ratio",
      status: features && (features.cancel_to_trade_ratio ?? 0) >= 20 ? "confirmed" : scenario ? "observed" : "pending",
      value: `${formatNumber(features?.cancel_to_trade_ratio)}:1`
    }
  ];
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  if (Math.abs(value) >= 1_000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

import type { NebiusUsageMetrics } from "@/features/nebius/types";

export function UsageCostMonitor({ metrics }: { metrics: NebiusUsageMetrics }) {
  return (
    <section className="usage-cost-card">
      <div className="nebius-card-heading">
        <div>
          <h2>Usage & Cost Monitor</h2>
        </div>
      </div>
      <div className="usage-monitor-grid">
        <UsageMetric label="LLM Tokens" value={metrics.tokensUsed.toLocaleString()} detail={`${metrics.aiEndpointCallsToday} Nebius AI calls today`} />
        <UsageMetric label="Managed Experiment Runs" value={String(metrics.serverlessJobsRun)} detail={`${metrics.simulationEventsGenerated.toLocaleString()} events generated`} />
        <UsageMetric label="Storage" value={`${metrics.replayStorageMb} MB`} detail="Replay and artifact storage" />
        <UsageMetric label="Total Cost" value={`$${metrics.estimatedCostUsd.toFixed(2)}`} detail={`${metrics.averageLlmLatencySec.toFixed(1)}s avg LLM latency`} />
      </div>
    </section>
  );
}

function UsageMetric({ detail, label, value }: { label: string; value: string; detail: string }) {
  return (
    <article className="usage-monitor-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

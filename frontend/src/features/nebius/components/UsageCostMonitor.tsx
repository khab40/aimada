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
        <UsageMetric label="LLM Tokens" value="Not reported" detail="Endpoint request count is not metered here" />
        <UsageMetric label="Managed Experiment Runs" value={String(metrics.serverlessJobsRun)} detail="Event count is not reported by the control-plane probe" />
        <UsageMetric label="Storage" value="Not reported" detail="Artifact links are listed below" />
        <UsageMetric label="Total Cost" value="Not metered" detail={`${metrics.averageLlmLatencySec.toFixed(1)}s recorded average latency`} />
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

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
        <UsageMetric label="Session" value={formatDuration(metrics.sessionDurationSec)} detail="Current Command Center browser session" />
        <UsageMetric label="Endpoint calls" value={String(metrics.aiEndpointCallsSession)} detail={`${metrics.averageLlmLatencySec.toFixed(3)}s average measured latency`} />
        <UsageMetric label="LLM tokens" value={metrics.tokensUsed.toLocaleString()} detail="Provider-reported prompt and completion tokens" />
        <UsageMetric label="Job runs" value={String(metrics.serverlessJobsRun)} detail={`${formatDuration(metrics.jobRuntimeSec)} measured runtime · ${metrics.simulationEventsGenerated} workloads/events`} />
        <UsageMetric label="Artifacts" value={String(metrics.artifactCount)} detail={`${metrics.replayStorageMb.toFixed(3)} MB stored this session`} />
        <UsageMetric label="Estimated cost" value={`$${metrics.estimatedCostUsd.toFixed(6)}`} detail={metrics.costBasis} />
      </div>
    </section>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${(seconds - minutes * 60).toFixed(0)}s`;
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

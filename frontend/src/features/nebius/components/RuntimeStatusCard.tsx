import type { NebiusRuntimeStatus, NebiusUsageMetrics } from "@/features/nebius/types";

export function RuntimeStatusCard({ status, usage }: { status: NebiusRuntimeStatus; usage: NebiusUsageMetrics }) {
  const cards = [
    {
      cost: `$${usage.estimatedCostUsd.toFixed(2)}`,
      gpu: status.mode === "nebius-cloud" ? "available" : "not attached",
      lastExecution: status.activeSimulation,
      latency: "regional",
      status: status.cloudStatus,
      title: "Nebius Cloud"
    },
    {
      cost: `$${(usage.aiEndpointCallsToday * 0.002).toFixed(2)}`,
      gpu: "model endpoint",
      lastExecution: `${usage.aiEndpointCallsToday} calls`,
      latency: `${usage.averageLlmLatencySec.toFixed(2)}s`,
      status: status.aiEndpointStatus,
      title: "Nebius AI"
    },
    {
      cost: `$${(usage.serverlessJobsRun * 0.21).toFixed(2)}`,
      gpu: status.serverlessStatus === "running" ? "active" : "ready",
      lastExecution: `${status.ticksProcessed.toLocaleString()} steps`,
      latency: `${status.eventsPerSecond.toLocaleString()}/sec`,
      status: status.serverlessStatus,
      title: "Managed Experiment Jobs"
    },
    {
      cost: "included",
      gpu: "not required",
      lastExecution: `${usage.replayStorageMb.toFixed(0)} MB stored`,
      latency: status.websocketStatus === "live" ? "connected" : "offline",
      status: status.storageStatus,
      title: "Artifacts"
    }
  ];

  return (
    <section className="panel nebius-runtime-card">
      <div className="nebius-card-heading">
        <div>
          <h2>Nebius Runtime</h2>
        </div>
      </div>
      <div className="runtime-status-grid">
        {cards.map((card) => (
          <RuntimeCard key={card.title} {...card} />
        ))}
      </div>
    </section>
  );
}

function RuntimeCard({
  cost,
  gpu,
  lastExecution,
  latency,
  status,
  title
}: {
  cost: string;
  gpu: string;
  lastExecution: string;
  latency: string;
  status: string;
  title: string;
}) {
  return (
    <article className={`runtime-standard-card ${status}`}>
      <div className="runtime-standard-card-header">
        <strong>{title}</strong>
      </div>
      <dl>
        <Metric label="Status" value={status.replace("-", " ")} />
        <Metric label="Latency" value={latency} />
        <Metric label="GPU" value={gpu} />
        <Metric label="Cost" value={cost} />
        <Metric label="Last execution" value={lastExecution} />
      </dl>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

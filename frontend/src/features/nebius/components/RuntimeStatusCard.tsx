import type { NebiusRuntimeStatus, NebiusUsageMetrics } from "@/features/nebius/types";

export function RuntimeStatusCard({ status, usage }: { status: NebiusRuntimeStatus; usage: NebiusUsageMetrics }) {
  const cards = [
    {
      cost: "not metered",
      gpu: "not reported",
      lastExecution: status.activeSimulation,
      latency: "live probes",
      status: status.cloudStatus,
      title: "Nebius Cloud"
    },
    {
      cost: "not metered",
      gpu: "model endpoint",
      lastExecution: usage.aiEndpointCallsToday > 0 ? `${usage.aiEndpointCallsToday} calls` : "not reported",
      latency: usage.averageLlmLatencySec > 0 ? `${usage.averageLlmLatencySec.toFixed(2)}s` : "not reported",
      status: status.aiEndpointStatus,
      title: "Nebius AI"
    },
    {
      cost: "not metered",
      gpu: "not reported",
      lastExecution: `${status.ticksProcessed.toLocaleString()} steps`,
      latency: status.eventsPerSecond > 0 ? `${status.eventsPerSecond.toLocaleString()}/sec` : "not reported",
      status: status.serverlessStatus,
      title: "Managed Experiment Jobs"
    },
    {
      cost: "not metered",
      gpu: "not required",
      lastExecution: `${usage.replayStorageMb.toFixed(0)} MB stored`,
      latency: status.storageStatus === "synced" ? "live probe succeeded" : "unavailable",
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

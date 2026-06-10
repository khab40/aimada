import type { NebiusRuntimeStatus } from "@/features/nebius/types";

export function RuntimeStatusCard({ status }: { status: NebiusRuntimeStatus }) {
  return (
    <section className="panel nebius-runtime-card">
      <div className="runtime-badge-strip">
        <StatusBadge label="Nebius Cloud" value={status.cloudStatus} />
        <StatusBadge label="AI Endpoint" value={status.aiEndpointStatus} />
        <StatusBadge label="Serverless" value={status.serverlessStatus} />
        <StatusBadge label="Storage" value={status.storageStatus} />
      </div>
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Cloud Runtime Status</p>
          <h2>Nebius Runtime</h2>
        </div>
        <strong>{status.cloudStatus === "online" ? "Connected" : status.cloudStatus}</strong>
      </div>
      <div className="runtime-status-grid">
        <Metric label="Region" value={status.region} />
        <Metric label="Mode" value={status.mode === "nebius-cloud" ? "Nebius Cloud" : "Local"} />
        <Metric label="Active simulation" value={status.activeSimulation} />
        <Metric label="Running agents" value={status.runningAgents.toLocaleString()} />
        <Metric label="Ticks processed" value={status.ticksProcessed.toLocaleString()} />
        <Metric label="Events/sec" value={status.eventsPerSecond.toLocaleString()} />
        <Metric label="WebSocket stream" value={status.websocketStatus === "live" ? "Live" : "Disconnected"} />
      </div>
    </section>
  );
}

function StatusBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className={`runtime-top-badge ${value}`}>
      {label}: {value.replace("-", " ").toUpperCase()}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="runtime-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

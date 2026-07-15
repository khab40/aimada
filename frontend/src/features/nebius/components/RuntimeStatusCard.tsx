import type { NebiusRuntimeStatus } from "@/features/nebius/types";

export function RuntimeStatusCard({ status }: { status: NebiusRuntimeStatus }) {
  const cards = [
    {
      detail: status.region === "not reported" ? "Region not reported" : status.region,
      lastExecution: status.activeSimulation,
      status: status.cloudStatus,
      title: "Nebius Cloud"
    },
    {
      detail: "Investigation and scenario routes",
      lastExecution: status.activeSimulation,
      status: status.aiEndpointStatus,
      title: "Nebius AI"
    },
    {
      detail: "Detector tournament execution",
      lastExecution: `${status.ticksProcessed.toLocaleString()} steps`,
      status: status.serverlessStatus,
      title: "Managed Experiment Jobs"
    },
    {
      detail: "Experiment and evidence storage",
      lastExecution: status.storageStatus === "synced" ? "Live probe succeeded" : "No successful probe",
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
  detail,
  lastExecution,
  status,
  title
}: {
  detail: string;
  lastExecution: string;
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
        <Metric label="Role" value={detail} />
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

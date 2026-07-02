import type { ServiceHealth } from "@/features/nebius/types";

type DeploymentHealthCardProps = {
  services: ServiceHealth[];
  message: string | null;
  onPingAi: () => void;
  onTestServerless: () => void;
  onTestStorage: () => void;
  onRestartSimulation: () => void;
};

export function DeploymentHealthCard({
  message,
  onPingAi,
  onRestartSimulation,
  onTestServerless,
  onTestStorage,
  services
}: DeploymentHealthCardProps) {
  return (
    <section className="panel deployment-health-card">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Deployment Health</p>
          <h2>Deployment Health</h2>
        </div>
      </div>
      <div className="deployment-health-list">
        {services.map((service) => (
          <article key={service.name}>
            <strong>{service.name}</strong>
            <span className={`runtime-status ${service.status}`}>{service.status}</span>
          </article>
        ))}
      </div>
      <div className="nebius-button-row">
        <button onClick={onPingAi} type="button">Ping Nebius AI</button>
        <button onClick={onTestServerless} type="button">Test Managed Experiment Job</button>
        <button onClick={onTestStorage} type="button">Test Storage Write</button>
        <button onClick={onRestartSimulation} type="button">Restart Simulation Engine</button>
      </div>
      {message ? <p className="artifact-action-message">{message}</p> : null}
    </section>
  );
}

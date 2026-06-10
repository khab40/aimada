import { Link } from "react-router-dom";

export function ExperimentLabPage() {
  return (
    <section className="experiment-lab-page">
      <div className="panel lab-hero-panel">
        <div>
          <p className="eyebrow">Consolidated workflow</p>
          <h2>Lab moved into Nebius Control Panel</h2>
          <p>
            The old Lab duplicated the serverless runner. Use Arena for the live demo simulation,
            Nebius Control Panel for scenario creation, cloud jobs, detectors, explanations, and reports,
            and Replay & Reports for persisted evidence/history.
          </p>
        </div>
        <Link className="primary-link-button" to="/nebius">Open Nebius Control Panel</Link>
      </div>

      <div className="lab-grid">
        <section className="panel report-card">
          <h3>Arena</h3>
          <p>Live demo simulation, order-book replay, red-team activity, and blue-team detector state.</p>
          <Link to="/arena">Open Arena</Link>
        </section>
        <section className="panel report-card">
          <h3>Nebius Control Panel</h3>
          <p>Create attack scenarios, generate experiment grids, run serverless batches, call AI endpoints, and store artifacts.</p>
          <Link to="/nebius">Open Control Panel</Link>
        </section>
        <section className="panel report-card">
          <h3>Replay & Reports</h3>
          <p>Review benchmark runs, incident explanations, Nebius artifacts, exported files, and promoted evidence.</p>
          <Link to="/reports">Open Replay & Reports</Link>
        </section>
      </div>
    </section>
  );
}

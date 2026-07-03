import { Link } from "react-router-dom";
import { useAuth } from "@/auth/useAuth";
import type { ArenaRole } from "@/api/client";

const tournamentRoles: { value: ArenaRole; label: string; summary: string }[] = [
  {
    value: "attacker",
    label: "Attacker",
    summary: "Create red-team scenarios, inject pressure, and try to evade detector scoring."
  },
  {
    value: "defender",
    label: "Detector",
    summary: "Monitor alerts, call detection endpoints, explain incidents, and defend precision/recall."
  },
  {
    value: "observer",
    label: "Observer",
    summary: "Watch arena state, replay history, and compare participant decisions without changing the run."
  },
  {
    value: "judge",
    label: "Judge",
    summary: "Review evidence, score outcomes, inspect replay windows, and prepare winner reports."
  }
];

export function ExperimentLabPage() {
  const { busy, loginWithGoogle, role, session, setRole, user } = useAuth();
  const selectedRole = tournamentRoles.find((item) => item.value === role) ?? tournamentRoles[2];

  return (
    <section className="experiment-lab-page tournament-page">
      <div className="panel lab-hero-panel tournament-hero">
        <div>
          <h2>Select Role, Login, Join Arena</h2>
        </div>
        <div className="tournament-login-box">
          <span className="endpoint-badge">{session ? "logged in" : "login required"}</span>
          <strong>{session ? `${user?.name ?? "Player"} as ${selectedRole.label}` : selectedRole.label}</strong>
          {!session ? (
            <button className="google-login-button" disabled={busy} onClick={() => void loginWithGoogle(role)} type="button">
              <span className="google-icon" aria-hidden="true">G</span>
              <span>Login with Google</span>
            </button>
          ) : null}
        </div>
      </div>

      <section className="panel tournament-role-panel" aria-label="Tournament role selection">
        <h3>Role</h3>
        <div className="tournament-role-grid">
          {tournamentRoles.map((item) => (
            <button
              className={item.value === role ? "selected" : ""}
              disabled={busy}
              key={item.value}
              onClick={() => void setRole(item.value)}
              type="button"
            >
              <strong>{item.label}</strong>
              <span>{item.summary}</span>
            </button>
          ))}
        </div>
      </section>

      {session ? <RoleWorkspace role={role} /> : (
        <section className="panel tournament-locked-panel">
          <h3>{selectedRole.label} controls locked</h3>
        </section>
      )}
    </section>
  );
}

function RoleWorkspace({ role }: { role: ArenaRole }) {
  if (role === "attacker") {
    return (
      <section className="panel tournament-workspace red">
        <h3>Attacker Console</h3>
        <div className="tournament-action-row">
          <Link className="primary-link-button" to="/attack-scenarios">Create Attack Scenario</Link>
          <Link to="/arena">Open Arena</Link>
        </div>
      </section>
    );
  }
  if (role === "defender") {
    return (
      <section className="panel tournament-workspace blue">
        <h3>Detector Console</h3>
        <div className="tournament-action-row">
          <Link className="primary-link-button" to="/detection">Open Detection</Link>
          <Link to="/detection">Review Alerts</Link>
        </div>
      </section>
    );
  }
  if (role === "judge") {
    return (
      <section className="panel tournament-workspace judge">
        <h3>Judge Console</h3>
        <div className="tournament-action-row">
          <Link className="primary-link-button" to="/detection">Open Detection Outputs</Link>
          <Link to="/nebius">Inspect Artifacts</Link>
        </div>
      </section>
    );
  }
  return (
    <section className="panel tournament-workspace">
      <h3>Observer Console</h3>
      <div className="tournament-action-row">
        <Link className="primary-link-button" to="/arena">Watch Arena</Link>
        <Link to="/detection">Open Detection</Link>
      </div>
    </section>
  );
}

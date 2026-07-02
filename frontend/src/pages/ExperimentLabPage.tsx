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
          <p className="eyebrow">Tournament entry</p>
          <h2>Select Role, Login, Join Arena</h2>
          <p>
            Choose a tournament role before Google login. Anonymous arena mode still works elsewhere; tournament persistence,
            scoring, replay, and later multi-user participation are tied to the logged-in persona.
          </p>
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
          <p>Login with Google to persist the selected role, restore history, and show tournament controls for that persona.</p>
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
        <p>Prepare and launch red-team scenarios. Detector-only and judging actions are hidden for this role.</p>
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
        <p>Watch detector state, run endpoint scoring, and generate incident explanations. Attack creation controls are hidden.</p>
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
        <p>Review persisted evidence, compare runs, inspect replay windows, and prepare winner reports.</p>
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
      <p>Follow live arena state and replay history without attacker, detector, or judge controls.</p>
      <div className="tournament-action-row">
        <Link className="primary-link-button" to="/arena">Watch Arena</Link>
        <Link to="/detection">Open Detection</Link>
      </div>
    </section>
  );
}

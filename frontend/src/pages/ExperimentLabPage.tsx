import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { listManagedExperiments, type ManagedExperiment } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
import { NebiusExecutionTrace, type NebiusExecutionTraceData } from "@/components/NebiusExecutionTrace";
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
  const { busy, role, session, setRole, user } = useAuth();
  const selectedRole = tournamentRoles.find((item) => item.value === role) ?? tournamentRoles[2];
  const [experiments, setExperiments] = useState<ManagedExperiment[]>([]);

  useEffect(() => {
    let cancelled = false;
    listManagedExperiments()
      .then((rows) => {
        if (!cancelled) {
          setExperiments(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setExperiments([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const traces = useMemo(() => createExperimentRunTraces(experiments), [experiments]);

  return (
    <section className="experiment-lab-page tournament-page">
      <div className="panel lab-hero-panel tournament-hero">
        <div>
          <h2>Select Role, Login, Join Arena</h2>
        </div>
        <div className="tournament-login-box">
          <span className="endpoint-badge">{session ? "Google connected" : "Google not connected"}</span>
          <strong>{session ? `${user?.name ?? "Player"} as ${selectedRole.label}` : selectedRole.label}</strong>
          <span>{session ? user?.email ?? "Signed in" : "Use the account menu in the top-right to sign in."}</span>
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

      <section className="panel tournament-workspace experiment-run-records">
        <div className="section-heading-row">
          <div>
            <h3>Reproducible Nebius Job Runs</h3>
          </div>
          <Link to="/nebius">Manage Jobs</Link>
        </div>
        <div className="experiment-comparison-grid">
          <span>Detector thresholds</span>
          <span>Model choices</span>
          <span>Scenario types</span>
          <span>Latency / cost / quality</span>
        </div>
        <div className="experiment-run-trace-grid">
          {traces.map((trace) => <NebiusExecutionTrace key={trace.runId} trace={trace} />)}
        </div>
      </section>
    </section>
  );
}

function createExperimentRunTraces(experiments: ManagedExperiment[]): NebiusExecutionTraceData[] {
  const source = experiments.length ? experiments.slice(0, 3) : [null];
  return source.map((experiment, index) => {
    const metrics = experiment?.metrics?.[0] ?? {};
    const latency = Number(metrics.avg_detection_latency_ms ?? metrics.latency_ms ?? 0);
    const f1 = Number(metrics.f1 ?? 0);
    const simulated = !experiment || experiment.nebius_mode !== "real_nebius_pending";
    return {
      artifactLink: experiment?.artifact_paths.benchmark_report ?? experiment?.artifact_dir ?? null,
      endpointId: null,
      estimatedCost: simulated ? "$0.0000 simulated" : `$${(0.04 + (experiment.attack_count * 0.0008)).toFixed(4)}`,
      executionType: "job",
      fallback: simulated ? "simulated" : "real",
      jobId: experiment ? `JOB-${experiment.id}` : "SIM-JOB-DEMO",
      lastExecutionTime: experiment ? formatExperimentTime(experiment.updated_at) : "Not run yet",
      latency: latency ? `${latency.toFixed(0)} ms` : experiment ? "recorded" : "-",
      model: experiment ? `benchmark model · F1 ${Number.isFinite(f1) && f1 > 0 ? f1.toFixed(2) : "pending"}` : "Deterministic fallback benchmark",
      runId: experiment?.id ?? `demo-experiment-${index + 1}`,
      runtimeGpu: simulated ? "Local deterministic fallback" : "Nebius Serverless GPU job",
      status: experiment?.status.replaceAll("_", " ") ?? "No run yet",
      tokensIn: experiment ? (1200 + experiment.attack_count * 18).toLocaleString() : "-",
      tokensOut: experiment ? (500 + experiment.scenarios.length * 80).toLocaleString() : "-"
    };
  });
}

function formatExperimentTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short"
  }).format(parsed);
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

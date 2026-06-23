import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import "./App.css";
import { AboutPage } from "@/pages/AboutPage";
import { useAuth } from "@/auth/useAuth";
import type { ArenaRole } from "@/api/client";
import { ArenaPage } from "@/pages/ArenaPage";
import { AttackScenarioGeneratorPage } from "@/pages/AttackScenarioGeneratorPage";
import { BlueTeamSurveillancePage } from "@/pages/BlueTeamSurveillancePage";
import { ExperimentLabPage } from "@/pages/ExperimentLabPage";
import { NebiusControlPanelPage } from "@/pages/NebiusControlPanelPage";
import { ReportsPage } from "@/pages/ReportsPage";

const disclaimer =
  "This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic “abuse-like” patterns designed to demonstrate order-book anomaly detection and AI-generated explanations.";

export function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { role } = useAuth();
  const visibleSidebarItems = sidebarItems.filter((item) => item.visibleFor.includes(role));

  return (
    <BrowserRouter>
      <main className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <aside className="app-sidebar" aria-label="Application navigation">
          <div className="sidebar-brand">
            <div>
              <p className="eyebrow">Synthetic order-book arena</p>
              <h1>Market Abuse Arena</h1>
            </div>
            <button
              aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
              className="sidebar-toggle"
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
              type="button"
            >
              {sidebarCollapsed ? ">>" : "<<"}
            </button>
          </div>

          <nav className="side-nav" aria-label="Main screens">
            {visibleSidebarItems.map((item) => (
              <SidebarLink
                icon={item.icon}
                key={item.to}
                label={item.label}
                shortLabel={item.shortLabel}
                team={item.team}
                to={item.to}
              />
            ))}
          </nav>

          <AuthPanel collapsed={sidebarCollapsed} />
        </aside>

        <section className="app-workspace">
          <section className="disclaimer" aria-label="Project disclaimer">
            <strong>Disclaimer: </strong>
            {disclaimer}
          </section>

          <Routes>
            <Route path="/" element={<Navigate to="/arena" replace />} />
            <Route path="/arena" element={<ArenaPage />} />
            <Route path="/attack-scenarios" element={canAccessPath(role, "/attack-scenarios") ? <AttackScenarioGeneratorPage /> : <Navigate to="/arena" replace />} />
            <Route path="/blue-team" element={canAccessPath(role, "/blue-team") ? <BlueTeamSurveillancePage /> : <Navigate to="/arena" replace />} />
            <Route path="/lab" element={canAccessPath(role, "/lab") ? <ExperimentLabPage /> : <Navigate to="/arena" replace />} />
            <Route path="/nebius" element={<NebiusControlPanelPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
          <ArenaSplashOverlay />
        </section>
      </main>
    </BrowserRouter>
  );
}

const SPLASH_HIDE_KEY = "nmaa.hideArenaSplash";
const oneSlideUrl = "/img/ai_market_abuse_arena_one_slide.jpg";

function ArenaSplashOverlay() {
  const location = useLocation();
  const { session } = useAuth();
  const [dismissedSessionId, setDismissedSessionId] = useState<string | null>(null);
  const [dontShowAgain, setDontShowAgain] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const sessionId = session?.session_id ?? null;
    const hidden = window.localStorage.getItem(SPLASH_HIDE_KEY) === "true";
    setDontShowAgain(hidden);
    setVisible(Boolean(sessionId && location.pathname === "/arena" && !hidden && dismissedSessionId !== sessionId));
  }, [dismissedSessionId, location.pathname, session?.session_id]);

  if (!visible || !session) {
    return null;
  }

  function closeSplash() {
    if (dontShowAgain) {
      window.localStorage.setItem(SPLASH_HIDE_KEY, "true");
    }
    setDismissedSessionId(session?.session_id ?? null);
    setVisible(false);
  }

  return (
    <div className="arena-splash-backdrop" role="presentation">
      <section aria-labelledby="arena-splash-title" aria-modal="true" className="arena-splash-panel" role="dialog">
        <div className="arena-splash-copy">
          <p className="eyebrow">Arena overview</p>
          <h2 id="arena-splash-title">Market Abuse Arena</h2>
          <p>
            Synthetic market state, red-team scenarios, detector evidence, replay history, and reports in one shared arena.
          </p>
        </div>
        <img
          alt="One-slide overview of the Market Abuse Arena workflow"
          className="arena-splash-image"
          src={oneSlideUrl}
        />
        <div className="arena-splash-actions">
          <label>
            <input
              checked={dontShowAgain}
              onChange={(event) => setDontShowAgain(event.target.checked)}
              type="checkbox"
            />
            Don&apos;t show on next login
          </label>
          <button onClick={closeSplash} type="button">Enter Arena</button>
        </div>
      </section>
    </div>
  );
}

function SidebarLink({
  label,
  shortLabel,
  icon,
  team,
  to
}: {
  label: string;
  shortLabel: string;
  icon: AppIconName;
  team?: "red" | "blue";
  to: string;
}) {
  return (
    <NavLink className={team ? `team-nav-link ${team}` : undefined} title={label} to={to}>
      <span className="nav-short">{shortLabel}</span>
      <AppIcon name={icon} />
      <span className="nav-label">{label}</span>
    </NavLink>
  );
}

type AppIconName = "arena" | "attack" | "detection" | "tournament" | "reports" | "cloud" | "about";

type SidebarItem = {
  icon: AppIconName;
  label: string;
  shortLabel: string;
  team?: "red" | "blue";
  to: string;
  visibleFor: ArenaRole[];
};

const allRoles: ArenaRole[] = ["observer", "attacker", "defender", "judge"];
const observerAndJudge: ArenaRole[] = ["observer", "judge"];

const sidebarItems: SidebarItem[] = [
  { icon: "arena", label: "Market Arena", shortLabel: "MA", to: "/arena", visibleFor: allRoles },
  { icon: "attack", label: "Attackers", shortLabel: "AT", team: "red", to: "/attack-scenarios", visibleFor: ["observer", "attacker", "judge"] },
  { icon: "detection", label: "Detection", shortLabel: "DT", team: "blue", to: "/blue-team", visibleFor: ["observer", "defender", "judge"] },
  { icon: "tournament", label: "Tournament", shortLabel: "TN", to: "/lab", visibleFor: observerAndJudge },
  { icon: "reports", label: "Replay & Reports", shortLabel: "RR", to: "/reports", visibleFor: allRoles },
  { icon: "cloud", label: "Nebius Control", shortLabel: "NC", to: "/nebius", visibleFor: allRoles },
  { icon: "about", label: "About", shortLabel: "AB", to: "/about", visibleFor: allRoles }
];

function canAccessPath(role: ArenaRole, path: string) {
  const item = sidebarItems.find((candidate) => candidate.to === path);
  return item ? item.visibleFor.includes(role) : true;
}

function AppIcon({ name }: { name: AppIconName }) {
  const paths: Record<AppIconName, string[]> = {
    about: ["M12 17v-5", "M12 8h.01", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
    arena: ["M4 17h16", "M6 14l3-4 3 2 4-6 2 3", "M5 5v14h14"],
    attack: ["M4 12h10", "M10 6l6 6-6 6", "M16 4h4v4", "M16 20h4v-4"],
    cloud: ["M7 18h10a4 4 0 0 0 .8-7.9A6 6 0 0 0 6.4 8.4 4.5 4.5 0 0 0 7 18Z"],
    detection: ["M12 3v3", "M12 18v3", "M3 12h3", "M18 12h3", "M7.8 7.8l2.1 2.1", "M14.1 14.1l2.1 2.1", "M16.2 7.8l-2.1 2.1", "M9.9 14.1l-2.1 2.1", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"],
    reports: ["M6 3h9l3 3v15H6z", "M15 3v4h4", "M9 13h6", "M9 17h6", "M9 9h2"],
    tournament: ["M8 4h8v3a4 4 0 0 1-8 0z", "M6 5H4v2a4 4 0 0 0 4 4", "M18 5h2v2a4 4 0 0 1-4 4", "M12 11v5", "M9 20h6", "M10 16h4"]
  };
  return (
    <svg aria-hidden="true" className="app-icon" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">
      {paths[name].map((path) => <path d={path} key={path} />)}
    </svg>
  );
}

const arenaRoles: { label: string; value: ArenaRole }[] = [
  { label: "Observer", value: "observer" },
  { label: "Attacker", value: "attacker" },
  { label: "Detector", value: "defender" },
  { label: "Judge", value: "judge" }
];

function AuthPanel({ collapsed }: { collapsed: boolean }) {
  const { busy, error, lastMessage, loginWithGoogle, logout, role, saveNow, session, setRole, user } = useAuth();
  return (
    <section className="auth-panel" aria-label="Google login and tournament persona">
      <div className="auth-main">
        {user ? (
          <div>
            <span className="endpoint-badge">Google</span>
            <strong>{user.name}</strong>
            <span>{user.email}</span>
          </div>
        ) : (
          <div>
            <span className="endpoint-badge">anonymous</span>
            <strong>Local arena mode</strong>
            <span>Login persists history for replay.</span>
          </div>
        )}
      </div>
      <label className="auth-role-select" title="Tournament role">
        Role
        <select disabled={busy} value={role} onChange={(event) => void setRole(event.target.value as ArenaRole)}>
          {arenaRoles.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </label>
      <div className="auth-actions">
        {session ? (
          <>
            <button disabled={busy} onClick={() => void saveNow()} title="Save History" type="button">{collapsed ? "S" : "Save History"}</button>
            <button disabled={busy} onClick={() => void logout()} title="Logout" type="button">{collapsed ? "X" : "Logout"}</button>
          </>
        ) : (
          <button className="google-login-button" disabled={busy} onClick={() => void loginWithGoogle(role)} title="Continue with Google" type="button">
            <span className="google-icon" aria-hidden="true">G</span>
            <span>{collapsed ? "G" : "Continue with Google"}</span>
          </button>
        )}
      </div>
      {error ? <span className="auth-status warning">{error}</span> : lastMessage ? <span className="auth-status">{lastMessage}</span> : null}
    </section>
  );
}

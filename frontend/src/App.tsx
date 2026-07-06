import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import "./App.css";
import { AboutPage } from "@/pages/AboutPage";
import { useAuth } from "@/auth/useAuth";
import type { ArenaRole } from "@/api/client";
import { ArenaPage } from "@/pages/ArenaPage";
import { AttackScenarioGeneratorPage } from "@/pages/AttackScenarioGeneratorPage";
import { NebiusControlPanelPage } from "@/pages/NebiusControlPanelPage";
import { featureFlags } from "@/featureFlags";
import { productRoleLabel } from "@/platform/identity";
import {
  getStoredRuntimeMode,
  runtimeComponents,
  storeRuntimeMode,
  visibleRuntimeOptions,
  type RuntimeComponent,
  type RuntimeMode,
  type RuntimeStatus
} from "@/runtimeModes";

const disclaimer =
  "This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic “abuse-like” patterns designed to demonstrate order-book anomaly detection and AI Investigator explanations.";

type ThemePreference = "system" | "light" | "dark";
type ResolvedTheme = "light" | "dark";

const THEME_PREFERENCE_KEY = "aimada.themePreference";
const SIDEBAR_WIDTH_KEY = "aimada.sidebarWidth";
const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 420;
const SIDEBAR_DEFAULT_WIDTH = 292;
const SIDEBAR_COLLAPSED_WIDTH = 78;

export function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(() => getStoredSidebarWidth());
  const resizingRef = useRef(false);
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => getStoredThemePreference());
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() => getSystemTheme());
  const resolvedTheme = themePreference === "system" ? systemTheme : themePreference;
  const visibleSidebarItems = sidebarItems.filter((item) => item.primary || featureFlags.enableLegacyPages);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    function handleChange() {
      setSystemTheme(media.matches ? "dark" : "light");
    }
    handleChange();
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(THEME_PREFERENCE_KEY, themePreference);
  }, [themePreference]);

  useEffect(() => {
    if (!sidebarCollapsed) {
      window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth));
    }
  }, [sidebarCollapsed, sidebarWidth]);

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.dataset.themePreference = themePreference;
    document.documentElement.style.colorScheme = resolvedTheme;
  }, [resolvedTheme, themePreference]);

  function startSidebarResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (sidebarCollapsed) {
      return;
    }
    resizingRef.current = true;
    event.currentTarget.setPointerCapture(event.pointerId);
    document.body.dataset.sidebarResizing = "true";
  }

  function resizeSidebar(event: ReactPointerEvent<HTMLDivElement>) {
    if (!resizingRef.current) {
      return;
    }
    setSidebarWidth(clampSidebarWidth(event.clientX));
  }

  function stopSidebarResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (!resizingRef.current) {
      return;
    }
    resizingRef.current = false;
    event.currentTarget.releasePointerCapture(event.pointerId);
    delete document.body.dataset.sidebarResizing;
  }

  const shellStyle = {
    "--sidebar-width": `${sidebarCollapsed ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth}px`
  } as CSSProperties;

  return (
    <BrowserRouter>
      <main className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`} style={shellStyle}>
        <aside className="app-sidebar" aria-label="Application navigation">
          <div className="sidebar-brand">
            <div className="sidebar-wordmark">
              <strong>AIMADA</strong>
              <span>Nebius AI Serverless</span>
            </div>
            <button
              aria-label={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
              className="sidebar-toggle"
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
              type="button"
            >
              <SidebarToggleIcon direction={sidebarCollapsed ? "right" : "left"} />
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
          <div />
          <div
            aria-hidden={sidebarCollapsed}
            className="sidebar-resize-handle"
            onDoubleClick={() => setSidebarWidth(SIDEBAR_DEFAULT_WIDTH)}
            onPointerCancel={stopSidebarResize}
            onPointerDown={startSidebarResize}
            onPointerMove={resizeSidebar}
            onPointerUp={stopSidebarResize}
            role="separator"
          />
        </aside>

        <section className="app-workspace">
          <header className="global-workspace-header" aria-label="Global account controls">
            <ConsoleTopbar />
            <ThemePanel
              collapsed={false}
              onPreferenceChange={setThemePreference}
              preference={themePreference}
              resolvedTheme={resolvedTheme}
            />
            {featureFlags.enableGoogleAuth ? <IdentityPanel /> : null}
            <RuntimePanel />
          </header>
          <section className="disclaimer" aria-label="Project disclaimer">
            <strong>Disclaimer: </strong>
            {disclaimer}
          </section>

          <Routes>
            <Route path="/" element={<Navigate to="/nebius" replace />} />
            <Route path="/demo" element={<Navigate to="/nebius" replace />} />
            <Route path="/arena" element={<ArenaPage />} />
            <Route path="/attack" element={<Navigate to="/attack-scenarios" replace />} />
            <Route path="/attack-scenarios" element={<AttackScenarioGeneratorPage />} />
            <Route path="/scenario-generator" element={<Navigate to="/attack-scenarios" replace />} />
            <Route path="/benchmark" element={<Navigate to="/nebius" replace />} />
            <Route path="/investigations" element={<Navigate to="/nebius" replace />} />
            <Route path="/detection" element={<Navigate to="/arena" replace />} />
            <Route path="/blue-team" element={<Navigate to="/arena" replace />} />
            <Route path="/lab" element={<Navigate to="/nebius" replace />} />
            <Route path="/experiments" element={<Navigate to="/nebius" replace />} />
            <Route path="/deploy" element={<Navigate to="/nebius" replace />} />
            <Route path="/deployment" element={<Navigate to="/nebius" replace />} />
            <Route path="/ai-platform" element={<Navigate to="/nebius" replace />} />
            <Route path="/nebius" element={<NebiusControlPanelPage />} />
            <Route path="/reports" element={<Navigate to="/arena" replace />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
          <ArenaSplashOverlay />
        </section>
      </main>
    </BrowserRouter>
  );
}

function ConsoleTopbar() {
  return (
    <section className="console-topbar" aria-label="AI command console">
      <div className="console-project-selector">
        <span>Project</span>
        <strong>AIMADA Market Surveillance</strong>
      </div>
      <label className="console-search">
        <span className="sr-only">Search</span>
        <input placeholder="Search incidents, jobs, scenarios" type="search" />
      </label>
      <span className="runtime-status active console-ai-button">Investigator ready</span>
      <span className="runtime-status connected">AI active</span>
    </section>
  );
}

function getStoredThemePreference(): ThemePreference {
  const stored = window.localStorage.getItem(THEME_PREFERENCE_KEY);
  return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
}

function getStoredSidebarWidth() {
  const stored = Number(window.localStorage.getItem(SIDEBAR_WIDTH_KEY));
  return clampSidebarWidth(Number.isFinite(stored) ? stored : SIDEBAR_DEFAULT_WIDTH);
}

function clampSidebarWidth(value: number) {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, Math.round(value)));
}

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

const SPLASH_HIDE_KEY = "aimada.hideArenaSplash";
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
    const demoLaunch = new URLSearchParams(location.search).has("demo");
    setDontShowAgain(hidden);
    setVisible(Boolean(sessionId && location.pathname === "/arena" && !demoLaunch && !hidden && dismissedSessionId !== sessionId));
  }, [dismissedSessionId, location.pathname, location.search, session?.session_id]);

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
          <h2 id="arena-splash-title">AI Market Abuse Detection Arena</h2>
          <p>
            Synthetic market state, red-team scenarios, detector evidence, replay history, and reports in one shared arena.
          </p>
        </div>
        <img
          alt="One-slide overview of the AI Market Abuse Detection Arena workflow"
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

function SidebarToggleIcon({ direction }: { direction: "left" | "right" }) {
  const paths = direction === "left"
    ? ["M13 6l-5 6 5 6", "M18 6l-5 6 5 6"]
    : ["M11 6l5 6-5 6", "M6 6l5 6-5 6"];
  return (
    <svg aria-hidden="true" className="sidebar-toggle-icon" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24">
      {paths.map((path) => <path d={path} key={path} />)}
    </svg>
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

type AppIconName = "arena" | "attack" | "demo" | "detection" | "tournament" | "reports" | "cloud" | "about";

type SidebarItem = {
  icon: AppIconName;
  label: string;
  primary?: boolean;
  shortLabel: string;
  team?: "red" | "blue";
  to: string;
  visibleFor: ArenaRole[];
};

const allRoles: ArenaRole[] = ["observer", "attacker", "defender", "judge"];
const sidebarItems: SidebarItem[] = [
  { icon: "cloud", label: "AI Command Center", primary: true, shortLabel: "AI", to: "/nebius", visibleFor: allRoles },
  { icon: "arena", label: "Arena / Workload Generator", primary: true, shortLabel: "WG", to: "/arena", visibleFor: allRoles },
  { icon: "detection", label: "Incidents / Investigations", shortLabel: "IN", to: "/investigations", visibleFor: allRoles },
  { icon: "tournament", label: "Detector Benchmark", shortLabel: "DB", to: "/benchmark", visibleFor: allRoles },
  { icon: "about", label: "Docs / Demo", primary: true, shortLabel: "DD", to: "/about", visibleFor: allRoles },
  { icon: "attack", label: "Scenario Setup", shortLabel: "SS", team: "red", to: "/attack-scenarios", visibleFor: allRoles }
];

function AppIcon({ name }: { name: AppIconName }) {
  const paths: Record<AppIconName, string[]> = {
    about: ["M12 17v-5", "M12 8h.01", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"],
    arena: ["M4 17h16", "M6 14l3-4 3 2 4-6 2 3", "M5 5v14h14"],
    attack: ["M4 12h10", "M10 6l6 6-6 6", "M16 4h4v4", "M16 20h4v-4"],
    cloud: ["M7 18h10a4 4 0 0 0 .8-7.9A6 6 0 0 0 6.4 8.4 4.5 4.5 0 0 0 7 18Z"],
    demo: ["M4 5h16v12H4z", "M9 21h6", "M12 17v4", "M10 9l5 3-5 3z"],
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

const themeOptions: { label: string; mode: ThemePreference }[] = [
  { label: "System", mode: "system" },
  { label: "Light", mode: "light" },
  { label: "Dark", mode: "dark" }
];

function ThemePanel({
  collapsed,
  onPreferenceChange,
  preference,
  resolvedTheme
}: {
  collapsed: boolean;
  onPreferenceChange: (preference: ThemePreference) => void;
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
}) {
  function cycleTheme() {
    const index = themeOptions.findIndex((option) => option.mode === preference);
    onPreferenceChange(themeOptions[(index + 1) % themeOptions.length].mode);
  }

  if (collapsed) {
    return (
      <section className="theme-panel collapsed" aria-label="Theme mode">
        <button
          aria-label={`Theme: ${preference}`}
          className="theme-cycle-button"
          onClick={cycleTheme}
          title={`Theme: ${preference}`}
          type="button"
        >
          <ThemeIcon mode={preference === "system" ? "system" : resolvedTheme} />
        </button>
      </section>
    );
  }

  return (
    <section className="theme-panel" aria-label="Theme mode">
      <span>Theme</span>
      <div className="theme-segmented-control" role="group" aria-label="Theme mode">
        {themeOptions.map((option) => (
          <button
            aria-pressed={preference === option.mode}
            className={preference === option.mode ? "active" : ""}
            key={option.mode}
            onClick={() => onPreferenceChange(option.mode)}
            title={option.label}
            type="button"
          >
            <ThemeIcon mode={option.mode} />
          </button>
        ))}
      </div>
    </section>
  );
}

function ThemeIcon({ mode }: { mode: ThemePreference | ResolvedTheme }) {
  const paths: Record<string, string[]> = {
    dark: ["M21 12.8A8.5 8.5 0 1 1 11.2 3a6.8 6.8 0 0 0 9.8 9.8Z"],
    light: ["M12 4V2", "M12 22v-2", "M4 12H2", "M22 12h-2", "M5.6 5.6 4.2 4.2", "M19.8 19.8l-1.4-1.4", "M18.4 5.6l1.4-1.4", "M4.2 19.8l1.4-1.4", "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"],
    system: ["M5 5h14v10H5z", "M9 19h6", "M12 15v4"]
  };
  return (
    <svg aria-hidden="true" className="theme-icon" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24">
      {paths[mode].map((path) => <path d={path} key={path} />)}
    </svg>
  );
}

function AuthToggleIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg aria-hidden="true" className="auth-toggle-mark" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24">
      <path d={expanded ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6"} />
    </svg>
  );
}

function RuntimePanel() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>(() => getStoredRuntimeMode());
  const [runtimeMessage, setRuntimeMessage] = useState("Local Demo is ready. Mock AI fallback is active.");
  const [runtimeOverrides, setRuntimeOverrides] = useState<Partial<Record<RuntimeMode, Partial<Record<RuntimeComponent, RuntimeStatus>>>>>({});
  const runtime = visibleRuntimeOptions.find((option) => option.value === runtimeMode) ?? visibleRuntimeOptions[0];
  const currentMatrix = { ...runtime.matrix, ...runtimeOverrides[runtimeMode] };

  useEffect(() => storeRuntimeMode(runtimeMode), [runtimeMode]);

  function switchRuntime(mode: RuntimeMode) {
    setRuntimeMode(mode);
    if (mode === "local-demo") {
      setRuntimeOverrides({});
      setRuntimeMessage("Switched to Local Demo. Mock AI fallback is active.");
      return;
    }
    setRuntimeMessage(`${visibleRuntimeOptions.find((option) => option.value === mode)?.label ?? "Runtime"} selected. If Nebius is not configured, cloud status will show deployment required.`);
  }

  function testNebiusConnection() {
    setRuntimeOverrides((current) => ({
      ...current,
      [runtimeMode]: {
        ...current[runtimeMode],
        "AI Endpoint": "Endpoint unavailable"
      }
    }));
    setRuntimeMessage("Nebius unavailable or not configured. Falling back to mock AI.");
  }

  function deployNebiusCloud() {
    if (runtimeMode !== "nebius-cloud") {
      setRuntimeMessage("Switch to Nebius Cloud before deploying.");
      return;
    }
    setRuntimeOverrides((current) => ({
      ...current,
      "nebius-cloud": Object.fromEntries(runtimeComponents.map((component) => [component, "Deploying" as RuntimeStatus]))
    }));
    setRuntimeMessage("Nebius deployment requested. If credentials are missing, the demo continues with mock AI.");
  }

  return (
    <section className="runtime-control" aria-label="Runtime mode">
      <button
        aria-expanded={menuOpen}
        className="runtime-status-pill"
        onClick={() => setMenuOpen((value) => !value)}
        title="Runtime mode"
        type="button"
      >
        <span aria-hidden="true">{runtime.marker}</span>
        <strong>{runtime.label}</strong>
        <AuthToggleIcon expanded={menuOpen} />
      </button>
      {menuOpen ? (
        <div className="runtime-drawer" role="menu">
          <div className="runtime-mode-options" role="group" aria-label="Runtime modes">
            {visibleRuntimeOptions.map((option) => (
              <button
                aria-pressed={option.value === runtimeMode}
                className={option.value === runtimeMode ? "active" : ""}
                key={option.value}
                onClick={() => switchRuntime(option.value)}
                type="button"
              >
                Switch to {option.label}
              </button>
            ))}
          </div>
          <p>{runtime.description}</p>
          <table className="runtime-matrix">
            <thead>
              <tr>
                <th>Component</th>
                {visibleRuntimeOptions.map((option) => <th key={option.value}>{option.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {runtimeComponents.map((component) => (
                <tr key={component}>
                  <th>{component}</th>
                  {visibleRuntimeOptions.map((option) => {
                    const status = option.value === runtimeMode ? currentMatrix[component] : option.matrix[component];
                    return <td className={option.value === runtimeMode ? "current" : ""} key={option.value}><span className={`runtime-status ${status.toLowerCase().replace(/\s+/g, "-")}`}>{status}</span></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="runtime-actions">
            <button onClick={() => switchRuntime("local-demo")} type="button">Switch to Local Demo</button>
            <button onClick={() => switchRuntime("nebius-cloud")} type="button">Switch to Nebius Cloud</button>
            <button onClick={testNebiusConnection} type="button">Test Nebius Connection</button>
            <button disabled={runtimeMode !== "nebius-cloud"} onClick={deployNebiusCloud} type="button">Deploy to Nebius Cloud</button>
          </div>
          <p className="runtime-fallback-note">{runtimeMessage}</p>
        </div>
      ) : null}
    </section>
  );
}

function IdentityPanel() {
  const { busy, clearAuthError, error, lastMessage, loginWithGoogle, logout, platformUser, role, saveNow, session, workspace } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const accountName = platformUser.name;
  const initial = (platformUser.name || platformUser.email || "A").trim().charAt(0).toUpperCase() || "A";
  const connected = Boolean(session);

  return (
    <section className={`auth-panel identity-panel ${connected ? "connected" : "not-connected"} ${error ? "error" : ""}`} aria-label="User and workspace">
      <button
        aria-expanded={menuOpen}
        className="auth-compact-toggle identity-chip"
        onClick={() => setMenuOpen((value) => !value)}
        title="User and workspace"
        type="button"
      >
        <span className="auth-avatar" aria-hidden="true">{initial}</span>
        <span className="auth-compact-copy">
          <strong>👤 {accountName}</strong>
          <span>{connected ? "Google connected" : "Local Demo"}</span>
        </span>
        <AuthToggleIcon expanded={menuOpen} />
      </button>
      {menuOpen ? (
        <div className="auth-details" role="menu">
          <div className="auth-detail-block">
            <span>Current User</span>
            <strong>{accountName}</strong>
            <small>{platformUser.email}</small>
          </div>
          <div className="auth-detail-block">
            <span>Workspace</span>
            <strong>{workspace.name}</strong>
            <small>{productRoleLabel(role)}</small>
          </div>
          <div className="auth-actions">
            {connected ? (
              <>
                <button disabled={busy} onClick={() => void saveNow()} type="button">Save history</button>
                <button disabled={busy} onClick={() => void logout()} type="button">Disconnect</button>
              </>
            ) : (
              <button className="google-login-button" disabled={busy} onClick={() => void loginWithGoogle(role)} type="button">
                <span className="google-icon" aria-hidden="true">G</span>
                {busy ? "Connecting..." : "Connect Google Account"}
              </button>
            )}
          </div>
          {error ? (
            <div className="auth-actions">
              <span className="auth-status warning">{error}</span>
              <button onClick={clearAuthError} type="button">Continue in Demo Mode</button>
            </div>
          ) : <span className="auth-status">{lastMessage ?? "Demo mode requires no login."}</span>}
        </div>
      ) : null}
    </section>
  );
}

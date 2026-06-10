import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import "./App.css";
import { AboutPage } from "@/pages/AboutPage";
import { ArenaPage } from "@/pages/ArenaPage";
import { AttackScenarioGeneratorPage } from "@/pages/AttackScenarioGeneratorPage";
import { BlueTeamSurveillancePage } from "@/pages/BlueTeamSurveillancePage";
import { TeamMark } from "@/components/TeamMark";
import { ExperimentLabPage } from "@/pages/ExperimentLabPage";
import { NebiusControlPanelPage } from "@/pages/NebiusControlPanelPage";
import { ReportsPage } from "@/pages/ReportsPage";

const disclaimer =
  "This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic “abuse-like” patterns designed to demonstrate order-book anomaly detection and AI-generated explanations.";

export function App() {
  return (
    <BrowserRouter>
      <main className="app-shell">
        <header className="app-header">
          <div>
            <p className="eyebrow">Synthetic order-book anomaly arena</p>
            <h1>Nebius Market Abuse Arena</h1>
          </div>
          <nav className="top-nav" aria-label="Main screens">
            <NavLink to="/arena">Market Arena</NavLink>
            <NavLink className="team-nav-link red" to="/attack-scenarios">
              <TeamMark team="red" />
              <span>Attack Scenario Generator</span>
            </NavLink>
            <NavLink className="team-nav-link blue" to="/blue-team">
              <TeamMark team="blue" />
              <span>Blue Team Surveillance</span>
            </NavLink>
            <NavLink to="/nebius">Nebius Control Panel</NavLink>
            <NavLink to="/reports">Replay & Reports</NavLink>
            <NavLink to="/about">About</NavLink>
          </nav>
        </header>

        <section className="disclaimer" aria-label="Project disclaimer">
          <strong>Disclaimer: </strong>
          {disclaimer}
        </section>

        <Routes>
          <Route path="/" element={<Navigate to="/arena" replace />} />
          <Route path="/arena" element={<ArenaPage />} />
          <Route path="/attack-scenarios" element={<AttackScenarioGeneratorPage />} />
          <Route path="/blue-team" element={<BlueTeamSurveillancePage />} />
          <Route path="/lab" element={<ExperimentLabPage />} />
          <Route path="/nebius" element={<NebiusControlPanelPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

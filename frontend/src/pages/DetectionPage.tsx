import { useState } from "react";
import { BlueTeamSurveillancePage } from "@/pages/BlueTeamSurveillancePage";
import { ReportsPage } from "@/pages/ReportsPage";

type DetectionView = "live" | "outputs";

export function DetectionPage() {
  const [view, setView] = useState<DetectionView>("live");

  return (
    <section className="detection-page">
      <div className="panel detection-page-tabs">
        <div className="widget-tab-row" role="tablist" aria-label="Detection workspace views">
          <button className={view === "live" ? "active" : ""} onClick={() => setView("live")} type="button">Live Detection</button>
          <button className={view === "outputs" ? "active" : ""} onClick={() => setView("outputs")} type="button">Detection Outputs</button>
        </div>
      </div>
      {view === "live" ? <BlueTeamSurveillancePage /> : <ReportsPage />}
    </section>
  );
}

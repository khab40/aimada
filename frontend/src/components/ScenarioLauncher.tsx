import type { ArenaScenarioType } from "@/hooks/useArenaSource";

export type ScenarioLauncherConfig = {
  defaults: string[];
  description: string;
  difficulty: "Low" | "Medium" | "High";
  label: string;
  type: ArenaScenarioType;
};

const scenarioLauncherConfigs: ScenarioLauncherConfig[] = [
  {
    defaults: ["wall 48 BTC", "lifetime 5s", "distance 3 ticks"],
    description: "Adds a large short-lived ask wall, then removes it before execution.",
    difficulty: "Medium",
    label: "Spoofing-like Wall",
    type: "spoofing_like_wall"
  },
  {
    defaults: ["3 ask levels", "lifetime 6s", "stacked above touch"],
    description: "Creates several large same-side ask levels that cancel together.",
    difficulty: "High",
    label: "Layering-like Pattern",
    type: "layering_like"
  },
  {
    defaults: ["message rate 260/s", "lifetime 4s", "low execution"],
    description: "Spikes place/cancel message flow and quote-stuffing detector confidence.",
    difficulty: "High",
    label: "Quote Stuffing Burst",
    type: "quote_stuffing"
  },
  {
    defaults: ["top depth -75%", "lifetime 5s", "spread widens"],
    description: "Removes top-of-book depth and widens the synthetic spread.",
    difficulty: "Medium",
    label: "Liquidity Evaporation",
    type: "liquidity_evaporation"
  }
];

export function ScenarioLauncher({
  activeScenario,
  onLaunch
}: {
  activeScenario?: ArenaScenarioType | string | null;
  onLaunch: (type: ArenaScenarioType) => void;
}) {
  return (
    <section className="scenario-launcher-panel">
      <div className="section-heading-row">
        <h2>Scenario Launcher</h2>
        <span>Defaults enabled</span>
      </div>
      <div className="scenario-card-grid">
        {scenarioLauncherConfigs.map((scenario) => {
          const isActive = activeScenario === scenario.type;
          return (
            <article className={`scenario-card ${isActive ? "active" : ""}`} key={scenario.type}>
              <div className="scenario-card-header">
                <h3>{scenario.label}</h3>
                <span className={`difficulty-tag ${scenario.difficulty.toLowerCase()}`}>
                  {scenario.difficulty}
                </span>
              </div>
              <p>{scenario.description}</p>
              <div className="scenario-defaults" aria-label={`${scenario.label} default controls`}>
                {scenario.defaults.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
              <button type="button" onClick={() => onLaunch(scenario.type)}>
                {isActive ? "Relaunch" : "Launch"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

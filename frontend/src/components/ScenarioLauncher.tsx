import { launchScenario } from "../api/client";

const scenarios = ["spoofing-like", "layering-like", "quote-stuffing-like", "liquidity-evaporation"];

export function ScenarioLauncher() {
  return (
    <section>
      <h2>Scenarios</h2>
      {scenarios.map((scenario) => (
        <button key={scenario} type="button" onClick={() => void launchScenario(scenario)}>
          {scenario}
        </button>
      ))}
    </section>
  );
}

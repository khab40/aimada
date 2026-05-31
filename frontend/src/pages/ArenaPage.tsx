import { AgentFeed } from "../components/AgentFeed";
import { DetectorConfidence } from "../components/DetectorConfidence";
import { ImbalanceGauge } from "../components/ImbalanceGauge";
import { IncidentDrawer } from "../components/IncidentDrawer";
import { OrderBookLadder } from "../components/OrderBookLadder";
import { PriceChart } from "../components/PriceChart";
import { ScenarioLauncher } from "../components/ScenarioLauncher";
import { SpreadChart } from "../components/SpreadChart";

export function ArenaPage() {
  return (
    <section>
      <h2>Arena</h2>
      <ScenarioLauncher />
      <OrderBookLadder />
      <PriceChart />
      <SpreadChart />
      <ImbalanceGauge />
      <DetectorConfidence />
      <AgentFeed />
      <IncidentDrawer />
    </section>
  );
}

from app.agents.layering_like import LayeringLikeAgent
from app.agents.liquidity_evaporation import LiquidityEvaporationAgent
from app.agents.noise_trader import NoiseTrader
from app.agents.quote_stuffing import QuoteStuffingAgent
from app.agents.spoofing_like import SpoofingLikeAgent
from app.arena.engine import ArenaEngine


class ScenarioController:
    def __init__(self) -> None:
        self.running = False
        self.engine = ArenaEngine()

    def start(self) -> dict[str, object]:
        self.running = True
        self.engine = ArenaEngine(agents=[NoiseTrader("noise-1")])
        return {"running": self.running, "snapshot": self.engine.step()}

    def stop(self) -> dict[str, object]:
        self.running = False
        return {"running": self.running}

    def launch(self, scenario_name: str) -> dict[str, object]:
        agents = {
            "spoofing_like_wall": [NoiseTrader("noise-1"), SpoofingLikeAgent("spoof-1")],
            "layering_like": [NoiseTrader("noise-1"), LayeringLikeAgent("layer-1")],
            "quote_stuffing": [QuoteStuffingAgent("stuff-1")],
            "liquidity_evaporation": [LiquidityEvaporationAgent("evap-1")],
        }.get(scenario_name)
        if agents is None:
            return {"accepted": False, "error": f"unknown scenario: {scenario_name}"}
        self.running = True
        self.engine = ArenaEngine(agents=agents)
        return {"accepted": True, "scenario": scenario_name, "snapshot": self.engine.step()}

    def snapshot(self) -> dict[str, object]:
        if not self.running:
            return {"running": False, "book": self.engine.matching_engine.snapshot()}
        return {"running": True, "snapshot": self.engine.step()}

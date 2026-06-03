from dataclasses import dataclass


@dataclass
class SimulationClock:
    tick: int = 0
    tick_interval_ms: int = 500

    def step(self) -> int:
        self.tick += 1
        return self.tick

    def reset(self) -> None:
        self.tick = 0

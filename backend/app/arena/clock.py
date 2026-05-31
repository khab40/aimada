from dataclasses import dataclass


@dataclass
class SimulationClock:
    tick: int = 0

    def step(self) -> int:
        self.tick += 1
        return self.tick

package ai.lobarena.kernel.simulation;

final class SimulationClock {
    private long tick;

    long step() {
        tick = Math.incrementExact(tick);
        return tick;
    }

    long tick() {
        return tick;
    }
}

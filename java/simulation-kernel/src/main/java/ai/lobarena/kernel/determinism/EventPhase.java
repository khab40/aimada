package ai.lobarena.kernel.determinism;

public enum EventPhase {
    HISTORICAL(5),
    AGENT(10),
    SCENARIO(20),
    BASELINE(30),
    SNAPSHOT(40),
    METRICS(50);

    private final int code;

    EventPhase(int code) {
        this.code = code;
    }

    public int code() {
        return code;
    }
}

package ai.lobarena.kernel.book;

import ai.lobarena.exchange.v1.EventSource;

public record MutationContext(
        Long tick,
        String scenarioId,
        String scenarioName,
        String scenarioFamily,
        EventSource source,
        Long sourceSequence,
        Long exchangeTimestampNs,
        Long receivedTimestampNs) {
    public static final MutationContext EMPTY =
            new MutationContext(null, null, null, null, null, null, null, null);

    public MutationContext(Long tick, String scenarioId, String scenarioName, String scenarioFamily) {
        this(tick, scenarioId, scenarioName, scenarioFamily, null, null, null, null);
    }

    public MutationContext {
        if (tick != null && tick < 0) {
            throw new IllegalArgumentException("tick must be non-negative");
        }
        if (source != null
                && source != EventSource.EVENT_SOURCE_SIMULATION
                && source != EventSource.EVENT_SOURCE_HISTORICAL) {
            throw new IllegalArgumentException("source must be simulation, historical, or unspecified");
        }
        if (sourceSequence != null && sourceSequence < 0) {
            throw new IllegalArgumentException("sourceSequence must be non-negative");
        }
        if (exchangeTimestampNs != null && exchangeTimestampNs < 0) {
            throw new IllegalArgumentException("exchangeTimestampNs must be non-negative");
        }
        if (receivedTimestampNs != null && receivedTimestampNs < 0) {
            throw new IllegalArgumentException("receivedTimestampNs must be non-negative");
        }
    }
}

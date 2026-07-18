package ai.lobarena.kernel.simulation;

import ai.lobarena.exchange.v1.Side;
import java.util.Comparator;

record AgentIntent(
        long tick,
        String agentId,
        Kind kind,
        int sequence,
        int latencyBucket,
        String eventType,
        Side side,
        Long priceTicks,
        long quantityLots,
        String message) implements Comparable<AgentIntent> {
    private static final Comparator<AgentIntent> ORDER = Comparator
            .comparingLong(AgentIntent::tick)
            .thenComparingInt(AgentIntent::latencyBucket)
            .thenComparing(AgentIntent::agentId)
            .thenComparingInt(AgentIntent::sequence)
            .thenComparing(intent -> intent.kind().wireName);

    enum Kind {
        SET_LEVEL("set_level"),
        MARKET("market");

        private final String wireName;

        Kind(String wireName) {
            this.wireName = wireName;
        }
    }

    @Override
    public int compareTo(AgentIntent other) {
        return ORDER.compare(this, other);
    }
}

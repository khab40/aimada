package ai.lobarena.kernel.determinism;

import java.util.Comparator;

public record EventOrderKey(
        long logicalTime,
        int phase,
        int sourcePriority,
        String actorId,
        long sourceSequence,
        long insertionSequence) implements Comparable<EventOrderKey> {
    private static final Comparator<EventOrderKey> ORDER = Comparator
            .comparingLong(EventOrderKey::logicalTime)
            .thenComparingInt(EventOrderKey::phase)
            .thenComparingInt(EventOrderKey::sourcePriority)
            .thenComparing(EventOrderKey::actorId)
            .thenComparingLong(EventOrderKey::sourceSequence)
            .thenComparingLong(EventOrderKey::insertionSequence);

    public EventOrderKey {
        if (logicalTime < 0) {
            throw new IllegalArgumentException("logicalTime must be non-negative");
        }
        if (phase < 0) {
            throw new IllegalArgumentException("phase must be non-negative");
        }
        if (sourcePriority < 0) {
            throw new IllegalArgumentException("sourcePriority must be non-negative");
        }
        if (sourceSequence < 0) {
            throw new IllegalArgumentException("sourceSequence must be non-negative");
        }
        if (insertionSequence < 0) {
            throw new IllegalArgumentException("insertionSequence must be non-negative");
        }
        DeterministicValues.requireAscii("actorId", actorId, false);
    }

    @Override
    public int compareTo(EventOrderKey other) {
        return ORDER.compare(this, other);
    }
}

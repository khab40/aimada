package ai.lobarena.kernel.book;

public record MutationContext(
        Long tick,
        String scenarioId,
        String scenarioName,
        String scenarioFamily) {
    public static final MutationContext EMPTY = new MutationContext(null, null, null, null);
}

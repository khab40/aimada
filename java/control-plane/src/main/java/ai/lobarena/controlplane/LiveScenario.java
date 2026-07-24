package ai.lobarena.controlplane;

record LiveScenario(String id, String family, String name, String agentId, long startTick, long seed) {
    long age(long tick) {
        return Math.max(0, tick - startTick);
    }

    String stage(long tick) {
        long age = age(tick);
        if (age == 0) {
            return "armed";
        }
        return switch (family) {
            case "spoofing_like_wall" -> age < 3 ? "wall_placed" : age < 5 ? "wall_cancelled" : "done";
            case "layering_like", "quote_stuffing" -> age < 4 ? "pressure_phase" : age < 6 ? "cancelled" : "done";
            case "liquidity_evaporation" -> age < 4 ? "pressure_phase" : "done";
            default -> "done";
        };
    }
}

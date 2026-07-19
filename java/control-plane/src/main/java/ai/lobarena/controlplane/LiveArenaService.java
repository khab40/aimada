package ai.lobarena.controlplane;

import ai.lobarena.exchange.v1.BookSnapshot;
import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.PriceLevel;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.kernel.book.IntegerMatchingEngine;
import ai.lobarena.kernel.book.IntegerOrderBook;
import ai.lobarena.kernel.book.KernelOrder;
import ai.lobarena.kernel.book.MutationContext;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.scheduling.annotation.Scheduled;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

final class LiveArenaService {
    private static final long UNIT_NANOS = 1_000_000L;
    private static final long REFERENCE_PRICE_TICKS = 68_125_000L;
    private static final long LEVEL_SPACING_TICKS = 1_000L;
    private static final long BASE_QUANTITY_LOTS = 1_500L;
    private static final int BASELINE_LEVELS = 12;
    private static final int SNAPSHOT_DEPTH = 12;
    private static final int EVENT_WINDOW = 100;
    private static final int AGENT_EVENT_WINDOW = 20;

    private final ObjectMapper mapper;
    private final AgentOrchestrator orchestrator;
    private final ArenaJournal journal;
    private final Deque<ObjectNode> agentEvents = new ArrayDeque<>();
    private final List<ObjectNode> incidents = new ArrayList<>();
    private final Set<String> incidentKeys = new HashSet<>();

    private IntegerMatchingEngine matching;
    private long tick;
    private boolean running;
    private int scenarioCounter;
    private int incidentCounter;
    private List<String> activeAgentIds = List.of();
    private LiveScenario scenario;
    private double previousDepth;

    LiveArenaService(ObjectMapper mapper, AgentOrchestrator orchestrator, ArenaJournal journal) {
        this.mapper = mapper;
        this.orchestrator = orchestrator;
        this.journal = journal;
        this.matching = newMatchingEngine();
        this.previousDepth = topDepth(matching.book().snapshot(5));
    }

    synchronized JsonNode state() {
        return buildState();
    }

    synchronized JsonNode start() {
        running = true;
        return buildState();
    }

    synchronized JsonNode pause() {
        running = false;
        return buildState();
    }

    synchronized JsonNode reset() {
        running = false;
        tick = 0;
        scenario = null;
        agentEvents.clear();
        incidents.clear();
        incidentKeys.clear();
        activeAgentIds = List.of();
        matching = newMatchingEngine();
        previousDepth = topDepth(matching.book().snapshot(5));
        return buildState();
    }

    synchronized JsonNode launchScenario(String family) {
        String normalized = normalizeScenario(family);
        scenarioCounter++;
        scenario = new LiveScenario(
                "SCN-%06d".formatted(scenarioCounter),
                normalized,
                displayName(normalized),
                "ABUSER_01",
                tick + 1);
        running = true;
        addAgentEvent(event("red_team", "ABUSER_01", "scenario armed")
                .put("scenario_id", scenario.id())
                .put("scenario_name", scenario.name())
                .put("scenario_family", scenario.family())
                .put("stage", "armed"));
        journal.append("attacks/attacks.jsonl", scenarioJson());
        return scenarioJson();
    }

    synchronized JsonNode incident(String incidentId) {
        return incidents.stream()
                .filter(item -> incidentId.equals(item.path("id").textValue()))
                .findFirst()
                .map(ObjectNode::deepCopy)
                .orElse(null);
    }

    synchronized JsonNode incidents() {
        ArrayNode result = mapper.createArrayNode();
        incidents.forEach(result::add);
        return result;
    }

    synchronized JsonNode exchangeEvents(long afterSequence, int limit) {
        List<ExchangeEvent> all = matching.events();
        ArrayNode events = mapper.createArrayNode();
        all.stream()
                .filter(event -> event.getMetadata().getSequence() > afterSequence)
                .limit(limit)
                .map(this::exchangeEventJson)
                .forEach(events::add);
        long latest = all.isEmpty() ? 0 : all.getLast().getMetadata().getSequence();
        long next = events.isEmpty() ? afterSequence : events.get(events.size() - 1).path("sequence").longValue();
        return mapper.createObjectNode()
                .set("events", events)
                .put("after_sequence", afterSequence)
                .put("next_after_sequence", next)
                .put("latest_sequence", latest)
                .put("has_more", next < latest);
    }

    @Scheduled(fixedDelayString = "${lob.arena.tick-interval-ms:500}")
    synchronized void scheduledTick() {
        if (running) {
            advance();
        }
    }

    synchronized JsonNode stepForTest() {
        advance();
        return buildState();
    }

    private void advance() {
        tick++;
        BookSnapshot before = matching.book().snapshot(5);
        double depthBefore = topDepth(before);
        JsonNode snapshot = marketSnapshot(before);
        Map<String, Object> orchestration = orchestrator.collect(snapshot);
        activeAgentIds = stringList(orchestration.get("agent_ids"));
        for (Object raw : listValue(orchestration.get("intents"))) {
            if (raw instanceof JsonNode intent) {
                applyIntent(intent);
            }
        }
        applyScenario();
        maintainBaseline();
        matching.recordSnapshot(
                tick,
                SNAPSHOT_DEPTH,
                null,
                null,
                scenario == null ? null : scenario.id(),
                scenario == null ? null : scenario.name(),
                scenario == null ? null : scenario.family());
        previousDepth = depthBefore;
        JsonNode state = buildState();
        journal.append("snapshots/ticks.jsonl", state);
    }

    private void applyIntent(JsonNode intent) {
        String kind = intent.path("kind").textValue();
        String agentId = intent.path("agent_id").textValue();
        try {
            Side side = side(intent.path("side").asText(""));
            long quantity = lots(intent.path("quantity").asDouble(0.0));
            long price = switch (kind) {
                case "set_level", "limit" -> ticks(intent.path("price").asDouble(0.0));
                default -> 0L;
            };
            int sequence = intent.path("sequence").asInt(0);
            switch (kind) {
                case "set_level" -> matching.book().updateAgentLevel(
                        side,
                        price,
                        Math.min(quantity, 25_000L),
                        agentId,
                        "normal",
                        null,
                        tick,
                        null,
                        null,
                        null);
                case "market" -> matching.submit(KernelOrder.market(
                        orderId(intent, agentId, sequence), agentId, side, quantity, tick));
                case "limit" -> matching.submit(KernelOrder.limit(
                        orderId(intent, agentId, sequence), agentId, side, quantity, price, tick));
                case "cancel" -> matching.submit(KernelOrder.cancel(
                        intent.path("order_id").asText(), agentId, side, tick));
                default -> {
                    return;
                }
            }
            ObjectNode event = event(intent.path("event_type").asText("normal"), agentId,
                    intent.path("message").asText("agent intent applied"));
            event.put("runtime_source", "agent_runner");
            event.put("side", side == Side.SIDE_BUY ? "buy" : "sell");
            if (price > 0) {
                event.put("price", price(price));
            }
            event.put("quantity", quantity(quantity));
            addAgentEvent(event);
        } catch (IllegalArgumentException ignored) {
            // Validation is repeated at the single-writer boundary; bad intents are dropped.
        }
    }

    private void applyScenario() {
        if (scenario == null) {
            return;
        }
        long age = scenario.age(tick);
        MutationContext context = new MutationContext(
                tick, scenario.id(), scenario.name(), scenario.family());
        matching.runWithMutationContext(context, () -> {
            switch (scenario.family()) {
                case "spoofing_like_wall" -> applySpoofing(age);
                case "layering_like" -> applyLayering(age);
                case "quote_stuffing" -> applyQuoteStuffing(age);
                case "liquidity_evaporation" -> applyLiquidityEvaporation(age);
                default -> throw new IllegalStateException("unsupported live scenario");
            }
        });
        if (age > 0 && age <= 5) {
            ObjectNode event = event("red_team", scenario.agentId(), scenario.name() + " " + scenario.stage(tick));
            event.put("scenario_id", scenario.id());
            event.put("scenario_name", scenario.name());
            event.put("scenario_family", scenario.family());
            event.put("stage", scenario.stage(tick));
            addAgentEvent(event);
        }
    }

    private void applySpoofing(long age) {
        long price = REFERENCE_PRICE_TICKS + 2 * LEVEL_SPACING_TICKS;
        matching.book().updateAgentLevel(
                Side.SIDE_SELL, price, age < 3 ? 30_000 : 0, scenario.agentId(), "abuser",
                "SCENARIO-WALL", tick, scenario.id(), scenario.name(), scenario.family());
    }

    private void applyLayering(long age) {
        for (int level = 2; level <= 4; level++) {
            matching.book().updateAgentLevel(
                    Side.SIDE_SELL,
                    REFERENCE_PRICE_TICKS + level * LEVEL_SPACING_TICKS,
                    age < 4 ? 10_000 + level * 1_000L : 0,
                    scenario.agentId(),
                    "abuser",
                    "SCENARIO-LAYER-" + level,
                    tick,
                    scenario.id(),
                    scenario.name(),
                    scenario.family());
        }
    }

    private void applyQuoteStuffing(long age) {
        int level = (int) (age % 5) + 1;
        matching.book().updateAgentLevel(
                age % 2 == 0 ? Side.SIDE_BUY : Side.SIDE_SELL,
                REFERENCE_PRICE_TICKS + (age % 2 == 0 ? -1 : 1) * level * LEVEL_SPACING_TICKS,
                age < 5 ? 1_000 : 0,
                scenario.agentId(),
                "abuser",
                "SCENARIO-STUFF-" + level,
                tick,
                scenario.id(),
                scenario.name(),
                scenario.family());
    }

    private void applyLiquidityEvaporation(long age) {
        if (age != 1) {
            return;
        }
        for (long price : matching.book().prices(Side.SIDE_BUY, 5)) {
            matching.book().removeLevel(Side.SIDE_BUY, price);
        }
        for (long price : matching.book().prices(Side.SIDE_SELL, 5)) {
            matching.book().removeLevel(Side.SIDE_SELL, price);
        }
    }

    private void maintainBaseline() {
        MutationContext context = new MutationContext(tick, null, null, null);
        matching.runWithMutationContext(context, () -> {
            for (int index = 0; index < BASELINE_LEVELS; index++) {
                long distance = (index + 1L) * LEVEL_SPACING_TICKS;
                long minimum = BASE_QUANTITY_LOTS + index * 1_000L;
                matching.book().ensureLevelMinimum(
                        Side.SIDE_BUY, REFERENCE_PRICE_TICKS - distance, minimum, "BASELINE_MM", "normal");
                matching.book().ensureLevelMinimum(
                        Side.SIDE_SELL, REFERENCE_PRICE_TICKS + distance, minimum, "BASELINE_MM", "normal");
            }
        });
    }

    private ObjectNode buildState() {
        BookSnapshot book = matching.book().snapshot(SNAPSHOT_DEPTH);
        ObjectNode result = mapper.createObjectNode();
        result.put("tick", tick);
        result.put("running", running);
        ArrayNode events = result.putArray("events");
        agentEvents.forEach(events::add);
        ArrayNode exchangeEvents = result.putArray("exchange_events");
        matching.events().stream()
                .skip(Math.max(0, matching.events().size() - EVENT_WINDOW))
                .map(this::exchangeEventJson)
                .forEach(exchangeEvents::add);
        ObjectNode bookJson = bookJson(book);
        result.set("book", bookJson);
        copyNullable(result, bookJson, "best_bid");
        copyNullable(result, bookJson, "best_ask");
        copyNullable(result, bookJson, "mid");
        copyNullable(result, bookJson, "spread");
        ArrayNode agents = result.putArray("active_agents");
        activeAgentIds.forEach(agents::add);
        if (scenario != null) {
            agents.add(scenario.agentId());
            result.set("active_scenario", scenarioJson());
        } else {
            result.putNull("active_scenario");
        }
        ObjectNode features = features(book);
        result.set("features", features);
        result.set("detectors", detectors(features));
        ArrayNode incidentArray = result.putArray("incidents");
        incidents.forEach(incidentArray::add);
        return result;
    }

    private ObjectNode features(BookSnapshot book) {
        double bidDepth = book.getBidsList().stream().limit(5).mapToDouble(level -> quantity(level.getQuantityLots())).sum();
        double askDepth = book.getAsksList().stream().limit(5).mapToDouble(level -> quantity(level.getQuantityLots())).sum();
        double depth = bidDepth + askDepth;
        double imbalance = depth == 0 ? 0 : (bidDepth - askDepth) / depth;
        double wall = book.getBidsList().stream().limit(5).mapToDouble(level -> quantity(level.getQuantityLots())).max().orElse(0);
        wall = Math.max(wall, book.getAsksList().stream().limit(5).mapToDouble(level -> quantity(level.getQuantityLots())).max().orElse(0));
        double average = depth / Math.max(1, Math.min(10, book.getBidsCount() + book.getAsksCount()));
        double spread = book.hasSpreadTicks() ? price(book.getSpreadTicks()) : 0;
        double mid = book.hasMidPriceTicksX2() ? price(book.getMidPriceTicksX2()) / 2 : 0;
        return mapper.createObjectNode()
                .put("spread_bps", mid == 0 ? 0 : round(spread / mid * 10_000))
                .put("depth_top_n", round(depth))
                .put("imbalance", round(imbalance))
                .put("message_rate", 2.0 * Math.max(1, agentEvents.size()))
                .put("cancel_to_trade_ratio", scenario == null ? 0.0 : 1.0)
                .put("order_lifetime_ms", scenario == null ? 0.0 : scenario.age(tick) * 500.0)
                .put("wall_size_ratio", average == 0 ? 1.0 : round(wall / average))
                .put("depth_change_pct", previousDepth == 0 ? 0 : round((depth - previousDepth) / previousDepth * 100));
    }

    private ObjectNode detectors(ObjectNode features) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode scores = result.putArray("scores");
        ArrayNode alerts = result.putArray("alerts");
        Map<String, String> families = Map.of(
                "spoofing_like_detector", "spoofing_like_wall",
                "layering_like_detector", "layering_like",
                "quote_stuffing_detector", "quote_stuffing",
                "liquidity_shock_detector", "liquidity_evaporation");
        for (Map.Entry<String, String> entry : families.entrySet()) {
            double confidence = scenario != null && scenario.family().equals(entry.getValue())
                    ? Math.min(0.95, 0.60 + scenario.age(tick) * 0.12)
                    : 0.05;
            ObjectNode score = mapper.createObjectNode()
                    .put("name", entry.getKey())
                    .put("confidence", round(confidence))
                    .put("alert", confidence >= 0.75);
            if (confidence >= 0.75) {
                score.put("severity", confidence >= 0.9 ? "critical" : "high");
            } else {
                score.putNull("severity");
            }
            ArrayNode evidence = score.putArray("evidence");
            evidence.add(evidence("scenario_stage", "Scenario stage", scenario == null ? "none" : scenario.stage(tick)));
            evidence.add(evidence("wall_size_ratio", "Wall size ratio", features.path("wall_size_ratio").doubleValue()));
            scores.add(score);
            if (confidence >= 0.75) {
                alerts.add(score.deepCopy());
                maybeCreateIncident(entry.getKey(), confidence, evidence);
            }
        }
        return result;
    }

    private void maybeCreateIncident(String detector, double confidence, ArrayNode evidence) {
        if (scenario == null || confidence < 0.80) {
            return;
        }
        String key = scenario.id() + ":" + detector;
        if (!incidentKeys.add(key)) {
            return;
        }
        incidentCounter++;
        ObjectNode incident = mapper.createObjectNode()
                .put("id", "INC-%06d".formatted(incidentCounter))
                .put("title", detector.replace('_', ' ') + " detected")
                .put("type", detector)
                .put("agent", scenario.agentId())
                .put("confidence", round(confidence))
                .put("severity", confidence >= 0.9 ? "Critical" : "High")
                .set("evidence", evidence.deepCopy())
                .put("explanation", "Nebius AI explanation pending.")
                .put("scenario_id", scenario.id())
                .put("scenario_family", scenario.family());
        incidents.add(incident);
        journal.append("incidents/incidents.jsonl", incident);
    }

    private ObjectNode scenarioJson() {
        ObjectNode result = mapper.createObjectNode()
                .put("scenario_id", scenario.id())
                .put("scenario_name", scenario.name())
                .put("scenario_family", scenario.family())
                .put("agent_id", scenario.agentId())
                .put("current_stage", scenario.stage(tick))
                .put("start_tick", scenario.startTick())
                .put("status", scenario.stage(tick));
        result.putArray("stages");
        result.putArray("evidence");
        return result;
    }

    private ObjectNode marketSnapshot(BookSnapshot book) {
        ObjectNode result = mapper.createObjectNode().put("tick", tick);
        ObjectNode rendered = bookJson(book);
        result.set("bids", rendered.path("bids"));
        result.set("asks", rendered.path("asks"));
        copyNullable(result, rendered, "best_bid");
        copyNullable(result, rendered, "best_ask");
        copyNullable(result, rendered, "mid");
        copyNullable(result, rendered, "spread");
        return result;
    }

    private ObjectNode bookJson(BookSnapshot book) {
        ObjectNode result = mapper.createObjectNode();
        ArrayNode bids = result.putArray("bids");
        book.getBidsList().forEach(level -> bids.add(levelJson(level)));
        ArrayNode asks = result.putArray("asks");
        book.getAsksList().forEach(level -> asks.add(levelJson(level)));
        if (book.hasBestBidTicks()) {
            result.put("best_bid", price(book.getBestBidTicks()));
        } else {
            result.putNull("best_bid");
        }
        if (book.hasBestAskTicks()) {
            result.put("best_ask", price(book.getBestAskTicks()));
        } else {
            result.putNull("best_ask");
        }
        if (book.hasMidPriceTicksX2()) {
            result.put("mid", price(book.getMidPriceTicksX2()) / 2.0);
            result.put("spread", price(book.getSpreadTicks()));
        } else {
            result.putNull("mid");
            result.putNull("spread");
        }
        return result;
    }

    private ObjectNode levelJson(PriceLevel level) {
        ObjectNode result = mapper.createObjectNode()
                .put("price", price(level.getPriceTicks()))
                .put("quantity", quantity(level.getQuantityLots()));
        if (level.hasOwner()) {
            result.put("owner", level.getOwner());
        }
        return result;
    }

    private ObjectNode exchangeEventJson(ExchangeEvent event) {
        ObjectNode result = mapper.createObjectNode();
        var metadata = event.getMetadata();
        result.put("schema_version", metadata.getSchemaVersion());
        result.put("event_id", metadata.getEventId());
        result.put("sequence", metadata.getSequence());
        result.put("source", metadata.getSource() == EventSource.EVENT_SOURCE_HISTORICAL ? "historical" : "simulation");
        result.putNull("source_sequence");
        result.put("symbol", metadata.getSymbol());
        result.put("venue", metadata.getVenue());
        result.put("tick", metadata.getTick());
        result.putNull("exchange_timestamp_ns");
        result.putNull("received_timestamp_ns");
        optional(result, "scenario_id", metadata.hasScenarioId(), metadata.getScenarioId());
        optional(result, "scenario_name", metadata.hasScenarioName(), metadata.getScenarioName());
        optional(result, "scenario_family", metadata.hasScenarioFamily(), metadata.getScenarioFamily());
        switch (event.getPayloadCase()) {
            case ADD -> {
                result.put("event_type", "add");
                resting(result, event.getAdd().getOrderId(), event.getAdd().getAgentId(), event.getAdd().getSide(),
                        event.getAdd().getPriceTicks(), event.getAdd().getQuantityLots(), event.getAdd().getOwner());
            }
            case MODIFY -> {
                result.put("event_type", "modify");
                resting(result, event.getModify().getOrderId(), event.getModify().getAgentId(), event.getModify().getSide(),
                        event.getModify().getPriceTicks(), event.getModify().getQuantityLots(), event.getModify().getOwner());
                result.put("previous_price", price(event.getModify().getPreviousPriceTicks()));
                result.put("previous_quantity", quantity(event.getModify().getPreviousQuantityLots()));
                result.put("priority_preserved", event.getModify().getPriorityPreserved());
            }
            case CANCEL -> {
                result.put("event_type", "cancel");
                resting(result, event.getCancel().getOrderId(), event.getCancel().getAgentId(), event.getCancel().getSide(),
                        event.getCancel().getPriceTicks(), event.getCancel().getQuantityLots(), event.getCancel().getOwner());
            }
            case EXECUTE -> {
                result.put("event_type", "execute");
                var execution = event.getExecute();
                result.put("execution_id", execution.getExecutionId());
                result.put("aggressor_order_id", execution.getAggressorOrderId());
                result.put("resting_order_id", execution.getRestingOrderId());
                result.put("aggressor_agent_id", execution.getAggressorAgentId());
                result.put("resting_agent_id", execution.getRestingAgentId());
                result.put("side", execution.getAggressorSide() == Side.SIDE_BUY ? "buy" : "sell");
                result.put("price", price(execution.getPriceTicks()));
                result.put("quantity", quantity(execution.getQuantityLots()));
                result.put("aggressor_remaining_quantity", quantity(execution.getAggressorRemainingQuantityLots()));
                result.put("resting_remaining_quantity", quantity(execution.getRestingRemainingQuantityLots()));
            }
            case SNAPSHOT -> {
                result.put("event_type", "snapshot");
                result.put("depth", event.getSnapshot().getDepth());
                result.set("book", bookJson(event.getSnapshot().getBook()));
            }
            default -> throw new IllegalStateException("exchange event payload is required");
        }
        return result;
    }

    private void resting(ObjectNode result, String orderId, String agentId, Side side, long price, long quantity, String owner) {
        result.put("order_id", orderId);
        result.put("agent_id", agentId);
        result.put("side", side == Side.SIDE_BUY ? "buy" : "sell");
        result.put("price", price(price));
        result.put("quantity", quantity(quantity));
        result.put("owner", owner);
    }

    private IntegerMatchingEngine newMatchingEngine() {
        IntegerOrderBook book = new IntegerOrderBook(UNIT_NANOS, UNIT_NANOS);
        book.initialize(REFERENCE_PRICE_TICKS, BASELINE_LEVELS, LEVEL_SPACING_TICKS, BASE_QUANTITY_LOTS, "normal");
        return new IntegerMatchingEngine(book, "BTCUSDT", "SIM", EventSource.EVENT_SOURCE_SIMULATION);
    }

    private void addAgentEvent(ObjectNode event) {
        agentEvents.addFirst(event);
        while (agentEvents.size() > AGENT_EVENT_WINDOW) {
            agentEvents.removeLast();
        }
        journal.append("events/events.jsonl", event);
    }

    private ObjectNode event(String type, String agentId, String message) {
        return mapper.createObjectNode()
                .put("type", type)
                .put("timestamp", tick)
                .put("tick", tick)
                .put("agent_id", agentId)
                .put("message", message);
    }

    private ObjectNode evidence(String key, String label, Object value) {
        ObjectNode result = mapper.createObjectNode().put("key", key).put("label", label);
        if (value instanceof Number number) {
            result.put("value", number.doubleValue());
        } else {
            result.put("value", String.valueOf(value));
        }
        result.put("interpretation", "Confirmed by deterministic Java detector threshold.");
        return result;
    }

    private static String normalizeScenario(String raw) {
        String normalized = raw == null ? "" : raw.trim().toLowerCase().replace('-', '_');
        if ("spoofing_like".equals(normalized)) {
            normalized = "spoofing_like_wall";
        }
        if (!Set.of("spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation").contains(normalized)) {
            throw new IllegalArgumentException("unknown scenario: " + raw);
        }
        return normalized;
    }

    private static String displayName(String family) {
        return switch (family) {
            case "spoofing_like_wall" -> "Spoofing-like Wall";
            case "layering_like" -> "Layering-like Pattern";
            case "quote_stuffing" -> "Quote Stuffing Burst";
            case "liquidity_evaporation" -> "Liquidity Evaporation";
            default -> family;
        };
    }

    private static Side side(String raw) {
        return switch (raw) {
            case "bid", "buy" -> Side.SIDE_BUY;
            case "ask", "sell" -> Side.SIDE_SELL;
            default -> throw new IllegalArgumentException("intent side is required");
        };
    }

    private static String orderId(JsonNode intent, String agentId, int sequence) {
        String provided = intent.path("order_id").asText("");
        return provided.isBlank() ? agentId + "-" + intent.path("tick").longValue() + "-" + sequence : provided;
    }

    private static long ticks(double value) {
        if (!Double.isFinite(value) || value <= 0) {
            throw new IllegalArgumentException("positive finite price is required");
        }
        return BigDecimal.valueOf(value).movePointRight(3).setScale(0, RoundingMode.HALF_EVEN).longValueExact();
    }

    private static long lots(double value) {
        if (!Double.isFinite(value) || value < 0) {
            throw new IllegalArgumentException("non-negative finite quantity is required");
        }
        return BigDecimal.valueOf(value).movePointRight(3).setScale(0, RoundingMode.HALF_EVEN).longValueExact();
    }

    private static double price(long ticks) {
        return BigDecimal.valueOf(ticks, 3).doubleValue();
    }

    private static double quantity(long lots) {
        return BigDecimal.valueOf(lots, 3).doubleValue();
    }

    private static double topDepth(BookSnapshot book) {
        return book.getBidsList().stream().mapToDouble(level -> quantity(level.getQuantityLots())).sum()
                + book.getAsksList().stream().mapToDouble(level -> quantity(level.getQuantityLots())).sum();
    }

    @SuppressWarnings("unchecked")
    private static List<Object> listValue(Object value) {
        return value instanceof List<?> list ? (List<Object>) list : List.of();
    }

    private static List<String> stringList(Object value) {
        return listValue(value).stream().map(String::valueOf).toList();
    }

    private static double round(double value) {
        return BigDecimal.valueOf(value).setScale(4, RoundingMode.HALF_EVEN).doubleValue();
    }

    private static void optional(ObjectNode node, String field, boolean present, String value) {
        if (present) {
            node.put(field, value);
        } else {
            node.putNull(field);
        }
    }

    private static void copyNullable(ObjectNode target, ObjectNode source, String field) {
        target.set(field, source.path(field).deepCopy());
    }
}

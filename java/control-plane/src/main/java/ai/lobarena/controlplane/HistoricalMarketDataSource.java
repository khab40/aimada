package ai.lobarena.controlplane;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.regex.Pattern;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/** Replays the vendor-neutral normalized historical Parquet contract. */
final class HistoricalMarketDataSource implements ReplayMarketDataSource {
    private static final Pattern SAFE_DATASET_ID = Pattern.compile("[A-Za-z0-9._-]+");
    private static final int EVENT_WINDOW = 100;
    private final ObjectMapper mapper;
    private final Path registryRoot;
    private final int rowsPerTick;
    private final Deque<ObjectNode> eventTail = new ArrayDeque<>();
    private Connection connection;
    private Statement statement;
    private ResultSet rows;
    private JsonNode manifest;
    private ArrayNode asks;
    private ArrayNode bids;
    private String datasetId;
    private long sourceSequence;
    private long replayPosition;
    private long timestampNs;
    private long tick;
    private long totalRows;
    private boolean running;
    private boolean eof;

    HistoricalMarketDataSource(ObjectMapper mapper, Path registryRoot, int rowsPerTick) {
        this.mapper = mapper;
        this.registryRoot = registryRoot.toAbsolutePath().normalize();
        this.rowsPerTick = Math.max(1, rowsPerTick);
    }

    public synchronized JsonNode load(String requestedDatasetId) {
        if (!SAFE_DATASET_ID.matcher(requestedDatasetId).matches()) {
            throw new IllegalArgumentException("invalid dataset id");
        }
        clearState();
        Path dataset;
        try {
            dataset = registryRoot.resolve(requestedDatasetId).toRealPath();
            if (!dataset.startsWith(registryRoot.toRealPath())) {
                throw new IllegalArgumentException("historical dataset escapes the registry");
            }
        } catch (IOException exception) {
            throw new IllegalArgumentException("unknown historical dataset");
        }
        if (!Files.isDirectory(dataset)) throw new IllegalArgumentException("unknown historical dataset");
        Path manifestPath = dataset.resolve("manifest.json");
        Path eventsPath = dataset.resolve("events.parquet");
        Path booksPath = dataset.resolve("book_snapshots.parquet");
        if (!Files.isRegularFile(manifestPath) || !Files.isRegularFile(eventsPath) || !Files.isRegularFile(booksPath)) {
            throw new IllegalArgumentException("historical dataset is incomplete");
        }
        try {
            manifest = mapper.readTree(Files.readString(manifestPath));
            if (!"ready".equals(manifest.path("status").asText())
                    || !requestedDatasetId.equals(manifest.path("dataset_id").asText())) {
                throw new IllegalArgumentException("historical manifest is not ready");
            }
            datasetId = requestedDatasetId;
            totalRows = manifest.path("row_count").longValue();
            connection = DriverManager.getConnection("jdbc:duckdb:");
            statement = connection.createStatement();
            rows = statement.executeQuery("""
                    SELECT e.source_sequence, e.timestamp_ns_since_midnight, e.event_kind,
                           e.source_event_code, e.source_order_id, e.size, e.price_x10000,
                           e.direction, e.book_side, e.aggressor_side, e.halt_state,
                           to_json(b.asks) AS asks_json, to_json(b.bids) AS bids_json
                    FROM read_parquet('%s') e
                    INNER JOIN read_parquet('%s') b USING (source_sequence)
                    ORDER BY e.source_sequence
                    """.formatted(sqlPath(eventsPath), sqlPath(booksPath)));
            tick = 0;
            replayPosition = 0;
            running = false;
            eof = false;
            eventTail.clear();
            if (!readNext()) {
                throw new IllegalArgumentException("historical dataset is empty");
            }
            return state();
        } catch (IOException | SQLException exception) {
            clearState();
            throw new IllegalArgumentException("failed to load historical dataset: " + exception.getMessage(), exception);
        } catch (RuntimeException exception) {
            clearState();
            throw exception;
        }
    }

    public synchronized boolean loaded() {
        return datasetId != null;
    }

    public synchronized void clear() {
        clearState();
    }

    public synchronized JsonNode start() {
        requireLoaded();
        running = !eof;
        return state();
    }

    public synchronized JsonNode pause() {
        requireLoaded();
        running = false;
        return state();
    }

    public synchronized JsonNode reset() {
        requireLoaded();
        return load(datasetId);
    }

    public synchronized void advance() {
        requireLoaded();
        if (!running || eof) return;
        tick++;
        for (int index = 0; index < rowsPerTick; index++) {
            if (!readNext()) {
                eof = true;
                running = false;
                break;
            }
            if (eof) break;
        }
    }

    public synchronized JsonNode state() {
        requireLoaded();
        ObjectNode result = mapper.createObjectNode();
        result.put("tick", tick);
        result.put("running", running);
        ArrayNode events = result.putArray("events");
        eventTail.forEach(events::add);
        result.putArray("exchange_events");
        ArrayNode historical = result.putArray("historical_events");
        eventTail.forEach(historical::add);
        ObjectNode book = book();
        result.set("book", book);
        copyNullable(result, book, "best_bid");
        copyNullable(result, book, "best_ask");
        copyNullable(result, book, "mid");
        copyNullable(result, book, "spread");
        result.putArray("active_agents");
        result.putNull("active_scenario");
        result.set("features", features(book));
        ObjectNode detectors = result.putObject("detectors");
        detectors.putArray("scores");
        detectors.putArray("alerts");
        result.putArray("incidents");
        ObjectNode context = result.putObject("market_data");
        context.put("source_type", "historical");
        context.put("dataset_id", datasetId);
        context.put("symbol", manifest.path("symbol").asText());
        context.put("trade_date", manifest.path("trade_date").asText());
        context.put("depth", manifest.path("depth").intValue());
        context.put("source_sequence", sourceSequence);
        context.put("replay_position", replayPosition);
        context.put("exchange_timestamp_ns", timestampNs);
        context.put("row_count", totalRows);
        context.put("progress", totalRows == 0 ? 0 : Math.min(1.0, (double) replayPosition / totalRows));
        context.put("eof", eof);
        return result;
    }

    private boolean readNext() {
        try {
            if (!rows.next()) return false;
            sourceSequence = rows.getLong("source_sequence");
            replayPosition++;
            timestampNs = rows.getLong("timestamp_ns_since_midnight");
            ObjectNode event = mapper.createObjectNode()
                    .put("type", rows.getString("event_kind").toLowerCase())
                    .put("event_kind", rows.getString("event_kind"))
                    .put("source_event_code", rows.getInt("source_event_code"))
                    .put("source_sequence", sourceSequence)
                    .put("timestamp_ns_since_midnight", timestampNs)
                    .put("source_order_id", rows.getLong("source_order_id"))
                    .put("order_id", Long.toString(rows.getLong("source_order_id")))
                    .put("quantity", rows.getLong("size"))
                    .put("price_x10000", rows.getLong("price_x10000"))
                    .put("symbol", manifest.path("symbol").asText())
                    .put("source", "historical");
            putNullable(event, "side", rows.getString("book_side"), true);
            putNullable(event, "aggressor_side", rows.getString("aggressor_side"), true);
            putNullable(event, "halt_state", rows.getString("halt_state"), false);
            if (rows.getLong("price_x10000") > 1) event.put("price", rows.getLong("price_x10000") / 10_000.0);
            asks = (ArrayNode) mapper.readTree(rows.getString("asks_json"));
            bids = (ArrayNode) mapper.readTree(rows.getString("bids_json"));
            eventTail.addFirst(event);
            while (eventTail.size() > EVENT_WINDOW) eventTail.removeLast();
            if (replayPosition >= totalRows) {
                eof = true;
                running = false;
            }
            return true;
        } catch (SQLException exception) {
            throw new IllegalStateException("historical replay failed", exception);
        }
    }

    private ObjectNode book() {
        ObjectNode book = mapper.createObjectNode();
        ArrayNode askLevels = book.putArray("asks");
        ArrayNode bidLevels = book.putArray("bids");
        appendLevels(asks, askLevels);
        appendLevels(bids, bidLevels);
        Double bestAsk = priceAt(askLevels);
        Double bestBid = priceAt(bidLevels);
        if (bestAsk == null) book.putNull("best_ask"); else book.put("best_ask", bestAsk);
        if (bestBid == null) book.putNull("best_bid"); else book.put("best_bid", bestBid);
        if (bestAsk == null || bestBid == null) {
            book.putNull("mid");
            book.putNull("spread");
        } else {
            book.put("mid", (bestAsk + bestBid) / 2.0);
            book.put("spread", bestAsk - bestBid);
        }
        return book;
    }

    private void appendLevels(ArrayNode source, ArrayNode target) {
        if (source == null) return;
        source.forEach(level -> target.add(mapper.createObjectNode()
                .put("price", level.path("price_x10000").longValue() / 10_000.0)
                .put("quantity", level.path("quantity").longValue())));
    }

    private ObjectNode features(ObjectNode book) {
        double bidDepth = depth(book.path("bids"));
        double askDepth = depth(book.path("asks"));
        double total = bidDepth + askDepth;
        double mid = book.path("mid").asDouble(0);
        double spread = book.path("spread").asDouble(0);
        return mapper.createObjectNode()
                .put("spread_bps", mid == 0 ? 0 : spread / mid * 10_000)
                .put("depth_top_n", total)
                .put("imbalance", total == 0 ? 0 : (bidDepth - askDepth) / total)
                .put("message_rate", rowsPerTick)
                .put("cancel_to_trade_ratio", 0)
                .put("order_lifetime_ms", 0)
                .put("wall_size_ratio", 1)
                .put("depth_change_pct", 0);
    }

    private double depth(JsonNode levels) {
        double result = 0;
        for (JsonNode level : levels) result += level.path("quantity").doubleValue();
        return result;
    }

    private Double priceAt(ArrayNode levels) {
        return levels == null || levels.isEmpty() ? null : levels.get(0).path("price").doubleValue();
    }

    private void requireLoaded() {
        if (!loaded()) throw new IllegalStateException("no historical dataset is loaded");
    }

    private static void copyNullable(ObjectNode target, ObjectNode source, String field) {
        if (source.path(field).isNull()) target.putNull(field); else target.set(field, source.path(field));
    }

    private static void putNullable(ObjectNode target, String field, String value, boolean lowerCase) {
        if (value == null) target.putNull(field); else target.put(field, lowerCase ? value.toLowerCase() : value);
    }

    private static String sqlPath(Path path) {
        return path.toAbsolutePath().normalize().toString().replace("'", "''");
    }

    private void closeResources() {
        try { if (rows != null) rows.close(); } catch (SQLException ignored) {}
        try { if (statement != null) statement.close(); } catch (SQLException ignored) {}
        try { if (connection != null) connection.close(); } catch (SQLException ignored) {}
        rows = null;
        statement = null;
        connection = null;
    }

    private void clearState() {
        closeResources();
        datasetId = null;
        manifest = null;
        asks = null;
        bids = null;
        sourceSequence = 0;
        replayPosition = 0;
        timestampNs = 0;
        tick = 0;
        totalRows = 0;
        eventTail.clear();
        running = false;
        eof = false;
    }

    @Override
    public synchronized void close() {
        clear();
    }
}

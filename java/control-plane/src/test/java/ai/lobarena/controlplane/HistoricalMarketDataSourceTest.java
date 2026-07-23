package ai.lobarena.controlplane;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class HistoricalMarketDataSourceTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void replaysAlignedEventsAndSnapshotsWithoutMutatingTheSimulationKernel(@TempDir Path root) throws Exception {
        String datasetId = "lobster-aapl-2012-06-21-demo";
        Path dataset = root.resolve(datasetId);
        Files.createDirectories(dataset);
        Path events = dataset.resolve("events.parquet");
        Path books = dataset.resolve("book_snapshots.parquet");
        try (Connection connection = DriverManager.getConnection("jdbc:duckdb:");
                Statement statement = connection.createStatement()) {
            statement.execute("""
                    CREATE TABLE events AS
                    SELECT 91::BIGINT source_sequence, 34200000000001::BIGINT timestamp_ns_since_midnight,
                           'ADD'::VARCHAR event_kind, 1::TINYINT source_event_code, 1001::BIGINT source_order_id,
                           100::BIGINT size, 911400::BIGINT price_x10000, 1::TINYINT direction,
                           'BUY'::VARCHAR book_side, NULL::VARCHAR aggressor_side, NULL::VARCHAR halt_state
                    UNION ALL
                    SELECT 93, 34200000000002, 'PARTIAL_CANCEL', 2, 1001, 25, 911400, 1, 'BUY', NULL, NULL
                    """);
            statement.execute("COPY events TO '" + sqlPath(events) + "' (FORMAT PARQUET)");
            statement.execute("""
                    CREATE TABLE books AS
                    SELECT 91::BIGINT source_sequence, 34200000000001::BIGINT timestamp_ns_since_midnight,
                           1::SMALLINT depth,
                           [{'level': 1::SMALLINT, 'price_x10000': 911500::BIGINT, 'quantity': 200::BIGINT}] asks,
                           [{'level': 1::SMALLINT, 'price_x10000': 911400::BIGINT, 'quantity': 100::BIGINT}] bids
                    UNION ALL
                    SELECT 93, 34200000000002, 1,
                           [{'level': 1::SMALLINT, 'price_x10000': 911500::BIGINT, 'quantity': 200::BIGINT}],
                           [{'level': 1::SMALLINT, 'price_x10000': 911400::BIGINT, 'quantity': 75::BIGINT}]
                    """);
            statement.execute("COPY books TO '" + sqlPath(books) + "' (FORMAT PARQUET)");
        }
        Files.writeString(dataset.resolve("manifest.json"), """
                {
                  "dataset_id": "%s",
                  "status": "ready",
                  "symbol": "AAPL",
                  "trade_date": "2012-06-21",
                  "depth": 1,
                  "row_count": 2
                }
                """.formatted(datasetId));

        HistoricalMarketDataSource source = new HistoricalMarketDataSource(mapper, root, 1);
        JsonNode loaded = source.load(datasetId);
        assertThat(loaded.path("market_data").path("source_sequence").longValue()).isEqualTo(91);
        assertThat(loaded.path("market_data").path("replay_position").longValue()).isEqualTo(1);
        assertThat(loaded.path("market_data").path("progress").doubleValue()).isEqualTo(0.5);
        assertThat(loaded.path("book").path("best_bid").doubleValue()).isEqualTo(91.14);
        assertThat(loaded.path("historical_events").get(0).path("price_x10000").longValue()).isEqualTo(911400);

        source.start();
        source.advance();
        JsonNode advanced = source.state();
        assertThat(advanced.path("market_data").path("source_sequence").longValue()).isEqualTo(93);
        assertThat(advanced.path("market_data").path("replay_position").longValue()).isEqualTo(2);
        assertThat(advanced.path("market_data").path("progress").doubleValue()).isEqualTo(1.0);
        assertThat(advanced.path("market_data").path("eof").booleanValue()).isTrue();
        assertThat(advanced.path("running").booleanValue()).isFalse();
        assertThat(advanced.path("book").path("bids").get(0).path("quantity").longValue()).isEqualTo(75);

        JsonNode reset = source.reset();
        assertThat(reset.path("market_data").path("source_sequence").longValue()).isEqualTo(91);
        assertThat(reset.path("running").booleanValue()).isFalse();
        source.close();
    }

    @Test
    void clearsTheLoadedStateWhenAReplacementDatasetIsInvalid(@TempDir Path root) throws Exception {
        String datasetId = "invalid-manifest";
        Path dataset = root.resolve(datasetId);
        Files.createDirectories(dataset);
        Files.writeString(dataset.resolve("manifest.json"), """
                {"dataset_id": "different-id", "status": "ready"}
                """);
        Files.createFile(dataset.resolve("events.parquet"));
        Files.createFile(dataset.resolve("book_snapshots.parquet"));
        HistoricalMarketDataSource source = new HistoricalMarketDataSource(mapper, root, 1);

        org.assertj.core.api.Assertions.assertThatThrownBy(() -> source.load(datasetId))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("historical manifest is not ready");

        assertThat(source.loaded()).isFalse();
        source.close();
    }

    private static String sqlPath(Path path) {
        return path.toAbsolutePath().normalize().toString().replace("'", "''");
    }
}

package ai.lobarena.controlplane;

import tools.jackson.databind.JsonNode;

/**
 * Runtime replay boundary for normalized market data. Historical is implemented
 * now; a future hybrid implementation can compose replay with a simulated overlay.
 */
interface ReplayMarketDataSource extends AutoCloseable {
    boolean loaded();

    JsonNode load(String datasetId);

    JsonNode start();

    JsonNode pause();

    JsonNode reset();

    void advance();

    JsonNode state();

    void clear();
}

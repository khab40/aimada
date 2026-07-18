package ai.lobarena.exchange.v1;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.InputStream;
import org.junit.jupiter.api.Test;

final class ExchangeContractTest {
    @Test
    void generatedTypesParseTheSharedGoldenRequest() throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/normal-market-seed-42/request.pb")) {
            assertTrue(input != null, "golden request must be available as a test resource");
            SimulationRequest request = SimulationRequest.parseFrom(input);

            assertEquals(1, request.getContractVersion());
            assertEquals("normal_market", request.getScenario().getScenarioName());
            assertEquals("BTCUSDT", request.getConfig().getSymbol());
            assertEquals(25_000L, request.getConfig().getMaxAgentQuoteLots());
        }
    }
}

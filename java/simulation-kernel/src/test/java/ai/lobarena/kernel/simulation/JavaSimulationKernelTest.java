package ai.lobarena.kernel.simulation;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.ScenarioParameter;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.exchange.v1.TerminationReason;
import ai.lobarena.kernel.hashing.CanonicalHashes;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

final class JavaSimulationKernelTest {
    @Test
    void repeatedRequestProducesByteIdenticalResultWithValidHashes() throws IOException {
        SimulationRequest request = request("normal-market-seed-42");
        JavaSimulationKernel kernel = new JavaSimulationKernel();

        SimulationResult first = kernel.run(request);
        SimulationResult second = kernel.run(request);

        assertArrayEquals(first.toByteArray(), second.toByteArray());
        assertArrayEquals(
                first.getEventStreamHash().toByteArray(),
                CanonicalHashes.eventStreamHash(first.getEventsList(), 1));
        assertArrayEquals(first.getFinalBookHash().toByteArray(), CanonicalHashes.bookHash(first.getFinalBook()));
        assertEquals(TerminationReason.TERMINATION_REASON_COMPLETED, first.getTerminationReason());
        assertEquals(request.getScenario().getMaxTicks(),
                first.getEventsList().stream().filter(this::isSnapshot).count());
    }

    @Test
    void activeScenariosCollectivelyEmitEveryExchangePayload() throws IOException {
        Set<String> payloads = Set.of(
                        "spoofing-like-wall-seed-42",
                        "layering-like-seed-43",
                        "quote-stuffing-seed-44",
                        "liquidity-evaporation-seed-45")
                .stream()
                .flatMap(caseId -> {
                    try {
                        return new JavaSimulationKernel().run(request(caseId)).getEventsList().stream();
                    } catch (IOException exception) {
                        throw new IllegalStateException(exception);
                    }
                })
                .map(event -> event.getPayloadCase().name().toLowerCase())
                .collect(Collectors.toSet());

        assertEquals(Set.of("add", "modify", "cancel", "execute", "snapshot"), payloads);
    }

    @Test
    void emptyBookPreservesOptionalAbsenceAndSnapshotOnlyStream() throws IOException {
        SimulationRequest request = request("empty-book-seed-7");

        SimulationResult result = new JavaSimulationKernel().run(request);

        assertTrue(result.getEventsList().stream().allMatch(this::isSnapshot));
        assertTrue(!result.getFinalBook().hasBestBidTicks());
        assertTrue(!result.getFinalBook().hasBestAskTicks());
        assertTrue(!result.getFinalBook().hasMidPriceTicksX2());
        assertTrue(!result.getFinalBook().hasSpreadTicks());
    }

    @Test
    void unfrozenParametersAndResourceOverflowAreRejected() throws IOException {
        SimulationRequest parameterized = request("normal-market-seed-42").toBuilder()
                .setScenario(request("normal-market-seed-42").getScenario().toBuilder()
                        .addParameters(ScenarioParameter.newBuilder().setName("wall").setIntegerValue(1)))
                .build();
        SimulationRequest constrained = request("normal-market-seed-42").toBuilder()
                .setConfig(request("normal-market-seed-42").getConfig().toBuilder().setMaxEvents(1))
                .build();

        assertThrows(IllegalArgumentException.class, () -> new JavaSimulationKernel().run(parameterized));
        assertThrows(IllegalArgumentException.class, () -> new JavaSimulationKernel().run(constrained));
    }

    @Test
    void goldenRequestsMatchExactEventsBooksAndMetrics() throws IOException {
        for (String caseId : List.of(
                "normal-market-seed-42",
                "empty-book-seed-7",
                "spoofing-like-wall-seed-42",
                "layering-like-seed-43",
                "quote-stuffing-seed-44",
                "liquidity-evaporation-seed-45")) {
            SimulationResult actual = new JavaSimulationKernel().run(request(caseId));
            SimulationResult expected = expectedResult(caseId);
            assertEquals(expected.getEventsCount(), actual.getEventsCount(), caseId);
            for (int index = 0; index < expected.getEventsCount(); index++) {
                assertEquals(expected.getEvents(index), actual.getEvents(index), caseId + " event " + (index + 1));
            }
            assertEquals(expected.getEventStreamHash(), actual.getEventStreamHash(), caseId + " stream hash");
            assertEquals(expected.getFinalBookHash(), actual.getFinalBookHash(), caseId + " book hash");
            assertEquals(expected.getMetricsList(), actual.getMetricsList(), caseId + " metrics");
        }
    }

    private SimulationRequest request(String caseId) throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/" + caseId + "/request.pb")) {
            if (input == null) {
                throw new IOException("missing golden request " + caseId);
            }
            return SimulationRequest.parseFrom(input);
        }
    }

    private SimulationResult expectedResult(String caseId) throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/" + caseId + "/expected-result.pb")) {
            if (input == null) {
                throw new IOException("missing golden result " + caseId);
            }
            return SimulationResult.parseFrom(input);
        }
    }

    private boolean isSnapshot(ExchangeEvent event) {
        return event.getPayloadCase() == ExchangeEvent.PayloadCase.SNAPSHOT;
    }
}

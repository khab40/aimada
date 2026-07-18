package ai.lobarena.benchmarks;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.kernel.book.IntegerMatchingEngine;
import ai.lobarena.kernel.book.IntegerOrderBook;
import ai.lobarena.kernel.book.KernelOrder;
import ai.lobarena.kernel.simulation.JavaSimulationKernel;
import com.sun.management.ThreadMXBean;
import java.io.IOException;
import java.io.InputStream;
import java.lang.management.ManagementFactory;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

final class KernelPerformanceGateTest {
    private static final int WARMUP_RUNS = 20;
    private static final int MEASURED_RUNS = 50;
    private static final long MAX_P99_NANOS = 1_000_000_000L;
    private static final double MIN_THROUGHPUT_PER_SECOND = 5.0;
    private static final long MAX_ALLOCATED_BYTES_PER_RUN = 32L * 1024 * 1024;
    private static final int MEASURED_MATCHES = 1_000;
    private static final long MAX_MATCH_P99_NANOS = 50_000_000L;
    private static final double MIN_MATCHES_PER_SECOND = 100.0;
    private static final long MAX_ALLOCATED_BYTES_PER_MATCH = 1024L * 1024;

    @Test
    void largestGoldenScenarioStaysWithinPortableSmokeCeilings() throws IOException {
        SimulationRequest request = request("liquidity-evaporation-seed-45");
        SimulationResult expected = result("liquidity-evaporation-seed-45");
        JavaSimulationKernel kernel = new JavaSimulationKernel();
        for (int index = 0; index < WARMUP_RUNS; index++) {
            kernel.run(request);
        }

        ThreadMXBean threadMetrics = allocationMetrics();
        long threadId = Thread.currentThread().threadId();
        long allocatedBefore = threadMetrics.getThreadAllocatedBytes(threadId);
        long started = System.nanoTime();
        long[] durations = new long[MEASURED_RUNS];
        for (int index = 0; index < MEASURED_RUNS; index++) {
            long runStarted = System.nanoTime();
            SimulationResult actual = kernel.run(request);
            durations[index] = System.nanoTime() - runStarted;
            assertEquals(expected.getEventsCount(), actual.getEventsCount());
            assertArrayEquals(expected.getEventStreamHash().toByteArray(), actual.getEventStreamHash().toByteArray());
        }
        long elapsed = System.nanoTime() - started;
        long allocated = threadMetrics.getThreadAllocatedBytes(threadId) - allocatedBefore;
        Arrays.sort(durations);

        long p99Nanos = durations[(int) Math.ceil(MEASURED_RUNS * 0.99) - 1];
        double throughput = MEASURED_RUNS * 1_000_000_000.0 / elapsed;
        long allocatedPerRun = allocated / MEASURED_RUNS;

        assertTrue(p99Nanos < MAX_P99_NANOS, () -> "p99 kernel latency exceeded: " + p99Nanos + " ns");
        assertTrue(
                throughput > MIN_THROUGHPUT_PER_SECOND,
                () -> "kernel throughput below floor: " + throughput + " runs/s");
        assertTrue(
                allocatedPerRun < MAX_ALLOCATED_BYTES_PER_RUN,
                () -> "kernel allocation exceeded: " + allocatedPerRun + " bytes/run");
    }

    @Test
    void crossingMatchPathStaysWithinPortableSmokeCeilings() {
        for (int index = 0; index < WARMUP_RUNS; index++) {
            assertEquals(1, runCrossingMatch(index));
        }
        ThreadMXBean threadMetrics = allocationMetrics();
        long threadId = Thread.currentThread().threadId();
        long allocatedBefore = threadMetrics.getThreadAllocatedBytes(threadId);
        long started = System.nanoTime();
        long[] durations = new long[MEASURED_MATCHES];
        for (int index = 0; index < MEASURED_MATCHES; index++) {
            long matchStarted = System.nanoTime();
            assertEquals(1, runCrossingMatch(index));
            durations[index] = System.nanoTime() - matchStarted;
        }
        long elapsed = System.nanoTime() - started;
        long allocated = threadMetrics.getThreadAllocatedBytes(threadId) - allocatedBefore;
        Arrays.sort(durations);

        long p99Nanos = durations[(int) Math.ceil(MEASURED_MATCHES * 0.99) - 1];
        double throughput = MEASURED_MATCHES * 1_000_000_000.0 / elapsed;
        long allocatedPerMatch = allocated / MEASURED_MATCHES;

        assertTrue(p99Nanos < MAX_MATCH_P99_NANOS, () -> "p99 match latency exceeded: " + p99Nanos + " ns");
        assertTrue(
                throughput > MIN_MATCHES_PER_SECOND,
                () -> "matching throughput below floor: " + throughput + " matches/s");
        assertTrue(
                allocatedPerMatch < MAX_ALLOCATED_BYTES_PER_MATCH,
                () -> "matching allocation exceeded: " + allocatedPerMatch + " bytes/match");
    }

    private int runCrossingMatch(int sequence) {
        IntegerOrderBook book = new IntegerOrderBook(1_000_000L, 100_000_000L);
        book.initialize(100_000L, 12, 1, 10, "baseline");
        IntegerMatchingEngine engine = new IntegerMatchingEngine(
                book, "BTC-USD", "LOB-ARENA", EventSource.EVENT_SOURCE_SIMULATION);
        return engine.submit(KernelOrder.market(
                        "GATE-MARKET-" + sequence,
                        "performance-gate",
                        Side.SIDE_BUY,
                        5,
                        sequence))
                .size();
    }

    private ThreadMXBean allocationMetrics() {
        ThreadMXBean threadMetrics = (ThreadMXBean) ManagementFactory.getThreadMXBean();
        assertTrue(threadMetrics.isThreadAllocatedMemorySupported(), "Java allocation accounting is required");
        if (!threadMetrics.isThreadAllocatedMemoryEnabled()) {
            threadMetrics.setThreadAllocatedMemoryEnabled(true);
        }
        return threadMetrics;
    }

    private SimulationRequest request(String caseId) throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/" + caseId + "/request.pb")) {
            if (input == null) {
                throw new IOException("missing request for " + caseId);
            }
            return SimulationRequest.parseFrom(input);
        }
    }

    private SimulationResult result(String caseId) throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/" + caseId + "/expected-result.pb")) {
            if (input == null) {
                throw new IOException("missing result for " + caseId);
            }
            return SimulationResult.parseFrom(input);
        }
    }
}

package ai.lobarena.benchmarks;

import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.kernel.book.IntegerMatchingEngine;
import ai.lobarena.kernel.book.IntegerOrderBook;
import ai.lobarena.kernel.book.KernelOrder;
import ai.lobarena.kernel.simulation.JavaSimulationKernel;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;

@BenchmarkMode({Mode.AverageTime, Mode.Throughput})
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 3, time = 1)
@Measurement(iterations = 5, time = 1)
public class KernelBenchmarks {
    @Benchmark
    public SimulationResult runSimulation(SimulationState state) {
        return state.kernel.run(state.request);
    }

    @Benchmark
    public List<ExchangeEvent> matchCrossingMarketOrder(MatchingState state) {
        return state.engine.submit(state.aggressor);
    }

    @State(Scope.Thread)
    public static class SimulationState {
        @Param({"normal-market-seed-42", "quote-stuffing-seed-44", "liquidity-evaporation-seed-45"})
        public String caseId;

        private JavaSimulationKernel kernel;
        private SimulationRequest request;

        @Setup(Level.Trial)
        public void setup() throws IOException {
            kernel = new JavaSimulationKernel();
            try (InputStream input = KernelBenchmarks.class.getResourceAsStream(
                    "/parity-v1/cases/" + caseId + "/request.pb")) {
                if (input == null) {
                    throw new IOException("missing golden request for " + caseId);
                }
                request = SimulationRequest.parseFrom(input);
            }
        }
    }

    @State(Scope.Thread)
    public static class MatchingState {
        private long sequence;
        private IntegerMatchingEngine engine;
        private KernelOrder aggressor;

        @Setup(Level.Invocation)
        public void setup() {
            IntegerOrderBook book = new IntegerOrderBook(1_000_000L, 100_000_000L);
            book.initialize(100_000L, 12, 1, 10, "baseline");
            engine = new IntegerMatchingEngine(
                    book, "BTC-USD", "LOB-ARENA", EventSource.EVENT_SOURCE_SIMULATION);
            aggressor = KernelOrder.market(
                    "BENCH-MARKET-" + sequence++, "benchmark", Side.SIDE_BUY, 5, sequence);
        }
    }
}

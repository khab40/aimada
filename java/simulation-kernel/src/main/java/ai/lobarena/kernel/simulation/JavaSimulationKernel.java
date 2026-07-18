package ai.lobarena.kernel.simulation;

import ai.lobarena.exchange.v1.BookSnapshot;
import ai.lobarena.exchange.v1.EventSource;
import ai.lobarena.exchange.v1.ExchangeEvent;
import ai.lobarena.exchange.v1.Side;
import ai.lobarena.exchange.v1.SimulationConfig;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.exchange.v1.TerminationReason;
import ai.lobarena.kernel.book.IntegerMatchingEngine;
import ai.lobarena.kernel.book.IntegerOrderBook;
import ai.lobarena.kernel.book.KernelOrder;
import ai.lobarena.kernel.book.MutationContext;
import ai.lobarena.kernel.hashing.CanonicalHashes;
import com.google.protobuf.ByteString;
import java.util.ArrayList;
import java.util.List;

public final class JavaSimulationKernel {
    public SimulationResult run(SimulationRequest request) {
        validate(request);
        SimulationConfig config = request.getConfig();
        IntegerOrderBook book = new IntegerOrderBook(
                config.getPriceTickSizeNanos(), config.getQuantityLotSizeNanos());
        if (config.getBaselineLiquidityLevels() > 0) {
            book.initialize(
                    config.getReferencePriceTicks(),
                    config.getBaselineLiquidityLevels(),
                    config.getBaselineLiquidityTickSizeTicks(),
                    config.getBaselineLiquidityBaseLots(),
                    "normal");
        }
        IntegerMatchingEngine matching = new IntegerMatchingEngine(
                book,
                config.getSymbol(),
                config.getVenue(),
                EventSource.EVENT_SOURCE_SIMULATION);
        NormalAgentPhase agents = new NormalAgentPhase(
                config.getNormalAgentCount(), config.getQuantityLotSizeNanos());
        ScenarioProgram scenario = scenario(request, config);
        SimulationClock clock = new SimulationClock();
        KernelMetrics metrics = new KernelMetrics(
                config.getPriceTickSizeNanos(),
                config.getQuantityLotSizeNanos(),
                config.getTickIntervalNs());
        KernelMetrics.FeatureResult finalFeatures = metrics.calculate(0, book.snapshot(config.getSnapshotDepth()), List.of(), null);

        for (long index = 0; index < request.getScenario().getMaxTicks(); index++) {
            long tick = clock.step();
            Double previousDepth = metrics.topDepth(book.snapshot(Math.max(1, config.getSnapshotDepth())));
            List<Activity> activities = new ArrayList<>();
            BookSnapshot decisionBook = book.snapshot(12);
            for (AgentIntent intent : agents.decide(tick, decisionBook)) {
                activities.add(applyIntent(intent, matching, config.getMaxAgentQuoteLots()));
            }
            if (scenario != null) {
                matching.runWithMutationContext(
                        new MutationContext(
                                tick,
                                scenario.scenarioId(),
                                scenario.scenarioName(),
                                scenario.scenarioFamily()),
                        () -> activities.addAll(scenario.advance(book, tick)));
            }
            matching.runWithMutationContext(
                    new MutationContext(tick, null, null, null),
                    () -> maintainBaseline(book, config));
            matching.recordSnapshot(
                    tick,
                    config.getSnapshotDepth(),
                    null,
                    null,
                    scenario == null ? null : scenario.scenarioId(),
                    scenario == null ? null : scenario.scenarioName(),
                    scenario == null ? null : scenario.scenarioFamily());
            if (matching.events().size() > config.getMaxEvents()) {
                throw new IllegalArgumentException(
                        "simulation exceeded configured max_events at a completed tick boundary");
            }
            finalFeatures = metrics.calculate(
                    tick, book.snapshot(config.getSnapshotDepth()), List.copyOf(activities), previousDepth);
        }

        List<ExchangeEvent> events = matching.events();
        BookSnapshot finalBook = book.snapshot(config.getSnapshotDepth());
        return SimulationResult.newBuilder()
                .setContractVersion(request.getContractVersion())
                .setRunId(request.getRunId())
                .addAllEvents(events)
                .setFinalBook(finalBook)
                .addAllMetrics(metrics.toProto(clock.tick(), finalFeatures))
                .setEventStreamHash(ByteString.copyFrom(
                        CanonicalHashes.eventStreamHash(events, request.getContractVersion())))
                .setFinalBookHash(ByteString.copyFrom(CanonicalHashes.bookHash(finalBook)))
                .setTerminationReason(TerminationReason.TERMINATION_REASON_COMPLETED)
                .build();
    }

    private static Activity applyIntent(
            AgentIntent intent, IntegerMatchingEngine matching, long maxAgentQuoteLots) {
        if (intent.kind() == AgentIntent.Kind.SET_LEVEL) {
            long quantity = Math.min(Math.max(0, intent.quantityLots()), maxAgentQuoteLots);
            matching.runWithMutationContext(
                    new MutationContext(intent.tick(), null, null, null),
                    () -> matching.book().updateAgentLevel(
                            intent.side(),
                            intent.priceTicks(),
                            quantity,
                            intent.agentId(),
                            "normal",
                            null,
                            intent.tick(),
                            null,
                            null,
                            null));
            return new Activity(
                    intent.eventType(),
                    null,
                    null,
                    intent.agentId(),
                    intent.side(),
                    null,
                    intent.message());
        }
        String orderId = intent.agentId() + "-" + intent.tick() + "-" + intent.sequence();
        matching.submit(KernelOrder.market(
                orderId, intent.agentId(), intent.side(), intent.quantityLots(), intent.tick()));
        return new Activity(
                intent.eventType(),
                null,
                null,
                intent.agentId(),
                intent.side(),
                null,
                intent.message());
    }

    private static void maintainBaseline(IntegerOrderBook book, SimulationConfig config) {
        if (config.getBaselineLiquidityLevels() <= 0 || config.getBaselineLiquidityBaseLots() <= 0) {
            return;
        }
        if (1_000_000_000L % config.getQuantityLotSizeNanos() != 0) {
            throw new IllegalArgumentException("quantity unit must represent whole units exactly");
        }
        long lotsPerWholeUnit = 1_000_000_000L / config.getQuantityLotSizeNanos();
        for (int index = 0; index < config.getBaselineLiquidityLevels(); index++) {
            long distance = Math.multiplyExact(index + 1L, config.getBaselineLiquidityTickSizeTicks());
            long targetLots = Math.addExact(
                    config.getBaselineLiquidityBaseLots(),
                    Math.multiplyExact(index, lotsPerWholeUnit));
            book.ensureLevelMinimum(
                    Side.SIDE_BUY,
                    config.getReferencePriceTicks() - distance,
                    targetLots,
                    "BASELINE_MM",
                    "normal");
            book.ensureLevelMinimum(
                    Side.SIDE_SELL,
                    config.getReferencePriceTicks() + distance,
                    targetLots,
                    "BASELINE_MM",
                    "normal");
        }
    }

    private static ScenarioProgram scenario(SimulationRequest request, SimulationConfig config) {
        String name = request.getScenario().getScenarioName();
        if (name.isEmpty() || name.equals("normal_market")) {
            return null;
        }
        return new ScenarioProgram(
                name,
                request.getScenario().getSeed(),
                config.getPriceTickSizeNanos(),
                config.getQuantityLotSizeNanos());
    }

    private static void validate(SimulationRequest request) {
        if (request.getContractVersion() != 1) {
            throw new IllegalArgumentException("Java simulation kernel supports contract_version 1");
        }
        if (request.getRunId().isEmpty()) {
            throw new IllegalArgumentException("run_id must not be empty");
        }
        if (request.getScenario().getMaxTicks() <= 0) {
            throw new IllegalArgumentException("scenario.max_ticks must be positive");
        }
        if (request.getScenario().getParametersCount() != 0) {
            throw new IllegalArgumentException("scenario parameters are not supported until their semantics are frozen");
        }
        SimulationConfig config = request.getConfig();
        if (config.getPriceTickSizeNanos() <= 0
                || config.getQuantityLotSizeNanos() <= 0
                || config.getSnapshotDepth() <= 0
                || config.getMaxEvents() <= 0
                || config.getTickIntervalNs() <= 0
                || config.getBaselineLiquidityTickSizeTicks() <= 0
                || config.getMaxAgentQuoteLots() <= 0) {
            throw new IllegalArgumentException("simulation config contains non-positive required values");
        }
        if (config.getSymbol().isEmpty() || config.getVenue().isEmpty()) {
            throw new IllegalArgumentException("config symbol and venue must not be empty");
        }
    }
}

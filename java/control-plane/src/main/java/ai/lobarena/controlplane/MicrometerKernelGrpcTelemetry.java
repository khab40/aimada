package ai.lobarena.controlplane;

import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.grpc.KernelGrpcTelemetry;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.stereotype.Component;

@Component
final class MicrometerKernelGrpcTelemetry implements KernelGrpcTelemetry {
    private static final String COMPLETED = "completed";
    private static final String INVALID_ARGUMENT = "invalid_argument";
    private static final String INTERNAL_ERROR = "internal_error";

    private final ObservationRegistry observations;
    private final Map<String, Counter> requests;
    private final Map<String, Timer> durations;
    private final DistributionSummary eventCounts;

    MicrometerKernelGrpcTelemetry(MeterRegistry meters, ObservationRegistry observations) {
        this.observations = observations;
        requests = Map.of(
                COMPLETED, requestCounter(meters, COMPLETED),
                INVALID_ARGUMENT, requestCounter(meters, INVALID_ARGUMENT),
                INTERNAL_ERROR, requestCounter(meters, INTERNAL_ERROR));
        durations = Map.of(
                COMPLETED, durationTimer(meters, COMPLETED),
                INVALID_ARGUMENT, durationTimer(meters, INVALID_ARGUMENT),
                INTERNAL_ERROR, durationTimer(meters, INTERNAL_ERROR));
        eventCounts = DistributionSummary.builder("lob.kernel.grpc.events")
                .description("Canonical events returned by successful Java kernel calls")
                .baseUnit("events")
                .register(meters);
    }

    @Override
    public Call start(SimulationRequest request) {
        Observation observation = Observation.start("lob.kernel.grpc", observations);
        observation.lowCardinalityKeyValue("contract.version", Integer.toString(request.getContractVersion()));
        return new ObservedCall(observation, System.nanoTime());
    }

    private Counter requestCounter(MeterRegistry meters, String outcome) {
        return Counter.builder("lob.kernel.grpc.requests")
                .description("Java kernel gRPC requests by bounded outcome")
                .tag("outcome", outcome)
                .register(meters);
    }

    private Timer durationTimer(MeterRegistry meters, String outcome) {
        return Timer.builder("lob.kernel.grpc.duration")
                .description("Java kernel gRPC execution duration")
                .tag("outcome", outcome)
                .publishPercentileHistogram()
                .register(meters);
    }

    private final class ObservedCall implements Call {
        private final Observation observation;
        private final long startedNanos;
        private final AtomicBoolean completed = new AtomicBoolean();

        private ObservedCall(Observation observation, long startedNanos) {
            this.observation = observation;
            this.startedNanos = startedNanos;
        }

        @Override
        public void succeeded(SimulationResult result) {
            eventCounts.record(result.getEventsCount());
            finish(COMPLETED, null);
        }

        @Override
        public void invalidArgument(IllegalArgumentException exception) {
            finish(INVALID_ARGUMENT, exception);
        }

        @Override
        public void failed(RuntimeException exception) {
            finish(INTERNAL_ERROR, exception);
        }

        private void finish(String outcome, RuntimeException exception) {
            if (!completed.compareAndSet(false, true)) {
                return;
            }
            requests.get(outcome).increment();
            durations.get(outcome).record(System.nanoTime() - startedNanos, TimeUnit.NANOSECONDS);
            observation.lowCardinalityKeyValue("outcome", outcome);
            if (exception != null) {
                observation.error(exception);
            }
            observation.stop();
        }
    }
}

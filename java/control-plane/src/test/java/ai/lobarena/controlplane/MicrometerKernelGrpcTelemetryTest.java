package ai.lobarena.controlplane;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.grpc.JavaKernelGrpcService;
import io.grpc.stub.StreamObserver;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationHandler;
import io.micrometer.observation.ObservationRegistry;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

final class MicrometerKernelGrpcTelemetryTest {
    @Test
    void recordsBoundedMetricsAndObservationsForSuccessAndInvalidInput() throws IOException {
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        ObservationRegistry observations = ObservationRegistry.create();
        AtomicInteger started = new AtomicInteger();
        AtomicInteger stopped = new AtomicInteger();
        observations.observationConfig().observationHandler(new ObservationHandler<>() {
            @Override
            public void onStart(Observation.Context context) {
                started.incrementAndGet();
            }

            @Override
            public void onStop(Observation.Context context) {
                stopped.incrementAndGet();
            }

            @Override
            public boolean supportsContext(Observation.Context context) {
                return true;
            }
        });
        JavaKernelGrpcService service = new JavaKernelGrpcService(
                new MicrometerKernelGrpcTelemetry(meters, observations));

        RecordingObserver<SimulationResult> success = new RecordingObserver<>();
        service.runSimulation(request(), success);
        SimulationRequest invalid = request().toBuilder().setContractVersion(2).build();
        RecordingObserver<SimulationResult> rejected = new RecordingObserver<>();
        service.runSimulation(invalid, rejected);

        assertNotNull(success.value);
        assertNull(success.error);
        assertTrue(success.completed);
        assertNotNull(rejected.error);
        assertEquals(
                1.0,
                meters.get("lob.kernel.grpc.requests").tag("outcome", "completed").counter().count());
        assertEquals(
                1.0,
                meters.get("lob.kernel.grpc.requests").tag("outcome", "invalid_argument").counter().count());
        assertEquals(
                1,
                meters.get("lob.kernel.grpc.duration").tag("outcome", "completed").timer().count());
        assertEquals(success.value.getEventsCount(), meters.get("lob.kernel.grpc.events").summary().totalAmount());
        assertEquals(2, started.get());
        assertEquals(2, stopped.get());
    }

    private SimulationRequest request() throws IOException {
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/normal-market-seed-42/request.pb")) {
            if (input == null) {
                throw new IOException("missing golden request");
            }
            return SimulationRequest.parseFrom(input);
        }
    }

    private static final class RecordingObserver<T> implements StreamObserver<T> {
        private T value;
        private Throwable error;
        private boolean completed;

        @Override
        public void onNext(T value) {
            this.value = value;
        }

        @Override
        public void onError(Throwable error) {
            this.error = error;
        }

        @Override
        public void onCompleted() {
            completed = true;
        }
    }
}

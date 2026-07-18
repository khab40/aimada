package ai.lobarena.grpc;

import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;

public interface KernelGrpcTelemetry {
    Call start(SimulationRequest request);

    interface Call {
        void succeeded(SimulationResult result);

        void invalidArgument(IllegalArgumentException exception);

        void failed(RuntimeException exception);
    }

    static KernelGrpcTelemetry noop() {
        return ignored -> new Call() {
            @Override
            public void succeeded(SimulationResult result) {}

            @Override
            public void invalidArgument(IllegalArgumentException exception) {}

            @Override
            public void failed(RuntimeException exception) {}
        };
    }
}

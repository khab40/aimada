package ai.lobarena.grpc;

import ai.lobarena.exchange.v1.SimulationKernelGrpc;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.kernel.simulation.JavaSimulationKernel;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

public final class JavaKernelGrpcService extends SimulationKernelGrpc.SimulationKernelImplBase {
    private final JavaSimulationKernel kernel;
    private final KernelGrpcTelemetry telemetry;

    public JavaKernelGrpcService() {
        this(new JavaSimulationKernel(), KernelGrpcTelemetry.noop());
    }

    JavaKernelGrpcService(JavaSimulationKernel kernel) {
        this(kernel, KernelGrpcTelemetry.noop());
    }

    public JavaKernelGrpcService(KernelGrpcTelemetry telemetry) {
        this(new JavaSimulationKernel(), telemetry);
    }

    JavaKernelGrpcService(JavaSimulationKernel kernel, KernelGrpcTelemetry telemetry) {
        this.kernel = kernel;
        this.telemetry = telemetry == null ? KernelGrpcTelemetry.noop() : telemetry;
    }

    @Override
    public void runSimulation(
            SimulationRequest request,
            StreamObserver<SimulationResult> responseObserver) {
        KernelGrpcTelemetry.Call telemetryCall = startTelemetry(request);
        SimulationResult result;
        try {
            result = kernel.run(request);
        } catch (IllegalArgumentException exception) {
            safely(() -> telemetryCall.invalidArgument(exception));
            responseObserver.onError(Status.INVALID_ARGUMENT
                    .withDescription(exception.getMessage())
                    .withCause(exception)
                    .asRuntimeException());
            return;
        } catch (RuntimeException exception) {
            safely(() -> telemetryCall.failed(exception));
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Java kernel execution failed")
                    .withCause(exception)
                    .asRuntimeException());
            return;
        }
        safely(() -> telemetryCall.succeeded(result));
        responseObserver.onNext(result);
        responseObserver.onCompleted();
    }

    private KernelGrpcTelemetry.Call startTelemetry(SimulationRequest request) {
        try {
            KernelGrpcTelemetry.Call call = telemetry.start(request);
            return call == null ? KernelGrpcTelemetry.noop().start(request) : call;
        } catch (RuntimeException ignored) {
            return KernelGrpcTelemetry.noop().start(request);
        }
    }

    private void safely(Runnable action) {
        try {
            action.run();
        } catch (RuntimeException ignored) {
            // Observability must never change kernel transport behavior.
        }
    }
}

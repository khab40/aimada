package ai.lobarena.grpc;

import ai.lobarena.exchange.v1.SimulationKernelGrpc;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import ai.lobarena.kernel.simulation.JavaSimulationKernel;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

public final class JavaKernelGrpcService extends SimulationKernelGrpc.SimulationKernelImplBase {
    private final JavaSimulationKernel kernel;

    public JavaKernelGrpcService() {
        this(new JavaSimulationKernel());
    }

    JavaKernelGrpcService(JavaSimulationKernel kernel) {
        this.kernel = kernel;
    }

    @Override
    public void runSimulation(
            SimulationRequest request,
            StreamObserver<SimulationResult> responseObserver) {
        try {
            responseObserver.onNext(kernel.run(request));
            responseObserver.onCompleted();
        } catch (IllegalArgumentException exception) {
            responseObserver.onError(Status.INVALID_ARGUMENT
                    .withDescription(exception.getMessage())
                    .withCause(exception)
                    .asRuntimeException());
        } catch (RuntimeException exception) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Java kernel execution failed")
                    .withCause(exception)
                    .asRuntimeException());
        }
    }
}

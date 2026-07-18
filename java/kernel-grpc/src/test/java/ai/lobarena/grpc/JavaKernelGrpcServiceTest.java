package ai.lobarena.grpc;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import ai.lobarena.exchange.v1.SimulationKernelGrpc;
import ai.lobarena.exchange.v1.SimulationRequest;
import ai.lobarena.exchange.v1.SimulationResult;
import io.grpc.ManagedChannel;
import io.grpc.Server;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import io.grpc.inprocess.InProcessChannelBuilder;
import io.grpc.inprocess.InProcessServerBuilder;
import java.io.IOException;
import java.io.InputStream;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

final class JavaKernelGrpcServiceTest {
    private Server server;
    private ManagedChannel channel;
    private SimulationKernelGrpc.SimulationKernelBlockingStub stub;

    @BeforeEach
    void startServer() throws IOException {
        String name = InProcessServerBuilder.generateName();
        server = InProcessServerBuilder.forName(name)
                .directExecutor()
                .addService(new JavaKernelGrpcService())
                .build()
                .start();
        channel = InProcessChannelBuilder.forName(name).directExecutor().build();
        stub = SimulationKernelGrpc.newBlockingStub(channel);
    }

    @AfterEach
    void stopServer() {
        channel.shutdownNow();
        server.shutdownNow();
    }

    @Test
    void inProcessRpcReturnsExactGoldenResult() throws IOException {
        SimulationRequest request = resource("/parity-v1/cases/normal-market-seed-42/request.pb");
        SimulationResult expected;
        try (InputStream input = getClass().getResourceAsStream(
                "/parity-v1/cases/normal-market-seed-42/expected-result.pb")) {
            expected = SimulationResult.parseFrom(input);
        }

        assertEquals(expected, stub.runSimulation(request));
    }

    @Test
    void invalidRequestMapsToInvalidArgument() throws IOException {
        SimulationRequest invalid = resource("/parity-v1/cases/normal-market-seed-42/request.pb")
                .toBuilder()
                .setContractVersion(2)
                .build();

        StatusRuntimeException exception = assertThrows(
                StatusRuntimeException.class, () -> stub.runSimulation(invalid));

        assertEquals(Status.Code.INVALID_ARGUMENT, exception.getStatus().getCode());
    }

    private SimulationRequest resource(String path) throws IOException {
        try (InputStream input = getClass().getResourceAsStream(path)) {
            return SimulationRequest.parseFrom(input);
        }
    }
}

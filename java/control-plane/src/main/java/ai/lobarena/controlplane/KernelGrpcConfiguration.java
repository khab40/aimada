package ai.lobarena.controlplane;

import ai.lobarena.grpc.JavaKernelGrpcServer;
import ai.lobarena.grpc.JavaKernelGrpcService;
import java.io.IOException;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
class KernelGrpcConfiguration {
    @Bean(destroyMethod = "close")
    @ConditionalOnProperty(name = "lob.kernel.grpc.enabled", havingValue = "true")
    JavaKernelGrpcServer kernelGrpcServer(
            MicrometerKernelGrpcTelemetry telemetry,
            @Value("${lob.kernel.grpc.port:50051}") int port) throws IOException {
        return new JavaKernelGrpcServer(port, new JavaKernelGrpcService(telemetry)).start();
    }
}

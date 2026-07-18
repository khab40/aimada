package ai.lobarena.controlplane;

import static org.assertj.core.api.Assertions.assertThat;

import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest
final class ControlPlaneApplicationTest {
    @Autowired
    private ApplicationContext context;

    @Test
    void contextLoadsWithKernelBoundary() {
        assertThat(context).isNotNull();
        assertThat(context.containsBean("kernelStatusController")).isTrue();
        assertThat(context.getBeansOfType(PrometheusMeterRegistry.class)).hasSize(1);
        assertThat(context.getBeansOfType(MicrometerKernelGrpcTelemetry.class)).hasSize(1);
        assertThat(context.getBeansOfType(ai.lobarena.grpc.JavaKernelGrpcServer.class)).isEmpty();
    }
}

package ai.lobarena.kernel;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

final class KernelBoundaryTest {
    @Test
    void kernelTargetsTheFrozenContractWithoutSpringOnItsClasspath() {
        assertEquals(1, KernelBoundary.CONTRACT_VERSION);
        assertThrows(
                ClassNotFoundException.class,
                () -> Class.forName(
                        "org.springframework.context.ApplicationContext",
                        false,
                        KernelBoundary.class.getClassLoader()));
    }
}

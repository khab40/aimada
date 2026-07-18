package ai.lobarena.controlplane;

import ai.lobarena.kernel.KernelBoundary;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/kernel/status")
final class KernelStatusController {
    @GetMapping
    Map<String, Object> status() {
        return Map.of(
                "authority", "java",
                "implementation", "java",
                "pythonFallback", false,
                "pythonReplay", false,
                "contractVersion", KernelBoundary.CONTRACT_VERSION);
    }
}

package ai.lobarena.controlplane;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;

@RestController
@RequestMapping("/internal/agents")
final class AgentOrchestrationController {
    private final AgentOrchestrator orchestrator;

    AgentOrchestrationController(AgentOrchestrator orchestrator) {
        this.orchestrator = orchestrator;
    }

    @PostMapping("/decide")
    Map<String, Object> decide(@RequestBody JsonNode request) {
        try {
            return orchestrator.collect(request.path("snapshot"));
        } catch (IllegalArgumentException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, exception.getMessage(), exception);
        }
    }

    @GetMapping("/status")
    Map<String, Object> status() {
        return Map.of("implementation", "java", "runnerCount", orchestrator.runnerCount());
    }
}

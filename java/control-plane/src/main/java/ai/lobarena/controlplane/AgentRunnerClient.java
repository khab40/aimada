package ai.lobarena.controlplane;

import java.net.URI;
import java.util.concurrent.CompletableFuture;
import tools.jackson.databind.JsonNode;

interface AgentRunnerClient {
    CompletableFuture<JsonNode> decide(URI runner, JsonNode snapshot);
}

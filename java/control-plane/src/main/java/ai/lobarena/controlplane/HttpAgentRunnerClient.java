package ai.lobarena.controlplane;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

final class HttpAgentRunnerClient implements AgentRunnerClient {
    private final HttpClient client;
    private final ObjectMapper mapper;
    private final Duration timeout;

    HttpAgentRunnerClient(ObjectMapper mapper, Duration timeout) {
        this.mapper = mapper;
        this.timeout = timeout;
        this.client = HttpClient.newBuilder()
                .connectTimeout(timeout)
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    @Override
    public CompletableFuture<JsonNode> decide(URI runner, JsonNode snapshot) {
        ObjectNode payload = mapper.createObjectNode().set("snapshot", snapshot);
        HttpRequest request = HttpRequest.newBuilder(runner.resolve("/decide"))
                .timeout(timeout)
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(payload)))
                .build();
        return client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .orTimeout(timeout.toMillis(), TimeUnit.MILLISECONDS)
                .thenApply(response -> {
                    if (response.statusCode() < 200 || response.statusCode() >= 300) {
                        throw new IllegalStateException("agent runner returned HTTP " + response.statusCode());
                    }
                    return mapper.readTree(response.body());
                });
    }
}

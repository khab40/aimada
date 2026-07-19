package ai.lobarena.controlplane;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

class LiveArenaServiceTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void ticksWithJavaOrchestratedAgentsAndMaintainsTwoSidedBook(@TempDir Path output) {
        LiveArenaService arena = arena(output, mapper.readTree("""
                {"agent_ids":["REMOTE_MM_001"],"intents":[
                  {"tick":1,"agent_id":"REMOTE_MM_001","kind":"set_level","side":"bid","price":68124.0,"quantity":2.5}
                ]}
                """));

        arena.start();
        JsonNode state = arena.stepForTest();

        assertThat(state.path("tick").longValue()).isEqualTo(1);
        assertThat(state.path("running").booleanValue()).isTrue();
        assertThat(state.path("active_agents").get(0).textValue()).isEqualTo("REMOTE_MM_001");
        assertThat(state.path("book").path("bids")).isNotEmpty();
        assertThat(state.path("book").path("asks")).isNotEmpty();
        assertThat(state.path("exchange_events").get(state.path("exchange_events").size() - 1)
                .path("event_type").textValue()).isEqualTo("snapshot");
        assertThat(Files.exists(output.resolve("snapshots/ticks.jsonl"))).isTrue();
    }

    @Test
    void appliesMarketIntentWithoutRequiringLimitPrice(@TempDir Path output) {
        LiveArenaService arena = arena(output, mapper.readTree("""
                {"agent_ids":["REMOTE_TAKER_001"],"intents":[
                  {"tick":1,"agent_id":"REMOTE_TAKER_001","kind":"market","side":"buy","quantity":0.5}
                ]}
                """));

        JsonNode state = arena.stepForTest();

        assertThat(state.path("tick").longValue()).isEqualTo(1);
        assertThat(state.path("events").get(0).path("agent_id").textValue()).isEqualTo("REMOTE_TAKER_001");
        assertThat(state.path("exchange_events")).anyMatch(
                event -> event.path("event_type").textValue().equals("execute"));
    }

    @Test
    void scenarioProgressCreatesDeterministicDetectorIncidentAndResetClearsIt(@TempDir Path output) {
        LiveArenaService arena = arena(output, mapper.readTree("{\"agent_ids\":[],\"intents\":[]}"));
        arena.launchScenario("spoofing_like_wall");

        JsonNode state = null;
        for (int index = 0; index < 3; index++) {
            state = arena.stepForTest();
        }

        assertThat(state.path("active_scenario").path("scenario_family").textValue())
                .isEqualTo("spoofing_like_wall");
        assertThat(state.path("detectors").path("alerts")).isNotEmpty();
        assertThat(state.path("incidents")).hasSize(1);
        assertThat(state.path("incidents").get(0).path("type").textValue())
                .isEqualTo("spoofing_like_detector");
        assertThat(Files.exists(output.resolve("incidents/incidents.jsonl"))).isTrue();

        JsonNode reset = arena.reset();
        assertThat(reset.path("tick").longValue()).isZero();
        assertThat(reset.path("active_scenario").isNull()).isTrue();
        assertThat(reset.path("incidents")).isEmpty();
    }

    @Test
    void exchangeReplayUsesCursorAndBoundedLimit(@TempDir Path output) {
        LiveArenaService arena = arena(output, mapper.readTree("{\"agent_ids\":[],\"intents\":[]}"));
        arena.stepForTest();
        arena.stepForTest();

        JsonNode replay = arena.exchangeEvents(0, 1);

        assertThat(replay.path("events")).hasSize(1);
        assertThat(replay.path("has_more").booleanValue()).isTrue();
        assertThat(replay.path("next_after_sequence").longValue()).isPositive();
    }

    private LiveArenaService arena(Path output, JsonNode runnerResponse) {
        AgentRunnerClient client = (URI runner, JsonNode snapshot) -> {
            JsonNode response = runnerResponse.deepCopy();
            if (response.path("intents").isArray()) {
                response.path("intents").forEach(intent -> ((ObjectNode) intent)
                        .put("tick", snapshot.path("tick").longValue()));
            }
            return CompletableFuture.completedFuture(response);
        };
        AgentOrchestrator orchestrator = new AgentOrchestrator(List.of(URI.create("http://runner:9100/")), client);
        return new LiveArenaService(mapper, orchestrator, new ArenaJournal(output, mapper));
    }
}

package ai.lobarena.controlplane;

import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import tools.jackson.databind.ObjectMapper;

@Configuration(proxyBeanMethods = false)
@EnableScheduling
class ArenaConfiguration {
    @Bean
    ArenaJournal arenaJournal(
            ObjectMapper mapper,
            @Value("${lob.arena.output-dir:../outputs}") String outputDir) {
        return new ArenaJournal(normalizePath(outputDir), mapper);
    }

    @Bean
    LiveArenaService liveArenaService(
            ObjectMapper mapper,
            AgentOrchestrator orchestrator,
            ArenaJournal journal,
            @Value("${lob.arena.historical-data-dir:../data/processed/lobster}") String historicalDataDir,
            @Value("${lob.arena.historical-rows-per-tick:250}") int historicalRowsPerTick) {
        return new LiveArenaService(
                mapper,
                orchestrator,
                journal,
                normalizePath(historicalDataDir),
                historicalRowsPerTick);
    }

    static Path normalizePath(String value) {
        return Path.of(value).toAbsolutePath().normalize();
    }
}

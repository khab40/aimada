package ai.lobarena.controlplane;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import tools.jackson.databind.ObjectMapper;

@Configuration(proxyBeanMethods = false)
@EnableWebSocket
class ArenaWebSocketConfiguration implements WebSocketConfigurer {
    private final ArenaWebSocketHandler handler;

    ArenaWebSocketConfiguration(ArenaWebSocketHandler handler) {
        this.handler = handler;
    }

    @Bean
    static ArenaWebSocketHandler arenaWebSocketHandler(LiveArenaService arena, ObjectMapper mapper) {
        return new ArenaWebSocketHandler(arena, mapper);
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(handler, "/ws/arena").setAllowedOriginPatterns("*");
    }
}

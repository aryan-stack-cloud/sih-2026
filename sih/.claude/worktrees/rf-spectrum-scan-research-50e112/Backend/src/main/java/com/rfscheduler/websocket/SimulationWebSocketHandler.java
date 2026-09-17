package com.rfscheduler.websocket;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import tools.jackson.databind.json.JsonMapper;

/**
 * WebSocket endpoint handler for {@code /ws/v1/simulations/{simulationId}}.
 *
 * <p>Client protocol, per API_CONTRACT.md Section 3: connect, receive {@code connection_ack},
 * optionally send {@code {"type":"subscribe","channels":[...]}}, and respond to server pings.
 * Anything unrecognised gets an error frame rather than a dropped connection - a client bug
 * should be diagnosable, not silent.
 */
@Component
public class SimulationWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(SimulationWebSocketHandler.class);
    private static final Set<String> VALID_CHANNELS =
            Set.of("spectrum", "scheduler", "metrics", "training");

    private final WebSocketHub hub;
    private final JsonMapper mapper = JsonMapper.builder().build();

    public SimulationWebSocketHandler(WebSocketHub hub) {
        this.hub = hub;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String simulationId = simulationIdOf(session);
        if (simulationId == null) {
            closeQuietly(session);
            return;
        }
        session.getAttributes().put("simulationId", simulationId);
        hub.register(simulationId, session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String simulationId = (String) session.getAttributes().get("simulationId");
        try {
            Map<?, ?> payload = mapper.readValue(message.getPayload(), Map.class);
            String type = String.valueOf(payload.get("type"));

            switch (type) {
                case "subscribe" -> {
                    Object channels = payload.get("channels");
                    Set<String> requested = new LinkedHashSet<>();
                    if (channels instanceof List<?> list) {
                        for (Object c : list) {
                            String channel = String.valueOf(c);
                            if (VALID_CHANNELS.contains(channel)) {
                                requested.add(channel);
                            }
                        }
                    }
                    if (requested.isEmpty()) {
                        requested.addAll(VALID_CHANNELS);
                    }
                    hub.subscribe(session, requested);
                }
                case "pong", "ping" -> {
                    // Heartbeat. Spring answers protocol-level pings itself; this handles clients
                    // that send an application-level one.
                }
                default -> hub.broadcastError(simulationId, "UNKNOWN_MESSAGE_TYPE",
                        "unrecognised message type: " + type);
            }
        } catch (RuntimeException e) {
            log.debug("bad websocket message on {}: {}", simulationId, e.toString());
            hub.broadcastError(simulationId, "MALFORMED_MESSAGE", "could not parse message");
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String simulationId = (String) session.getAttributes().get("simulationId");
        if (simulationId != null) {
            hub.unregister(simulationId, session);
        }
    }

    private static String simulationIdOf(WebSocketSession session) {
        if (session.getUri() == null) {
            return null;
        }
        String path = session.getUri().getPath();
        int idx = path.lastIndexOf('/');
        if (idx < 0 || idx == path.length() - 1) {
            return null;
        }
        return path.substring(idx + 1);
    }

    private static void closeQuietly(WebSocketSession session) {
        try {
            session.close(CloseStatus.BAD_DATA);
        } catch (Exception ignored) {
            // nothing to do
        }
    }
}

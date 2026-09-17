package com.rfscheduler.websocket;

import com.rfscheduler.service.SimulationService;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import tools.jackson.databind.json.JsonMapper;

/**
 * WebSocket session registry and fan-out - API_CONTRACT.md Section 3.
 *
 * <p>Endpoint {@code /ws/v1/simulations/{simulationId}}. On connect the server sends
 * {@code connection_ack}; the client may then {@code subscribe} to the channels {@code spectrum},
 * {@code scheduler}, {@code metrics} and {@code training}.
 *
 * <p>RECONNECT REPLAY. Section 3 requires the server to replay the last known state snapshot when
 * a client reconnects. That is what makes a dropped connection invisible to a viewer mid-demo:
 * without it a reconnecting dashboard sits blank until the next event happens, which on a
 * finished simulation is never. The snapshot rides along with {@code connection_ack}.
 *
 * <p>Fan-out is in-process. The PRD uses Redis pub/sub to spread this across instances; with one
 * instance the broadcast below is the same thing without the hop, and the seam is this class.
 */
@Component
public class WebSocketHub {

    private static final Logger log = LoggerFactory.getLogger(WebSocketHub.class);

    private final JsonMapper mapper = JsonMapper.builder().build();

    /** simulationId -> live sessions. */
    private final Map<String, Set<WebSocketSession>> sessions = new ConcurrentHashMap<>();
    /** session id -> channels that session subscribed to. */
    private final Map<String, Set<String>> subscriptions = new ConcurrentHashMap<>();

    private final SimulationService simulations;

    public WebSocketHub(@Lazy SimulationService simulations) {
        this.simulations = simulations;
    }

    // -- lifecycle ------------------------------------------------------------------------------

    public void register(String simulationId, WebSocketSession session) {
        sessions.computeIfAbsent(simulationId, k -> new CopyOnWriteArraySet<>()).add(session);
        // Default to every channel, so a client that never sends `subscribe` still sees events.
        subscriptions.put(session.getId(),
                new CopyOnWriteArraySet<>(Set.of("spectrum", "scheduler", "metrics", "training")));

        Map<String, Object> ack = new LinkedHashMap<>();
        ack.put("type", "connection_ack");
        ack.put("simulation_id", simulationId);
        ack.put("channels", Set.of("spectrum", "scheduler", "metrics", "training"));
        ack.put("heartbeat_seconds", 15);

        // Reconnect replay: hand the client the current picture immediately.
        var live = simulations.liveStateOrNull(simulationId);
        if (live != null) {
            ack.put("snapshot", live.snapshot());
        }
        send(session, ack);
    }

    public void unregister(String simulationId, WebSocketSession session) {
        Set<WebSocketSession> live = sessions.get(simulationId);
        if (live != null) {
            live.remove(session);
            if (live.isEmpty()) {
                sessions.remove(simulationId);
            }
        }
        subscriptions.remove(session.getId());
    }

    public void subscribe(WebSocketSession session, Set<String> channels) {
        subscriptions.put(session.getId(), new CopyOnWriteArraySet<>(channels));
    }

    // -- fan-out --------------------------------------------------------------------------------

    public void broadcast(String simulationId, String channel, Map<String, Object> frame) {
        Set<WebSocketSession> live = sessions.get(simulationId);
        if (live == null || live.isEmpty()) {
            return;
        }
        for (WebSocketSession session : live) {
            Set<String> channels = subscriptions.get(session.getId());
            if (channels == null || channels.contains(channel)) {
                send(session, frame);
            }
        }
    }

    /** Error frame, exactly the shape Section 3 gives. */
    public void broadcastError(String simulationId, String code, String message) {
        Map<String, Object> frame = new LinkedHashMap<>();
        frame.put("type", "error");
        frame.put("code", code);
        frame.put("message", message == null ? "" : message);
        broadcast(simulationId, "metrics", frame);
    }

    public int sessionCount(String simulationId) {
        Set<WebSocketSession> live = sessions.get(simulationId);
        return live == null ? 0 : live.size();
    }

    private void send(WebSocketSession session, Map<String, Object> frame) {
        if (!session.isOpen()) {
            return;
        }
        try {
            String json = mapper.writeValueAsString(frame);
            // Spring's WebSocketSession is not safe for concurrent senders, and the simulation
            // worker and the heartbeat both write.
            synchronized (session) {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                }
            }
        } catch (IOException e) {
            log.debug("dropping websocket session {}: {}", session.getId(), e.toString());
            try {
                session.close(CloseStatus.SERVER_ERROR);
            } catch (IOException ignored) {
                // already gone
            }
        } catch (RuntimeException e) {
            log.warn("failed to serialise websocket frame", e);
        }
    }
}

/**
 * Per-run live state without the shared store: opens one `SimulationConnection` for the run,
 * folds frames the same way the store does, and polls the REST fallback beside it.
 *
 * <p>Used by the judge view, where scrubbing across steps needs its own frame buffer rather
 * than the single shared tail the harness views read from the store.
 */

import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { SimulationConnection } from "../services/websocket/connection";
import type { ConnectionState } from "../services/websocket/connection";
import type { LiveSnapshot, WsFrame } from "../types/contract";
import { appendDecision, appendSpectrumFrame, applyFalseAlarms } from "../lib/frameWindow";
import type { SpectrumFrame } from "../lib/frameWindow";

export function useRunWatcher(simulationId: string | null, pollMs = 1500): {
  frames: SpectrumFrame[];
  live: LiveSnapshot | null;
  decisions: WsFrame[];
  connection: ConnectionState;
} {
  const [frames, setFrames] = useState<SpectrumFrame[]>([]);
  const [live, setLive] = useState<LiveSnapshot | null>(null);
  const [decisions, setDecisions] = useState<WsFrame[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("idle");

  useEffect(() => {
    // A new id is a new run: drop everything buffered, like the store's `watch` reset.
    setFrames([]);
    setLive(null);
    setDecisions([]);
    setConnection("idle");
    if (simulationId === null) return;

    const conn = new SimulationConnection(simulationId, {
      onFrame: (frame) => {
        switch (frame.type) {
          case "connection_ack":
            // Replacement, never merged: a reconnect means missed frames, so the local
            // buffer is stale - the same reconnect rule the store documents.
            if (frame.snapshot) {
              setLive(frame.snapshot);
              setFrames([]);
            }
            break;
          case "spectrum_update":
            setFrames((prev) => appendSpectrumFrame(prev, frame));
            break;
          case "detection_event":
            setFrames((prev) => applyFalseAlarms(prev, frame));
            break;
          case "scan_decision":
            setDecisions((prev) => appendDecision(prev, frame));
            break;
          case "metrics_update":
            setLive((prev) =>
              prev ? { ...prev, metrics: frame.metrics ?? prev.metrics } : prev,
            );
            break;
          default:
            break;
        }
      },
      onStateChange: (state) => setConnection(state),
    });
    conn.connect();

    // REST fallback for the socket; a stopped run answers SIM_NOT_RUNNING, which is the
    // expected idle state, and any other failure keeps the last good snapshot silently.
    const timer = setInterval(() => {
      void api
        .liveMetrics(simulationId)
        .then((snapshot) => setLive(snapshot))
        .catch(() => {});
    }, pollMs);
    return () => {
      clearInterval(timer);
      conn.close();
    };
  }, [simulationId, pollMs]);

  return { frames, live, decisions, connection };
}

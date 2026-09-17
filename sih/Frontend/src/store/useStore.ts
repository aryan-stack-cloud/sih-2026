/**
 * Zustand store: simulations, live spectrum state, and the WebSocket connection.
 *
 * <p>One live-updating store shared across every view, which is the reason the Frontend README
 * asks for Zustand even in the test-only build - the spectrum, scheduler and metrics views all
 * read the same stream and must not each open their own socket.
 *
 * <p>THE RECONNECT RULE. `connection_ack` may carry a state snapshot. It is applied as a
 * **replacement**, never merged: a reconnect means we missed an unknown number of frames, so
 * anything accumulated locally is stale. Treating it as an increment would double-count every
 * detection that happened before the drop.
 */

import { create } from "zustand";
import * as api from "../services/api/client";
import { SimulationConnection } from "../services/websocket/connection";
import type { ConnectionState } from "../services/websocket/connection";
import type {
  Experiment,
  ExperimentResults,
  LiveSnapshot,
  ReadyStatus,
  Scenario,
  Simulation,
  WsFrame,
} from "../types/contract";

/** Rolling window of recent frames; the harness shows the tail, not the whole run. */
const FRAME_WINDOW = 40;

export interface SpectrumFrame {
  t: number;
  activeBands: number[];
  scannedBands: number[];
  detectedBands: number[];
  /** Filled in by the detection_event frame, which is never coalesced away. */
  falseAlarmBands: number[];
}

interface StoreState {
  // connection
  connection: ConnectionState;
  connectionDetail: string;
  wsEventCount: number;
  lastFrameType: string;

  // health
  ready: ReadyStatus | null;

  // catalogue
  scenarios: Scenario[];
  simulations: Simulation[];
  experiments: Experiment[];

  // live
  activeSimulationId: string | null;
  live: LiveSnapshot | null;
  frames: SpectrumFrame[];
  lastDecision: WsFrame | null;

  // results
  results: Record<string, ExperimentResults>;

  error: string | null;

  refreshReady: () => Promise<void>;
  refreshScenarios: () => Promise<void>;
  refreshSimulations: () => Promise<void>;
  refreshExperiments: () => Promise<void>;
  watch: (simulationId: string) => void;
  unwatch: () => void;
  pollLive: (simulationId: string) => Promise<void>;
  loadResults: (experimentId: string) => Promise<void>;
  setError: (message: string | null) => void;
}

let connection: SimulationConnection | null = null;

export const useStore = create<StoreState>((set, get) => ({
  connection: "idle",
  connectionDetail: "",
  wsEventCount: 0,
  lastFrameType: "",
  ready: null,
  scenarios: [],
  simulations: [],
  experiments: [],
  activeSimulationId: null,
  live: null,
  frames: [],
  lastDecision: null,
  results: {},
  error: null,

  setError: (message) => set({ error: message }),

  refreshReady: async () => {
    try {
      set({ ready: await api.ready(), error: null });
    } catch (e) {
      set({ ready: null, error: describe(e) });
    }
  },

  refreshScenarios: async () => {
    try {
      set({ scenarios: await api.scenarios() });
    } catch (e) {
      set({ error: describe(e) });
    }
  },

  refreshSimulations: async () => {
    try {
      const page = await api.listSimulations(undefined, 0, 50);
      set({ simulations: page.items });
    } catch (e) {
      set({ error: describe(e) });
    }
  },

  refreshExperiments: async () => {
    try {
      const page = await api.listExperiments(undefined, 0, 50);
      set({ experiments: page.items });
    } catch (e) {
      set({ error: describe(e) });
    }
  },

  watch: (simulationId) => {
    get().unwatch();
    set({
      activeSimulationId: simulationId,
      frames: [],
      live: null,
      lastDecision: null,
      wsEventCount: 0,
    });

    connection = new SimulationConnection(
      simulationId,
      {
        onFrame: (frame) => applyFrame(set, get, frame),
        onStateChange: (state, detail) =>
          set({ connection: state, connectionDetail: detail ?? "" }),
      },
    );
    connection.connect();
  },

  unwatch: () => {
    connection?.close();
    connection = null;
    set({ connection: "idle", activeSimulationId: null });
  },

  pollLive: async (simulationId) => {
    // The contract calls GET /metrics/live the polling fallback for the WebSocket, so the
    // harness must work with the socket closed too.
    try {
      set({ live: await api.liveMetrics(simulationId), error: null });
    } catch (e) {
      set({ error: describe(e) });
    }
  },

  loadResults: async (experimentId) => {
    try {
      const results = await api.experimentResults(experimentId);
      set((s) => ({ results: { ...s.results, [experimentId]: results } }));
    } catch (e) {
      set({ error: describe(e) });
    }
  },
}));

function applyFrame(
  set: (partial: Partial<StoreState> | ((s: StoreState) => Partial<StoreState>)) => void,
  get: () => StoreState,
  frame: WsFrame,
): void {
  set((s) => ({ wsEventCount: s.wsEventCount + 1, lastFrameType: frame.type }));

  switch (frame.type) {
    case "connection_ack":
      // Replace, never merge - see the class note on the reconnect rule.
      if (frame.snapshot) {
        set({ live: frame.snapshot, frames: [] });
      }
      break;

    case "spectrum_update":
      set((s) => ({
        frames: [
          ...s.frames,
          {
            t: frame.t ?? 0,
            activeBands: frame.active_bands ?? [],
            scannedBands: frame.scanned_bands ?? [],
            detectedBands: frame.detected_bands ?? [],
            falseAlarmBands: [],
          },
        ].slice(-FRAME_WINDOW),
      }));
      break;

    case "scan_decision":
      set({ lastDecision: frame });
      break;

    case "detection_event":
      // Counters come from the server snapshot rather than being accumulated here, so a
      // reconnect cannot leave the UI showing a total nobody can reproduce. What this frame
      // does carry is false alarms, which spectrum_update omits and the waterfall needs -
      // detection_event is never coalesced, so nothing is lost by reading them only here.
      if (frame.false_alarm_bands?.length) {
        set((s) => ({
          frames: s.frames.map((f) =>
            f.t === frame.t ? { ...f, falseAlarmBands: frame.false_alarm_bands ?? [] } : f,
          ),
        }));
      }
      break;

    case "metrics_update":
      set((s) => ({
        live: s.live
          ? { ...s.live, metrics: frame.metrics ?? s.live.metrics }
          : s.live,
      }));
      void get().refreshSimulations();
      break;

    case "error":
      set({ error: `${frame.code}: ${frame.message}` });
      break;

    default:
      break;
  }
}

function describe(e: unknown): string {
  if (e instanceof api.ApiRequestError) return `${e.code}: ${e.message}`;
  return String(e);
}

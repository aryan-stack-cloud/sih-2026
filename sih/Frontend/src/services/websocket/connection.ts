/**
 * WebSocket connection manager - API_CONTRACT.md Section 3.
 *
 * The contract is explicit that this is the part most likely to break "seamless connection" if
 * skipped, and that clients must implement reconnect and coalescing tolerance **from day one,
 * even in the test-only build**. So this is not a thin `new WebSocket(...)` wrapper:
 *
 * - **Exponential backoff, 1s to a 30s cap.** A backend restart mid-demo should heal by itself
 *   rather than needing a page reload.
 * - **Reconnect replay is expected.** The server sends a state snapshot with `connection_ack`;
 *   consumers must treat that as a full state reset, not as an increment, or a reconnect
 *   double-counts everything that happened before it.
 * - **Coalescing tolerance.** The server drops intermediate `spectrum_update` frames under load
 *   and keeps only the latest, so `t` jumps. Nothing here may assume consecutive steps.
 * - **Deliberate closes do not reconnect.** Calling `close()` means the user navigated away;
 *   retrying then would leak a socket per visited page.
 */

import type { WsChannel, WsFrame } from "../../types/contract";
import { WS_CHANNELS } from "../../types/contract";
import { API_BASE } from "../api/client";

export type ConnectionState =
  | "idle"
  | "connecting"
  | "open"
  | "reconnecting"
  | "closed";

export interface ConnectionCallbacks {
  onFrame: (frame: WsFrame) => void;
  onStateChange?: (state: ConnectionState, detail?: string) => void;
}

const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30000;

function wsUrl(simulationId: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/ws/v1/simulations/${encodeURIComponent(simulationId)}`;
}

export class SimulationConnection {
  private socket: WebSocket | null = null;
  private backoffMs = INITIAL_BACKOFF_MS;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private deliberatelyClosed = false;
  private state: ConnectionState = "idle";

  constructor(
    private readonly simulationId: string,
    private readonly callbacks: ConnectionCallbacks,
    private readonly channels: WsChannel[] = WS_CHANNELS,
  ) {}

  connect(): void {
    this.deliberatelyClosed = false;
    this.open();
  }

  private open(): void {
    this.setState(this.backoffMs === INITIAL_BACKOFF_MS ? "connecting" : "reconnecting");

    let socket: WebSocket;
    try {
      socket = new WebSocket(wsUrl(this.simulationId));
    } catch (e) {
      this.scheduleRetry(String(e));
      return;
    }
    this.socket = socket;

    socket.onopen = () => {
      this.backoffMs = INITIAL_BACKOFF_MS;
      this.setState("open");
      // Section 3: the client may subscribe to specific channels after connection_ack.
      this.send({ type: "subscribe", channels: this.channels });
    };

    socket.onmessage = (event) => {
      let frame: WsFrame;
      try {
        frame = JSON.parse(event.data as string) as WsFrame;
      } catch {
        return; // a malformed frame is not worth tearing the connection down for
      }
      this.callbacks.onFrame(frame);
    };

    socket.onerror = () => {
      // Browsers give no detail here; onclose follows and carries the reconnect decision.
    };

    socket.onclose = (event) => {
      this.socket = null;
      if (this.deliberatelyClosed) {
        this.setState("closed");
        return;
      }
      this.scheduleRetry(`socket closed (${event.code})`);
    };
  }

  private scheduleRetry(detail: string): void {
    this.setState("reconnecting", detail);
    if (this.retryTimer !== null) return;

    const delay = this.backoffMs;
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      if (!this.deliberatelyClosed) this.open();
    }, delay);

    this.backoffMs = Math.min(this.backoffMs * 2, MAX_BACKOFF_MS);
  }

  send(message: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  close(): void {
    this.deliberatelyClosed = true;
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    this.socket?.close();
    this.socket = null;
    this.setState("closed");
  }

  currentState(): ConnectionState {
    return this.state;
  }

  /** Seconds until the next reconnect attempt, for the harness to display. */
  nextRetrySeconds(): number {
    return Math.round(this.backoffMs / 1000);
  }

  private setState(state: ConnectionState, detail?: string): void {
    this.state = state;
    this.callbacks.onStateChange?.(state, detail);
  }
}

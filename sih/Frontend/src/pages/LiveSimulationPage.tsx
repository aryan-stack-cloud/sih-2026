import { useEffect } from "react";
import { useStore } from "../store/useStore";

/**
 * Live view over the WebSocket, with the REST polling fallback beside it.
 *
 * Both paths are shown deliberately: the contract calls GET /metrics/live the polling fallback
 * for the socket, and a harness that only exercised one of them would not prove the contract.
 *
 * The spectrum strip is a plain text grid on purpose. `t` is expected to jump - the server
 * coalesces spectrum_update to 10/s and drops intermediate frames - so nothing here assumes
 * consecutive steps.
 */
export function LiveSimulationPage() {
  const {
    activeSimulationId, connection, connectionDetail, wsEventCount, lastFrameType,
    frames, live, lastDecision, pollLive, unwatch,
  } = useStore();

  useEffect(() => {
    if (!activeSimulationId) return;
    const timer = setInterval(() => void pollLive(activeSimulationId), 2000);
    return () => clearInterval(timer);
  }, [activeSimulationId, pollLive]);

  if (!activeSimulationId) {
    return (
      <section className="section simulation-workspace" aria-labelledby="live-simulation-heading">
        <div className="section-head">
          <div>
            <p className="eyebrow">Raw stream</p>
            <h2 id="live-simulation-heading">Live simulation</h2>
            <p className="note">Inspect WebSocket frames and the REST polling fallback together.</p>
          </div>
        </div>
        <div className="panel empty live-empty-state">
          <strong>No simulation selected.</strong>
          <span>Open Simulations and choose “Watch stream” on a run.</span>
        </div>
      </section>
    );
  }

  const bands = Math.max(
    16,
    ...frames.flatMap((frame) => [...frame.activeBands, ...frame.scannedBands]).map((band) => band + 1),
  );
  const connectionClass = connection === "open" ? "up" : connection === "closed" ? "down" : "";

  return (
    <div className="simulation-workspace">
      <section className="section" aria-labelledby="live-simulation-heading">
        <div className="section-head">
          <div>
            <p className="eyebrow">Raw stream</p>
            <h2 id="live-simulation-heading">Live simulation</h2>
            <p className="note">
              Monitoring <code className="mono live-simulation-id">{activeSimulationId}</code>
            </p>
          </div>
          <div className="controls">
            <span className={`service ${connectionClass}`}>
              <span className="dot" aria-hidden="true" />
              WebSocket {connection}
            </span>
            <button type="button" onClick={unwatch}>Disconnect</button>
          </div>
        </div>

        {connectionDetail && (
          <p className="alert" role="status">Connection detail: {connectionDetail}</p>
        )}

        <div className="tiles">
          <div className="tile">
            <div className="tile-label">Connection</div>
            <div className="tile-value">{connection}</div>
            <div className="tile-sub">WebSocket transport state</div>
          </div>
          <div className="tile">
            <div className="tile-label">Events received</div>
            <div className="tile-value">{wsEventCount}</div>
            <div className="tile-sub">All subscribed frame types</div>
          </div>
          <div className="tile">
            <div className="tile-label">Last event</div>
            <div className="tile-value live-event-name">{lastFrameType || "—"}</div>
            <div className="tile-sub">Most recent WebSocket message</div>
          </div>
          <div className="tile">
            <div className="tile-label">Current step</div>
            <div className="tile-value">{live?.t ?? "—"}</div>
            <div className="tile-sub">REST snapshot, polled every 2 seconds</div>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="spectrum-window-heading">
        <div className="section-head">
          <div>
            <p className="eyebrow">WebSocket telemetry</p>
            <h2 id="spectrum-window-heading">Spectrum window</h2>
            <p className="note">
              Last {frames.length} buffered frames. Steps may skip when the server coalesces
              updates to 10 frames per second under load.
            </p>
          </div>
        </div>

        <pre
          className="panel mono live-stream-readout"
          tabIndex={0}
          aria-label={`Spectrum activity across ${bands} bands`}
        >
          {frames.length === 0 ? "Waiting for frames…" : frames.map((frame) => {
            const active = new Set(frame.activeBands);
            const scanned = new Set(frame.scannedBands);
            const row = Array.from({ length: bands }, (_, band) => {
              if (active.has(band) && scanned.has(band)) return "#";
              if (active.has(band)) return "o";
              if (scanned.has(band)) return "_";
              return ".";
            }).join("");
            return `t=${String(frame.t).padStart(5)} |${row}|`;
          }).join("\n")}
        </pre>

        <div className="legend" aria-label="Spectrum symbol legend">
          <span className="legend-item">
            <span className="legend-swatch live-swatch-hit" aria-hidden="true" />
            <code>#</code> hit · active and scanned
          </span>
          <span className="legend-item">
            <span className="legend-swatch live-swatch-missed" aria-hidden="true" />
            <code>o</code> miss · active, not scanned
          </span>
          <span className="legend-item">
            <span className="legend-swatch live-swatch-listened" aria-hidden="true" />
            <code>_</code> listened · no activity
          </span>
          <span className="legend-item">
            <span className="legend-swatch live-swatch-idle" aria-hidden="true" />
            <code>.</code> idle
          </span>
        </div>
      </section>

      <div className="live-detail-grid">
        <section className="section" aria-labelledby="latest-decision-heading">
          <div className="section-head">
            <div>
              <p className="eyebrow">Scheduler output</p>
              <h2 id="latest-decision-heading">Latest decision</h2>
              <p className="note">The most recent action and its reward breakdown.</p>
            </div>
          </div>

          {lastDecision ? (
            <div className="panel">
              <table className="data live-key-value" aria-labelledby="latest-decision-heading">
                <tbody>
                  <tr><th scope="row">Step</th><td>{lastDecision.t ?? "—"}</td></tr>
                  <tr><th scope="row">Next band</th><td>{lastDecision.action ?? "—"}</td></tr>
                  <tr>
                    <th scope="row">Model</th>
                    <td><code className="live-simulation-id">{lastDecision.model_id || "—"}</code></td>
                  </tr>
                  <tr>
                    <th scope="row">Reward</th>
                    <td>{lastDecision.reward === undefined ? "—" : lastDecision.reward.toFixed(3)}</td>
                  </tr>
                  {lastDecision.reward_terms && Object.entries(lastDecision.reward_terms).map(([key, value]) => (
                    <tr key={key}>
                      <th scope="row">{key.replaceAll("_", " ")}</th>
                      <td>{Number(value).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="panel empty">Waiting for the first scheduler decision…</div>
          )}
        </section>

        <section className="section" aria-labelledby="rest-fallback-heading">
          <div className="section-head">
            <div>
              <p className="eyebrow">Contract fallback</p>
              <h2 id="rest-fallback-heading">REST live snapshot</h2>
              <p className="note"><code>GET /metrics/live</code> · polled every 2 seconds.</p>
            </div>
          </div>
          <pre
            className="panel mono live-stream-readout live-json"
            tabIndex={0}
            aria-label="Raw REST live metrics response"
          >
            {live ? JSON.stringify(live, null, 2) : "No live state; the simulation may not be running."}
          </pre>
        </section>
      </div>
    </div>
  );
}

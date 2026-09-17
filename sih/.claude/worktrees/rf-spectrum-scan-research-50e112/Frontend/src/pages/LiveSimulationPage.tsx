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
    return <p>No simulation selected. Pick one on the simulations tab and press "watch".</p>;
  }

  const bands = Math.max(
    16,
    ...frames.flatMap((f) => [...f.activeBands, ...f.scannedBands]).map((b) => b + 1),
  );

  return (
    <section>
      <h2>Live: <code>{activeSimulationId}</code></h2>
      <p>
        websocket: <strong>{connection}</strong>{" "}
        {connectionDetail && <span style={{ color: "#900" }}>({connectionDetail})</span>}{" "}
        | frames received: {wsEventCount} | last: {lastFrameType || "-"}{" "}
        <button onClick={unwatch}>disconnect</button>
      </p>

      <h3>Spectrum (last {frames.length} frames)</h3>
      <p style={{ fontSize: "0.85em", color: "#555" }}>
        <code>#</code> active and scanned (a hit) · <code>o</code> active, not scanned (a miss) ·
        <code> _</code> scanned, nothing there · <code>.</code> idle.
        Steps may skip: the server coalesces to 10 frames/sec under load.
      </p>
      <pre style={{ background: "#f4f4f4", padding: 8, overflowX: "auto", lineHeight: 1.25 }}>
{frames.length === 0 ? "waiting for frames..." : frames.map((f) => {
  const active = new Set(f.activeBands);
  const scanned = new Set(f.scannedBands);
  const row = Array.from({ length: bands }, (_, b) => {
    if (active.has(b) && scanned.has(b)) return "#";
    if (active.has(b)) return "o";
    if (scanned.has(b)) return "_";
    return ".";
  }).join("");
  return `t=${String(f.t).padStart(5)} |${row}|`;
}).join("\n")}
      </pre>

      <h3>Latest decision</h3>
      {lastDecision ? (
        <ul>
          <li>t = {lastDecision.t}</li>
          <li>action (next_band) = {lastDecision.action}</li>
          <li>model = <code>{lastDecision.model_id || "-"}</code></li>
          <li>reward = {lastDecision.reward?.toFixed(3)}</li>
          <li>
            terms ={" "}
            {lastDecision.reward_terms
              ? Object.entries(lastDecision.reward_terms)
                  .map(([k, v]) => `${k}=${Number(v).toFixed(2)}`)
                  .join("  ")
              : "-"}
          </li>
        </ul>
      ) : (
        <p>none yet</p>
      )}

      <h3>REST polling fallback (GET /metrics/live)</h3>
      <pre style={{ background: "#f4f4f4", padding: 8, overflowX: "auto" }}>
{live ? JSON.stringify(live, null, 2) : "no live state (the simulation may not be running)"}
      </pre>
    </section>
  );
}

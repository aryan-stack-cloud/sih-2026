import { useStore } from "../store/useStore";

/**
 * GET /health and GET /ready.
 *
 * Shows each ML service separately rather than one aggregate light, because "the Backend is up
 * but Ai-ml-1 is down" is the single most likely demo-day failure and it is invisible otherwise:
 * the scheduler degrades to round-robin and simply looks like a worse policy.
 */
export function HealthPanel() {
  const { ready, refreshReady } = useStore();

  return (
    <section className="section">
      <div className="section-head">
        <div>
          <p className="eyebrow">Diagnostics</p>
          <h2>Service health</h2>
          <p className="note">
            Each service is checked on its own. If an ML service drops mid-run, the scheduler
            quietly falls back to a fixed sweep — this is the one place that would show up.
          </p>
        </div>
        <div className="controls">
          <button onClick={() => void refreshReady()}>Refresh</button>
        </div>
      </div>

      {!ready ? (
        <p className="alert" role="alert">
          Backend unreachable at the configured API base.
        </p>
      ) : (
        <div className="tiles">
          <ServiceTile
            label="Backend"
            sub="API + orchestration"
            value={ready.status === "ready" ? "Ready" : "Degraded"}
            up={ready.status === "ready"}
          />
          <ServiceTile
            label="Scheduler"
            sub="Ai-ml-1 · :8500"
            value={ready.ml_scheduler === "up" ? "Up" : "Down"}
            up={ready.ml_scheduler === "up"}
          />
          <ServiceTile
            label="Periodicity"
            sub="Ai-ml-2 · :8600"
            value={ready.ml_periodicity === "up" ? "Up" : "Down"}
            up={ready.ml_periodicity === "up"}
          />
          <div className="tile">
            <div className="tile-label">Running simulations</div>
            <div className="tile-value">{ready.running_simulations}</div>
            <div className="tile-sub">active right now</div>
          </div>
        </div>
      )}
    </section>
  );
}

function ServiceTile({ label, sub, value, up }: { label: string; sub: string; value: string; up: boolean }) {
  return (
    <div className="tile" style={up ? undefined : { borderColor: "var(--false-alarm)" }}>
      <div className="tile-label">{label}</div>
      <div className="tile-value" style={{ color: up ? "var(--intercepted)" : "var(--false-alarm)" }}>
        {value}
      </div>
      <div className="tile-sub">{sub}</div>
    </div>
  );
}

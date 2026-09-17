import { useEffect, useState } from "react";
import { useStore } from "../store/useStore";
import { DemoPage } from "../pages/DemoPage";
import { SimulationsPage } from "../pages/SimulationsPage";
import { LiveSimulationPage } from "../pages/LiveSimulationPage";
import { ExperimentsPage } from "../pages/ExperimentsPage";
import { ModelsPage } from "../pages/ModelsPage";

type Tab = "demo" | "simulations" | "live" | "experiments" | "models";

const TABS: { id: Tab; label: string }[] = [
  { id: "demo", label: "Dashboard" },
  { id: "simulations", label: "Simulations" },
  { id: "live", label: "Raw stream" },
  { id: "experiments", label: "Experiments" },
  { id: "models", label: "Models" },
];

/**
 * Two audiences, one app.
 *
 * The dashboard is the judge-facing view and opens first. The remaining tabs are the engineer's
 * harness that came before it - every endpoint and the raw WebSocket stream, deliberately plain.
 * Keeping both matters: when the dashboard shows something surprising, the harness is where you
 * find out whether it is the scheduler or the plumbing.
 */
export function App() {
  const [tab, setTab] = useState<Tab>("demo");
  const { error, setError, ready, refreshReady } = useStore();

  useEffect(() => {
    void refreshReady();
  }, [refreshReady]);

  const service = (label: string, state: "up" | "down" | undefined) => (
    <span className={`service ${state ?? ""}`} key={label}>
      <span className="dot" />
      {label}
    </span>
  );

  return (
    <div className="shell">
      <header className="masthead">
        <div>
          <h1>Spectrum Scan Scheduler</h1>
          <p className="standfirst">
            A receiver that can hear two bands at a time, deciding where to listen next — and
            learning to do it better than a fixed sweep.
          </p>
          <p className="scope-note">
            Simulation only · no RF hardware · no interception · no jamming
          </p>
        </div>
        <div className="services">
          {service("Backend", ready ? "up" : "down")}
          {service("Scheduler", ready?.ml_scheduler)}
          {service("Periodicity", ready?.ml_periodicity)}
        </div>
      </header>

      <nav className="tabs" aria-label="Views">
        {TABS.map((t) => (
          <button
            key={t.id}
            aria-current={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error && (
        <p className="alert" role="alert">
          {error}{" "}
          <button style={{ marginLeft: 8 }} onClick={() => setError(null)}>
            Dismiss
          </button>
        </p>
      )}

      {tab === "demo" && <DemoPage />}
      {tab === "simulations" && <SimulationsPage onWatch={() => setTab("live")} />}
      {tab === "live" && <LiveSimulationPage />}
      {tab === "experiments" && <ExperimentsPage />}
      {tab === "models" && <ModelsPage />}
    </div>
  );
}

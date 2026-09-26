import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useStore } from "../store/useStore";
import { DemoPage } from "../pages/DemoPage";
import { SimulationsPage } from "../pages/SimulationsPage";
import { LiveSimulationPage } from "../pages/LiveSimulationPage";
import { ExperimentsPage } from "../pages/ExperimentsPage";
import { ModelsPage } from "../pages/ModelsPage";
import { HealthPanel } from "../pages/HealthPanel";

type Tab = "demo" | "simulations" | "live" | "experiments" | "models" | "health";

const TABS: { id: Tab; label: string }[] = [
  { id: "demo", label: "Dashboard" },
  { id: "simulations", label: "Simulations" },
  { id: "live", label: "Raw stream" },
  { id: "experiments", label: "Experiments" },
  { id: "models", label: "Models" },
  { id: "health", label: "Health" },
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
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    void refreshReady();
    const timer = setInterval(() => void refreshReady(), 8000);
    return () => clearInterval(timer);
  }, [refreshReady]);

  // WAI-ARIA tabs keyboard contract: arrows move between tabs, Home/End jump to the
  // ends. Selection follows focus, so there is exactly one Tab stop in the strip.
  const onTabKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next: number | null = null;
    if (e.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    if (next !== null) {
      e.preventDefault();
      setTab(TABS[next].id);
      tabRefs.current[next]?.focus();
    }
  };

  const service = (label: string, state: "up" | "down" | undefined) => (
    <span className={`service ${state ?? ""}`} key={label}>
      <span className="dot" />
      {label}
    </span>
  );

  return (
    <div className="shell">
      <div className="top-rule" aria-hidden="true"><span /><span /><span /></div>
      <header className="masthead">
        <div className="masthead-copy">
          <div className="brand-row">
            <img
              className="brand-mark"
              src="/favicon.svg"
              alt=""
              aria-hidden="true"
              width={20}
              height={20}
            />
            <span className="brand-name">Team Pushpak</span>
          </div>
          <div className="title-row">
            <h1>Spectrum Scan Scheduler</h1>
            <span className="classification">Research prototype</span>
          </div>
          <p className="standfirst">
            A receiver that can hear two bands at a time, deciding where to listen next — and
            learning to do it better than a fixed sweep.
          </p>
          <p className="scope-note">
            Simulation only · no RF hardware · no interception · no jamming
          </p>
        </div>
        <div className="masthead-status">
          <div className="status-kicker">System status</div>
          <div className="services">
            {service("Backend", ready ? "up" : "down")}
            {service("Scheduler", ready?.ml_scheduler)}
            {service("Periodicity", ready?.ml_periodicity)}
          </div>
        </div>
      </header>

      <div className="navigation-wrap">
        <span className="navigation-label">Mission views</span>
        <div className="tabs" role="tablist" aria-label="Views">
          {TABS.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              tabRefs.current[i] = el;
            }}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            tabIndex={tab === t.id ? 0 : -1}
            onClick={() => setTab(t.id)}
            onKeyDown={(e) => onTabKeyDown(e, i)}
          >
            {t.label}
          </button>
          ))}
        </div>
      </div>

      {error && (
        <p className="alert" role="alert">
          {error}{" "}
          <button style={{ marginLeft: 8 }} onClick={() => setError(null)}>
            Dismiss
          </button>
        </p>
      )}

      <div
        role="tabpanel"
        id={`panel-${tab}`}
        aria-labelledby={`tab-${tab}`}
        tabIndex={0}
        className="tabpanel"
      >
        {tab === "demo" && <DemoPage />}
        {tab === "simulations" && <SimulationsPage onWatch={() => setTab("live")} />}
        {tab === "live" && <LiveSimulationPage />}
        {tab === "experiments" && <ExperimentsPage />}
        {tab === "models" && <ModelsPage />}
        {tab === "health" && <HealthPanel />}
      </div>
    </div>
  );
}

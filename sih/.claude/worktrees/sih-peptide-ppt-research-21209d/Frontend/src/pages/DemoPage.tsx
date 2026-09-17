import { useEffect, useMemo, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { Waterfall } from "../components/Waterfall";
import { ComparisonTable, LiftChart } from "../components/LiftChart";
import type { LiftRow } from "../components/LiftChart";
import type { ExperimentResults, ScenarioId } from "../types/contract";

/**
 * The judge-facing view, and the 3-5 minute demo of PRD Section 20.4.
 *
 * Three beats in the order a viewer needs them: watch the receiver work, read what it achieved,
 * then see it measured against the sweep it replaces. The scripted run drives all three from one
 * button so the demo does not depend on anyone remembering a sequence under pressure.
 */

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const steps = (v: number) => `${v.toFixed(1)} steps`;

const TABLE_METRICS = [
  { key: "pd", label: "Detection rate (Pd)", format: pct },
  { key: "hpdr", label: "High-priority detection", format: pct },
  { key: "scan_efficiency", label: "Listening efficiency", format: pct },
  { key: "pfa", label: "False-alarm rate (Pfa)", format: pct },
  { key: "ait", label: "Intercept time, caught only", format: steps },
  { key: "ait_censored", label: "Intercept time, all bursts", format: steps },
  { key: "run_intercept_rate", label: "Distinct bursts caught", format: pct },
  { key: "interception_ratio", label: "Emitters seen at least once", format: pct },
];

export function DemoPage() {
  const {
    ready, frames, live, activeSimulationId, connection, watch, refreshReady,
    pollLive, setError,
  } = useStore();

  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [stage, setStage] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ExperimentResults | null>(null);
  const [bands, setBands] = useState(16);

  useEffect(() => {
    void refreshReady();
    const t = setInterval(() => void refreshReady(), 8000);
    return () => clearInterval(t);
  }, [refreshReady]);

  // Poll the live snapshot alongside the socket. The socket carries spectrum frames, but the
  // running totals live in the server's snapshot - reading them only from connection_ack froze
  // the tiles at whatever they were when the socket opened, which showed zero interceptions
  // beside a detection rate of 25%.
  useEffect(() => {
    if (!activeSimulationId) return;
    void pollLive(activeSimulationId);
    const t = setInterval(() => void pollLive(activeSimulationId), 1500);
    return () => clearInterval(t);
  }, [activeSimulationId, pollLive]);

  const runDemo = async () => {
    setRunning(true);
    setResults(null);
    try {
      setStage("Building the spectrum…");
      const all = await api.scenarios();
      const chosen = all.find((s) => s.id === scenario);
      setBands(chosen?.bands ?? 16);

      const sim = await api.createSimulation({
        name: `Demo ${scenario}`,
        bands: chosen?.bands ?? 16,
        durationSteps: 600,
        seed: 42,
        scenario,
        policy: "bandit",
      });

      setStage("Running the learned scheduler…");
      await api.startSimulation(sim.id);
      watch(sim.id);

      setStage("Racing it against the fixed sweep…");
      const exp = await api.createExperiment({
        scenario,
        policies: ["baseline", "bandit"],
        episodes: 3,
      });
      await api.runExperiment(exp.id, 500);

      // Poll until the comparison lands. The run streams into the waterfall meanwhile.
      for (let i = 0; i < 200; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        const state = await api.getExperiment(exp.id);
        if (state.status === "completed") {
          setResults(await api.experimentResults(exp.id));
          break;
        }
        if (state.status === "failed" || state.status === "cancelled") {
          throw new Error(`Experiment ${state.status}`);
        }
        if (state.progress) {
          setStage(
            `Racing it against the fixed sweep — ${(state.progress.fraction * 100).toFixed(0)}% (${state.progress.current_policy})`,
          );
        }
      }
      setStage("Done.");
    } catch (e) {
      setError(String(e));
      setStage("Stopped.");
    } finally {
      setRunning(false);
    }
  };

  const liftRows: LiftRow[] = useMemo(() => {
    if (!results) return [];
    const cmp = results.comparison as Record<string, Record<string, { percent: number | null; value: number; reference: number }>>;
    const learned = Object.keys(cmp).find((k) => k !== "reference");
    if (!learned) return [];
    const d = cmp[learned];

    const spec: [string, string, string, boolean, (v: number) => string][] = [
      ["pd", "Spectrum heard", "Share of transmitting band-moments actually observed", true, pct],
      ["hpdr", "High-priority heard", "Same, restricted to high-priority emitters", true, pct],
      ["scan_efficiency", "Listening efficiency", "Share of listening time spent on a live band", true, pct],
      ["ait", "Reaction time", "How fast it catches a burst once it finds one", false, steps],
      ["run_intercept_rate", "Distinct bursts caught", "Share of separate transmissions caught at least once", true, pct],
    ];

    return spec
      .filter(([k]) => d[k] && d[k].percent !== null)
      .map(([k, label, gloss, higherIsBetter, format]) => ({
        label,
        gloss,
        percent: d[k].percent as number,
        value: d[k].value,
        reference: d[k].reference,
        higherIsBetter,
        format,
      }));
  }, [results]);

  const metrics = live?.metrics;
  const counters = live?.counters;

  return (
    <>
      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Live receiver</p>
            <h2>What the receiver is hearing</h2>
            <p className="note">
              Frequency runs across, time runs down, newest at the top. The bracket is the
              receiver&rsquo;s aperture — the only bands it can hear at this instant. Everything
              amber is a transmission going past uncaught.
            </p>
          </div>
          <div className="controls">
            <label className="field">
              Scenario
              <select
                value={scenario}
                disabled={running}
                onChange={(e) => setScenario(e.target.value as ScenarioId)}
              >
                {["A", "B", "C", "D", "E", "F", "G"].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <button className="primary" disabled={running} onClick={() => void runDemo()}>
              {running ? "Running…" : "Run the demo"}
            </button>
          </div>
        </div>

        <div className="panel">
          <Waterfall frames={frames} bands={bands} />
        </div>

        {(stage || activeSimulationId) && (
          <p className="note mono" style={{ marginTop: 10 }}>
            {stage} {activeSimulationId && `· ${activeSimulationId} · socket ${connection}`}
          </p>
        )}
      </section>

      <section className="section">
        <p className="eyebrow">This run</p>
        <p className="note" style={{ marginBottom: 12 }}>
          One run of the learned scheduler. High-priority detection is left to the comparison
          below, where it is averaged over several runs — over a single run it swings on the luck
          of where two or three high-priority emitters happened to sit.
        </p>
        <div className="tiles">
          <Tile
            label="Spectrum heard"
            value={metrics ? pct(metrics.pd) : "—"}
            sub="of all transmitting band-moments"
          />
          <Tile
            label="False alarms"
            value={counters ? String(counters.false_alarms) : "—"}
            sub="heard something that was not there"
          />
          <Tile
            label="Listening efficiency"
            value={metrics ? pct(metrics.scan_efficiency) : "—"}
            sub="time spent on a live band"
          />
          <Tile
            label="Interceptions"
            value={counters ? counters.detections.toLocaleString() : "—"}
            sub="transmissions caught so far"
          />
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Head to head</p>
            <h2>Learned scheduler vs the fixed sweep</h2>
            <p className="note">
              Both run the same scenario on the same seeds, so the spectrum is identical and the
              only difference is where each chose to listen.
            </p>
          </div>
        </div>

        {results ? (
          <>
            <div className="panel">
              <LiftChart rows={liftRows} referenceName="fixed sweep" />
            </div>

            <details style={{ marginTop: 14 }}>
              <summary style={{ cursor: "pointer", color: "var(--ink-muted)", fontSize: "0.88rem" }}>
                Show the underlying numbers
              </summary>
              <div className="panel" style={{ marginTop: 10 }}>
                <ComparisonTable
                  policies={results.policies as unknown as Record<string, Record<string, number>>}
                  metrics={TABLE_METRICS}
                />
                <p className="note" style={{ marginTop: 12 }}>
                  Compare policies on <span className="mono">intercept time, all bursts</span>,
                  not on <span className="mono">caught only</span>. The second averages just the
                  bursts a policy managed to catch, so a scheduler that catches more of the hard
                  ones scores worse on it.
                </p>
              </div>
            </details>
          </>
        ) : (
          <p className="empty">
            Press <strong>Run the demo</strong> to race the learned scheduler against the sweep.
          </p>
        )}
      </section>

      {ready && (ready.ml_scheduler === "down" || ready.ml_periodicity === "down") && (
        <p className="alert">
          An ML service is unreachable, so the scheduler is falling back to a fixed sweep. Results
          below will understate it. Start Ai-ml-1 on :8500 and Ai-ml-2 on :8600.
        </p>
      )}
    </>
  );
}

function Tile({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      <div className="tile-sub">{sub}</div>
    </div>
  );
}

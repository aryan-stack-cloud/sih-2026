import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { policyLabel } from "../lib/policyLabels";
import { StatusDot } from "../components/StatusDot";
import { PolicyRunDetails } from "../components/PolicyRunDetails";
import { POLICY_TYPES, SCENARIO_IDS } from "../types/contract";
import type { PolicyType, ScenarioId } from "../types/contract";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const steps = (v: number) => `${v.toFixed(1)} steps`;

type MetricKey =
  | "pd" | "pfa" | "ait" | "ait_censored"
  | "hpdr" | "scan_efficiency" | "run_intercept_rate" | "interception_ratio";

/** Same keys and labels as the Dashboard's head-to-head table - one vocabulary for these
    metrics everywhere a judge might see them. */
const METRICS: { key: MetricKey; label: string; format: (v: number) => string; higherIsBetter: boolean }[] = [
  { key: "pd", label: "Detection rate (Pd)", format: pct, higherIsBetter: true },
  { key: "pfa", label: "False-alarm rate (Pfa)", format: pct, higherIsBetter: false },
  { key: "ait", label: "Intercept time, caught only", format: steps, higherIsBetter: false },
  { key: "ait_censored", label: "Intercept time, all bursts", format: steps, higherIsBetter: false },
  { key: "hpdr", label: "High-priority detection", format: pct, higherIsBetter: true },
  { key: "scan_efficiency", label: "Listening efficiency", format: pct, higherIsBetter: true },
  { key: "run_intercept_rate", label: "Distinct bursts caught", format: pct, higherIsBetter: true },
  { key: "interception_ratio", label: "Emitters seen at least once", format: pct, higherIsBetter: true },
];

// Raw AIT rewards a policy for catching fewer, harder runs (see the note below the table), so
// it never gets a winner highlight even though it still gets a row.
const NO_WINNER_HIGHLIGHT = new Set<MetricKey>(["ait"]);

/**
 * Experiments - the baseline-vs-ML comparison, and the judge-facing view.
 *
 * The table shows raw AIT and censored AIT side by side rather than picking one. They can point
 * in opposite directions, and that is not a bug: raw AIT only averages the activation runs a
 * policy actually caught, so a policy that intercepts more runs scores worse on it. Showing only
 * the flattering one would misrepresent the result.
 */
export function ExperimentsPage() {
  const { experiments, results, refreshExperiments, loadResults, clearResults, setError } = useStore();

  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [policies, setPolicies] = useState<PolicyType[]>(["random", "baseline", "bandit"]);
  const [episodes, setEpisodes] = useState(3);
  const [durationSteps, setDurationSteps] = useState(400);
  const [busy, setBusy] = useState(false);
  const [loadingResultsId, setLoadingResultsId] = useState<string | null>(null);

  useEffect(() => {
    void refreshExperiments();
    const timer = setInterval(() => void refreshExperiments(), 3000);
    return () => clearInterval(timer);
  }, [refreshExperiments]);

  const toggle = (p: PolicyType) =>
    setPolicies((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]));

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refreshExperiments();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Configure</p>
            <h2>Create an experiment</h2>
            <p className="note">
              Runs every selected policy on identical seeds so the comparison is fair. Section 13
              asks for at least 20 episodes per policy for statistical stability — fewer runs
              faster, but under-powers the comparison.
            </p>
          </div>
        </div>

        <div className="controls">
          <label className="field">
            Scenario
            <select value={scenario} onChange={(e) => setScenario(e.target.value as ScenarioId)}>
              {SCENARIO_IDS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Episodes
            <input
              type="number"
              value={episodes}
              style={{ width: 60 }}
              min={1}
              onChange={(e) => setEpisodes(Number(e.target.value))}
            />
          </label>
          <label className="field">
            Steps
            <input
              type="number"
              value={durationSteps}
              style={{ width: 80 }}
              min={1}
              onChange={(e) => setDurationSteps(Number(e.target.value))}
            />
          </label>
          <button
            className="primary"
            disabled={busy || policies.length === 0 || !Number.isInteger(episodes) || episodes < 1}
            onClick={() => void act(() => api.createExperiment({ scenario, policies, episodes }))}
          >
            Create
          </button>
        </div>

        <div className="controls controls-secondary">
          <span className="eyebrow">Policies</span>
          {POLICY_TYPES.map((p) => (
            <label key={p} className="field">
              <input type="checkbox" checked={policies.includes(p)} onChange={() => toggle(p)} />
              {policyLabel(p)}
            </label>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Catalogue</p>
            <h2>Experiments</h2>
          </div>
        </div>

        {experiments.length === 0 ? (
          <p className="empty">No experiments yet — create one above to compare policies.</p>
        ) : (
          <div className="panel panel-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Scenario</th>
                  <th>Policies</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((e) => (
                  <tr key={e.id}>
                    <td className="mono">{e.id}</td>
                    <td>{e.scenario}</td>
                    <td>
                      {Array.isArray(e.policies)
                        ? e.policies.map(policyLabel).join(", ")
                        : String(e.policies)}
                    </td>
                    <td>
                      <StatusDot tone={e.status === "completed" ? "good" : e.status === "failed" ? "bad" : "neutral"}>
                        {e.status}
                      </StatusDot>
                    </td>
                    <td>
                      {e.progress ? (
                        <>
                          <div className="progress">
                            <div className="progress-bar" style={{ width: `${e.progress.fraction * 100}%` }} />
                          </div>
                          <span className="mono progress-caption">
                            {(e.progress.fraction * 100).toFixed(0)}% · {policyLabel(e.progress.current_policy)}
                          </span>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          disabled={busy || e.status === "running" || !Number.isInteger(durationSteps) || durationSteps < 1}
                          onClick={() => void act(async () => {
                            await api.runExperiment(e.id, durationSteps);
                            clearResults(e.id);
                          })}
                        >
                          Run
                        </button>
                        <button disabled={busy || e.status !== "running"} onClick={() => void act(() => api.stopExperiment(e.id))}>
                          Stop
                        </button>
                        <button
                          disabled={loadingResultsId === e.id || e.status !== "completed"}
                          onClick={async () => {
                            setLoadingResultsId(e.id);
                            try {
                              await loadResults(e.id);
                            } finally {
                              setLoadingResultsId(null);
                            }
                          }}
                        >
                          {loadingResultsId === e.id ? "Loading…" : "Results"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Object.entries(results).map(([id, r]) => {
        const names = Object.keys(r.policies);
        return (
          <section className="section" key={id}>
            <div className="section-head">
              <div>
                <p className="eyebrow">Results</p>
                <h2>
                  {r.scenario_name}{" "}
                  <span className="mono heading-id">
                    {id}
                  </span>
                </h2>
                <p className="note">
                  {r.episodes} episodes × {r.duration_steps} steps, seeds [{r.seeds.join(", ")}].{" "}
                  <em>{r.expected_outcome}</em>
                </p>
              </div>
            </div>

            <div className="panel panel-scroll">
              <table className="data metric-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    {names.map((n) => (
                      <th key={n}>{policyLabel(n)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRICS.map((m) => {
                    const values = names.map((n) => r.policies[n]?.[m.key]);
                    const finite = values.filter((v): v is number => typeof v === "number" && Number.isFinite(v));
                    const best = m.higherIsBetter ? Math.max(...finite) : Math.min(...finite);
                    const canHighlight = finite.length > 1 && !NO_WINNER_HIGHLIGHT.has(m.key);
                    return (
                      <tr key={m.key}>
                        <td>{m.label}</td>
                        {values.map((v, i) => (
                          <td
                            key={names[i]}
                            style={canHighlight && v === best ? { color: "var(--better)", fontWeight: 600 } : undefined}
                          >
                            {typeof v === "number" && Number.isFinite(v) ? m.format(v) : "—"}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <PolicyRunDetails policies={r.policies} />
              {r.episodes < 2 && <p className="note">High-priority detection from one episode is noisy; use multiple episodes for evidence.</p>}

              <div className="legend" style={{ marginTop: 10 }}>
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "var(--better)" }} />
                  Best on that metric
                </span>
              </div>

              <p className="note" style={{ marginTop: 10 }}>
                Compare policies on <strong>intercept time, all bursts</strong>, not{" "}
                <strong>caught only</strong>: the second averages just the runs a
                policy actually caught, so a policy that intercepts more can score worse on it —
                which is why that row alone carries no winner highlight.
              </p>
            </div>
          </section>
        );
      })}
    </>
  );
}

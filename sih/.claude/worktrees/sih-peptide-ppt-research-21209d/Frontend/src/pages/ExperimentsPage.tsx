import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { POLICY_TYPES, SCENARIO_IDS } from "../types/contract";
import type { PolicyType, ScenarioId } from "../types/contract";

const HEADLINE = [
  "pd", "pfa", "ait", "ait_censored", "hpdr",
  "scan_efficiency", "run_intercept_rate", "interception_ratio",
] as const;

/**
 * Experiments - the baseline-vs-ML comparison, and the judge-facing view.
 *
 * The table shows raw AIT and censored AIT side by side rather than picking one. They can point
 * in opposite directions, and that is not a bug: raw AIT only averages the activation runs a
 * policy actually caught, so a policy that intercepts more runs scores worse on it. Showing only
 * the flattering one would misrepresent the result.
 */
export function ExperimentsPage() {
  const { experiments, results, refreshExperiments, loadResults, setError } = useStore();

  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [policies, setPolicies] = useState<PolicyType[]>(["random", "baseline", "bandit"]);
  const [episodes, setEpisodes] = useState(3);
  const [durationSteps, setDurationSteps] = useState(400);
  const [busy, setBusy] = useState(false);

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
    <section>
      <h2>Create an experiment</h2>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <label>
          scenario{" "}
          <select value={scenario} onChange={(e) => setScenario(e.target.value as ScenarioId)}>
            {SCENARIO_IDS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <span>
          policies:{" "}
          {POLICY_TYPES.map((p) => (
            <label key={p} style={{ marginRight: 6 }}>
              <input type="checkbox" checked={policies.includes(p)} onChange={() => toggle(p)} />
              {p}
            </label>
          ))}
        </span>
        <label>
          episodes{" "}
          <input type="number" value={episodes} style={{ width: 60 }}
                 onChange={(e) => setEpisodes(Number(e.target.value))} />
        </label>
        <label>
          steps{" "}
          <input type="number" value={durationSteps} style={{ width: 80 }}
                 onChange={(e) => setDurationSteps(Number(e.target.value))} />
        </label>
        <button
          disabled={busy || policies.length === 0}
          onClick={() => void act(() => api.createExperiment({ scenario, policies, episodes }))}
        >
          create
        </button>
      </div>
      <p style={{ fontSize: "0.85em", color: "#555" }}>
        Section 13 asks for at least 20 episodes per policy for statistical stability. Lower
        values run faster but the comparison is under-powered.
      </p>

      <h2>Experiments</h2>
      <table border={1} cellPadding={4} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr><th>id</th><th>scenario</th><th>policies</th><th>status</th>
              <th>progress</th><th>actions</th></tr>
        </thead>
        <tbody>
          {experiments.length === 0 && <tr><td colSpan={6}>none yet</td></tr>}
          {experiments.map((e) => (
            <tr key={e.id}>
              <td><code>{e.id}</code></td>
              <td>{e.scenario}</td>
              <td>{Array.isArray(e.policies) ? e.policies.join(", ") : String(e.policies)}</td>
              <td>{e.status}</td>
              <td>
                {e.progress
                  ? `${(e.progress.fraction * 100).toFixed(0)}% (${e.progress.current_policy})`
                  : "-"}
              </td>
              <td style={{ whiteSpace: "nowrap" }}>
                <button disabled={busy}
                        onClick={() => void act(() => api.runExperiment(e.id, durationSteps))}>
                  run
                </button>{" "}
                <button disabled={busy} onClick={() => void act(() => api.stopExperiment(e.id))}>
                  stop
                </button>{" "}
                <button onClick={() => void loadResults(e.id)}>results</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {Object.entries(results).map(([id, r]) => {
        const names = Object.keys(r.policies);
        return (
          <div key={id} style={{ marginTop: 20 }}>
            <h3>{r.scenario_name} <code>{id}</code></h3>
            <p style={{ fontSize: "0.9em", color: "#555" }}>
              {r.episodes} episodes x {r.duration_steps} steps, seeds [{r.seeds.join(", ")}].{" "}
              <em>{r.expected_outcome}</em>
            </p>
            <table border={1} cellPadding={4} style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr><th>metric</th>{names.map((n) => <th key={n}>{n}</th>)}</tr>
              </thead>
              <tbody>
                {HEADLINE.map((m) => (
                  <tr key={m}>
                    <td>{m}</td>
                    {names.map((n) => (
                      <td key={n} style={{ textAlign: "right" }}>
                        {Number(r.policies[n][m] ?? 0).toFixed(4)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: "0.85em", color: "#555", maxWidth: 720 }}>
              Compare policies on <code>ait_censored</code>, not <code>ait</code>: raw AIT only
              averages the runs a policy actually caught, so the policy that intercepts more runs
              can score worse on it.
            </p>
          </div>
        );
      })}
    </section>
  );
}

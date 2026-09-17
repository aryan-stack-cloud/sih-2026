import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { POLICY_TYPES, SCENARIO_IDS } from "../types/contract";
import type { PolicyType, ScenarioId } from "../types/contract";

/** Simulation CRUD and lifecycle: POST/GET/PUT/DELETE plus start, stop and reset. */
export function SimulationsPage({ onWatch }: { onWatch: () => void }) {
  const { simulations, scenarios, refreshSimulations, refreshScenarios, watch, setError } =
    useStore();

  const [name, setName] = useState("Demo run");
  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [policy, setPolicy] = useState<PolicyType>("bandit");
  const [durationSteps, setDurationSteps] = useState(400);
  const [seed, setSeed] = useState(42);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void refreshSimulations();
    void refreshScenarios();
  }, [refreshSimulations, refreshScenarios]);

  const selected = scenarios.find((s) => s.id === scenario);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refreshSimulations();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h2>Create a simulation</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <label>
          name <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          scenario{" "}
          <select value={scenario} onChange={(e) => setScenario(e.target.value as ScenarioId)}>
            {SCENARIO_IDS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          policy{" "}
          <select value={policy} onChange={(e) => setPolicy(e.target.value as PolicyType)}>
            {POLICY_TYPES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </label>
        <label>
          steps{" "}
          <input
            type="number"
            value={durationSteps}
            onChange={(e) => setDurationSteps(Number(e.target.value))}
            style={{ width: 90 }}
          />
        </label>
        <label>
          seed{" "}
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
            style={{ width: 80 }}
          />
        </label>
        <button
          disabled={busy}
          onClick={() =>
            void act(() =>
              api.createSimulation({
                name,
                bands: selected?.bands ?? 16,
                durationSteps,
                seed,
                scenario,
                policy,
              }),
            )
          }
        >
          create
        </button>
      </div>
      {selected && (
        <p style={{ color: "#555", fontSize: "0.9em" }}>
          {selected.name}: {selected.bands} bands, {selected.emitters} emitters.{" "}
          <em>{selected.expected_outcome}</em>
        </p>
      )}

      <h2>Simulations</h2>
      <button onClick={() => void refreshSimulations()}>refresh</button>
      <table border={1} cellPadding={4} style={{ borderCollapse: "collapse", marginTop: 8 }}>
        <thead>
          <tr>
            <th>id</th><th>name</th><th>scenario</th><th>policy</th>
            <th>status</th><th>step</th><th>actions</th>
          </tr>
        </thead>
        <tbody>
          {simulations.length === 0 && (
            <tr><td colSpan={7}>none yet</td></tr>
          )}
          {simulations.map((s) => (
            <tr key={s.id}>
              <td><code>{s.id}</code></td>
              <td>{s.name}</td>
              <td>{s.scenario_id ?? "-"}</td>
              <td>{s.policy_type}</td>
              <td>{s.status}</td>
              <td>{s.current_step}/{s.duration_steps}</td>
              <td style={{ whiteSpace: "nowrap" }}>
                <button disabled={busy} onClick={() => void act(() => api.startSimulation(s.id))}>
                  start
                </button>{" "}
                <button disabled={busy} onClick={() => void act(() => api.stopSimulation(s.id))}>
                  stop
                </button>{" "}
                <button disabled={busy} onClick={() => void act(() => api.resetSimulation(s.id))}>
                  reset
                </button>{" "}
                <button disabled={busy} onClick={() => void act(() => api.deleteSimulation(s.id))}>
                  delete
                </button>{" "}
                <button onClick={() => { watch(s.id); onWatch(); }}>watch</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

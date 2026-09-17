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
    <div className="simulation-workspace">
      <section className="section" aria-labelledby="create-simulation-heading">
        <div className="section-head">
          <div>
            <p className="eyebrow">Simulation harness</p>
            <h2 id="create-simulation-heading">Create a simulation</h2>
            <p className="note">
              Configure a repeatable scenario, then start and inspect it from the run catalogue.
            </p>
          </div>
        </div>

        <div className="panel" aria-busy={busy}>
          <div className="controls simulation-form">
            <label className="field">
              <span>Run name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="field">
              <span>Scenario</span>
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value as ScenarioId)}
              >
                {SCENARIO_IDS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Policy</span>
              <select value={policy} onChange={(e) => setPolicy(e.target.value as PolicyType)}>
                {POLICY_TYPES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Steps</span>
              <input
                type="number"
                value={durationSteps}
                onChange={(e) => setDurationSteps(Number(e.target.value))}
              />
            </label>
            <label className="field">
              <span>Seed</span>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </label>
            <button
              className="primary"
              type="button"
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
              Create simulation
            </button>
          </div>

          {selected && (
            <p className="note simulation-scenario-note" aria-live="polite">
              <strong>Scenario {selected.id} · {selected.name}</strong>
              {" · "}{selected.bands} bands · {selected.emitters} emitters. Expected: {" "}
              <em>{selected.expected_outcome}</em>
            </p>
          )}
        </div>
      </section>

      <section className="section" aria-labelledby="simulation-catalogue-heading">
        <div className="section-head">
          <div>
            <p className="eyebrow">Run catalogue</p>
            <h2 id="simulation-catalogue-heading">Simulations</h2>
            <p className="note">Manage lifecycle actions or open a run in the raw stream view.</p>
          </div>
          <div className="controls">
            <span className="mono simulation-count">
              {simulations.length} {simulations.length === 1 ? "run" : "runs"}
            </span>
            <button type="button" onClick={() => void refreshSimulations()}>
              Refresh list
            </button>
          </div>
        </div>

        <div className="panel simulation-table-panel" aria-busy={busy}>
          <div className="simulation-table-scroll">
            <table className="data simulation-table" aria-labelledby="simulation-catalogue-heading">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Status</th>
                  <th scope="col">Scenario</th>
                  <th scope="col">Policy</th>
                  <th scope="col">Progress</th>
                  <th scope="col">ID</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {simulations.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty">No simulations yet. Create a run above to begin.</div>
                    </td>
                  </tr>
                )}
                {simulations.map((simulation) => (
                  <tr key={simulation.id}>
                    <td className="simulation-name">{simulation.name}</td>
                    <td>{simulation.status}</td>
                    <td>{simulation.scenario_id ?? "—"}</td>
                    <td>{simulation.policy_type}</td>
                    <td className="mono">
                      {simulation.current_step} / {simulation.duration_steps}
                    </td>
                    <td>
                      <code className="simulation-id" title={simulation.id}>{simulation.id}</code>
                    </td>
                    <td>
                      <div
                        className="controls simulation-row-actions"
                        role="group"
                        aria-label={`Actions for ${simulation.name}`}
                      >
                        <button
                          type="button"
                          disabled={busy}
                          aria-label={`Start ${simulation.name}`}
                          onClick={() => void act(() => api.startSimulation(simulation.id))}
                        >
                          Start
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          aria-label={`Stop ${simulation.name}`}
                          onClick={() => void act(() => api.stopSimulation(simulation.id))}
                        >
                          Stop
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          aria-label={`Reset ${simulation.name}`}
                          onClick={() => void act(() => api.resetSimulation(simulation.id))}
                        >
                          Reset
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            watch(simulation.id);
                            onWatch();
                          }}
                        >
                          Watch stream
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          aria-label={`Delete ${simulation.name}`}
                          onClick={() => void act(() => api.deleteSimulation(simulation.id))}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

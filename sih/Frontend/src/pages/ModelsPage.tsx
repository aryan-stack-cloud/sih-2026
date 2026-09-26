import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { policyLabel } from "../lib/policyLabels";
import { StatusDot } from "../components/StatusDot";
import { SCENARIO_IDS } from "../types/contract";
import type { ModelMetadata, ScenarioId } from "../types/contract";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const seedRange = (m: ModelMetadata) =>
  m.seed_range ? `${m.seed_range[0]}–${m.seed_range[1]}` : "—";

const trainedOn = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};

/**
 * Model registry, proxied by the Backend onto Ai-ml-1.
 *
 * Training is asynchronous: POST returns a job id and the status endpoint reports
 * `detail.phase` as `training` then `evaluating`. Both phases are shown, because evaluation runs
 * 20 episodes and can take longer than the training itself - a bar that sat at 100% through it
 * would look like a hang.
 */
export function ModelsPage() {
  const { models, trainingJob, refreshModels, startTraining, setError } = useStore();
  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [algorithm, setAlgorithm] = useState("bandit");
  const [episodes, setEpisodes] = useState(5);

  // Job tracking lives in the store, not here - so it survives switching away from this tab and
  // back mid-training (this component unmounts on every tab change; a local useState would not).
  useEffect(() => { void refreshModels(); }, [refreshModels]);

  const training = trainingJob?.status === "running";

  return (
    <>
      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Train</p>
            <h2>Train a model</h2>
            <p className="note">
              Train a policy for a scenario, then compare it on held-out seeds. DQN and PPO take
              longer to train than Bandit and Q-learning.
            </p>
          </div>
        </div>

        <div className="controls">
          <label className="field">
            Algorithm
            <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
              <option value="bandit">Bandit</option>
              <option value="q_learning">Q-Learning</option>
              <option value="dqn">DQN</option>
              <option value="ppo">PPO</option>
            </select>
          </label>
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
              onChange={(e) => setEpisodes(Number(e.target.value))}
            />
          </label>
          <button
            className="primary"
            disabled={training}
            onClick={() => void startTraining({ algorithm, scenario, episodeCount: episodes })}
          >
            {training ? "Training…" : "Train"}
          </button>
        </div>

        {trainingJob && (
          <div className="panel" style={{ marginTop: 14 }}>
            <div className="section-head">
              <span className="mono text-muted">
                Job {trainingJob.id}
                {trainingJob.phase && ` · ${trainingJob.phase}`}
              </span>
              <StatusDot
                tone={trainingJob.status === "failed" ? "bad" : trainingJob.status === "running" ? "neutral" : "good"}
              >
                {trainingJob.status}
              </StatusDot>
            </div>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${trainingJob.progress * 100}%` }} />
            </div>
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Registry</p>
            <h2>Registered models</h2>
            <p className="note">
              A model can only serve scenarios with its band count. When a run starts, the
              scheduler picks a model of that band count trained on the run&rsquo;s own scenario
              first, then the active one. Seed ranges are shown when the registry recorded them.
            </p>
          </div>
          <div className="controls">
            <button onClick={() => void refreshModels()}>Refresh</button>
          </div>
        </div>

        {models.length === 0 ? (
          <p className="empty">No models registered yet — train one above.</p>
        ) : (
          <div className="panel panel-scroll">
            <table className="data">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Algorithm</th>
                  <th>Ver</th>
                  <th>Scenario</th>
                  <th>Bands</th>
                  <th>Trained</th>
                  <th>Seeds</th>
                  <th>Pd</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.model_id}>
                    <td className="mono">{m.model_id}</td>
                    <td>{policyLabel(m.algorithm)}</td>
                    <td>{m.version}</td>
                    <td>{m.scenario ?? "—"}</td>
                    <td>{m.num_bands ?? "—"}</td>
                    <td>{trainedOn(m.created_at)}</td>
                    <td className="mono">{seedRange(m)}</td>
                    <td>{typeof m.metrics?.pd === "number" ? pct(m.metrics.pd as number) : "—"}</td>
                    <td>
                      {m.active ? (
                        <StatusDot tone="good">active</StatusDot>
                      ) : (
                        <span className="mono text-faint">—</span>
                      )}
                    </td>
                    <td>
                      {!m.active && (
                        <button
                          onClick={async () => {
                            const ok = window.confirm(
                              `Activate ${policyLabel(m.algorithm)} model ${m.model_id}? ` +
                                "It becomes the default for new runs whose scenario has no " +
                                "model of its own with the same band count.",
                            );
                            if (!ok) return;
                            try {
                              await api.activateModel(m.model_id);
                              await refreshModels();
                            } catch (e) {
                              setError(String(e));
                            }
                          }}
                        >
                          Activate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { SCENARIO_IDS } from "../types/contract";
import type { ModelMetadata, ScenarioId } from "../types/contract";

/**
 * Model registry, proxied by the Backend onto Ai-ml-1.
 *
 * Training is asynchronous: POST returns a job id and the status endpoint reports
 * `detail.phase` as `training` then `evaluating`. Both phases are shown, because evaluation runs
 * 20 episodes and can take longer than the training itself - a bar that sat at 100% through it
 * would look like a hang.
 */
export function ModelsPage() {
  const { setError } = useStore();
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [algorithm, setAlgorithm] = useState("bandit");
  const [episodes, setEpisodes] = useState(5);
  const [job, setJob] = useState<{ id: string; status: string; progress: number; phase: string } | null>(null);

  const refresh = async () => {
    try {
      setModels(await api.listModels());
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => { void refresh(); }, []);

  useEffect(() => {
    if (!job || job.status !== "running") return;
    const timer = setInterval(async () => {
      try {
        const s = await api.trainStatus(job.id);
        setJob({
          id: job.id,
          status: s.status,
          progress: s.progress,
          phase: String((s.detail as Record<string, unknown>)?.phase ?? ""),
        });
        if (s.status !== "running") void refresh();
      } catch (e) {
        setError(String(e));
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [job, setError]);

  return (
    <section>
      <h2>Train a model</h2>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <label>
          algorithm{" "}
          <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
            <option value="bandit">bandit</option>
            <option value="q_learning">q_learning</option>
            <option value="dqn">dqn</option>
            <option value="ppo">ppo</option>
          </select>
        </label>
        <label>
          scenario{" "}
          <select value={scenario} onChange={(e) => setScenario(e.target.value as ScenarioId)}>
            {SCENARIO_IDS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label>
          episodes{" "}
          <input type="number" value={episodes} style={{ width: 60 }}
                 onChange={(e) => setEpisodes(Number(e.target.value))} />
        </label>
        <button
          onClick={async () => {
            try {
              const r = await api.trainModel({ algorithm, scenario, episodeCount: episodes });
              setJob({ id: r.job_id, status: "running", progress: 0, phase: "" });
            } catch (e) {
              setError(String(e));
            }
          }}
        >
          train
        </button>
      </div>
      <p style={{ fontSize: "0.85em", color: "#555" }}>
        DQN and PPO are a V2 stretch goal, gated behind the bandit beating the baseline; the ML
        service will train them but the ladder exists for a reason.
      </p>

      {job && (
        <p>
          job <code>{job.id}</code>: {job.status} - {(job.progress * 100).toFixed(0)}%
          {job.phase && ` (${job.phase})`}
        </p>
      )}

      <h2>Registered models</h2>
      <button onClick={() => void refresh()}>refresh</button>
      <table border={1} cellPadding={4} style={{ borderCollapse: "collapse", marginTop: 8 }}>
        <thead>
          <tr><th>model_id</th><th>algorithm</th><th>v</th><th>active</th>
              <th>scenario</th><th>Pd</th><th></th></tr>
        </thead>
        <tbody>
          {models.length === 0 && <tr><td colSpan={7}>none registered</td></tr>}
          {models.map((m) => (
            <tr key={m.model_id}>
              <td><code>{m.model_id}</code></td>
              <td>{m.algorithm}</td>
              <td>{m.version}</td>
              <td>{m.active ? "yes" : ""}</td>
              <td>{m.scenario ?? "-"}</td>
              <td style={{ textAlign: "right" }}>
                {typeof m.metrics?.pd === "number" ? (m.metrics.pd as number).toFixed(4) : "-"}
              </td>
              <td>
                <button
                  onClick={async () => {
                    try {
                      await api.activateModel(m.model_id);
                      await refresh();
                    } catch (e) {
                      setError(String(e));
                    }
                  }}
                >
                  activate
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

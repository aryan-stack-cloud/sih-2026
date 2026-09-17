import { useEffect, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { SCENARIO_IDS } from "../types/contract";
import type { ModelMetadata, ScenarioId } from "../types/contract";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const ALGO_LABELS: Record<string, string> = {
  baseline: "Baseline (fixed sweep)",
  random: "Random",
  bandit: "Bandit",
  q_learning: "Q-Learning",
  dqn: "DQN",
  ppo: "PPO",
  index: "Index (Search-Confirm-Track)",
  ctmc: "CTMC (randomised floor)",
};
const algoLabel = (a: string) => ALGO_LABELS[a] ?? a;

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
    <>
      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Train</p>
            <h2>Train a model</h2>
            <p className="note">
              DQN and PPO are a V2 stretch goal, gated behind the bandit beating the baseline; the
              ML service will train them but the ladder exists for a reason.
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
            onClick={async () => {
              try {
                const r = await api.trainModel({ algorithm, scenario, episodeCount: episodes });
                setJob({ id: r.job_id, status: "running", progress: 0, phase: "" });
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            Train
          </button>
        </div>

        {job && (
          <div className="panel" style={{ marginTop: 14 }}>
            <div className="section-head" style={{ marginBottom: 10 }}>
              <span className="mono" style={{ fontSize: "0.8rem", color: "var(--ink-muted)" }}>
                Job {job.id}
                {job.phase && ` · ${job.phase}`}
              </span>
              <StatusDot tone={job.status === "failed" ? "bad" : job.status === "running" ? "neutral" : "good"}>
                {job.status}
              </StatusDot>
            </div>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${job.progress * 100}%` }} />
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
              Every checkpoint carries the seed range it trained on, so a result can be traced
              back to the exact run that produced it.
            </p>
          </div>
          <div className="controls">
            <button onClick={() => void refresh()}>Refresh</button>
          </div>
        </div>

        {models.length === 0 ? (
          <p className="empty">No models registered yet — train one above.</p>
        ) : (
          <div className="panel" style={{ overflowX: "auto" }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Algorithm</th>
                  <th>Ver</th>
                  <th>Scenario</th>
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
                    <td>{algoLabel(m.algorithm)}</td>
                    <td>{m.version}</td>
                    <td>{m.scenario ?? "—"}</td>
                    <td>{trainedOn(m.created_at)}</td>
                    <td className="mono">{seedRange(m)}</td>
                    <td>{typeof m.metrics?.pd === "number" ? pct(m.metrics.pd as number) : "—"}</td>
                    <td>
                      {m.active ? (
                        <StatusDot tone="good">active</StatusDot>
                      ) : (
                        <span className="mono" style={{ color: "var(--ink-faint)" }}>—</span>
                      )}
                    </td>
                    <td>
                      {!m.active && (
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

function StatusDot({ tone, children }: { tone: "good" | "bad" | "neutral"; children: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span className={`status-dot${tone === "neutral" ? "" : ` ${tone}`}`} />
      <span style={{ fontSize: "0.78rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {children}
      </span>
    </span>
  );
}

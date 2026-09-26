import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "../services/api/client";
import { useStore } from "../store/useStore";
import { Waterfall } from "../components/Waterfall";
import { ComparisonTable, LiftChart } from "../components/LiftChart";
import { fellBackToSweep, PolicyRunDetails } from "../components/PolicyRunDetails";
import type { LiftRow } from "../components/LiftChart";
import { POLICY_LABELS as CHALLENGER_LABELS } from "../lib/policyLabels";
import { POLICY_TYPES } from "../types/contract";
import type { ExperimentResults, MetricsSummary, ModelMetadata, PolicyType, ScenarioId } from "../types/contract";

/**
 * The judge-facing view, and the 3-5 minute demo of PRD Section 20.4.
 *
 * Three beats in the order a viewer needs them: watch the receiver work, read what it achieved,
 * then see it measured against the sweep it replaces. The scripted run drives all three from one
 * button so the demo does not depend on anyone remembering a sequence under pressure.
 */

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const steps = (v: number) => `${v.toFixed(1)} steps`;
const scenarioName = (name: string) => name.replace(/^[A-G]\s*[-–—:]\s*/, "").trim();

const CHALLENGERS = POLICY_TYPES.filter((p) => p !== "baseline");
const CHECKPOINT_POLICIES: PolicyType[] = ["dqn", "ppo"];

const POLICY_STORY: Record<PolicyType, { category: string; title: string; detail: string }> = {
  baseline: { category: "Reference", title: "Fixed round-robin sweep", detail: "Visits bands in a fixed order without adapting to what it finds." },
  random: { category: "Reference", title: "Randomised scan", detail: "Samples the spectrum without relying on a predictable sweep pattern." },
  ctmc: { category: "Designed scheduler", title: "CTMC floor", detail: "A mathematical random-walk safety floor for uncertain emitters." },
  index: { category: "Designed scheduler", title: "Index scheduler", detail: "Ranks bands by revisit pressure, occupancy belief and threat value." },
  bandit: { category: "Lightweight RL", title: "Contextual bandit", detail: "Learns which band is most worthwhile to scan right now." },
  q_learning: { category: "Lightweight RL", title: "Q-learning", detail: "Learns the future value of choices, not only the immediate reward." },
  dqn: { category: "Deep RL", title: "Deep Q-network", detail: "Uses a neural network to estimate the value of each scanning decision." },
  ppo: { category: "Deep RL", title: "PPO policy", detail: "Uses a neural network to learn the scanning strategy directly." },
};

/** Step delay in ms for each preset; 0 means uncapped (run as fast as the backend can). */
const SPEED_PRESETS: { label: string; stepDelayMs: number }[] = [
  { label: "0.5×", stepDelayMs: 200 },
  { label: "1×", stepDelayMs: 100 },
  { label: "2×", stepDelayMs: 50 },
  { label: "4×", stepDelayMs: 25 },
  { label: "Max", stepDelayMs: 0 },
];

/** One entry per phase runDemo actually goes through, in order. */
const DEMO_STEPS = ["Build spectrum", "Run scheduler", "Compare vs sweep"] as const;

// The Dashboard is a live explanation, not the statistical evaluation workbench. Keeping each
// episode short makes the graph presentation-safe; the Experiments tab retains user-selected,
// long studies for evidence collection.
//
// The race still needs several episodes, though. One 80-step episode is one spectrum layout, and
// whether a learner wins it depends on where that layout happens to put the busy emitters: on
// Scenario B, seed 42 alone had DQN hearing live bands 25% LESS than the sweep, while seeds 42-51
// together had it 66% MORE. Ten short worlds keep the race to seconds and make its sign honest.
const DEMO_LIVE_STEPS = 160;
const DEMO_COMPARISON_EPISODES = 10;
const DEMO_COMPARISON_STEPS = 80;
const SLOW_COMPARISON_NOTICE_SECONDS = 20;

/** Thrown to unwind runDemo's try block when the user cancels mid-run; never surfaced as an error. */
class DemoCancelled extends Error {}

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

type MetricCount = { success: number; total: number };

function countWithTotal(success: unknown, total: unknown): MetricCount | null {
  return typeof success === "number" && typeof total === "number" &&
    Number.isInteger(success) && Number.isInteger(total) && total > 0 &&
    success >= 0 && success <= total ? { success, total } : null;
}

function countWithMisses(success: unknown, misses: unknown): MetricCount | null {
  return typeof success === "number" && typeof misses === "number" &&
    Number.isInteger(success) && Number.isInteger(misses) && misses >= 0
    ? countWithTotal(success, success + misses) : null;
}

function countForMetric(key: string, metrics: MetricsSummary | undefined): MetricCount | null {
  if (!metrics) return null;
  if (key === "pd") return countWithMisses(metrics.counts?.tp, metrics.counts?.fn);
  if (key === "hpdr") return countWithMisses(metrics.tp_high_priority, metrics.fn_high_priority);
  if (key === "run_intercept_rate") return countWithTotal(metrics.detected_runs, metrics.total_runs);
  return null;
}

export function DemoPage() {
  const {
    ready, frames, live, activeSimulationId, connection, watch, unwatch,
    scenarios, refreshScenarios, pollLive, setError,
  } = useStore();

  const [scenario, setScenario] = useState<ScenarioId>("B");
  const [challenger, setChallenger] = useState<PolicyType>("bandit");
  const [stage, setStage] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ExperimentResults | null>(null);
  const [bands, setBands] = useState(16);
  // Deep policies cannot make a valid decision from an empty session. Keep their Dashboard
  // option unavailable unless some registered checkpoint has the selected scenario's band count -
  // Ai-ml-1 serves the best such model (its own scenario's first), and without one it answers
  // 409 and the Backend would fall back to the sweep.
  const [checkpointReady, setCheckpointReady] = useState<Partial<Record<PolicyType, boolean>>>({});
  // Default Max (0 = uncapped) - same behaviour as before this control existed, unless a viewer
  // deliberately slows it down to actually watch it rather than a five-second blur.
  const [speedMs, setSpeedMs] = useState(0);

  // -1 = no run started yet; DEMO_STEPS.length once the whole sequence finished cleanly.
  const [stepIndex, setStepIndex] = useState(-1);
  const [stepFailed, setStepFailed] = useState(false);
  // Determinate fraction for the "Compare vs sweep" phase, reported by the experiment
  // itself. Null everywhere else, where there is no meaningful total to measure against.
  const [raceFraction, setRaceFraction] = useState<number | null>(null);

  // Read inside the async runDemo loop, which a state variable closed over at call time can't do -
  // cancelDemo needs to flip a flag the in-flight run notices on its very next check.
  const cancelledRef = useRef(false);
  const activeRunRef = useRef<{ simulationId?: string; experimentId?: string }>({});
  const requestAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    void refreshScenarios();
  }, [refreshScenarios]);

  const scenarioBands = scenarios.find((s) => s.id === scenario)?.bands;

  useEffect(() => {
    let disposed = false;
    setCheckpointReady({});
    if (scenarioBands === undefined) return () => { disposed = true; };
    const bandsOf = (model: ModelMetadata) =>
      model.num_bands ?? scenarios.find((s) => s.id === model.scenario)?.bands;
    void Promise.all(
      CHECKPOINT_POLICIES.map(async (policy) => {
        const models = await api.listModels(policy);
        return [policy, models.some((model) => bandsOf(model) === scenarioBands)] as const;
      }),
    ).then((entries) => {
      if (!disposed) setCheckpointReady(Object.fromEntries(entries));
    }).catch(() => {
      if (!disposed) setCheckpointReady(Object.fromEntries(CHECKPOINT_POLICIES.map((p) => [p, false])));
    });
    return () => { disposed = true; };
  }, [scenario, scenarioBands, scenarios]);

  const policyAvailable = (policy: PolicyType) =>
    !CHECKPOINT_POLICIES.includes(policy) || checkpointReady[policy] === true;

  useEffect(() => {
    if (!policyAvailable(challenger)) setChallenger("bandit");
  }, [challenger, checkpointReady]);

  const selectedScenario = scenarios.find((s) => s.id === scenario);

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

  const throwIfCancelled = () => {
    if (cancelledRef.current) throw new DemoCancelled();
  };

  const runDemo = async () => {
    cancelledRef.current = false;
    activeRunRef.current = {};
    requestAbortRef.current = new AbortController();
    const requestSignal = requestAbortRef.current.signal;
    setRunning(true);
    setResults(null);
    setStepFailed(false);
    setRaceFraction(null);
    setStepIndex(0);
    try {
      setStage("Building the spectrum…");
      const all = await api.scenarios();
      const chosen = all.find((s) => s.id === scenario);
      setBands(chosen?.bands ?? 16);
      throwIfCancelled();

      const sim = await api.createSimulation({
        name: `Demo ${scenario}`,
        bands: chosen?.bands ?? 16,
        durationSteps: DEMO_LIVE_STEPS,
        seed: 42,
        scenario,
        policy: challenger,
      });
      activeRunRef.current.simulationId = sim.id;
      throwIfCancelled();

      setStepIndex(1);
      setStage(`Running ${CHALLENGER_LABELS[challenger]}…`);
      watch(sim.id);
      await api.startSimulation(sim.id);
      if (speedMs > 0) {
        // Best-effort: a slow/degraded speed endpoint should not derail the demo over a cosmetic
        // pacing setting, so a failure here is swallowed rather than surfaced as a run error.
        void api.setSimulationSpeed(sim.id, speedMs).catch(() => {});
      }
      throwIfCancelled();

      setStepIndex(2);
      setStage("Racing it against the fixed sweep…");
      const exp = await api.createExperiment({
        scenario,
        policies: ["baseline", challenger],
        episodes: DEMO_COMPARISON_EPISODES,
      });
      activeRunRef.current.experimentId = exp.id;
      throwIfCancelled();
      await api.runExperiment(exp.id, DEMO_COMPARISON_STEPS);
      throwIfCancelled();

      // Poll until the comparison lands. The run streams into the waterfall meanwhile.
      let landed = false;
      let waitedSeconds = 0;
      // A valid experiment can take longer on a busy laptop. Keep polling until it either
      // completes, fails, or the viewer presses Cancel; never abandon a completed result before
      // the graph has a chance to render.
      while (!landed) {
        await new Promise((r) => setTimeout(r, 1000));
        throwIfCancelled();
        waitedSeconds++;
        const state = await api.getExperiment(exp.id, requestSignal);
        if (state.status === "completed") {
          setResults(await api.experimentResults(exp.id, requestSignal));
          landed = true;
          break;
        }
        if (state.status === "failed" || state.status === "cancelled") {
          throw new Error(`Experiment ${state.status}`);
        }
        if (state.progress) {
          setRaceFraction(state.progress.fraction);
          setStage(
            waitedSeconds >= SLOW_COMPARISON_NOTICE_SECONDS
              ? `Still calculating — ${(state.progress.fraction * 100).toFixed(0)}%. The graph will appear automatically.`
              : `Racing it against the fixed sweep — ${(state.progress.fraction * 100).toFixed(0)}% (${state.progress.current_policy})`,
          );
        }
      }
      setStage("Done.");
      setStepIndex(DEMO_STEPS.length);
    } catch (e) {
      if (e instanceof DemoCancelled || cancelledRef.current) {
        setStage("Cancelled.");
      } else {
        setStepFailed(true);
        setError(String(e));
        setStage("Stopped.");
      }
    } finally {
      requestAbortRef.current = null;
      setRunning(false);
    }
  };

  const changeSpeed = (stepDelayMs: number) => {
    setSpeedMs(stepDelayMs);
    // Live update: the backend re-reads this every step, so a viewer can slow down or speed up
    // a run that's already in flight instead of only choosing a pace before pressing start.
    const simId = activeRunRef.current.simulationId;
    if (simId && running) {
      void api.setSimulationSpeed(simId, stepDelayMs).catch(() => {});
    }
  };

  const cancelDemo = async () => {
    cancelledRef.current = true;
    requestAbortRef.current?.abort();
    setStage("Cancelling…");
    const { simulationId, experimentId } = activeRunRef.current;
    unwatch();
    // Best-effort: the server-side run stops regardless of whether these land, since the
    // frontend has already stopped watching it either way.
    if (experimentId) await api.stopExperiment(experimentId).catch(() => {});
    if (simulationId) await api.stopSimulation(simulationId).catch(() => {});
  };

  const liftRows: LiftRow[] = useMemo(() => {
    if (!results) return [];
    const cmp = results.comparison;
    const learned = Object.keys(cmp).find((k) => k !== "reference" && typeof cmp[k] === "object");
    if (!learned) return [];
    const d = cmp[learned] as Record<string, { percent: number | null; value: number; reference: number }>;

    const spec: [string, string, string, boolean, (v: number) => string, boolean][] = [
      ["pd", "Spectrum heard", "Share of transmitting band-moments actually observed", true, pct, true],
      ["hpdr", "High-priority heard", "Same, restricted to high-priority emitters", true, pct, true],
      ["scan_efficiency", "Listening efficiency", "Share of listening time spent on a live band", true, pct, false],
      ["ait_censored", "Reaction time, all bursts", "Average steps from a burst starting to first catch; a missed burst counts as the whole run", false, steps, false],
      ["run_intercept_rate", "Distinct bursts caught", "Share of separate transmissions caught at least once", true, pct, true],
    ];

    const referenceName = typeof cmp.reference === "string" ? cmp.reference : "baseline";
    const referenceMetrics = results.policies[referenceName];
    const learnedMetrics = results.policies[learned];

    return spec
      .filter(([k]) => d[k] && typeof d[k].percent === "number" &&
        Number.isFinite(d[k].percent) && Number.isFinite(d[k].value) && Number.isFinite(d[k].reference))
      .map(([k, label, gloss, higherIsBetter, format, requiresCounts]) => {
        const referenceCount = countForMetric(k, referenceMetrics);
        const learnedCount = countForMetric(k, learnedMetrics);
        return {
          label,
          gloss,
          percent: d[k].percent as number,
          value: d[k].value,
          reference: d[k].reference,
          higherIsBetter,
          format,
          requiresCounts,
          counts: referenceCount && learnedCount
            ? { reference: referenceCount, value: learnedCount } : null,
        };
      });
  }, [results]);

  const comparisonPolicy = results && Object.keys(results.comparison).find((k) => k !== "reference");
  const fallbackOnly = comparisonPolicy
    ? fellBackToSweep(comparisonPolicy, results?.policies[comparisonPolicy]) : false;
  const referencePolicy = results && typeof results.comparison.reference === "string"
    ? results.policies[results.comparison.reference] : results?.policies.baseline;
  const highPriorityCount = countForMetric("hpdr", referencePolicy);
  const burstCount = countForMetric("run_intercept_rate", referencePolicy);
  const sampleCaption = results ? [
    `${results.episodes} episode${results.episodes === 1 ? "" : "s"}`,
    `${results.duration_steps} steps${results.episodes === 1 ? "" : " per episode"}`,
    highPriorityCount && `${highPriorityCount.total} high-priority moments`,
    burstCount && `${burstCount.total} bursts`,
  ].filter(Boolean).join(" · ") +
    (results.episodes === 1 ? " — illustrative, not a stable estimate" : "") : "";

  const metrics = live?.metrics;
  const counters = live?.counters;
  const waterfallFrames = frames.length > 0 ? frames : live?.scanned_bands && live.active_bands
    ? [{
        t: live.t,
        activeBands: live.active_bands,
        scannedBands: live.scanned_bands,
        detectedBands: live.detected_bands ?? [],
        falseAlarmBands: [],
      }] : [];
  const spotlight = POLICY_STORY[challenger];
  const apertureStart = live?.scanned_bands?.[0] ?? Math.max(0, Math.floor(bands / 2) - 1);

  return (
    <>
      <section className="mission-hero">
        <div className="mission-copy">
          <p className="eyebrow">Live receiver intelligence</p>
          <p className="mission-number">01 / Observe · Decide · Adapt</p>
          <h2>The spectrum is wide.<br /><em>Your receiver is not.</em></h2>
          <p className="mission-lede">The scheduler makes every listening window count by selecting the next frequency band from information learned in previous scans.</p>
          <div className="mission-badges">
            <span><b>K = 2</b> bands heard at once</span>
            <span><b>{bands}</b> bands under surveillance</span>
          </div>
        </div>
        <div className="aperture-card" aria-label={`Receiver aperture observing bands ${apertureStart + 1} and ${apertureStart + 2} of ${bands}`}>
          <div className="aperture-card-top"><span>Receiver aperture</span><strong>K = 2</strong></div>
          <div className="aperture-ruler" style={{ gridTemplateColumns: `repeat(${bands}, minmax(0, 1fr))` }} aria-hidden="true">
            {Array.from({ length: bands }, (_, band) => (
              <span key={band} className={band === apertureStart || band === (apertureStart + 1) % bands ? "is-observed" : ""}>
                <i /><small>{String(band + 1).padStart(2, "0")}</small>
              </span>
            ))}
          </div>
          <div className="aperture-caption"><span className="aperture-pulse" />Observing the highlighted bands now</div>
        </div>
      </section>

      <section className="section receiver-stage">
        <div className="section-head">
          <div>
            <p className="eyebrow">Configure mission</p>
            <h2>What the receiver is hearing</h2>
            <p className="note">
              Frequency runs across, time runs down, newest at the top. The bracket is the
              receiver&rsquo;s aperture — the only bands it can hear at this instant. Everything
              amber is a transmission going past uncaught.
            </p>
          </div>
          <div className="strategy-spotlight">
            <span>{spotlight.category}</span>
            <strong>{spotlight.title}</strong>
            <p>{spotlight.detail}</p>
          </div>
          <div className="controls mission-controls">
            <label className="field">
              Scenario
              <select
                value={scenario}
                disabled={running}
                onChange={(e) => setScenario(e.target.value as ScenarioId)}
              >
                {["A", "B", "C", "D", "E", "F", "G"].map((s) => {
                  const name = scenarios.find((item) => item.id === s)?.name;
                  return <option key={s} value={s}>{name ? `${s} · ${scenarioName(name)}` : s}</option>;
                })}
              </select>
            </label>
            <label className="field">
              Compare against
              <select
                value={challenger}
                disabled={running}
                onChange={(e) => setChallenger(e.target.value as PolicyType)}
              >
                {CHALLENGERS.map((p) => (
                  <option key={p} value={p} disabled={!policyAvailable(p)}>
                    {CHALLENGER_LABELS[p]}{!policyAvailable(p) ? ` — needs a trained ${scenarioBands ?? ""}-band checkpoint` : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Speed
              <select
                value={speedMs}
                onChange={(e) => changeSpeed(Number(e.target.value))}
              >
                {SPEED_PRESETS.map((s) => (
                  <option key={s.label} value={s.stepDelayMs}>{s.label}</option>
                ))}
              </select>
            </label>
            {running ? (
              <button className="primary" onClick={() => void cancelDemo()}>
                Cancel
              </button>
            ) : (
              <button className="primary" onClick={() => void runDemo()}>
                <span className="button-mark">▶</span> Run live comparison
              </button>
            )}
          </div>
        </div>

        {selectedScenario && (
          <p className="note scenario-description">
            Scenario {selectedScenario.id} — <strong>{scenarioName(selectedScenario.name)}.</strong>{" "}
            {selectedScenario.expected_outcome}
          </p>
        )}

        <div className="panel spectrum-panel">
          <Waterfall frames={waterfallFrames} bands={bands} />
          {frames.length === 0 && waterfallFrames.length > 0 &&
            <p className="note">Latest REST snapshot only; no live spectrum frames were captured.</p>}
          {live?.unavailable_reason &&
            <p className="note" role="status">
              Running the fixed sweep instead: {live.unavailable_reason}
            </p>}
        </div>

        {stepIndex >= 0 && (
          <ol className="step-tracker" aria-label="Demo progress">
            {DEMO_STEPS.map((label, i) => {
              const isCurrent = i === Math.min(stepIndex, DEMO_STEPS.length - 1);
              const state =
                stepFailed && isCurrent && stepIndex < DEMO_STEPS.length
                  ? "error"
                  : i < stepIndex
                    ? "done"
                    : i === stepIndex
                      ? "active"
                      : "pending";
              return (
                <li key={label} className={state} aria-current={state === "active"}>
                  <span className="step-index">{state === "done" ? "✓" : i + 1}</span>
                  {label}
                </li>
              );
            })}
          </ol>
        )}

        {(stage || activeSimulationId) && (
          <div className="demo-status">
            {running && (
              raceFraction !== null ? (
                <progress
                  className="demo-progress"
                  value={raceFraction}
                  max={1}
                  aria-label="Comparison against the fixed sweep"
                />
              ) : (
                <progress className="demo-progress" aria-label={stage || "Demo running"} />
              )
            )}
            <p className="note demo-status-line" role="status">
              <span className={`demo-status-dot${stepFailed ? " is-error" : stage === "Done." ? " is-done" : ""}`} aria-hidden="true" />
              <span>{stage === "Done." ? "Done" : stage === "Cancelled." ? "Cancelled" : stage === "Stopped." ? "Stopped" : stage}
                {activeSimulationId && ` — live run ${activeSimulationId}`}
                {activeSimulationId && connection !== "open" && ` · connection ${connection}`}</span>
            </p>
          </div>
        )}
      </section>

      <section className="section">
        <p className="eyebrow">This run</p>
        <p className="note" style={{ marginBottom: 12 }}>
          The tiles summarize one {DEMO_LIVE_STEPS}-step live run of {CHALLENGER_LABELS[challenger]}.
          The comparison below averages {DEMO_COMPARISON_EPISODES} matched {DEMO_COMPARISON_STEPS}-step episodes.
        </p>
        <div className={`tiles${results ? " results-reveal" : ""}`}>
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
            <h2>{CHALLENGER_LABELS[challenger]} vs the fixed sweep</h2>
            <p className="note">
              Both run the same scenario on the same seeds, so the spectrum is identical and the
              only difference is where each chose to listen.
            </p>
          </div>
        </div>

        {results ? (
          <>
            <div className="panel results-reveal">
              <p className="lift-sample">{sampleCaption}</p>
              {fallbackOnly ? (
                <p className="policy-provenance-alert">Fell back to sweep — no trained model served this scenario. A 0% lift would describe the fallback, not the selected policy.</p>
              ) : <LiftChart rows={liftRows} referenceName="fixed sweep" policyName={comparisonPolicy ? CHALLENGER_LABELS[comparisonPolicy as PolicyType] ?? comparisonPolicy : CHALLENGER_LABELS[challenger]} />}
              {!fallbackOnly && <PolicyRunDetails policies={results.policies} compact />}
            </div>

            <details className="numbers-disclosure">
              <summary>
                <span>Show the underlying numbers</span>
                <small>all 8 metrics for both policies</small>
              </summary>
              <div className="panel panel-scroll" style={{ marginTop: 10 }}>
                <ComparisonTable
                  policies={results.policies as unknown as Record<string, Record<string, unknown>>}
                  metrics={TABLE_METRICS}
                />
                <p className="note" style={{ marginTop: 12 }}>
                  Compare policies on <strong>intercept time, all bursts</strong>,
                  not on <strong>caught only</strong>. The second averages just the
                  bursts a policy managed to catch, so a scheduler that catches more of the hard
                  ones scores worse on it.
                </p>
              </div>
            </details>
          </>
        ) : (
          <p className="empty">
            Press <strong>Run the demo</strong> to race {CHALLENGER_LABELS[challenger]} against
            the fixed sweep.
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

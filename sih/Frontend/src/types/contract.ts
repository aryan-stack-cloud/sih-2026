/**
 * TypeScript mirror of API_CONTRACT.md - Sections 1, 2, 3 and 6.
 *
 * THIS FILE IS A MIRROR, NOT A SOURCE. `API_CONTRACT.md` is the single source of truth and is
 * copied byte-identically into all four domain folders. If a shape has to change, change it there
 * first, propagate to all four copies in the same commit, and tell the Backend owner.
 */

// -- Section 6: shared enums ---------------------------------------------------------------

export const BEHAVIOR_CLASSES = [
  "fixed",
  "periodic",
  "agile",
  "random",
  "intermittent",
] as const;
export type BehaviorClass = (typeof BEHAVIOR_CLASSES)[number];

/** `baseline` and `random` are the two open-loop references; the rest are learned. */
export const POLICY_TYPES = [
  "baseline",
  "random",
  "bandit",
  "q_learning",
  "dqn",
  "ppo",
  "index",
  "ctmc",
] as const;
export type PolicyType = (typeof POLICY_TYPES)[number];

export const SCENARIO_IDS = ["A", "B", "C", "D", "E", "F", "G"] as const;
export type ScenarioId = (typeof SCENARIO_IDS)[number];

export type DetectionType = "TP" | "FN" | "FP" | "TN";

export type SimulationStatus =
  | "draft"
  | "running"
  | "stopped"
  | "completed"
  | "failed";

// -- Section 1: standard envelope -----------------------------------------------------------

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  requestId: string;
}

// -- Section 2: public resources -------------------------------------------------------------

export interface Simulation {
  id: string;
  name: string;
  status: SimulationStatus;
  bands: number;
  duration_steps: number;
  current_step: number;
  seed: number;
  policy_type: PolicyType;
  scenario_id: ScenarioId | null;
  created_at: string;
  live?: LiveSnapshot;
}

export interface CreateSimulationRequest {
  name: string;
  bands: number;
  durationSteps: number;
  seed?: number;
  scenario?: ScenarioId;
  policy?: PolicyType;
}

export interface Paged<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
}

/** Shared by `GET /metrics/live` and the WebSocket reconnect replay - deliberately one shape. */
export interface LiveSnapshot {
  simulation_id: string;
  t: number;
  counters: { detections: number; false_alarms: number; reward: number };
  last_action?: number;
  scanned_bands?: number[];
  active_bands?: number[];
  detected_bands?: number[];
  reward?: number;
  model_id?: string;
  metrics?: MetricsSummary;
  error?: string;
}

export interface MetricsSummary {
  pd: number;
  pfa: number;
  ait: number;
  /**
   * AIT over every activation run, charging undetected ones the full episode.
   *
   * Use this to compare two policies. Raw `ait` only averages the runs a policy actually caught,
   * so a policy that intercepts more runs reports a worse `ait` - the extra runs it caught are
   * the hard, late ones the weaker policy missed entirely.
   */
  ait_censored: number;
  hpdr: number;
  median_latency: number;
  interception_ratio: number;
  scan_efficiency: number;
  precision: number;
  recall: number;
  f1: number;
  coverage: number;
  miss_rate: number;
  run_intercept_rate: number;
  detected_runs: number;
  total_runs: number;
  steps: number;
  total_scans: number;
  useful_scans: number;
  counts: { tp: number; fn: number; fp: number; tn: number };
  [key: string]: unknown;
}

export interface Scenario {
  id: ScenarioId;
  name: string;
  bands: number;
  emitters: number;
  duration_steps: number;
  episodes: number;
  emitter_mix: Record<BehaviorClass, number>;
  expected_outcome: string;
}

export interface Experiment {
  id: string;
  name: string;
  scenario: ScenarioId;
  policies: string[];
  episodes: number;
  seed: number;
  status: string;
  expected_outcome: string;
  created_at: string;
  progress?: ExperimentProgress;
}

export interface ExperimentProgress {
  fraction: number;
  completed_runs: number;
  total_runs: number;
  current_policy: string;
  current_episode: number;
  episodes_per_policy: number;
  finished: boolean;
  cancelled: boolean;
}

export interface MetricDelta {
  value: number;
  reference: number;
  absolute: number;
  percent: number | null;
}

export interface ExperimentResults {
  scenario: ScenarioId;
  scenario_name: string;
  episodes: number;
  duration_steps: number;
  seeds: number[];
  expected_outcome: string;
  policies: Record<string, MetricsSummary & { episodes: number }>;
  comparison: Record<string, Record<string, MetricDelta> | string>;
}

export interface SchedulerStatus {
  simulation_id: string;
  policy: PolicyType;
  status: string;
  step_count: number;
  ml_scheduler_degraded: boolean;
  ml_periodicity_degraded: boolean;
  available_policies: PolicyType[];
}

export interface ReadyStatus {
  status: "ready" | "degraded";
  ml_scheduler: "up" | "down";
  ml_periodicity: "up" | "down";
  running_simulations: number;
}

export interface ModelMetadata {
  model_id: string;
  algorithm: string;
  version: number;
  active: boolean;
  scenario: string | null;
  created_at: string;
  metrics: Record<string, unknown>;
  hyperparams: Record<string, unknown>;
  /** [min, max] training seed range, or null when the algorithm has nothing to train (e.g.
   * ctmc's fixed-form policy). Always present on the wire (Ai-ml-1's ModelRegistry.register
   * writes it on every entry) - missing here before 17 Sep was a stale mirror, not an
   * optional field the Backend might omit. */
  seed_range: [number, number] | null;
}

// -- Section 3: WebSocket frames ---------------------------------------------------------------

export type WsEventType =
  | "connection_ack"
  | "spectrum_update"
  | "scan_decision"
  | "detection_event"
  | "metrics_update"
  | "training_progress"
  | "error";

export interface WsFrame {
  type: WsEventType;
  simulation_id?: string;
  t?: number;
  active_bands?: number[];
  scanned_bands?: number[];
  detected_bands?: number[];
  false_alarm_bands?: number[];
  action?: number;
  model_id?: string;
  reward?: number;
  reward_terms?: Record<string, number>;
  valid_observation?: boolean;
  metrics?: MetricsSummary;
  status?: string;
  degraded?: boolean;
  snapshot?: LiveSnapshot;
  channels?: string[];
  heartbeat_seconds?: number;
  code?: string;
  message?: string;
  [key: string]: unknown;
}

export type WsChannel = "spectrum" | "scheduler" | "metrics" | "training";
export const WS_CHANNELS: WsChannel[] = [
  "spectrum",
  "scheduler",
  "metrics",
  "training",
];

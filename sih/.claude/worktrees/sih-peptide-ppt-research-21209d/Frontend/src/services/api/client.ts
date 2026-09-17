/**
 * Typed REST client for API_CONTRACT.md Section 2.
 *
 * <p>One place unwraps the Section 1 envelope, so no caller ever touches `.data` or has to
 * remember that a failure comes back as `{success:false, error}` with a real HTTP status. An
 * error becomes a thrown {@link ApiRequestError} carrying the contract's `code`, because the code
 * is what callers should branch on - `SIM_NOT_RUNNING` and `RESOURCE_NOT_FOUND` mean different
 * things to the UI and the message text is not a stable contract.
 */

import type {
  ApiEnvelope,
  CreateSimulationRequest,
  Experiment,
  ExperimentResults,
  LiveSnapshot,
  MetricsSummary,
  ModelMetadata,
  Paged,
  PolicyType,
  ReadyStatus,
  Scenario,
  ScenarioId,
  SchedulerStatus,
  Simulation,
} from "../../types/contract";

const DEFAULT_BASE = "http://localhost:8080";

/** Overridable so the harness can point at a deployed backend without a rebuild. */
export const API_BASE =
  (import.meta.env?.VITE_API_BASE as string | undefined) ?? DEFAULT_BASE;

export class ApiRequestError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { query?: Record<string, unknown> },
): Promise<T> {
  const url = new URL(API_BASE + path);
  for (const [key, value] of Object.entries(init?.query ?? {})) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const v of value) url.searchParams.append(key, String(v));
    } else {
      url.searchParams.set(key, String(value));
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (cause) {
    // A dead backend is the most common failure in a demo; say so plainly rather than
    // surfacing a bare "Failed to fetch".
    throw new ApiRequestError(
      "NETWORK_ERROR",
      `Cannot reach the backend at ${API_BASE}. Is it running?`,
      0,
      { cause: String(cause) },
    );
  }

  let envelope: ApiEnvelope<T> | null = null;
  try {
    envelope = (await response.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiRequestError(
      "MALFORMED_RESPONSE",
      `${response.status} ${response.statusText} with a non-JSON body`,
      response.status,
    );
  }

  if (!response.ok || !envelope.success) {
    const error = envelope.error;
    throw new ApiRequestError(
      error?.code ?? "UNKNOWN_ERROR",
      error?.message ?? `${response.status} ${response.statusText}`,
      response.status,
      error?.details ?? {},
    );
  }
  return envelope.data as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

// -- health --------------------------------------------------------------------------------

export const health = () =>
  request<{ status: string; service: string; scope: string }>("/health");

export const ready = () => request<ReadyStatus>("/ready");

// -- simulations ----------------------------------------------------------------------------

export const createSimulation = (body: CreateSimulationRequest) =>
  request<Simulation>("/api/v1/simulations", json(body));

export const listSimulations = (status?: string, page = 0, size = 20) =>
  request<Paged<Simulation>>("/api/v1/simulations", {
    query: { status, page, size },
  });

export const getSimulation = (id: string) =>
  request<Simulation>(`/api/v1/simulations/${id}`);

export const updateSimulation = (
  id: string,
  body: Partial<CreateSimulationRequest>,
) =>
  request<Simulation>(`/api/v1/simulations/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

export const deleteSimulation = (id: string) =>
  request<{ id: string; deleted: boolean }>(`/api/v1/simulations/${id}`, {
    method: "DELETE",
  });

export const startSimulation = (id: string) =>
  request<Simulation>(`/api/v1/simulations/${id}/start`, { method: "POST" });

export const stopSimulation = (id: string) =>
  request<Simulation>(`/api/v1/simulations/${id}/stop`, { method: "POST" });

export const resetSimulation = (id: string) =>
  request<Simulation>(`/api/v1/simulations/${id}/reset`, { method: "POST" });

// -- scheduler -------------------------------------------------------------------------------

export const schedulerStatus = (simulationId: string) =>
  request<SchedulerStatus>("/api/v1/scheduler/status", {
    query: { simulationId },
  });

export const setPolicy = (simulationId: string, policy: PolicyType) =>
  request<Simulation>("/api/v1/scheduler/config", {
    method: "PUT",
    body: JSON.stringify({ policy }),
    query: { simulationId },
  });

export const latestDecision = (simulationId: string) =>
  request<{ simulation_id: string; decision: Record<string, unknown> | null }>(
    "/api/v1/scheduler/decision",
    { query: { simulationId } },
  );

export const scenarios = () =>
  request<Scenario[]>("/api/v1/scheduler/scenarios");

// -- metrics ----------------------------------------------------------------------------------

/** Polling fallback for the WebSocket - same snapshot the reconnect replay sends. */
export const liveMetrics = (simulationId: string) =>
  request<LiveSnapshot>("/api/v1/metrics/live", { query: { simulationId } });

export const experimentMetrics = (experimentId: string) =>
  request<ExperimentResults>(`/api/v1/metrics/${experimentId}`);

export const compareExperiments = (ids: string[]) =>
  request<{ experiments: Record<string, ExperimentResults>; unavailable?: string[] }>(
    "/api/v1/metrics/compare",
    { query: { ids } },
  );

// -- experiments --------------------------------------------------------------------------------

export const createExperiment = (body: {
  name?: string;
  scenario: ScenarioId;
  policies: PolicyType[];
  episodes?: number;
  seed?: number;
}) => request<Experiment>("/api/v1/experiments", json(body));

export const listExperiments = (status?: string, page = 0, size = 20) =>
  request<Paged<Experiment>>("/api/v1/experiments", {
    query: { status, page, size },
  });

export const getExperiment = (id: string) =>
  request<Experiment>(`/api/v1/experiments/${id}`);

export const runExperiment = (id: string, durationSteps?: number) =>
  request<Experiment>(`/api/v1/experiments/${id}/run`, json({ durationSteps }));

export const stopExperiment = (id: string) =>
  request<Experiment>(`/api/v1/experiments/${id}/stop`, { method: "POST" });

export const experimentResults = (id: string) =>
  request<ExperimentResults>(`/api/v1/experiments/${id}/results`);

// -- models ---------------------------------------------------------------------------------------

export const listModels = (algorithm?: string, active?: boolean) =>
  request<ModelMetadata[]>("/api/v1/models", { query: { algorithm, active } });

export const getModel = (id: string) =>
  request<ModelMetadata>(`/api/v1/models/${id}`);

export const activateModel = (id: string) =>
  request<ModelMetadata>(`/api/v1/models/${id}/activate`, { method: "POST" });

export const trainModel = (body: {
  algorithm: string;
  scenario: ScenarioId;
  hyperparams?: Record<string, unknown>;
  episodeCount?: number;
}) => request<{ job_id: string }>("/api/v1/models/train", json(body));

export const trainStatus = (jobId: string) =>
  request<{ status: string; progress: number; detail: Record<string, unknown> }>(
    `/api/v1/models/train/${jobId}/status`,
  );

export const evaluateModel = (
  id: string,
  body: { scenario: ScenarioId; episodeCount?: number },
) => request<MetricsSummary>(`/api/v1/models/${id}/evaluate`, json(body));

/**
 * Waiting for the paced live runs to finish after the comparison lands (no runtime imports).
 *
 * <p>The wait is injectable so it can be unit-tested without timers or a backend: the caller
 * supplies how to poll a run, how to sleep, and what time it is. A rejected poll counts that
 * run as finished (best-effort: one failed poll must not abort the demo), and the deadline
 * is checked after every poll round so the cap always ends the wait.
 *
 * <p>This module must stay import-free at runtime: the `node --test` suite imports it with
 * an explicit `.ts` extension under type stripping, so only `import type` and erasable
 * TypeScript are allowed.
 */

export interface RaceFinishDeps {
  /** True while the run is still going; a rejection counts that run as finished. */
  isRunning: (id: string) => Promise<boolean>;
  /** Runs before every poll round; an exception (e.g. Cancel) propagates out untouched. */
  beforePoll?: () => void;
  sleep: (ms: number) => Promise<void>;
  now: () => number;
  /** Ms between poll rounds; defaults to 500. */
  intervalMs?: number;
  /** Max ms to wait before giving up; defaults to 90_000. */
  capMs?: number;
}

/**
 * Polls every truthy id until no run is still running ("finished") or the cap is reached
 * ("capped"). Falsy ids are skipped; with no ids at all it returns "finished" at once.
 */
export async function waitForRunsToFinish(
  ids: Array<string | null | undefined>,
  deps: RaceFinishDeps,
): Promise<"finished" | "capped"> {
  const intervalMs = deps.intervalMs ?? 500;
  const deadline = deps.now() + (deps.capMs ?? 90_000);
  for (;;) {
    deps.beforePoll?.();
    let running = false;
    for (const id of ids) {
      if (!id) continue;
      try {
        if (await deps.isRunning(id)) running = true;
      } catch {
        // Best-effort: a failed poll counts that run as finished rather than aborting.
      }
    }
    if (!running) return "finished";
    if (deps.now() >= deadline) return "capped";
    await deps.sleep(intervalMs);
  }
}

import type { MetricsSummary } from "../types/contract";
import { policyLabel } from "../lib/policyLabels";

export function fellBackToSweep(policy: string, metrics: MetricsSummary | undefined): boolean {
  return policy !== "baseline" && policy !== "random" &&
    metrics?.ml_decisions === 0 &&
    typeof metrics.fallback_decisions === "number" && metrics.fallback_decisions > 0;
}

/** New provenance fields are optional because previously saved experiments predate them. */
export function PolicyRunDetails({ policies, compact = false }: { policies: Record<string, MetricsSummary>; compact?: boolean }) {
  const entries = Object.entries(policies).filter(([name, m]) =>
    (!compact || name !== "baseline") && (
    typeof m.ml_decisions === "number" || typeof m.fallback_decisions === "number" ||
    Array.isArray(m.model_ids) ||
    typeof m.unavailable_reason === "string" ||
    (!compact && typeof m.tp_high_priority === "number" && typeof m.fn_high_priority === "number")),
  );
  if (entries.length === 0) return null;

  if (compact) return (
    <div className="policy-run-details">
      {entries.map(([name, m]) => (
        <div key={name}>
          {(fellBackToSweep(name, m) || m.unavailable_reason) && (
            <p className="policy-provenance-alert">
              {fellBackToSweep(name, m) && "Fell back to sweep — no trained model served this scenario."}
              {m.unavailable_reason && ` ${m.unavailable_reason}`}
            </p>
          )}
          <p className="policy-provenance-line">
            <strong>{policyLabel(name)}</strong>
            {Array.isArray(m.model_ids) && m.model_ids.length > 0 &&
              <> · Served by <span className="mono">{m.model_ids.join(", ")}</span></>}
            {typeof m.ml_decisions === "number" && ` · ${m.ml_decisions} model decisions`}
            {typeof m.fallback_decisions === "number" && ` · ${m.fallback_decisions} fallbacks`}
          </p>
        </div>
      ))}
    </div>
  );

  return (
    <div className="note" style={{ marginTop: 12 }}>
      {entries.map(([name, m]) => (
        <p key={name} style={{ margin: "6px 0" }}>
          <strong>{policyLabel(name)}:</strong>{" "}
          {fellBackToSweep(name, m) && "Fell back to sweep — no trained model served this scenario. "}
          {typeof m.unavailable_reason === "string" && m.unavailable_reason && `${m.unavailable_reason}. `}
          {typeof m.ml_decisions === "number" && `${m.ml_decisions} model decisions. `}
          {typeof m.fallback_decisions === "number" && `${m.fallback_decisions} fallback decisions. `}
          {Array.isArray(m.model_ids) && m.model_ids.length > 0 &&
            <>Served by <span className="mono">{m.model_ids.join(", ")}</span>. </>}
          {typeof m.tp_high_priority === "number" && typeof m.fn_high_priority === "number" &&
            (m.tp_high_priority + m.fn_high_priority > 0
              ? `High-priority detections: ${m.tp_high_priority}/${m.tp_high_priority + m.fn_high_priority}.`
              : "No high-priority transmissions in this run.")}
        </p>
      ))}
    </div>
  );
}

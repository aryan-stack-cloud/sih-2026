import { useStore } from "../store/useStore";

/**
 * GET /health and GET /ready.
 *
 * Shows each ML service separately rather than one aggregate light, because "the Backend is up
 * but Ai-ml-1 is down" is the single most likely demo-day failure and it is invisible otherwise:
 * the scheduler degrades to round-robin and simply looks like a worse policy.
 */
export function HealthPanel() {
  const { ready, refreshReady } = useStore();

  const dot = (up: boolean) => (up ? "up" : "DOWN");

  return (
    <section style={{ border: "1px solid #ccc", padding: 8 }}>
      <strong>Services</strong>{" "}
      <button onClick={() => void refreshReady()}>refresh</button>
      {!ready ? (
        <p style={{ color: "#900" }}>Backend unreachable at the configured API base.</p>
      ) : (
        <table>
          <tbody>
            <tr>
              <td>backend</td>
              <td>{ready.status}</td>
            </tr>
            <tr>
              <td>ml-scheduler (Ai-ml-1, :8500)</td>
              <td style={{ color: ready.ml_scheduler === "up" ? "#060" : "#900" }}>
                {dot(ready.ml_scheduler === "up")}
              </td>
            </tr>
            <tr>
              <td>ml-periodicity (Ai-ml-2, :8600)</td>
              <td style={{ color: ready.ml_periodicity === "up" ? "#060" : "#900" }}>
                {dot(ready.ml_periodicity === "up")}
              </td>
            </tr>
            <tr>
              <td>running simulations</td>
              <td>{ready.running_simulations}</td>
            </tr>
          </tbody>
        </table>
      )}
    </section>
  );
}

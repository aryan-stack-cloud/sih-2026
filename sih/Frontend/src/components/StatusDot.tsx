/** One inline status readout: a coloured dot plus its word, in the vocabulary the masthead's
    service lights and the Waterfall's legend already use. Previously redefined identically in
    ExperimentsPage and ModelsPage - one copy now, so a future tone or size change lands once. */
export function StatusDot({
  tone,
  children,
}: {
  tone: "good" | "bad" | "neutral";
  children: string;
}) {
  return (
    <span className="status-readout">
      <span className={`status-dot${tone === "neutral" ? "" : ` ${tone}`}`} />
      <span className="status-readout-label">{children}</span>
    </span>
  );
}

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- Before answering a structural/architectural question, check graphify-out/reflections/LESSONS.md if it exists — it may already have the answer or a past correction.
- After answering a codebase question using the graph (query/path/explain/affected/god-nodes), run `graphify save-result --question "<question>" --answer "<short answer>" --nodes <node labels cited> --outcome useful` to record it. If a prior saved answer turns out to be wrong, save it with `--outcome corrected --correction "<what was actually right>"` instead.
- Periodically (e.g. after several save-result calls, or when starting a new session on this project) run `graphify reflect` to consolidate graphify-out/memory/ into graphify-out/reflections/LESSONS.md.

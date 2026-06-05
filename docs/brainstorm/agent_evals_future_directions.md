# Agent Evals — Future Directions

Dimensions removed from `agent.md` for simplicity. Revisit when the core recall/precision baseline is stable.

---

## Ingest Agent — Additional Dimensions

| Metric | What it catches |
|---|---|
| **Schema compliance rate** | Fraction of proposals that conform to `graph_schema.md` without the user having to edit the type or label. Catches prompt drift. |
| **Deduplication accuracy** | Precision/recall on the dedup step specifically: did the agent correctly flag candidates that match existing nodes, without false-merging distinct concepts? Requires a fixture where some concepts are already in `index.md`. |
| **Property completeness** | For confirmed nodes, what fraction of required properties were non-null? Catches shallow extraction that leaves most fields empty. |
| **User edit rate** | How much did the user change proposals before confirming? Measured as edit distance on `summary` fields. Low edits → high proposal quality. Observable from `log.md` without a gold set. |
| **Confirmation rate** | Fraction of proposals the user confirmed vs. discarded. A rough proxy for precision when no gold set exists. |

---

## Lint Agent — Attribute-Level Checks

These were scoped out in favor of structural-only linting:

- **Internal consistency** — does the `summary` agree with connected relationships?
- **Stale claims** — does `confidence: low` appear unresolved past a threshold?
- **Contradiction detection** — do two nodes make incompatible factual claims?

If attribute-level linting is added later, the gold set would need fixtures that include incorrect or stale property values, not just structural defects.

---

## Lint Agent — Additional Dimensions

| Metric | What it catches |
|---|---|
| **False positive rate on clean graphs** | Run the agent on a deliberately well-formed graph snapshot. Any finding is a false positive. Catches over-triggering. |
| **Run-to-run stability** | Run the agent twice on the same graph state; diff the findings. LLMs are non-deterministic — instability here means users see different issues on repeated runs, which erodes trust. |
| **Severity calibration** | Do findings marked `high` severity actually matter more to a human reviewer than `low` ones? Requires periodic human spot-checks; track agreement rate. |
| **Cross-node detection rate** | Reduce-phase recall only: `cross_node_issues_found / cross_node_issues_in_manifest`. Isolates whether the aggregation step is doing useful work beyond the per-node scan. |
| **Actionability rate** | Fraction of reported issues the user acted on (edited or acknowledged in the UI). Observable from `log.md`. A low rate means findings are too vague or unfixable — a prompt quality signal. |

---

## Shared Considerations

**Running evals:** Each eval run calls the agent endpoint against a fixture, compares the output to the gold manifest, and writes a score file. A standalone Python script (`evals/run_evals.py`) reading fixtures from `evals/fixtures/` and printing a summary table is sufficient at this scale.

**LLM-as-judge for subjective dimensions:** For edit rate and actionability, a second LLM call can judge whether a proposal is "high quality" against the source text. Useful for bulk scoring when human review is too slow, but treat it as a noisy signal.

**Thresholds (suggested starting points):**

| Agent | Metric | Target |
|---|---|---|
| Ingest | Node recall | ≥ 0.80 |
| Ingest | Node precision | ≥ 0.75 |
| Ingest | Schema compliance | ≥ 0.95 |
| Lint | Issue recall | ≥ 0.75 |
| Lint | False positive rate (clean graph) | 0 |
| Lint | Run-to-run stability | ≥ 0.90 agreement |

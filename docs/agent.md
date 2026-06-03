# Agent Architecture

## LLM

**Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
**Provider:** Anthropic API

## Framework

**LangGraph** (open-source, provider-agnostic, from the LangChain team).

LangChain is the right instinct — open-source, not cloud-locked, pluggable LLM providers — but it is better suited to sequential text pipelines than agent loops. LangGraph models agent logic as a state machine (nodes + edges + shared state), which maps cleanly onto both agents below and handles loops naturally. It uses the same LangChain integrations (tools, chat models, message formats), so the ecosystem stays consistent.

> Alternative: the raw Anthropic SDK with `tool_use` also works for these two agents and has zero framework overhead. Worth starting there if you want to keep dependencies minimal.

---

## Shared Tools

| Tool | Library | Purpose |
|---|---|---|
| `read_pdf` | `pypdf` | Extract text from PDF files |
| `read_website` | HTTP call to `r.jina.ai/<url>` | Convert any URL to clean markdown |
| `read_ocr` | `easyocr` or `pytesseract` | Extract text from images and scanned documents |

---

## Agents

### Ingest Agent

**Trigger:** `POST /ingest` — receives a file path or a raw text prompt

**Context injected at runtime:**
- Graph schema (node labels, relationship types, property definitions from `graph_schema.md`)
- Current `index.md` (so the agent knows what already exists and avoids duplicates)

**Steps:**

1. **Parse** — select the right tool based on input type (PDF, URL, image, or passthrough for plain text)
2. **Extract** — LLM reads the parsed content and identifies candidate nodes and relationships
3. **Deduplicate** — LLM checks `index.md` to flag any matches against existing nodes
4. **Propose** — LLM outputs:
   - New or updated nodes with properties (`summary`, `aliases`, `raw_sources`, etc.)
   - New or updated relationships with `justification`, `confidence`, and `date_added`
5. **Review** — proposals are returned to the UI; the user inspects each node and relationship, edits if needed, and confirms or discards
6. **Write** — FastAPI commits confirmed proposals to Neo4j, updates `index.md`, and appends to `log.md`

---

### Lint Agent

**Trigger:** `POST /lint` — on demand via the UI, or on a schedule via a system cron job (`cron` is a Unix daemon; no library needed — you add one line to your crontab that calls `curl -X POST http://localhost:8000/lint` at whatever interval you want, e.g. weekly)

**Context injected at runtime:**
- `index.md` (full catalog of all nodes)
- Node and relationship data fetched from Neo4j as needed

**Loop (map-reduce):**

*Map phase — per-node scan:*
For each entry in `index.md`, the agent:
1. Fetches the node's properties and all connected relationships from Neo4j
2. Calls the LLM to check:
   - Internal consistency (do the `summary` and relationships agree?)
   - Stale claims (does `confidence: low` still appear unresolved?)
   - Relationship validity (do edge types match the schema's decision rules?)
3. Emits a findings list for this node

*Reduce phase — cross-node check:*
After all nodes are scanned, the LLM reviews the aggregated findings and checks for:
- Contradictions between two nodes making incompatible claims
- Structural issues: orphan nodes (no edges), relationship cycles that violate hierarchy
- Duplicate nodes that should be merged

**Output:**
- Lint report (structured list of issues with node references and severity)
- Report appended to `log.md`
- Report returned to the UI for the user to review

> The agent reports issues only — it does not auto-fix. A future iteration can add auto-fix proposals with human confirmation, following the same pattern as the ingest agent's proposal step.

---

## Evals

Recall and precision here are adapted from information retrieval, not binary classification. The denominator for recall is the gold set; the denominator for precision is what the agent proposed.

```
recall    = |correct ∩ proposed| / |correct|
precision = |correct ∩ proposed| / |proposed|
```

Each agent needs its own gold set and has its own additional failure modes worth tracking.

---

### Ingest Agent Evals

**Gold set construction:** For each fixture document (PDF, URL, or text snippet), a human annotates the expected nodes and relationships — labels, key properties, and edge types. Store these alongside the fixture as a JSON file.

**Recall** — did the agent find everything?
- Node recall: `nodes_correctly_proposed / nodes_in_gold_set`
- Relationship recall: `edges_correctly_proposed / edges_in_gold_set`
- A node counts as "correct" if the label and at least the `summary` property match the gold entry (fuzzy match is fine; exact string equality is too strict).

**Precision** — were the proposals worth reviewing?
- Node precision: `nodes_in_gold_set ∩ proposed / nodes_proposed`
- Relationship precision: `edges_in_gold_set ∩ proposed / edges_proposed`
- Hallucinated nodes (plausible-sounding but not present in the source) are the main precision killer here.

**Additional dimensions:**

| Metric | What it catches |
|---|---|
| **Schema compliance rate** | Fraction of proposals that conform to `graph_schema.md` without the user having to edit the type or label. Catches prompt drift. |
| **Deduplication accuracy** | Precision/recall on the dedup step specifically: did the agent correctly flag candidates that match existing nodes, without false-merging distinct concepts? Requires a fixture where some concepts are already in `index.md`. |
| **Property completeness** | For confirmed nodes, what fraction of required properties were non-null? Catches shallow extraction that leaves most fields empty. |
| **User edit rate** | How much did the user change proposals before confirming? Measured as edit distance on `summary` fields. Low edits → high proposal quality. This is observable from `log.md` without a gold set. |
| **Confirmation rate** | Fraction of proposals the user confirmed vs. discarded. A rough proxy for precision when no gold set exists. |

---

### Lint Agent Evals

**Gold set construction:** Build a set of synthetic graph snapshots with known injected defects. Each fixture is a Neo4j dump (or equivalent JSON) plus a manifest listing every injected issue — node reference, issue type, and severity. Defect types to cover:
- Unresolved `confidence: low` that has aged past a threshold
- `summary` that contradicts a connected node's claim
- Edge type that violates schema decision rules
- Orphan node (no relationships)
- Duplicate nodes (same concept, different IDs)

**Recall** — did the agent surface everything?
- `issues_found / issues_in_manifest`
- Track separately for map-phase issues (per-node) vs. reduce-phase issues (cross-node contradictions, duplicates) — they have different LLM calls and different failure modes.

**Precision** — were the findings actionable?
- `genuine_issues / issues_reported`
- A finding is genuine if it maps to an entry in the manifest, or if a human reviewer judges it valid on a clean fixture (no injected defects).

**Additional dimensions:**

| Metric | What it catches |
|---|---|
| **False positive rate on clean graphs** | Run the agent on a deliberately well-formed graph snapshot. Any finding is a false positive. Catches over-triggering. |
| **Run-to-run stability** | Run the agent twice on the same graph state; diff the findings. LLMs are non-deterministic — instability here means users see different issues on repeated runs, which erodes trust. |
| **Severity calibration** | Do findings marked `high` severity actually matter more to a human reviewer than `low` ones? Requires periodic human spot-checks; track agreement rate. |
| **Cross-node detection rate** | Reduce-phase recall only: `cross_node_issues_found / cross_node_issues_in_manifest`. Isolates whether the aggregation step is doing useful work beyond the per-node scan. |
| **Actionability rate** | Fraction of reported issues the user acted on (edited or acknowledged in the UI). Observable from `log.md`. A low rate means findings are too vague or unfixable — a prompt quality signal. |

---

### Shared Considerations

**Running evals:** Each eval run calls the agent endpoint against a fixture, compares the output to the gold manifest, and writes a score file. This can be a standalone Python script (`evals/run_evals.py`) that reads fixtures from `evals/fixtures/` and prints a summary table. No eval framework required at this scale.

**LLM-as-judge for subjective dimensions:** For edit rate and actionability, you can also prompt a second LLM call to judge whether a proposal is "high quality" against the source text. Useful for bulk scoring when human review is too slow, but treat it as a noisy signal.

**Thresholds (suggested starting points):**

| Agent | Metric | Target |
|---|---|---|
| Ingest | Node recall | ≥ 0.80 |
| Ingest | Node precision | ≥ 0.75 |
| Ingest | Schema compliance | ≥ 0.95 |
| Lint | Issue recall | ≥ 0.75 |
| Lint | False positive rate (clean graph) | 0 |
| Lint | Run-to-run stability | ≥ 0.90 agreement |

These are guardrails, not goals — adjust as you accumulate real-world data from `log.md`.

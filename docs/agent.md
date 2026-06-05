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

---

### Ingest Agent Evals

**Gold set:** For each fixture document (PDF, URL, or text snippet), annotate the expected nodes and relationships — labels, key properties, and edge types. Store alongside the fixture as a JSON file.

**Recall** — did the agent find everything?
- Node recall: `nodes_correctly_proposed / nodes_in_gold_set`
- Relationship recall: `edges_correctly_proposed / edges_in_gold_set`

**Precision** — were the proposals worth reviewing?
- Node precision: `nodes_correctly_proposed / nodes_proposed`
- Relationship precision: `edges_correctly_proposed / edges_proposed`

---

### Lint Agent Evals

Scope: structural issues only — nodes and relationships. Attribute-level checks (e.g. stale `summary`, contradicting claims) are out of scope for now.

**Gold set:** Synthetic graph snapshots with known injected defects. Each fixture is a Neo4j dump (or equivalent JSON) plus a manifest of every injected issue. Defect types to cover:
- Orphan node (no relationships)
- Duplicate nodes (same concept, different IDs)
- Edge type that violates schema decision rules
- Relationship cycle that violates hierarchy

**Recall** — did the agent surface everything?
- `issues_found / issues_in_manifest`

**Precision** — were the findings genuine?
- `genuine_issues / issues_reported`
- A finding is genuine if it maps to an entry in the manifest, or if a human reviewer confirms it on a clean fixture.

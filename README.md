# DS Learning Pal

A locally-hosted, graph-based knowledge wiki for building and maintaining a personal knowledge base of data science, machine learning, and AI engineering concepts. Inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

The core idea: ingest raw learning materials (papers, articles, videos, notes), let an LLM extract structured knowledge from them, and store everything as a typed graph of concepts, algorithms, models, and their relationships. The graph grows with you — every new source deepens the existing structure rather than piling into an unorganized folder. A second agent periodically lints the graph for contradictions, stale claims, and orphan nodes.

---

## Graph Schema

The knowledge graph is built around a fixed set of node labels and typed relationships. Decision rules specify exactly when each edge type applies, keeping the graph consistent as it grows.

**Relationships**

| Edge | Direction | Meaning |
|---|---|---|
| `SUBCLASS_OF` | A → B | A is a more specific category of B |
| `INSTANCE_OF` | A → B | A is a specific member of class B |
| `BELONGS_TO` | A → B | A is situated within a field or discipline; B must be a `Domain` node |
| `ADDRESSES` | A → B | A is a solution or mitigation for B |
| `PART_OF` | A → B | A is a component of B |
| `USED_ON` | A → B | A operates on or is applied to B |

**Node Properties**

| Property | Description |
|---|---|
| `summary` | LLM-generated description of the concept |
| `aliases` | Other names this node goes by |
| `notes` | Free-form personal annotations |
| `raw_sources` | Source files that informed this node |
| `courses` | Links to structured learning modules |
| `videos` | Links to video lectures or YouTube |
| `docs` | Official documentation links |
| `references` | Seminal papers, articles, and canonical reads |

**Relationship Properties**

| Property | Description |
|---|---|
| `justification` | Short explanation of why this relationship holds |
| `confidence` | `high`, `medium`, or `low` — flags uncertain edges for lint |
| `date_added` | ISO date the edge was created |

→ [Graph Schema](docs/graph_schema.md)

---

## Workflow

The wiki operates across three layers: immutable **raw sources** (your uploaded files), the **wiki** (LLM-maintained markdown), and a **schema** document that governs how the LLM maintains everything. Three main operations drive the system: **Ingest** (adding new sources and updating the graph), **Query** (asking questions answered by traversing the graph), and **Lint** (health checks for contradictions, orphans, and stale edges). Two special files — `index.md` and `log.md` — let the LLM navigate and audit the wiki as it scales.

→ [Workflow](docs/workflow.md)

---

## Agent Architecture

Two LangGraph agents power the system, both backed by Claude Haiku 4.5 via the Anthropic API. The **Ingest Agent** parses a source file or prompt, extracts candidate nodes and relationships, deduplicates against `index.md`, and returns proposals for human review before anything is written to the graph. The **Lint Agent** runs a map-reduce scan — checking each node for internal consistency and relationship validity, then doing a cross-node pass for contradictions and duplicates — and returns a structured report without auto-applying any fixes. Shared tools cover PDF extraction, website-to-markdown conversion, and OCR.

→ [Agent Architecture](docs/agent.md)

---

## Architecture

The system is a three-layer stack running entirely on local hardware. The **data layer** pairs Neo4j (knowledge graph) with MongoDB (raw source file storage via GridFS). The **app layer** is a FastAPI backend that owns all reads and writes to both databases and exposes REST endpoints for nodes, relationships, sources, wiki files, and agent triggers. The **presentation layer** is a React frontend with a force-directed graph explorer, a node editor, an ingest panel with proposal review, and a lint panel. Agents run server-side inside the FastAPI process, invoked through `/ingest` and `/lint`.

→ [Architecture](docs/architecture.md)

---

## Implementation Plan

**Phase 1** brings up the full application locally — Neo4j and MongoDB running natively, FastAPI backend with CRUD routers and both agents, JWT-based auth with admin/viewer roles, and a React/Vite frontend. The only external dependency is an Anthropic API key. Build order goes: database connection helpers → CRUD routers → auth → agents → frontend views → local dev wiring.

**Phase 2** migrates to the cloud with no application code changes — only environment variables swap. Neo4j local → AuraDB, MongoDB local → Atlas, FastAPI → Cloud Run or Azure Container Apps, React → Firebase Hosting or Azure Static Web Apps. GitHub Actions adds CI (lint + tests on PRs) and CD (deploy on merge to `main`).

→ [Implementation Plan](docs/implementation.md)

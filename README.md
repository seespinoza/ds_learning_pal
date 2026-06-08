# DS Learning Pal

A locally-hosted, graph-based knowledge wiki for building and maintaining a personal knowledge base of
data science, machine learning, and AI engineering concepts.
Inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

The core idea: ingest raw learning materials (papers, articles, videos, notes), let an LLM extract
structured knowledge from them, and store everything as a typed graph of concepts, algorithms, models,
and their relationships. The graph grows with you — every new source deepens the existing structure
rather than piling into an unorganized folder. A second agent periodically lints the graph for
contradictions, stale claims, and orphan nodes.

---

## Graph Schema

The knowledge graph is built around a fixed set of node labels and typed relationships.
Decision rules specify exactly when each edge type applies, keeping the graph consistent as it grows.

**Hierarchical Relationships**

| Edge | Direction | Meaning |
|---|---|---|
| `SUBCLASS_OF` | A → B | A is a more specific category of B |
| `INSTANCE_OF` | A → B | A is a specific member of class B |
| `BELONGS_TO` | A → B | A is situated within a field or discipline; B must be a `Domain` node |

**Associative Relationships**

| Edge | Direction | Meaning |
|---|---|---|
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

The wiki operates across three layers:

- **Raw sources** — immutable uploaded files; the LLM reads from them but never modifies them
- **Wiki** — LLM-maintained markdown files; summaries, entity pages, cross-references
- **Schema** — configuration document governing how the LLM maintains the wiki

Three main operations drive the system:

- **Ingest** — add a new source file or prompt; LLM creates or updates nodes and relationships
- **Query** — ask natural language questions; LLM traverses the graph to answer them
- **Lint** — health checks for contradictions, orphan nodes, and stale edges

Two special files help navigation as the wiki scales:
`index.md` catalogs every node with a one-line summary; `log.md` is an append-only audit trail of all operations.

→ [Workflow](docs/workflow.md)

---

## Agent Architecture

Both agents are backed by Claude Haiku 4.5 via the Anthropic API.

**Ingest Agent** — triggered by `POST /ingest` with a file path or prompt:

1. Parse the input (PDF, URL, image, or plain text)
2. Extract candidate nodes and relationships (schema + decision rules injected into prompt)
3. Deduplicate against `index.md`
4. Return proposals to the UI for human review
5. Write confirmed proposals to Neo4j; update `index.md` and `log.md`

Linear pipeline — implemented as plain async functions, no graph framework needed.

**Lint Agent** — triggered by `POST /lint` on demand or via cron:

1. Map phase: for each node, check internal consistency and relationship validity against schema rules
2. Reduce phase: cross-node pass for contradictions, orphans, and duplicates
3. Return a structured report — issues only, no auto-fixes

Map-reduce structure implemented with LangGraph `StateGraph`.

Shared tools cover PDF extraction (`pypdf`), website-to-markdown conversion (`r.jina.ai`), and OCR (`easyocr`).

→ [Agent Architecture](docs/agent.md)

---

## Architecture

The system is a three-layer stack running entirely on local hardware:

- **Data layer** — Neo4j stores the knowledge graph; MongoDB stores raw source files via GridFS
- **App layer** — FastAPI backend; single access point for all reads and writes to both databases;
  exposes REST endpoints for nodes, relationships, sources, wiki files, and agent triggers
- **Presentation layer** — React frontend with a force-directed graph explorer, node editor,
  ingest panel with proposal review, and lint panel

Agents run server-side inside the FastAPI process, invoked through `/ingest` and `/lint`.

→ [Architecture](docs/architecture.md)

---

## Implementation Plan

**Phase 1 — Local Standup ✓ Complete**

Source lives under `src/`. Copy `.env.example` → `.env`, fill in secrets, then:

```bash
# 1. Start databases
sudo systemctl start mongod   # MongoDB
# Start Neo4j Desktop and open your local database

# 2. Backend
PYTHONPATH=src uvicorn backend.main:app --reload

# 3. Create first admin account (one-time, while no users exist)
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme","role":"admin"}'

# 4. Frontend
cd src/frontend && npm install && npm run dev

# 5. Evals (optional, requires backend running + JWT token)
python src/evals/run_evals.py --token <your-jwt>
```

Stack: FastAPI + Neo4j + MongoDB + LangGraph (lint) + Claude Haiku 4.5 + React/Vite/Tailwind.

**Phase 2 — Cloud Migration**

No application code changes — only environment variables swap:

- Neo4j local → Neo4j AuraDB
- MongoDB local → MongoDB Atlas
- FastAPI → Cloud Run or Azure Container Apps
- React → Firebase Hosting or Azure Static Web Apps

GitHub Actions adds CI (ruff + pytest + eslint + eval suite on PRs) and CD (deploy on merge to `main`).

→ [Implementation Plan](docs/implementation.md)

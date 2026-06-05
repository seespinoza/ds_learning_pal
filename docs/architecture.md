# Architecture

## Overview

A locally-hosted knowledge graph platform for DS/MLE/AIE concepts. Human users and AI agents can maintain and explore a Neo4j graph via a FastAPI backend and a React frontend.

---

## Layers

### Data Layer — Neo4j + MongoDB (both local)

**Neo4j** stores the knowledge graph: nodes (e.g. `Concept`, `Algorithm`, `Model`) and typed relationships (e.g. `SUBCLASS_OF`, `ADDRESSES`) as defined in `graph_schema.md`. Each raw source ingested into the system gets a corresponding `Source` node in Neo4j that holds a reference to its MongoDB document ID — this is how the graph tracks provenance without duplicating file content.

Two auxiliary markdown files live alongside the graph:
- `index.md` — catalog of all nodes, updated on every ingest
- `log.md` — append-only audit log of all operations (ingest, lint, queries)

**MongoDB** stores raw source files. It serves two roles:
- **GridFS** — stores large binary files (PDFs, images, scanned docs) as chunked binary data, avoiding filesystem dependency
- **Document metadata** — each file is stored with structured metadata (filename, upload date, file type, user-defined tags/categories) that you can browse and organize independently of the graph

### App Layer — FastAPI (Python)

The single access point for all clients (UI and agents). Owns all reads and writes to Neo4j.

| Endpoint group | Purpose |
|---|---|
| `POST /ingest` | Trigger the ingest agent with a file path or raw text prompt |
| `POST /lint` | Trigger the lint agent on demand |
| `GET/POST/PATCH/DELETE /nodes` | CRUD for graph nodes |
| `GET/POST/PATCH/DELETE /relationships` | CRUD for graph edges |
| `GET /search` | Keyword/filter search over the graph |
| `GET/PUT /wiki/{filename}` | Read and write `index.md` and `log.md` |
| `GET/POST /sources` | Upload and browse raw source files in MongoDB |

### Presentation Layer — React (JS)

Web UI for human users. Two main views:

- **Graph explorer** — interactive force-directed canvas (`react-force-graph`) for browsing the graph; click a node to inspect its properties and connected edges
- **Node editor** — form-based view for reading and manually editing node and relationship properties

### AI Layer

Agent processes run server-side within the FastAPI process, invoked through the `/ingest` and `/lint` endpoints. See `agent.md`.

**Evals** run as a separate dev-time harness — not part of the production app. The eval runner (`evals/run_evals.py`) calls the same `/ingest` and `/lint` endpoints against fixture inputs, compares outputs to gold manifests, and prints a score table. Fixtures and gold manifests live in `evals/fixtures/` alongside the source code.

---

## Data Flow

**Ingest (file):**
User uploads file → React UI → `POST /sources` stores file in MongoDB → `POST /ingest` → Ingest Agent parses file and calls LLM → proposals returned to UI → user reviews and confirms → FastAPI writes nodes/relationships to Neo4j → updates `index.md` and appends to `log.md`

**Ingest (prompt):**
User types a prompt → `POST /ingest` → same pipeline, no MongoDB write (no raw file)

**Browse:**
User navigates graph → React UI → `GET /nodes` + `GET /relationships` → Neo4j → rendered in graph explorer

**Lint (on demand):**
User triggers lint → `POST /lint` → Lint Agent scans nodes → lint report appended to `log.md` and returned to UI

**Lint (scheduled):**
System cron job calls `curl -X POST http://localhost:8000/lint` on a schedule (e.g. weekly). No additional libraries needed — cron is a Unix system daemon configured via a one-line crontab entry.

**Eval run:**
Developer runs `python evals/run_evals.py` → script calls `/ingest` or `/lint` with fixture inputs → compares agent output against gold manifest JSON → prints recall/precision scores per agent.

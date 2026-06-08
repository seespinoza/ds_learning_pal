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
sudo systemctl start neo4j    # Neo4j

# 2. Backend (activate venv first)
source .venv/bin/activate
PYTHONPATH=src uvicorn backend.main:app --reload

# 3. Create first admin account (one-time, while no users exist)
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme","role":"admin"}'

# 4. Frontend
cd src/frontend && npm install && npm run dev

# 5. Evals (optional, requires backend running + JWT token; venv must be active)
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

---

## Setup

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Neo4j Community | 5.x | Installed via `dnf` — see install note below |
| MongoDB Community | 8.0+ | Not in default Fedora repos — see install note below |
| Python | 3.11+ | Backend and agents |
| Node.js | 20+ | React frontend |
| Anthropic API key | — | Set as `ANTHROPIC_API_KEY` in `.env` |

**Neo4j on Fedora** — add the official RPM repo:

```bash
sudo rpm --import https://debian.neo4j.com/neotechnology.gpg.key
sudo tee /etc/yum.repos.d/neo4j.repo << 'EOF'
[neo4j]
name=Neo4j RPM Repository
baseurl=https://yum.neo4j.com/stable/latest
enabled=1
gpgcheck=1
EOF
sudo dnf install -y neo4j
```

Set the password before first start:

```bash
sudo neo4j-admin dbms set-initial-password yourpassword
sudo systemctl enable --now neo4j
```

**MongoDB on Fedora** — add the official repo first:

```bash
sudo tee /etc/yum.repos.d/mongodb-org-8.0.repo << 'EOF'
[mongodb-org-8.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/9/mongodb-org/8.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-8.0.asc
EOF
sudo dnf install -y mongodb-org
sudo systemctl enable --now mongod
```

### 1. Clone and configure environment

```bash
cp .env.example .env
```

Fill in all values in `.env`:

```
ANTHROPIC_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=<your Neo4j local database password>
MONGO_URI=mongodb://localhost:27017
JWT_SECRET_KEY=<output of: openssl rand -hex 32>
```

### 2. Create virtual environment and install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd src/frontend && npm install
```

### 4. Create the first admin account

Do this once, while the backend is running and no users exist yet:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme","role":"admin"}'
```

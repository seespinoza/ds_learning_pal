# Implementation

## Phase 1 — Local Standup ✓ Complete

Everything runs on your machine. The only external dependency is the Anthropic API key. Goal is a fully functional app — graph CRUD, both agents, and the React UI — before touching any cloud infrastructure.

**Status:** Implemented. Source tree lives under `src/`:

```
src/
  backend/          FastAPI app (main.py, routers/, db/, agents/, auth/)
  frontend/         React + Vite + Tailwind (npm project)
  evals/            Eval runner + 4 fixtures (2 ingest, 2 lint)
  wiki/             index.md and log.md (runtime-written)
```

**First-run setup:**
1. Copy `.env.example` → `.env` and fill in all values
2. Generate JWT secret: `openssl rand -hex 32`
3. `sudo systemctl start neo4j && sudo systemctl start mongod`
4. `PYTHONPATH=src uvicorn backend.main:app --reload` (from project root)
5. Create your first admin user: `POST /auth/register` with `{"username": "...", "password": "...", "role": "admin"}`
6. `cd src/frontend && npm install && npm run dev`

### Prerequisites

| Requirement | Notes |
|---|---|
| Neo4j Community | Install via RPM repo (`dnf install neo4j`); runs as a system service; browser UI available at `localhost:7474` |
| MongoDB Community 7.0 | Install via package manager (e.g. `dnf install mongodb-org` from the 7.0 repo on Fedora); 8.x incompatible with Linux kernel 6.19+ |
| Python 3.11+ | Backend and agents |
| Node.js 20+ | React frontend |
| Anthropic API key | Set as env var `ANTHROPIC_API_KEY` |

---

### 1. Infrastructure

Start both database services (`sudo systemctl start neo4j && sudo systemctl start mongod`). Both run natively as system services — no containers needed in this phase.

---

### 2. Backend — FastAPI

**Project layout:**
```
backend/
  main.py
  routers/
    nodes.py
    relationships.py
    sources.py
    ingest.py
    lint.py
    wiki.py
  db/
    neo4j.py       # driver + session helpers
    mongo.py       # motor async client + GridFS
  agents/
    ingest.py
    lint.py
    tools.py
    prompts.py   # shared GRAPH_SCHEMA constant
  config.py        # env vars via pydantic-settings
```

**Key dependencies:** `fastapi`, `uvicorn`, `neo4j` (official driver), `motor` (async MongoDB), `pydantic-settings`

**Build order:**
1. `db/neo4j.py` and `db/mongo.py` — connection setup and session helpers
2. CRUD routers (`nodes`, `relationships`, `sources`, `wiki`) — no agent dependency
3. `ingest` and `lint` routers — stub endpoints first (`return {"status": "not implemented"}`), wire agents in next step

**Neo4j schema constraints** (run once on startup): add uniqueness constraints on node name + label to prevent duplicates.

---

### 3. Auth — JWT + Role-Based Access

**Approach:** Users stored in MongoDB with bcrypt-hashed passwords. Login returns a signed JWT. Protected FastAPI routes check the token and role via `Depends()`. No external auth service needed.

**Libraries:** `PyJWT` (JWT), `passlib[bcrypt]` (password hashing)

**User document (MongoDB):**
```json
{
  "username": "string",
  "hashed_password": "string",
  "role": "admin | viewer"
}
```

**Roles:**

| Role | Access |
|---|---|
| `admin` | Full access — ingest, lint, write nodes/relationships |
| `viewer` | Read-only — browse graph, search |

**Endpoints added:**
- `POST /auth/token` — login with username + password, returns JWT
- `POST /auth/register` — create a new user; restricted to `admin` role after the first account is created

**Add to project layout:**
```
backend/
  routers/
    auth.py
  auth/
    jwt.py       # PyJWT token creation and validation
    deps.py      # FastAPI Depends() helpers: get_current_user, require_admin
```

**Avoiding credential commits:**
- Add `JWT_SECRET_KEY` to `.env` — generate once with `openssl rand -hex 32`
- Add `.env` to `.gitignore` immediately when the repo is created (before any commits)
- Never hardcode passwords or keys in source files — load everything through `config.py` via `pydantic-settings`
- Seed the first admin account manually via a one-off script or the `/auth/register` endpoint on first run, using credentials from `.env`

---

### 4. Agents — LangChain + Anthropic

**Shared tools** (`agents/tools.py`):

| Tool | Library |
|---|---|
| `read_pdf` | `pypdf` |
| `read_website` | `httpx` call to `r.jina.ai/<url>` |
| `read_ocr` | `easyocr` |

**Shared schema** (`agents/prompts.py`):
- Single `GRAPH_SCHEMA` constant imported by both agents
- Contains node label definitions, relationship decision rules (`Ask:` / `Violation if:` framing), hierarchy constraints, and property descriptions
- Source of truth for all LLM prompt context — edit here to change agent behavior globally

**Ingest agent** (`agents/ingest.py`):
- Plain async functions — no graph framework; the workflow is strictly linear (parse → extract) with no branching or looping
- Uses `langchain-anthropic` (`ChatAnthropic`) for LLM calls
- `_parse()` dispatches to the appropriate tool based on input type
- `_extract()` sends `GRAPH_SCHEMA` + existing index + parsed content to the LLM, returns structured JSON proposal
- Router holds the payload; does **not** write to Neo4j until `/ingest/confirm` is called with user-approved proposals

**Lint agent** (`agents/lint.py`):
- LangGraph `StateGraph` — map-reduce structure justifies the framework: parallel per-node checks feed into a single cross-node reduce pass
- Map phase: one LLM call per node, checks internal consistency and relationship validity against `GRAPH_SCHEMA`
- Reduce phase: single LLM call over all per-node findings for cross-node issues (contradictions, orphans, duplicates, cycles)
- Returns structured lint report; router appends it to `log.md`

---

### 5. Evals

**Directory layout:**
```
evals/
  run_evals.py          # runner — calls endpoints, scores output, prints table
  fixtures/
    ingest/
      <fixture-name>/
        input.pdf       # or input.txt / input.url
        gold.json       # expected nodes and relationships
    lint/
      <fixture-name>/
        graph.json      # Neo4j dump with injected defects
        manifest.json   # list of expected issues (node ref, type, severity)
```

**Gold set format (`gold.json` for ingest):**
```json
{
  "nodes": [
    { "label": "Concept", "name": "Gradient Descent" }
  ],
  "relationships": [
    { "from": "Gradient Descent", "to": "Optimization", "type": "SUBCLASS_OF" }
  ]
}
```

**Running evals locally:**
1. Start the backend (`uvicorn backend.main:app --reload`)
2. `python evals/run_evals.py` — prints a table of recall/precision per fixture and agent

Build at least two fixtures per agent before considering the baseline stable. A node counts as correct if its label and name match the gold entry; exact property equality is too strict for LLM output.

---

### 6. Frontend — React + Vite

**Scaffold:** `npm create vite@latest frontend -- --template react`

**Key libraries:**

| Library | Purpose |
|---|---|
| `react-force-graph` | Force-directed graph canvas |
| `react-query` | API data fetching and caching |
| `axios` | HTTP client |
| `react-hook-form` | Node editor forms |

**Views:**

- **Graph explorer** — fetches all nodes and edges, renders `ForceGraph2D`; click a node to open a side panel with its properties
- **Node editor** — form for editing node properties and managing edges; triggered from the side panel
- **Ingest panel** — file upload + optional prompt text field; shows agent proposals in a review table before confirming
- **Lint panel** — "Run lint" button; displays the returned report in a structured list

---

### 7. Local Dev Wiring

`.env` at project root (never committed):
```
ANTHROPIC_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=...
MONGO_URI=mongodb://localhost:27017
```

Run order:
1. `sudo systemctl start neo4j && sudo systemctl start mongod`
2. `uvicorn backend.main:app --reload`
3. `npm run dev` (from `frontend/`)

---

## Phase 2 — Cloud Migration and CI/CD

Phase 1 produces a working local app. This phase makes it accessible from anywhere, replaces local databases with managed cloud services, and adds automated testing and deployment on every push to `main`. Only env vars change — no application code needs to be rewritten.

### 1. Containerize the Backend

Azure and GCP are container-native platforms — containerization is best practice for backend services on both.

- `backend/Dockerfile` — Python image, install deps, `CMD ["uvicorn", ...]`

The React frontend does **not** need a container. `npm run build` produces static files (HTML/CSS/JS) that are deployed directly to a static hosting service.

### 2. Managed Databases

| Service | Cloud replacement | Notes |
|---|---|---|
| Neo4j local | Neo4j AuraDB Free | Drop-in; swap `NEO4J_URI` to AuraDB connection string |
| MongoDB local | MongoDB Atlas Free (M0) | Drop-in; swap `MONGO_URI` to Atlas connection string |

No code changes needed — only env vars change.

### 3. Deploy Services

| Service | GCP option | Azure option | Notes |
|---|---|---|---|
| FastAPI | Cloud Run | Azure Container Apps | Push container image to registry; platform handles scaling and serving |
| React | Firebase Hosting | Azure Static Web Apps | Deploy static build output directly from GitHub; no container |

### 4. CI/CD — GitHub Actions

Two workflows:

**`ci.yml`** — runs on every PR:
- `ruff` lint + `pytest` for backend
- `eslint` + `npm run build` for frontend
- `python evals/run_evals.py` — runs the eval suite against the agent endpoints; fails the build if recall or precision drops below threshold. Requires `ANTHROPIC_API_KEY` stored as a GitHub Actions secret. Note: each eval run makes real API calls — keep the fixture set small enough that the cost per CI run is acceptable.

**`deploy.yml`** — runs on merge to `main`:
- Triggers Render/Railway redeploy via deploy hook URL
- Triggers Vercel redeploy (automatic if repo is linked)

### 5. Secrets

Store all env vars in the deployment platform's secret manager (Render → Environment, Railway → Variables, Vercel → Environment Variables). Remove the local `.env` from any deploy context.

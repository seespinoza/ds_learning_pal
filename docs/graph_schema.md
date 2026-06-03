# Graph Schema

## Relationships

### Hierarchical

| Edge | Direction | Meaning |
|---|---|---|
| `SUBCLASS_OF` | A → B | A is a more specific category of B |
| `INSTANCE_OF` | A → B | A is a specific member of class B |
| `BELONGS_TO` | A → B | A is situated within a field or discipline; B must be a `Domain` node |

### Associative

| Edge | Direction | Meaning |
|---|---|---|
| `ADDRESSES` | A → B | A is a solution or mitigation for B |
| `PART_OF` | A → B | A is a component of B |
| `USED_ON` | A → B | A operates on or is applied to B |

---

## Node Labels

| Label | Description | Examples |
|---|---|---|
| `Domain` | Top-level field or discipline | Statistics, Machine Learning, Linear Algebra |
| `Concept` | Theoretical construct, phenomenon, or framework | Overfitting, Bias-Variance Tradeoff, Regularization |
| `Algorithm` | Step-by-step computational procedure | Gradient Descent, PCA, k-means |
| `Model` | Statistical or ML model family | Linear Regression, Ridge Regression, Random Forest |
| `Technique` | Analytical approach, paradigm, or operational procedure | Bayesian Inference, MLE, Model Training, Cross-Validation, Fine-tuning, RAG |
| `Tool` | Programming language, library, or framework | Python, PyTorch, scikit-learn, LangChain, SQL |
| `Platform` | Infrastructure, database, or cloud service | AWS, PostgreSQL, Pinecone, Docker, Hugging Face Hub |

---

## Decision Rules

### Hierarchical

**`SUBCLASS_OF`** — B organizes things by type. A is a narrower category of the same kind.
- Both nodes share the same or compatible label
- Ask: *"Is A a more specific type of B?"*
- `Supervised Learning --[SUBCLASS_OF]--> Machine Learning`

**`INSTANCE_OF`** — B is a class or family. A is a specific member of it.
- A is an individual; B is a grouping of similar individuals
- Ask: *"Is A a specific example of B?"*
- `Ridge Regression --[INSTANCE_OF]--> Linear Regression`

**`BELONGS_TO`** — B is a field or discipline. A is situated within it.
- B must be labeled `Domain` — this is the hard constraint
- Ask: *"Is B a subject area, not a type or class?"*
- `Eigendecomposition --[BELONGS_TO]--> Linear Algebra`

### Associative

**`PART_OF`** — B is a process or structure with internal components. A is one of those components.
- A is structurally or procedurally inside B
- Ask: *"Would removing A make B incomplete?"*
- `Loss Function --[PART_OF]--> Model Training`

**`ADDRESSES`** — B is a problem, phenomenon, or failure mode. A is a solution or mitigation for it.
- A acts on B to reduce or resolve it
- Ask: *"Does A solve or mitigate B?"*
- `Regularization --[ADDRESSES]--> Overfitting`

**`USED_ON`** — B is an object or structure that A operates on directly.
- A is an algorithm or process; B is what it acts upon
- Ask: *"Does A take B as its direct input or target?"*
- `Gradient Descent --[USED_ON]--> Loss Function`

---

## Node Properties

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

---

## Relationship Properties

| Property | Description |
|---|---|
| `justification` | Short explanation of why this relationship holds |
| `confidence` | `high`, `medium`, or `low` — flags uncertain edges for lint |
| `date_added` | ISO date the edge was created |

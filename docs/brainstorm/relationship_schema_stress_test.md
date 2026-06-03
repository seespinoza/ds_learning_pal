# Relationship Schema Stress Test

Using 17 concepts across Statistics, ML, and Linear Algebra to probe the current vocabulary.

---

## Concepts with Node Labels

| # | Concept | Label |
|---|---|---|
| 1 | Statistics | `Domain` |
| 2 | Machine Learning | `Domain` |
| 3 | Linear Algebra | `Domain` |
| 4 | Model Training | `Technique` |
| 5 | Probability Theory | `Concept` |
| 6 | Bayesian Inference | `Technique` |
| 7 | Maximum Likelihood Estimation (MLE) | `Technique` |
| 8 | Supervised Learning | `Technique` |
| 9 | Linear Regression | `Model` |
| 10 | Ridge Regression | `Model` |
| 11 | Gradient Descent | `Algorithm` |
| 12 | Loss Function | `Concept` |
| 13 | Regularization | `Technique` |
| 14 | Overfitting | `Concept` |
| 15 | Bias-Variance Tradeoff | `Concept` |
| 16 | Eigendecomposition | `Algorithm` |
| 17 | PCA | `Algorithm` |

---

## Edges

```
Probability Theory    --[SUBCLASS_OF]-->  Statistics
Bayesian Inference    --[SUBCLASS_OF]-->  Statistics
MLE                   --[SUBCLASS_OF]-->  Statistics
Supervised Learning   --[SUBCLASS_OF]-->  Machine Learning
Linear Regression     --[INSTANCE_OF]--> Supervised Learning
Ridge Regression      --[INSTANCE_OF]--> Linear Regression
Ridge Regression      --[INSTANCE_OF]--> Regularization
Eigendecomposition    --[PART_OF]-->      Linear Algebra
Loss Function         --[PART_OF]-->      Model Training
Gradient Descent      --[PART_OF]-->      Model Training
Eigendecomposition    --[PART_OF]-->      PCA
Regularization        --[ADDRESSES]-->    Overfitting
Bias-Variance Tradeoff --[ADDRESSES]-->   Overfitting
Gradient Descent      --[USED_ON]-->      Loss Function
```

---

## Resolved from Previous Schema

### 1. Node labels resolve "show me all algorithms" ✓

The previous schema had no node type distinction — queries couldn't filter by kind. Node labels (`Algorithm`, `Model`, `Technique`, etc.) now encode this directly. Gradient Descent, PCA, and Eigendecomposition are all `Algorithm`; Linear Regression and Ridge Regression are both `Model`.

### 2. SUBCLASS_OF replaces SUBFIELD_OF ✓

`SUBCLASS_OF` carries stricter semantics (A is a more specific category of B), which is a better fit than the loosely-defined `SUBFIELD_OF`. Probability Theory is genuinely a more specific category within Statistics.

### 3. INSTANCE_OF replaces TYPE_OF ✓

`INSTANCE_OF` (specific member of a class) is a clearer name than `TYPE_OF`. Ridge Regression is a specific member of the Linear Regression model family.

### 4. Gradient Descent ↔ Loss Function resolved ✓

`USED_ON` makes the relationship explicit and directional: Gradient Descent operates on a Loss Function to minimize it.

```
Gradient Descent --[USED_ON]--> Loss Function
```

### 5. Ridge Regression ↔ Regularization resolved ✓

The previous schema used `RELATED_TO` here. With `INSTANCE_OF`, Ridge Regression is modeled as a specific instance of the Regularization technique — directional and semantically precise.

```
Ridge Regression --[INSTANCE_OF]--> Regularization
```

### 6. Bias-Variance Tradeoff ↔ Overfitting resolved ✓

Previously `RELATED_TO`. Bias-Variance Tradeoff `ADDRESSES` Overfitting — the framework is a direct explanatory tool for diagnosing and mitigating the phenomenon.

```
Bias-Variance Tradeoff --[ADDRESSES]--> Overfitting
```

---

## Remaining Issues

### 1. USED_IN removal leaves Eigendecomposition → PCA ambiguous

Eigendecomposition is a procedure *invoked inside* PCA — it is not a structural component in the same way Loss Function is a component of Model Training. `PART_OF` is the closest fit in the current vocabulary but overstates the compositional relationship.

```
Eigendecomposition --[PART_OF]--> PCA   ← fits, but "used as a step within" is more precise
```

Candidate addition: `USED_IN` — technique or algorithm appears and operates inside a broader method. Would cleanly separate "structural component" (`PART_OF`) from "procedural dependency" (`USED_IN`).

### 2. Cross-domain secondary membership has no edge type

Linear Regression has a primary home in ML (`INSTANCE_OF` Supervised Learning) but is also grounded in Statistics. The previous schema used `RELATED_TO` for this secondary association. With `RELATED_TO` removed and no equivalent, the Stats connection is currently unmodeled.

Same pattern: Gradient Descent relates to both ML and numerical methods in mathematics.

Options: (a) add `RELATED_TO` back as a loose-association escape hatch, (b) accept the gap, (c) add a secondary `INSTANCE_OF` edge to a broader parent.

### 3. SUBCLASS_OF applied to Techniques across a Domain boundary is semantically off

```
Bayesian Inference (Technique) --[SUBCLASS_OF]--> Statistics (Domain)
```

`SUBCLASS_OF` means "A is a more specific category of B" — but a `Technique` is not a subcategory of a `Domain`. Bayesian Inference *belongs to* or *is practiced within* Statistics, which is a different relationship than subclassing.

The edge is useful for navigation but mis-typed. Possible fix: a `BELONGS_TO` edge for Technique/Algorithm/Model → Domain relationships, reserving `SUBCLASS_OF` for same-label hierarchies.

### 4. Probability Theory label is ambiguous

Probability Theory is labeled `Concept`, but it functions more like a `Domain` sub-field (it has its own sub-concepts, theorems, and applications). A `Domain` label would make it feel equivalent to Statistics or Machine Learning, which overstates it. The `Concept` label undersells it.

The schema has no intermediate label for "sub-domain" or "branch" — this is a known gap if the node set grows to include other field-level concepts (e.g., Information Theory, Optimization).

---

## Current Vocabulary

| Edge Type | Meaning | Directed? |
|---|---|---|
| `SUBCLASS_OF` | A is a more specific category of B | Yes |
| `INSTANCE_OF` | A is a specific member of class B | Yes |
| `PART_OF` | A is a structural component of B | Yes |
| `ADDRESSES` | A is a solution or mitigation for B | Yes |
| `USED_ON` | A operates on or is applied to B | Yes |

| Node Label | Description | Examples |
|---|---|---|
| `Domain` | Top-level field or discipline | Statistics, Machine Learning, Linear Algebra |
| `Concept` | Theoretical construct, phenomenon, or framework | Overfitting, Bias-Variance Tradeoff, Loss Function |
| `Algorithm` | Step-by-step computational procedure | Gradient Descent, PCA, Eigendecomposition |
| `Model` | Statistical or ML model family | Linear Regression, Ridge Regression |
| `Technique` | Analytical approach, paradigm, or operational procedure | Bayesian Inference, MLE, Model Training, Regularization, Supervised Learning |
| `Tool` | Programming language, library, or framework | Python, PyTorch, scikit-learn |
| `Platform` | Infrastructure, database, or cloud service | AWS, PostgreSQL, Docker |

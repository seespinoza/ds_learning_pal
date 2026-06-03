# Knowledge Graph Relationship Design — Research Notes

> Reference material for deciding relationship vocabulary in DS Learning Pal.

---

## How others have structured knowledge graphs of large fields

### 1. Wikidata / DBpedia — two-property hierarchy

Wikidata powers Wikipedia's structured data and covers all of human knowledge. They solved hierarchy with just **two core properties**:

- `instance of` — "Logistic Regression **instance of** Classification Algorithm"
- `subclass of` — "Classification Algorithm **subclass of** Supervised Learning"

Plus `part of` for composition. The key insight: **"is a" breaks into two distinct ideas** — membership in a category (`instance of`) vs. a category being a subset of a broader one (`subclass of`).

---

### 2. Mathematics Subject Classification (MSC)

Used by the AMS and zbMATH to classify every math paper ever written. A **pure taxonomy** — three levels deep, no typed edges:

```
62 Statistics
  62J Regression
    62J05 Linear regression
    62J12 Generalized linear models
```

Simple and navigable, but no edges between branches — it can't say "PCA requires Linear Algebra." It's a tree, not a graph.

---

### 3. ACM Computing Classification System

The CS equivalent of MSC. Same pure tree structure, used to classify papers. Same limitation — great for browsing, blind to cross-domain dependencies.

---

### 4. Concept Maps (Novak, 1984 — educational research)

Every link is a **labeled proposition**:

```
Gradient Descent --[minimizes]--> Loss Function
Loss Function --[measures]--> Model Error
```

No fixed vocabulary — you make up the label. Very expressive, but hard to query uniformly and hard to enforce consistency.

---

### 5. WordNet — splits IS-A and PART-OF cleanly

WordNet uses:

- `hypernym/hyponym` — is-a hierarchy ("dog is a hypernym of poodle")
- `holonym/meronym` — part-of hierarchy ("wheel is a meronym of car")

This split is useful because **is-a and part-of have different traversal semantics** — you inherit properties through is-a but not through part-of.

---

## Core Insight: "Hierarchy" in DS/ML is actually three different things

| Relationship | Example | Meaning |
|---|---|---|
| Taxonomic | Random Forest `IS_TYPE_OF` Ensemble Method | Classification / membership |
| Compositional | Backprop `IS_PART_OF` Neural Network Training | Assembly / inclusion |
| Dependency | Calculus `IS_PREREQ_OF` Gradient Descent | Learning order |

Collapsing these into a single `IS_CHILD_OF` loses the ability to query "what do I need to know before X?" vs "what sub-topics make up X?" — those are very different graph traversals.

---

## Proposed Vocabulary (starting point)

| Edge Type | Example | Direction |
|---|---|---|
| `SUBFIELD_OF` | Bayesian Statistics → Statistics | Directed |
| `TYPE_OF` | Ridge Regression → Regularized Linear Model | Directed |
| `PART_OF` | Bayes' Theorem → Bayesian Inference | Directed |
| `PREREQUISITE_OF` | Linear Algebra → PCA | Directed |
| `RELATED_TO` | Regularization ↔ Overfitting | Undirected |

---

## Open Questions

1. Is the **learning dependency / prerequisite** relationship important in v1, or is taxonomy browsing the primary use case?
2. Should relationships always be **directional**, or should some (e.g., `RELATED_TO`) be undirected?
3. **Fixed vocabulary** of edge types, or allow users to define custom types per node?

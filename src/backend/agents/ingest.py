"""
Ingest agent: parse → extract → propose.

Returns a ProposalPayload without writing to Neo4j.
Writing happens only after the user confirms via POST /ingest/confirm.
"""
import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.agents.tools import read_ocr, read_pdf, read_website
from backend.config import settings

_SCHEMA = """\
## Node Labels

- Domain    — Top-level field or discipline (e.g. Machine Learning, Linear Algebra, Statistics)
- Concept   — Theoretical construct, phenomenon, or framework (e.g. Overfitting, Bias-Variance Tradeoff)
- Algorithm — Step-by-step computational procedure (e.g. Gradient Descent, PCA, k-means)
- Model     — Statistical or ML model family (e.g. Linear Regression, Random Forest)
- Technique — Analytical approach, paradigm, or operational procedure (e.g. Cross-Validation, Fine-tuning, RAG)
- Tool      — Programming language, library, or framework (e.g. Python, PyTorch, scikit-learn)
- Platform  — Infrastructure, database, or cloud service (e.g. AWS, PostgreSQL, Docker)

## Relationship Types and Decision Rules

SUBCLASS_OF (A → B): A is a more specific category of B. Both share the same or compatible label.
  Ask: "Is A a more specific *type* of B?" (not a member, not a discipline)
  Example: Supervised Learning --[SUBCLASS_OF]--> Machine Learning

INSTANCE_OF (A → B): A is a specific member of class B. A is an individual; B is a grouping.
  Ask: "Is A a specific *example* of B?" (not a subtype)
  Example: Ridge Regression --[INSTANCE_OF]--> Linear Regression
  Note: Adam is INSTANCE_OF Optimizer, not SUBCLASS_OF. Use this when A is a concrete named thing.

BELONGS_TO (A → B): A is situated within a field or discipline. B MUST be a Domain node — hard constraint.
  Ask: "Is B a subject area, not a type or class?"
  Example: Eigendecomposition --[BELONGS_TO]--> Linear Algebra

PART_OF (A → B): A is a structural or procedural component of B. Removing A makes B incomplete.
  Ask: "Would removing A make B incomplete?"
  Example: Loss Function --[PART_OF]--> Model Training

ADDRESSES (A → B): A is a solution or mitigation for B. B is a problem, phenomenon, or failure mode.
  Ask: "Does A solve or mitigate B?"
  Example: Regularization --[ADDRESSES]--> Overfitting

USED_ON (A → B): A operates on B directly. A is an algorithm or process; B is what it acts upon.
  Ask: "Does A take B as its direct input or target?"
  Example: Gradient Descent --[USED_ON]--> Loss Function

## Relationship Properties

- justification: short explanation of why this relationship holds
- confidence: high | medium | low  (use low when uncertain; lint will flag it)
- date_added: ISO date (leave empty; backend sets this on write)

## Node Properties

- summary: concise description (1-3 sentences)
- aliases: list of other names this concept is known by
- raw_sources: leave empty (backend fills this from the uploaded source)
"""

_EXTRACT_PROMPT = """\
You are a knowledge graph builder for data science, ML, and AI engineering concepts.
Extract all relevant nodes and relationships from the content below.

{schema}

Existing nodes (do not create duplicates — reuse exact names if an entity already exists):
{index}

Return ONLY valid JSON in this exact format, with no markdown fences:
{{
  "nodes": [
    {{"label": "<label>", "name": "<name>", "summary": "<summary>", "aliases": [], "raw_sources": []}}
  ],
  "relationships": [
    {{"from": "<name>", "to": "<name>", "type": "<type>", "justification": "<why>", "confidence": "high|medium|low"}}
  ]
}}

Content to extract from:
{content}
"""


def _llm():
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        temperature=0,
    )


def _parse(input_type: str, input_value: str) -> str:
    if input_type == "pdf":
        return read_pdf.invoke({"file_path": input_value})
    if input_type == "url":
        return read_website.invoke({"url": input_value})
    if input_type == "image":
        return read_ocr.invoke({"file_path": input_value})
    return input_value


def _extract(content: str, index_content: str) -> dict:
    prompt = _EXTRACT_PROMPT.format(
        schema=_SCHEMA,
        index=index_content or "(empty — this is the first ingest)",
        content=content[:12000],
    )
    response = _llm().invoke([HumanMessage(content=prompt)])
    raw = response.content
    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return {"nodes": [], "relationships": [], "parse_error": raw}


async def run_ingest(
    input_type: str,
    input_value: str,
    index_content: str = "",
) -> dict:
    """Run the ingest pipeline and return the proposal payload."""
    content = _parse(input_type, input_value)
    return _extract(content, index_content)

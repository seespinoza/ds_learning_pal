"""
Ingest agent: parse → extract → deduplicate → propose.

Returns a ProposalPayload without writing to Neo4j.
Writing happens only after the user confirms via POST /ingest/confirm.
"""
import json
import os
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.agents.tools import read_ocr, read_pdf, read_website
from backend.config import settings

_SCHEMA = """\
Node labels: Domain, Concept, Algorithm, Model, Technique, Tool, Platform.
Relationship types: SUBCLASS_OF, INSTANCE_OF, BELONGS_TO, ADDRESSES, PART_OF, USED_ON.
Relationship properties: justification (str), confidence (high|medium|low), date_added (ISO date).
Node properties: summary, aliases (list), raw_sources (list), notes, courses (list), videos (list), docs (list), references (list).
"""

_EXTRACT_PROMPT = """\
You are a knowledge graph builder for data science, ML, and AI engineering concepts.
Given the following content, extract all relevant nodes and relationships.

Graph schema:
{schema}

Existing nodes (do not duplicate):
{index}

Return ONLY valid JSON in this exact format:
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


class IngestState(TypedDict):
    input_type: str          # "pdf" | "url" | "image" | "text"
    input_value: str         # file path or raw text
    index_content: str       # current index.md content
    parsed_content: str
    proposal: dict           # nodes + relationships
    messages: Annotated[list, add_messages]


def _llm():
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        temperature=0,
    )


def parse_node(state: IngestState) -> IngestState:
    input_type = state["input_type"]
    val = state["input_value"]

    if input_type == "pdf":
        content = read_pdf.invoke({"file_path": val})
    elif input_type == "url":
        content = read_website.invoke({"url": val})
    elif input_type == "image":
        content = read_ocr.invoke({"file_path": val})
    else:
        content = val

    return {**state, "parsed_content": content}


def extract_node(state: IngestState) -> IngestState:
    prompt = _EXTRACT_PROMPT.format(
        schema=_SCHEMA,
        index=state["index_content"] or "(empty — this is the first ingest)",
        content=state["parsed_content"][:12000],
    )
    llm = _llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content

    try:
        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        proposal = json.loads(raw.strip())
    except Exception:
        proposal = {"nodes": [], "relationships": [], "parse_error": raw}

    return {**state, "proposal": proposal}


def build_ingest_graph() -> StateGraph:
    g = StateGraph(IngestState)
    g.add_node("parse", parse_node)
    g.add_node("extract", extract_node)
    g.set_entry_point("parse")
    g.add_edge("parse", "extract")
    g.add_edge("extract", END)
    return g.compile()


_graph = build_ingest_graph()


async def run_ingest(
    input_type: str,
    input_value: str,
    index_content: str = "",
) -> dict:
    """Run the ingest pipeline and return the proposal payload."""
    result = await _graph.ainvoke({
        "input_type": input_type,
        "input_value": input_value,
        "index_content": index_content,
        "parsed_content": "",
        "proposal": {},
        "messages": [],
    })
    return result["proposal"]

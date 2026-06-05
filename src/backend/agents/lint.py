"""
Lint agent: map-reduce over all nodes.

Map phase: per-node consistency check.
Reduce phase: cross-node check for contradictions, orphans, duplicates.
"""
import json
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from backend.config import settings

_SCHEMA = """\
Node labels: Domain, Concept, Algorithm, Model, Technique, Tool, Platform.
Relationship types: SUBCLASS_OF, INSTANCE_OF, BELONGS_TO, ADDRESSES, PART_OF, USED_ON.
BELONGS_TO target must be a Domain node.
Hierarchical relationships (SUBCLASS_OF, INSTANCE_OF, BELONGS_TO) must not form cycles.
"""

_NODE_CHECK_PROMPT = """\
You are a knowledge graph linter. Check this node and its relationships for issues.

Graph schema:
{schema}

Node data:
{node_data}

Check for:
1. Internal consistency: does the summary agree with the relationships?
2. Stale confidence: any confidence=low edges that appear unresolved?
3. Relationship validity: do edge types match schema decision rules?
4. Wrong target: any BELONGS_TO edge where the target is not a Domain node?

Return ONLY valid JSON:
{{
  "node": "<name>",
  "issues": [
    {{"type": "internal_consistency|stale_confidence|schema_violation|wrong_target", "severity": "error|warning", "detail": "<short description>"}}
  ]
}}
Return {{"node": "<name>", "issues": []}} if no issues found.
"""

_CROSS_CHECK_PROMPT = """\
You are a knowledge graph linter. Review the per-node findings below and check for cross-node problems.

All per-node findings:
{findings}

All nodes summary:
{index}

Check for:
1. Contradictions: two nodes making incompatible claims about the same concept
2. Orphan nodes: nodes with no relationships
3. Duplicate nodes: same concept under different names
4. Hierarchy cycles: circular SUBCLASS_OF or INSTANCE_OF chains

Return ONLY valid JSON:
{{
  "cross_node_issues": [
    {{"type": "contradiction|orphan|duplicate|cycle", "severity": "error|warning", "nodes": ["<name>", ...], "detail": "<short description>"}}
  ]
}}
"""


class LintState(TypedDict):
    index_content: str
    node_list: list[dict]      # [{label, name, props, relationships}]
    per_node_findings: list[dict]
    final_report: dict
    messages: Annotated[list, add_messages]


def _llm():
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        temperature=0,
    )


def map_nodes(state: LintState) -> LintState:
    llm = _llm()
    findings = []
    for node in state["node_list"]:
        prompt = _NODE_CHECK_PROMPT.format(
            schema=_SCHEMA,
            node_data=json.dumps(node, indent=2),
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            findings.append(json.loads(raw.strip()))
        except Exception:
            findings.append({"node": node.get("name", "unknown"), "issues": [], "parse_error": raw})

    return {**state, "per_node_findings": findings}


def reduce_findings(state: LintState) -> LintState:
    llm = _llm()
    prompt = _CROSS_CHECK_PROMPT.format(
        findings=json.dumps(state["per_node_findings"], indent=2),
        index=state["index_content"][:8000],
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content
    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        cross = json.loads(raw.strip())
    except Exception:
        cross = {"cross_node_issues": [], "parse_error": raw}

    report = {
        "per_node_findings": state["per_node_findings"],
        "cross_node_issues": cross.get("cross_node_issues", []),
    }
    return {**state, "final_report": report}


def build_lint_graph() -> StateGraph:
    g = StateGraph(LintState)
    g.add_node("map_nodes", map_nodes)
    g.add_node("reduce_findings", reduce_findings)
    g.set_entry_point("map_nodes")
    g.add_edge("map_nodes", "reduce_findings")
    g.add_edge("reduce_findings", END)
    return g.compile()


_graph = build_lint_graph()


async def run_lint(node_list: list[dict], index_content: str = "") -> dict:
    """Run the lint pipeline and return the structured report."""
    result = await _graph.ainvoke({
        "index_content": index_content,
        "node_list": node_list,
        "per_node_findings": [],
        "final_report": {},
        "messages": [],
    })
    return result["final_report"]

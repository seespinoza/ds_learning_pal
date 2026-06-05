import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.agents.lint import run_lint
from backend.auth.deps import require_admin
from backend.config import settings
from backend.db.neo4j import get_session

router = APIRouter(prefix="/lint", tags=["lint"])


def _read_index() -> str:
    path = os.path.join(settings.wiki_dir, "index.md")
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


def _append_log(content: str):
    path = os.path.join(settings.wiki_dir, "log.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(path, "a") as f:
        f.write(f"\n## Lint — {ts}\n{content}\n")


async def _fetch_all_nodes() -> list[dict]:
    """Fetch every node with its properties and connected relationships from Neo4j."""
    async with get_session() as session:
        result = await session.run(
            "MATCH (n) "
            "OPTIONAL MATCH (n)-[r]->(m) "
            "RETURN labels(n)[0] AS label, n.name AS name, properties(n) AS props, "
            "collect({type: type(r), target: m.name, target_label: labels(m)[0], props: properties(r)}) AS rels"
        )
        records = await result.data()

    nodes = {}
    for r in records:
        key = (r["label"], r["name"])
        if key not in nodes:
            nodes[key] = {
                "label": r["label"],
                "name": r["name"],
                "properties": r["props"],
                "relationships": [],
            }
        for rel in r["rels"]:
            if rel["type"]:
                nodes[key]["relationships"].append(rel)

    return list(nodes.values())


@router.post("")
async def lint(_: dict = Depends(require_admin)):
    """Run the lint agent over the full graph and return the structured report."""
    node_list = await _fetch_all_nodes()
    index = _read_index()
    report = await run_lint(node_list, index)

    total_issues = sum(
        len(f.get("issues", [])) for f in report.get("per_node_findings", [])
    ) + len(report.get("cross_node_issues", []))

    _append_log(f"Lint complete. {len(node_list)} nodes scanned. {total_issues} issues found.")

    return {
        "nodes_scanned": len(node_list),
        "total_issues": total_issues,
        **report,
    }


class FixtureRequest(BaseModel):
    graph: dict  # {nodes: [...], relationships: [...]}


@router.post("/fixture")
async def lint_fixture(req: FixtureRequest, _: dict = Depends(require_admin)):
    """Run the lint agent against an in-memory graph snapshot (used by evals)."""
    nodes = req.graph.get("nodes", [])
    rels = req.graph.get("relationships", [])

    rel_map: dict[str, list] = {n["name"]: [] for n in nodes}
    for r in rels:
        src = r.get("from")
        if src in rel_map:
            rel_map[src].append({
                "type": r.get("type"),
                "target": r.get("to"),
                "target_label": None,
                "props": {k: v for k, v in r.items() if k not in ("from", "to", "type")},
            })

    node_list = [
        {
            "label": n.get("label"),
            "name": n.get("name"),
            "properties": {k: v for k, v in n.items() if k not in ("label", "name")},
            "relationships": rel_map.get(n["name"], []),
        }
        for n in nodes
    ]

    report = await run_lint(node_list, "")
    total_issues = sum(
        len(f.get("issues", [])) for f in report.get("per_node_findings", [])
    ) + len(report.get("cross_node_issues", []))

    return {"nodes_scanned": len(node_list), "total_issues": total_issues, **report}

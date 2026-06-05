import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.agents.ingest import run_ingest
from backend.auth.deps import require_admin
from backend.config import settings
from backend.db.neo4j import get_session

router = APIRouter(prefix="/ingest", tags=["ingest"])

# In-memory pending proposals keyed by a simple incrementing ID.
# Fine for a single-process local server; Phase 2 can move to Redis/DB.
_pending: dict[int, dict] = {}
_counter = 0


class IngestRequest(BaseModel):
    input_type: str       # "pdf" | "url" | "image" | "text"
    input_value: str      # file path or raw text/URL
    source_id: str | None = None   # MongoDB source ID for file ingests


class ConfirmRequest(BaseModel):
    proposal_id: int
    nodes: list[dict]
    relationships: list[dict]


def _read_index() -> str:
    path = os.path.join(settings.wiki_dir, "index.md")
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


def _append_log(message: str):
    path = os.path.join(settings.wiki_dir, "log.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(path, "a") as f:
        f.write(f"\n## {ts}\n{message}\n")


def _update_index(nodes: list[dict]):
    path = os.path.join(settings.wiki_dir, "index.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    existing_lines: list[str] = []
    if os.path.exists(path):
        with open(path) as f:
            existing_lines = f.readlines()

    existing_names = {
        line.split("|")[1].strip()
        for line in existing_lines
        if line.startswith("|") and not line.startswith("| Name")
    }

    with open(path, "a") as f:
        if not existing_lines:
            f.write("| Name | Label | Summary |\n|---|---|---|\n")
        for node in nodes:
            name = node.get("name", "")
            if name not in existing_names:
                label = node.get("label", "")
                summary = (node.get("summary") or "").replace("\n", " ")[:120]
                f.write(f"| {name} | {label} | {summary} |\n")


@router.post("")
async def ingest(req: IngestRequest, _: dict = Depends(require_admin)):
    """Trigger the ingest agent. Returns a proposal for human review."""
    global _counter
    index = _read_index()
    proposal = await run_ingest(req.input_type, req.input_value, index)

    _counter += 1
    _pending[_counter] = {
        "proposal": proposal,
        "source_id": req.source_id,
        "input_value": req.input_value,
    }
    return {"proposal_id": _counter, **proposal}


@router.post("/confirm")
async def confirm(req: ConfirmRequest, _: dict = Depends(require_admin)):
    """Write confirmed proposals to Neo4j and update index.md / log.md."""
    if req.proposal_id not in _pending:
        raise HTTPException(status_code=404, detail="Proposal ID not found or already confirmed")

    pending = _pending.pop(req.proposal_id)

    async with get_session() as session:
        for node in req.nodes:
            label = node.pop("label")
            name = node.get("name")
            props = {k: v for k, v in node.items() if v is not None}
            await session.run(
                f"MERGE (n:{label} {{name: $name}}) SET n += $props",
                name=name,
                props=props,
            )

        for rel in req.relationships:
            from datetime import date
            props = {
                "justification": rel.get("justification"),
                "confidence": rel.get("confidence", "high"),
                "date_added": date.today().isoformat(),
            }
            await session.run(
                f"MATCH (a {{name: $from_name}}), (b {{name: $to_name}}) "
                f"MERGE (a)-[r:{rel['type']}]->(b) SET r += $props",
                from_name=rel["from"],
                to_name=rel["to"],
                props=props,
            )

    _update_index(req.nodes)
    summary = f"Ingested {len(req.nodes)} nodes and {len(req.relationships)} relationships from `{pending['input_value']}`."
    _append_log(summary)

    return {"status": "committed", "nodes": len(req.nodes), "relationships": len(req.relationships)}

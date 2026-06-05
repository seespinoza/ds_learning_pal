from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Any

from backend.auth.deps import get_current_user, require_admin
from backend.db.neo4j import get_session

router = APIRouter(prefix="/nodes", tags=["nodes"])

VALID_LABELS = {"Domain", "Concept", "Algorithm", "Model", "Technique", "Tool", "Platform"}


class NodeCreate(BaseModel):
    label: str
    name: str
    summary: str | None = None
    aliases: list[str] = []
    notes: str | None = None
    raw_sources: list[str] = []
    courses: list[str] = []
    videos: list[str] = []
    docs: list[str] = []
    references: list[str] = []


class NodeUpdate(BaseModel):
    summary: str | None = None
    aliases: list[str] | None = None
    notes: str | None = None
    raw_sources: list[str] | None = None
    courses: list[str] | None = None
    videos: list[str] | None = None
    docs: list[str] | None = None
    references: list[str] | None = None


def _node_to_dict(record_node) -> dict:
    props = dict(record_node.items())
    props["label"] = list(record_node.labels)[0]
    return props


@router.get("")
async def list_nodes(
    label: str | None = Query(None),
    _: dict = Depends(get_current_user),
):
    label_filter = f":{label}" if label else ""
    async with get_session() as session:
        result = await session.run(f"MATCH (n{label_filter}) RETURN n")
        records = await result.data()
    return [_node_to_dict(r["n"]) for r in records]


@router.get("/{label}/{name}")
async def get_node(label: str, name: str, _: dict = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.run(
            f"MATCH (n:{label} {{name: $name}}) RETURN n", name=name
        )
        record = await result.single()
    if not record:
        raise HTTPException(status_code=404, detail="Node not found")
    return _node_to_dict(record["n"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_node(node: NodeCreate, _: dict = Depends(require_admin)):
    if node.label not in VALID_LABELS:
        raise HTTPException(status_code=422, detail=f"Invalid label. Choose from {VALID_LABELS}")
    props = node.model_dump(exclude={"label"})
    async with get_session() as session:
        result = await session.run(
            f"CREATE (n:{node.label} $props) RETURN n", props=props
        )
        record = await result.single()
    return _node_to_dict(record["n"])


@router.patch("/{label}/{name}")
async def update_node(label: str, name: str, update: NodeUpdate, _: dict = Depends(require_admin)):
    props = {k: v for k, v in update.model_dump().items() if v is not None}
    if not props:
        raise HTTPException(status_code=422, detail="No fields to update")
    async with get_session() as session:
        result = await session.run(
            f"MATCH (n:{label} {{name: $name}}) SET n += $props RETURN n",
            name=name,
            props=props,
        )
        record = await result.single()
    if not record:
        raise HTTPException(status_code=404, detail="Node not found")
    return _node_to_dict(record["n"])


@router.delete("/{label}/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(label: str, name: str, _: dict = Depends(require_admin)):
    async with get_session() as session:
        result = await session.run(
            f"MATCH (n:{label} {{name: $name}}) DETACH DELETE n RETURN count(n) AS deleted",
            name=name,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Node not found")

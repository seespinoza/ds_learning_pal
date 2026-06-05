from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth.deps import get_current_user, require_admin
from backend.db.neo4j import get_session

router = APIRouter(prefix="/relationships", tags=["relationships"])

VALID_TYPES = {"SUBCLASS_OF", "INSTANCE_OF", "BELONGS_TO", "ADDRESSES", "PART_OF", "USED_ON"}
VALID_CONFIDENCE = {"high", "medium", "low"}


class RelationshipCreate(BaseModel):
    from_label: str
    from_name: str
    to_label: str
    to_name: str
    type: str
    justification: str | None = None
    confidence: str = "high"


class RelationshipUpdate(BaseModel):
    justification: str | None = None
    confidence: str | None = None


@router.get("")
async def list_relationships(_: dict = Depends(get_current_user)):
    async with get_session() as session:
        result = await session.run(
            "MATCH (a)-[r]->(b) RETURN "
            "labels(a)[0] AS from_label, a.name AS from_name, "
            "type(r) AS type, properties(r) AS props, "
            "labels(b)[0] AS to_label, b.name AS to_name"
        )
        records = await result.data()
    return [
        {
            "from_label": r["from_label"],
            "from_name": r["from_name"],
            "to_label": r["to_label"],
            "to_name": r["to_name"],
            "type": r["type"],
            **r["props"],
        }
        for r in records
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_relationship(rel: RelationshipCreate, _: dict = Depends(require_admin)):
    if rel.type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid relationship type. Choose from {VALID_TYPES}")
    if rel.confidence not in VALID_CONFIDENCE:
        raise HTTPException(status_code=422, detail=f"confidence must be one of {VALID_CONFIDENCE}")

    props = {
        "justification": rel.justification,
        "confidence": rel.confidence,
        "date_added": date.today().isoformat(),
    }

    async with get_session() as session:
        result = await session.run(
            f"MATCH (a:{rel.from_label} {{name: $from_name}}), (b:{rel.to_label} {{name: $to_name}}) "
            f"CREATE (a)-[r:{rel.type} $props]->(b) "
            "RETURN type(r) AS type, properties(r) AS props",
            from_name=rel.from_name,
            to_name=rel.to_name,
            props=props,
        )
        record = await result.single()
    if not record:
        raise HTTPException(status_code=404, detail="One or both nodes not found")
    return {"from_name": rel.from_name, "to_name": rel.to_name, "type": record["type"], **record["props"]}


@router.patch("/{from_label}/{from_name}/{type}/{to_label}/{to_name}")
async def update_relationship(
    from_label: str,
    from_name: str,
    type: str,
    to_label: str,
    to_name: str,
    update: RelationshipUpdate,
    _: dict = Depends(require_admin),
):
    props = {k: v for k, v in update.model_dump().items() if v is not None}
    if not props:
        raise HTTPException(status_code=422, detail="No fields to update")
    async with get_session() as session:
        result = await session.run(
            f"MATCH (a:{from_label} {{name: $from_name}})-[r:{type}]->(b:{to_label} {{name: $to_name}}) "
            "SET r += $props RETURN type(r) AS type, properties(r) AS props",
            from_name=from_name,
            to_name=to_name,
            props=props,
        )
        record = await result.single()
    if not record:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return {"from_name": from_name, "to_name": to_name, "type": record["type"], **record["props"]}


@router.delete("/{from_label}/{from_name}/{type}/{to_label}/{to_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    from_label: str,
    from_name: str,
    type: str,
    to_label: str,
    to_name: str,
    _: dict = Depends(require_admin),
):
    async with get_session() as session:
        result = await session.run(
            f"MATCH (a:{from_label} {{name: $from_name}})-[r:{type}]->(b:{to_label} {{name: $to_name}}) "
            "DELETE r RETURN count(r) AS deleted",
            from_name=from_name,
            to_name=to_name,
        )
        record = await result.single()
    if not record or record["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Relationship not found")

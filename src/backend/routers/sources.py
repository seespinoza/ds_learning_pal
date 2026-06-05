from datetime import datetime, timezone
from io import BytesIO

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from backend.auth.deps import get_current_user, require_admin
from backend.db.mongo import get_db, get_gridfs

router = APIRouter(prefix="/sources", tags=["sources"])


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid ObjectId")


@router.get("")
async def list_sources(_: dict = Depends(get_current_user)):
    db = get_db()
    cursor = db.source_metadata.find({}, {"_id": 1, "filename": 1, "file_type": 1, "tags": 1, "uploaded_at": 1})
    docs = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        docs.append(doc)
    return docs


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_source(
    file: UploadFile = File(...),
    tags: str = Form(""),
    _: dict = Depends(require_admin),
):
    content = await file.read()
    fs = get_gridfs()
    file_id = await fs.upload_from_stream(file.filename, BytesIO(content))

    db = get_db()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    await db.source_metadata.insert_one({
        "_id": file_id,
        "filename": file.filename,
        "file_type": file.content_type,
        "tags": tag_list,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(content),
    })
    return {"id": str(file_id), "filename": file.filename}


@router.get("/{source_id}")
async def get_source(source_id: str, _: dict = Depends(get_current_user)):
    db = get_db()
    meta = await db.source_metadata.find_one({"_id": _oid(source_id)})
    if not meta:
        raise HTTPException(status_code=404, detail="Source not found")
    meta["id"] = str(meta.pop("_id"))
    return meta


@router.get("/{source_id}/download")
async def download_source(source_id: str, _: dict = Depends(get_current_user)):
    db = get_db()
    meta = await db.source_metadata.find_one({"_id": _oid(source_id)}, {"filename": 1, "file_type": 1})
    if not meta:
        raise HTTPException(status_code=404, detail="Source not found")

    fs = get_gridfs()
    buf = BytesIO()
    await fs.download_to_stream(_oid(source_id), buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type=meta.get("file_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{meta["filename"]}"'},
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str, _: dict = Depends(require_admin)):
    oid = _oid(source_id)
    db = get_db()
    result = await db.source_metadata.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    fs = get_gridfs()
    try:
        await fs.delete(oid)
    except Exception:
        pass

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.deps import get_current_user, require_admin
from backend.config import settings

router = APIRouter(prefix="/wiki", tags=["wiki"])

ALLOWED_FILES = {"index.md", "log.md"}


def _wiki_path(filename: str) -> str:
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown wiki file. Must be one of {ALLOWED_FILES}")
    return os.path.join(settings.wiki_dir, filename)


@router.get("/{filename}")
async def read_wiki(filename: str, _: dict = Depends(get_current_user)):
    path = _wiki_path(filename)
    if not os.path.exists(path):
        return {"filename": filename, "content": ""}
    with open(path, "r") as f:
        return {"filename": filename, "content": f.read()}


class WikiWrite(BaseModel):
    content: str


@router.put("/{filename}")
async def write_wiki(filename: str, body: WikiWrite, _: dict = Depends(require_admin)):
    path = _wiki_path(filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(body.content)
    return {"filename": filename, "written": True}

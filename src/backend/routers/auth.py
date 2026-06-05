from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext

from backend.auth.jwt import create_access_token
from backend.auth.deps import get_current_user
from backend.db.mongo import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VALID_ROLES = {"admin", "viewer"}


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


@router.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    user = await db.users.find_one({"username": form.username})
    if not user or not pwd_context.verify(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """
    Open for the very first user (bootstrap). After that, admin token required.
    The caller must include a valid admin Bearer token in subsequent registrations.
    FastAPI resolves this dynamically — see _check_registration_auth below.
    """
    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")

    db = get_db()
    count = await db.users.count_documents({})

    # Only the first registration is unauthenticated
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required after initial setup. Use POST /auth/register with an admin token.",
        )

    if await db.users.find_one({"username": req.username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    await db.users.insert_one({
        "username": req.username,
        "hashed_password": pwd_context.hash(req.password),
        "role": req.role,
    })
    return {"username": req.username, "role": req.role}


@router.post("/register/admin", status_code=status.HTTP_201_CREATED)
async def register_as_admin(req: RegisterRequest, caller: dict = Depends(get_current_user)):
    """Admin-only endpoint for creating additional users after bootstrap."""
    if caller.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")

    db = get_db()
    if await db.users.find_one({"username": req.username}):
        raise HTTPException(status_code=409, detail="Username already taken")

    await db.users.insert_one({
        "username": req.username,
        "hashed_password": pwd_context.hash(req.password),
        "role": req.role,
    })
    return {"username": req.username, "role": req.role}

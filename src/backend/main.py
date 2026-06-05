from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.neo4j import apply_constraints, close_driver
from backend.db.mongo import close_client
from backend.routers import auth, nodes, relationships, sources, wiki, ingest, lint


@asynccontextmanager
async def lifespan(app: FastAPI):
    await apply_constraints()
    yield
    await close_driver()
    await close_client()


app = FastAPI(title="DS Learning Pal", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(relationships.router)
app.include_router(sources.router)
app.include_router(wiki.router)
app.include_router(ingest.router)
app.include_router(lint.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

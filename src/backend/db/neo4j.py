from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncDriver
from backend.config import settings

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def get_session():
    driver = await get_driver()
    async with driver.session() as session:
        yield session


async def apply_constraints():
    """Run once on startup to enforce uniqueness on node name + label."""
    labels = ["Domain", "Concept", "Algorithm", "Model", "Technique", "Tool", "Platform"]
    async with get_session() as session:
        for label in labels:
            await session.run(
                f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.name IS UNIQUE"
            )

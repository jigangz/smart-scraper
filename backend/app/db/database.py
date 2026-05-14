import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Read DATABASE_URL from env (set by docker-compose to a volume-mounted path),
# fall back to volume-mounted default so backend + worker + beat share state.
# Bug history: hardcoded "./scraper.db" caused split-brain between backend (created table)
# and worker (couldn't find table) since each container had its own writable /app layer.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/scraper.db")

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

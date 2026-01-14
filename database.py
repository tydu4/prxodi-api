from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from db.models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Use asyncpg driver
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False, 
    autoflush=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def init_async_db():
    async with engine.begin() as conn:
        # Create tables if they don't exist (useful for testing/first run)
        # In production, use Alembic
        await conn.run_sync(Base.metadata.create_all)

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.sessions.database_session_service import DatabaseSessionService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

session_service=DatabaseSessionService(
    'mysql+aiomysql://root:password@127.0.0.1:3306/schema1'
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        yield db

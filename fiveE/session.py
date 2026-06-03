import os
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.sessions.database_session_service import DatabaseSessionService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .models import ChatHistory

load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

if not all([host, port, user, password, database]):
    raise RuntimeError("5E database config missing: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD and DB_NAME are required")

DB1_URL = "mysql+aiomysql://{}:{}@{}:{}/{}".format(user, password, host, port, database)
engine1 = create_async_engine(DB1_URL, pool_pre_ping=True)
SessionLocal1 = async_sessionmaker(autocommit=False, autoflush=False, bind=engine1)

session_db_path = Path("data") / "fivee_sessions.db"
session_db_path.parent.mkdir(parents=True, exist_ok=True)
DB2_URL = os.getenv("SESSION_DATABASE_URL", f"sqlite+aiosqlite:///{session_db_path.as_posix()}")
engine2 = create_async_engine(DB2_URL, pool_pre_ping=True)
SessionLocal2 = async_sessionmaker(autocommit=False, autoflush=False, bind=engine2)
session_service = DatabaseSessionService(DB2_URL)


async def get_db1() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal1() as db:
        yield db


async def get_db2() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal2() as db:
        yield db


# Default alias
get_db = get_db1

async def check_session_exists(user_id: str, course_id: str) -> bool:
    async with SessionLocal2() as db:
        stmt = select(ChatHistory.id).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == course_id
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar() is not None

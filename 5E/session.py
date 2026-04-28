import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.sessions.database_session_service import DatabaseSessionService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

DB1_URL = "mysql+aiomysql://{}:{}@{}:{}/{}".format(user, password, host, port, database)
engine1 = create_async_engine(DB1_URL, pool_pre_ping=True)
SessionLocal1 = async_sessionmaker(autocommit=False, autoflush=False, bind=engine1)

DB2_URL = os.getenv("SESSION_DATABASE_URL", "mysql+aiomysql://root:password@127.0.0.1:3306/schema1")
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

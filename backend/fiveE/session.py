"""Use the shared MySQL configuration and isolated fivee_* ADK tables."""
import os
from types import SimpleNamespace

from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.sessions.migration import _schema_check_utils
from sqlalchemy.engine import URL
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from tools.env_loader import load_project_env
from . import storage_schema

load_project_env()

required = ('DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME')
if not all(os.getenv(key) for key in required):
    raise RuntimeError('5E database config missing: ' + ', '.join(required))

DB1_URL = URL.create(
    'mysql+aiomysql',
    username=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD'],
    host=os.environ['DB_HOST'],
    port=int(os.environ['DB_PORT']),
    database=os.environ['DB_NAME'],
    query={'charset': os.getenv('DB_CHARSET', 'utf8mb4')},
)
engine1 = create_async_engine(DB1_URL, pool_pre_ping=True)
SessionLocal1 = async_sessionmaker(autocommit=False, autoflush=False, bind=engine1)


class CourseAgentSessionService(DatabaseSessionService):
    """Retain ADK behavior with tables separate from website login sessions.

    The ADK v1 schema is pinned with google-adk==2.1.0. Its default sessions and
    user_states tables conflict with application tables in dev20260912, so all
    ADK models and foreign keys use the fivee_ prefix in the same schema.
    """

    def _get_schema_classes(self):
        return SimpleNamespace(
            StorageSession=storage_schema.StorageSession,
            StorageEvent=storage_schema.StorageEvent,
            StorageAppState=storage_schema.StorageAppState,
            StorageUserState=storage_schema.StorageUserState,
        )

    async def _prepare_tables(self):
        if self._tables_created:
            return
        async with self._table_creation_lock:
            if self._tables_created:
                return
            async with self.db_engine.begin() as connection:
                await connection.run_sync(storage_schema.Base.metadata.create_all)
            async with self.database_session_factory() as db:
                key = _schema_check_utils.SCHEMA_VERSION_KEY
                metadata = await db.get(storage_schema.StorageMetadata, key)
                if metadata and metadata.value != _schema_check_utils.LATEST_SCHEMA_VERSION:
                    raise RuntimeError('Unsupported fivee_* schema version: ' + metadata.value)
                if not metadata:
                    db.add(storage_schema.StorageMetadata(key=key, value=_schema_check_utils.LATEST_SCHEMA_VERSION))
                    await db.commit()
            self._db_schema_version = _schema_check_utils.LATEST_SCHEMA_VERSION
            self._tables_created = True

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        """Delete events and session atomically without relying on MySQL FK grants."""
        await self._prepare_tables()
        predicates = (
            storage_schema.StorageSession.app_name == app_name,
            storage_schema.StorageSession.user_id == user_id,
            storage_schema.StorageSession.id == session_id,
        )
        async with self._with_session_lock(app_name=app_name, user_id=user_id, session_id=session_id):
            async with self.database_session_factory() as db:
                async with db.begin():
                    # Use the same parent-row lock as append_event, including
                    # concurrent writers in another worker/process.
                    await db.execute(select(storage_schema.StorageSession).where(*predicates).with_for_update())
                    await db.execute(delete(storage_schema.StorageEvent).where(
                        storage_schema.StorageEvent.app_name == app_name,
                        storage_schema.StorageEvent.user_id == user_id,
                        storage_schema.StorageEvent.session_id == session_id,
                    ))
                    await db.execute(delete(storage_schema.StorageSession).where(*predicates))


DB2_URL = DB1_URL
session_service = CourseAgentSessionService(DB2_URL)
engine2 = session_service.db_engine
SessionLocal2 = session_service.database_session_factory
get_db = SessionLocal1
get_agent_db = SessionLocal2


async def check_session_exists(user_id: str, course_id: str) -> bool:
    return await session_service.get_session(
        app_name='agents', user_id=str(user_id), session_id=str(course_id),
    ) is not None

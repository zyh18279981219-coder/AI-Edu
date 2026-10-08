"""Regression checks for ADK sharing the business database without table clashes."""
import asyncio

from google.adk.events import Event, EventActions
from google.genai import types
from sqlalchemy import text

from fiveE.session import CourseAgentSessionService


def test_prefixed_storage_keeps_login_tables_and_restores_agent_state():
    async def run():
        service = CourseAgentSessionService('sqlite+aiosqlite:///:memory:')
        async with service.db_engine.begin() as connection:
            await connection.execute(text('CREATE TABLE sessions (session_id TEXT PRIMARY KEY, username TEXT)'))
            await connection.execute(text("INSERT INTO sessions VALUES ('login', 'student')"))
            await connection.execute(text('CREATE TABLE user_states (username TEXT PRIMARY KEY, payload_json TEXT)'))
        try:
            # Exercise application cleanup even with DB foreign keys disabled.
            async with service.db_engine.begin() as connection:
                await connection.execute(text('PRAGMA foreign_keys=OFF'))
            session = await service.create_session(app_name='agents', user_id='student', session_id='42')
            await service.append_event(session, Event(
                author='user', invocation_id='round1',
                content=types.Content(role='user', parts=[types.Part(text='hello')]),
                actions=EventActions(state_delta={'stage': 'engagement', 'user:visits': 1}),
            ))
            restored = await service.get_session(app_name='agents', user_id='student', session_id='42')
            assert restored.state['stage'] == 'engagement'
            assert restored.state['user:visits'] == 1
            assert restored.events[0].content.parts[0].text == 'hello'
            await service.append_event(restored, Event(author='assistant', invocation_id='round2'))
            assert len((await service.get_session(app_name='agents', user_id='student', session_id='42')).events) == 2
            await service.delete_session(app_name='agents', user_id='student', session_id='42')
            assert await service.get_session(app_name='agents', user_id='student', session_id='42') is None
            async with service.db_engine.connect() as connection:
                assert (await connection.execute(text('SELECT username FROM sessions'))).scalar() == 'student'
                assert (await connection.execute(text('SELECT count(*) FROM fivee_events'))).scalar() == 0
        finally:
            await service.db_engine.dispose()
    asyncio.run(run())


def test_mysql_schema_does_not_require_references_grant():
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects.mysql import dialect
    from fiveE.storage_schema import StorageEvent
    assert 'FOREIGN KEY' not in str(CreateTable(StorageEvent.__table__).compile(dialect=dialect()))

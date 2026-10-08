import asyncio
import importlib.util
from pathlib import Path

from google.adk.events import Event
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from fiveE.session import CourseAgentSessionService


def test_sqlite_history_copy_is_repeatable_and_keeps_events(tmp_path):
    spec = importlib.util.spec_from_file_location('fivee_migration', Path(__file__).parents[1]/'tools/migrate_fivee_sqlite.py')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    async def run():
        source_path = tmp_path/'old.db'
        source = DatabaseSessionService('sqlite+aiosqlite:///' + source_path.as_posix())
        session = await source.create_session(app_name='agents', user_id='existing_student', session_id='7', state={'stage': 'exploration'})
        await source.append_event(session, Event(author='user', invocation_id='original-turn', content=types.Content(role='user', parts=[types.Part(text='original learning question')])))
        await source.db_engine.dispose()
        target = CourseAgentSessionService('sqlite+aiosqlite:///' + (tmp_path/'new.db').as_posix())
        migration.session_service = target
        await migration.migrate(str(source_path))
        await migration.migrate(str(source_path))
        restored = await target.get_session(app_name='agents', user_id='existing_student', session_id='7')
        assert restored.state['stage'] == 'exploration'
        assert len(restored.events) == 1
        assert restored.events[0].id == session.events[0].id
        assert restored.events[0].content.parts[0].text == 'original learning question'
        await target.db_engine.dispose()
    asyncio.run(run())

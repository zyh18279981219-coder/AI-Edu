"""Copy an offline ADK v1 SQLite snapshot into the shared fivee_* MySQL tables.

Usage: python backend/tools/migrate_fivee_sqlite.py /path/to/snapshot.db
Existing primary keys must match exactly; conflicts abort the whole transaction.
"""
import asyncio
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fiveE import storage_schema as schema
from fiveE.session import session_service


async def migrate(source: str):
    path = Path(source).resolve(strict=True)
    source_db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    source_db.row_factory = sqlite3.Row
    models = [schema.StorageAppState, schema.StorageUserState,
              schema.StorageSession, schema.StorageEvent]
    await session_service._prepare_tables()
    counts = {}
    try:
        async with session_service.database_session_factory() as target:
            async with target.begin():
                for model in models:
                    table = model.__table__
                    old_name = table.name.removeprefix('fivee_')
                    counts[old_name] = {'inserted': 0, 'existing': 0}
                    for row in source_db.execute('SELECT * FROM ' + old_name):
                        data = dict(row)
                        for name in ['state', 'event_data']:
                            if isinstance(data.get(name), str):
                                data[name] = json.loads(data[name])
                        for name in ['create_time', 'update_time', 'timestamp']:
                            if isinstance(data.get(name), str):
                                data[name] = datetime.fromisoformat(data[name])
                        identity = tuple(data[c.name] for c in table.primary_key)
                        existing = await target.get(model, identity)
                        if existing:
                            if any(getattr(existing, k) != v for k, v in data.items()):
                                raise RuntimeError(f'Existing {table.name} key conflicts; migration rolled back')
                            counts[old_name]['existing'] += 1
                        else:
                            target.add(model(**data))
                            counts[old_name]['inserted'] += 1
                    await target.flush()
        print(json.dumps(counts, ensure_ascii=False))
    finally:
        source_db.close()
        await session_service.db_engine.dispose()


if __name__ == '__main__':
    asyncio.run(migrate(sys.argv[1]))

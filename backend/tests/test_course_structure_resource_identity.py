import threading
from contextlib import contextmanager

from DatabaseModule.mysql_store import MySQLStore


def test_structure_sync_upserts_existing_resources_and_keeps_review_state():
    statements = []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, sql, args): statements.append((' '.join(sql.split()), args))
        def fetchall(self):
            return [dict(node_id='p', resource_path='https://example.org/a.pdf',
                         quality_status='passed', review_status='disabled', is_enabled=0, is_deleted=0)]
    class Conn:
        def cursor(self): return Cursor()
    class Store(MySQLStore):
        @contextmanager
        def connection(self): yield Conn()
    store = Store.__new__(Store)
    store._lock = threading.RLock()
    result = store.sync_course_from_graph('test', {'name': 'Course', 'children': [
        {'name': 'Renamed point', 'node_id': 'p', 'description': 'Objective',
         'resource_path': ['https://example.org/a.pdf']} ]}, lifecycle_status='draft')
    assert result == {'nodes': 1, 'resources': 1}
    assert not any(sql.startswith('DELETE FROM resources') for sql, _ in statements)
    resource_insert = next((sql, args) for sql, args in statements if sql.startswith('INSERT INTO resources'))
    assert 'ON DUPLICATE KEY UPDATE' in resource_insert[0]
    assert resource_insert[1][8:11] == ('disabled', 0, 0)
    node_insert = next(args for sql, args in statements if sql.startswith('INSERT INTO course_nodes'))
    assert node_insert[1:3] == ('p', 'Renamed point')

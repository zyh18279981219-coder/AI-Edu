from DatabaseModule.mysql_store import MySQLStore


def test_read_write_account_does_not_initialize_schema(monkeypatch):
    monkeypatch.setenv('DB_AUTO_MIGRATE', '0')
    store = object.__new__(MySQLStore)
    # No connection/lock is provided: disabled migration must not request one.
    store._initialize()
    monkeypatch.setattr(store, '_table_columns', lambda cursor, table: {'log_id', 'payload_json'})
    assert store._ensure_llm_logs_table(None) == 'log_id'

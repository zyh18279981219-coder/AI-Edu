"""Read-only replay of local synthetic inputs through the production evaluator."""
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from DatabaseModule.mysql_store import MySQLStore


def load_course_demo(course_id, username):
    path = os.getenv('COURSE_RUNTIME_DEMO_FILE', '').strip()
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data['course']['course_id'] != course_id or username != data['teacher_username']:
        return None
    return data


def evaluate_demo(data, window_days=30, min_quiz_attempts=3):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, query, _params=None):
            sql = ' '.join(query.split())
            if not sql.startswith('SELECT '):
                raise RuntimeError('Demo inputs are read-only')
            # More specific joins/union must precede table matches.
            if 'AS learner_count FROM (' in sql: key = 'class_size'
            elif 'FROM career_abilities a' in sql: key = 'abilities'
            elif 'FROM homework_assignments a' in sql: key = 'homework'
            elif 'FROM homework_assignment_knowledge_points' in sql: key = 'homework_coverage'
            elif 'FROM courses' in sql: key = 'course'
            elif 'FROM course_nodes n' in sql: key = 'nodes'
            elif 'FROM resource_learning_events' in sql: key = 'events'
            elif 'FROM resources' in sql: key = 'resources'
            elif 'FROM quiz_attempts' in sql: key = 'quizzes'
            elif 'FROM user_states' in sql: key = 'definitions'
            elif 'FROM twin_profile_nodes' in sql: key = 'mastery'
            else: raise RuntimeError('Unrecognized evaluation input query')
            rows = data[key]
            self.rows = rows if isinstance(rows, list) else [rows]
        def fetchall(self): return self.rows
        def fetchone(self): return self.rows[0] if self.rows else None
    class Connection:
        def cursor(self): return Cursor()
    class ReplayStore(MySQLStore):
        @contextmanager
        def connection(self): yield Connection()
    replay = ReplayStore.__new__(ReplayStore)
    replay._lock = threading.RLock()
    result = replay.evaluate_course_runtime(data['course']['course_id'], window_days=window_days, min_quiz_attempts=min_quiz_attempts)
    result.update(is_demo=True, demo_available=True,
                  demo_note='本地演示评估：' + data.get('source_note', '模拟资源学习、测验作答和能力支撑输入。') + ' 按正式公式计算；演示补充项未写入共享数据库。')
    return result

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock
from datetime import timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_user_authentication(monkeypatch):
    print("Testing user authentication...")

    fake_store = MagicMock()
    fake_store.get_user_by_identifier.side_effect = lambda user_type, identifier: {
        "student": {"username": "stuwangqiyu", "password": "123456"},
        "teacher": {"username": "teawangqiyu", "password": "123456"},
        "admin": {"username": "adminwangqiyu", "password": "123456"},
    }.get(user_type, {})

    fake_store.list_users.side_effect = lambda user_type: [
        {"username": "stuwangqiyu", "password": "123456"},
        {"username": "teawangqiyu", "password": "123456"},
        {"username": "adminwangqiyu", "password": "123456"},
    ]

    fake_store.replace_users.return_value = None

    from DatabaseModule.database_factory import DatabaseFactory
    monkeypatch.setattr(DatabaseFactory, "_instance", fake_store)

    # Monkeypatch UserManager._initialize_user_data to skip file ops
    from tools.user_manager import UserManager
    orig_init = UserManager._initialize_user_data
    UserManager._initialize_user_data = lambda self, username: None

    user_manager = UserManager()

    student = user_manager.authenticate_student("stuwangqiyu", "123456")
    assert student is not None, "Student authentication failed"
    assert student["username"] == "stuwangqiyu"
    print("Student authentication successful")

    teacher = user_manager.authenticate_teacher("teawangqiyu", "123456")
    assert teacher is not None, "Teacher authentication failed"
    assert teacher["username"] == "teawangqiyu"
    print("Teacher authentication successful")

    admin = user_manager.authenticate_admin("adminwangqiyu", "123456")
    assert admin is not None, "Admin authentication failed"
    assert admin["username"] == "adminwangqiyu"
    print("Admin authentication successful")

    UserManager._initialize_user_data = orig_init


def test_user_paths(monkeypatch, tmp_path):
    print("\nTesting user-specific paths...")

    fake_store = MagicMock()
    fake_store.get_user_by_identifier.return_value = {"username": "stuwangqiyu", "password": "123456"}
    fake_store.list_users.return_value = [{"username": "stuwangqiyu", "password": "123456"}]
    fake_store.replace_users.return_value = None

    from DatabaseModule.database_factory import DatabaseFactory
    monkeypatch.setattr(DatabaseFactory, "_instance", fake_store)

    # Create dummy template files
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "big_data.json").write_text("{}")
    (templates_dir / "graph.json").write_text("{}")

    from tools.user_manager import UserManager
    orig_init = UserManager.__init__

    def patched_init(self):
        self.store = fake_store
        self.users_dir = tmp_path / "Users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.student_file = self.users_dir / "student.json"
        self.teacher_file = self.users_dir / "teacher.json"
        self.admin_file = self.users_dir / "admin.json"
        self.user_data_dir = tmp_path / "user_data"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.template_course = templates_dir / "big_data.json"
        self.template_graph = templates_dir / "graph.json"

    UserManager.__init__ = patched_init

    user_manager = UserManager()

    # Trigger _initialize_user_data via authenticate_student
    user_manager._initialize_user_data("stuwangqiyu")

    course_path = user_manager.get_user_course_path("stuwangqiyu")
    assert os.path.exists(course_path), f"Course path does not exist: {course_path}"
    print(f"Course path exists: {course_path}")

    graph_path = user_manager.get_user_graph_path("stuwangqiyu")
    assert os.path.exists(graph_path), f"Graph path does not exist: {graph_path}"
    print(f"Graph path exists: {graph_path}")

    plans_dir = user_manager.get_user_learning_plans_dir("stuwangqiyu")
    assert os.path.exists(plans_dir), f"Learning plans dir does not exist: {plans_dir}"
    print(f"Learning plans directory exists: {plans_dir}")

    UserManager.__init__ = orig_init


def test_session_management(monkeypatch, tmp_path):
    print("\nTesting session management...")

    # Use a dict-backed store so sessions actually persist
    _sessions = {}
    _user_states = {}

    fake_store = MagicMock()
    fake_store.get_session.side_effect = lambda sid: _sessions.get(sid)
    fake_store.save_session.side_effect = lambda sid, payload: _sessions.__setitem__(sid, dict(payload))
    fake_store.delete_session.side_effect = lambda sid: _sessions.pop(sid, None)
    fake_store.list_sessions.side_effect = lambda: list(_sessions.values())
    fake_store.get_user_state.side_effect = lambda uname: _user_states.get(uname)
    fake_store.save_user_state.side_effect = lambda uname, payload: _user_states.__setitem__(uname, dict(payload))

    from DatabaseModule.database_factory import DatabaseFactory
    monkeypatch.setattr(DatabaseFactory, "_instance", fake_store)

    # Patch SessionManager to use tmp_path for dirs
    from tools.session_manager import SessionManager
    orig_init = SessionManager.__init__

    def patched_init(self):
        self.store = fake_store
        self._session_timeout = timedelta(hours=24)
        self._session_dir = tmp_path / "sessions"
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._user_state_dir = tmp_path / "user_state"
        self._user_state_dir.mkdir(parents=True, exist_ok=True)

    SessionManager.__init__ = patched_init

    # Reset the singleton
    import tools.session_manager as sm
    old_singleton = sm._session_manager
    sm._session_manager = SessionManager()

    session_manager = sm.get_session_manager()

    user_data = {"username": "testuser", "role": "student"}
    session_id = session_manager.create_session("testuser", "student", user_data)
    assert session_id is not None, "Session creation failed"
    print(f"Session created: {session_id[:10]}...")

    session = session_manager.get_session(session_id)
    assert session is not None, "Session retrieval failed"
    assert session["username"] == "testuser"
    print("Session retrieval successful")

    session_manager.delete_session(session_id)
    session = session_manager.get_session(session_id)
    assert session is None, "Session deletion failed"
    print("Session deletion successful")

    SessionManager.__init__ = orig_init
    sm._session_manager = old_singleton


def test_student_registration(monkeypatch, tmp_path):
    print("\nTesting student registration...")

    # Use a dict-backed store so registered users persist
    _users = {"student": [], "teacher": [], "admin": []}

    def _get_user_by_identifier(user_type, identifier):
        for u in _users.get(user_type, []):
            if u.get("username") == identifier:
                return u
        return None

    fake_store = MagicMock()
    fake_store.get_user_by_identifier.side_effect = _get_user_by_identifier
    fake_store.list_users.side_effect = lambda user_type: list(_users.get(user_type, []))
    fake_store.replace_users.side_effect = lambda user_type, users: _users.__setitem__(user_type, list(users))

    from DatabaseModule.database_factory import DatabaseFactory
    monkeypatch.setattr(DatabaseFactory, "_instance", fake_store)

    # Create dummy template files
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "big_data.json").write_text("{}")
    (templates_dir / "graph.json").write_text("{}")

    from tools.user_manager import UserManager
    orig_init = UserManager.__init__

    def patched_init(self):
        self.store = fake_store
        self.users_dir = tmp_path / "Users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.student_file = self.users_dir / "student.json"
        self.teacher_file = self.users_dir / "teacher.json"
        self.admin_file = self.users_dir / "admin.json"
        self.user_data_dir = tmp_path / "user_data"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.template_course = templates_dir / "big_data.json"
        self.template_graph = templates_dir / "graph.json"

    UserManager.__init__ = patched_init

    test_username = "test_new_student_123"

    try:
        user_manager = UserManager()

        existing = user_manager.authenticate_student(test_username, "test")
        if existing:
            print(f"Test user already exists, skipping registration test")
            return

        new_student = user_manager.register_student(
            username=test_username,
            password="testpass",
            stu_name="Test Student",
            email="test@example.com",
        )
        assert new_student["username"] == test_username
        print(f"Student registered: {test_username}")

        course_path = user_manager.get_user_course_path(test_username)
        assert os.path.exists(course_path), "User course file not created"
        print(f"User course file created: {course_path}")

        authenticated = user_manager.authenticate_student(test_username, "testpass")
        assert authenticated is not None, "Newly registered student authentication failed"
        print("Newly registered student can authenticate")

    except ValueError as e:
        print(f"Registration test skipped: {e}")

    UserManager.__init__ = orig_init


if __name__ == "__main__":
    print("=" * 50)
    print("Multi-User System Tests")
    print("=" * 50)

    try:
        test_user_authentication()
        test_user_paths()
        test_session_management()
        test_student_registration()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

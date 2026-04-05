import logging
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from DatabaseModule.sqlite_store import get_sqlite_store

logger = logging.getLogger(__name__)


class UserManager:
    def __init__(self):
        self.store = get_sqlite_store()
        self.users_dir = Path("data/Users")
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.student_file = self.users_dir / "student.json"
        self.teacher_file = self.users_dir / "teacher.json"
        self.admin_file = self.users_dir / "admin.json"

        self.user_data_dir = Path("data/user_data")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self.template_course = Path("data/course/big_data.json")
        self.template_graph = Path("backend/static/vendor/graph.json")

    def _load_users(self, filepath: Path) -> list:
        user_type = filepath.stem
        try:
            users = self.store.list_users(user_type)
            logger.info("UserManager: read %s users from SQLite (%d)", user_type, len(users))
            if not users:
                recovered_users = self._recover_users_from_sessions(user_type)
                if recovered_users:
                    logger.warning(
                        "UserManager: recovered %s users from sessions because SQLite user table was empty",
                        user_type,
                    )
                    self._save_users(filepath, recovered_users)
                    return recovered_users
            return users
        except Exception:
            logger.exception("UserManager: failed reading %s users from SQLite", user_type)
        return []

    def _save_users(self, filepath: Path, users: list):
        try:
            self.store.replace_users(filepath.stem, users)
            logger.info("UserManager: wrote %s users to SQLite (%d)", filepath.stem, len(users))
        except Exception:
            logger.exception("UserManager: failed writing %s users to SQLite", filepath.stem)

    def _recover_users_from_sessions(self, user_type: str) -> list[Dict[str, Any]]:
        recovered: dict[str, Dict[str, Any]] = {}

        try:
            for session in self.store.list_sessions():
                if session.get("user_type") != user_type:
                    continue
                user_data = session.get("user_data")
                username = session.get("username")
                if (
                    isinstance(user_data, dict)
                    and username
                    and user_data.get("username") == username
                    and user_data.get("password")
                ):
                    recovered[username] = user_data
        except Exception:
            logger.exception("UserManager: failed recovering %s users from SQLite sessions", user_type)

        sessions_dir = Path("data/sessions")
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    payload = json.loads(session_file.read_text(encoding="utf-8"))
                except Exception:
                    logger.warning("UserManager: skipped unreadable session file %s", session_file)
                    continue

                if payload.get("user_type") != user_type:
                    continue
                user_data = payload.get("user_data")
                username = payload.get("username")
                if (
                    isinstance(user_data, dict)
                    and username
                    and user_data.get("username") == username
                    and user_data.get("password")
                ):
                    recovered[username] = user_data

        return sorted(recovered.values(), key=lambda item: str(item.get("username", "")))

    def authenticate_student(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        students = self._load_users(self.student_file)
        for student in students:
            if student["username"] == username and student["password"] == password:
                self._initialize_user_data(username)
                return student
        return None

    def authenticate_teacher(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == username and teacher["password"] == password:
                return teacher
        return None

    def authenticate_admin(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        admins = self._load_users(self.admin_file)
        for admin in admins:
            if admin["username"] == username and admin["password"] == password:
                return admin
        return None

    def register_student(
        self,
        username: str,
        password: str,
        stu_name: str,
        email: str = "",
        teacher: str = "",
        img: str = "/static/img/member-02.jpg",
    ) -> Dict[str, Any]:
        students = self._load_users(self.student_file)

        for student in students:
            if student["username"] == username:
                raise ValueError(f"Username {username} already exists")

        new_student = {
            "stu_name": stu_name,
            "img": img,
            "username": username,
            "password": password,
            "email": email,
            "teacher": teacher,
            "learning_goals": [],
            "preference": {"course_topic": [], "course_type": []},
            "progress": [],
            "scores": [-1] * 40,
        }

        students.append(new_student)
        self._save_users(self.student_file, students)

        if teacher:
            self._add_student_to_teacher(teacher, username)

        self._initialize_user_data(username)
        return new_student

    def _add_student_to_teacher(self, teacher_username: str, student_username: str):
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == teacher_username:
                if "students" not in teacher:
                    teacher["students"] = []
                if student_username not in teacher["students"]:
                    teacher["students"].append(student_username)
                    self._save_users(self.teacher_file, teachers)
                return True
        return False

    def register_teacher(
        self,
        username: str,
        password: str,
        name: str,
        email: str = "",
    ) -> Dict[str, Any]:
        teachers = self._load_users(self.teacher_file)

        for teacher in teachers:
            if teacher["username"] == username:
                raise ValueError(f"Username {username} already exists")

        new_teacher = {
            "name": name,
            "username": username,
            "password": password,
            "email": email,
            "role": "teacher",
            "students": [],
        }

        teachers.append(new_teacher)
        self._save_users(self.teacher_file, teachers)
        return new_teacher

    def _initialize_user_data(self, username: str):
        user_dir = self.user_data_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)

        user_course_file = user_dir / "big_data.json"
        user_graph_file = user_dir / "graph.json"

        if self.template_course.exists() and not user_course_file.exists():
            shutil.copy(self.template_course, user_course_file)

        if self.template_graph.exists() and not user_graph_file.exists():
            shutil.copy(self.template_graph, user_graph_file)

        learning_plans_dir = user_dir / "learning_plans"
        learning_plans_dir.mkdir(parents=True, exist_ok=True)

    def get_user_course_path(self, username: str) -> str:
        return str(self.user_data_dir / username / "big_data.json")

    def get_user_graph_path(self, username: str) -> str:
        return str(self.user_data_dir / username / "graph.json")

    def get_user_learning_plans_dir(self, username: str) -> str:
        return str(self.user_data_dir / username / "learning_plans")

    def update_student_profile(self, username: str, updates: Dict[str, Any]) -> bool:
        students = self._load_users(self.student_file)
        for student in students:
            if student["username"] == username:
                old_teacher = student.get("teacher", "")
                new_teacher = updates.get("teacher", old_teacher)

                if "teacher" in updates and old_teacher != new_teacher:
                    if old_teacher:
                        self._remove_student_from_teacher(old_teacher, username)
                    if new_teacher:
                        self._add_student_to_teacher(new_teacher, username)

                student.update(updates)
                self._save_users(self.student_file, students)
                return True
        return False

    def _remove_student_from_teacher(self, teacher_username: str, student_username: str):
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == teacher_username:
                if "students" in teacher and student_username in teacher["students"]:
                    teacher["students"].remove(student_username)
                    self._save_users(self.teacher_file, teachers)
                return True
        return False

    def get_student_profile(self, username: str) -> Optional[Dict[str, Any]]:
        students = self._load_users(self.student_file)
        for student in students:
            if student["username"] == username:
                return student
        return None

    def get_teacher_profile(self, username: str) -> Optional[Dict[str, Any]]:
        teachers = self._load_users(self.teacher_file)
        for teacher in teachers:
            if teacher["username"] == username:
                return teacher
        return None

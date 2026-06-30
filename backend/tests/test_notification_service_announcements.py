import os
import sys
import threading
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DatabaseModule.notification_service import NotificationService


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self.rows = []

    def execute(self, query, params=None):
        if "FROM teaching_announcements" in query:
            self.rows = self.store.announcements
        else:
            self.rows = []

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self.store)


class FakeNotificationStore:
    def __init__(self, announcements):
        self._lock = threading.RLock()
        self.announcements = announcements

    def connection(self):
        return FakeConnection(self)

    def get_user_by_identifier(self, user_type, identifier):
        if user_type == "student" and identifier == "zyh":
            return {
                "username": "zyh",
                "class_name": "大数据一班",
                "course_id": "course_big_data",
            }
        return None

    def list_users(self, user_type):
        if user_type == "teacher":
            return [
                {"username": "teacher"},
                {"username": "other_teacher"},
            ]
        return []

    def list_teacher_students(self, teacher_identifier):
        if teacher_identifier == "teacher":
            return [{"student_username": "zyh"}]
        return []


def _build_service(announcements):
    NotificationService._cache.clear()
    service = NotificationService.__new__(NotificationService)
    service.store = FakeNotificationStore(announcements)
    return service


def test_recent_notifications_include_visible_teacher_announcement():
    now = datetime.now()
    service = _build_service([
        {
            "id": "ann-1",
            "teacher_username": "teacher",
            "title": "本周补充学习安排",
            "content": "请完成资源学习",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now,
            "created_at": now,
        }
    ])

    result = service.get_recent_notifications("zyh", limit=5)

    assert result == [
        {
            "icon": "📢",
            "title": "教师公告：本周补充学习安排",
            "time": result[0]["time"],
            "timestamp": now.isoformat(),
            "type": "teaching_announcement",
            "link": "/student/interaction",
        }
    ]


def test_recent_notifications_hide_unrelated_and_unpublished_announcements():
    now = datetime.now()
    service = _build_service([
        {
            "id": "visible",
            "teacher_username": "teacher",
            "title": "可见公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now,
            "created_at": now,
        },
        {
            "id": "other-teacher",
            "teacher_username": "other_teacher",
            "title": "其他教师公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now - timedelta(minutes=1),
            "created_at": now - timedelta(minutes=1),
        },
        {
            "id": "other-class",
            "teacher_username": "teacher",
            "title": "其他班级公告",
            "content": "",
            "class_name": "人工智能二班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now - timedelta(minutes=2),
            "created_at": now - timedelta(minutes=2),
        },
        {
            "id": "other-course",
            "teacher_username": "teacher",
            "title": "其他课程公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_python",
            "status": "published",
            "published_at": now - timedelta(minutes=3),
            "created_at": now - timedelta(minutes=3),
        },
        {
            "id": "draft",
            "teacher_username": "teacher",
            "title": "草稿公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "draft",
            "published_at": now - timedelta(minutes=4),
            "created_at": now - timedelta(minutes=4),
        },
    ])

    result = service.get_recent_notifications("zyh", limit=10)

    assert [item["title"] for item in result] == ["教师公告：可见公告"]


def test_recent_notifications_sort_announcements_with_other_sources_by_time():
    now = datetime.now()
    service = _build_service([
        {
            "id": "ann-old",
            "teacher_username": "teacher",
            "title": "较早公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now - timedelta(hours=2),
            "created_at": now - timedelta(hours=2),
        },
        {
            "id": "ann-new",
            "teacher_username": "teacher",
            "title": "最新公告",
            "content": "",
            "class_name": "大数据一班",
            "course_id": "course_big_data",
            "status": "published",
            "published_at": now,
            "created_at": now,
        },
    ])

    result = service.get_recent_notifications("zyh", limit=10)

    assert [item["title"] for item in result] == ["教师公告：最新公告", "教师公告：较早公告"]

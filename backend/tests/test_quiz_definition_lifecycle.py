import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from QuizModule.definition_service import (
    QuizDefinitionService,
    published_definition_index_from_state_rows,
)


class FakeStateStore:
    def __init__(self):
        self.state = {}

    def get_user_state(self, key):
        return self.state.get(key)

    def save_user_state(self, key, value):
        self.state[key] = value


def sample_question(topic="数组"):
    return {
        "topic": topic,
        "question": "以下哪一项是正确答案？\nA. 错误\nB. 正确",
        "correct": "b",
    }


def test_draft_definition_is_not_returned_as_published():
    service = QuizDefinitionService(FakeStateStore())

    draft = service.save_definition(
        {
            "course_id": "course_big_data",
            "node_id": "数组",
            "title": "数组小测",
            "status": "draft",
            "questions": [sample_question()],
        },
        teacher_username="teacher",
    )

    assert draft["status"] == "draft"
    assert service.get_published_definition("course_big_data", "数组") is None


def test_publish_definition_makes_it_available_and_unpublishes_previous():
    service = QuizDefinitionService(FakeStateStore())
    first = service.save_definition(
        {
            "course_id": "course_big_data",
            "node_id": "数组",
            "title": "数组小测 A",
            "questions": [sample_question("数组")],
        },
        teacher_username="teacher",
    )
    second = service.save_definition(
        {
            "course_id": "course_big_data",
            "node_id": "数组",
            "title": "数组小测 B",
            "questions": [sample_question("数组")],
        },
        teacher_username="teacher",
    )

    service.publish_definition(first["definition_id"], "course_big_data", "数组", "teacher")
    published = service.publish_definition(second["definition_id"], "course_big_data", "数组", "teacher")

    assert published["definition_id"] == second["definition_id"]
    assert service.get_published_definition("course_big_data", "数组")["definition_id"] == second["definition_id"]
    definitions = service.list_definitions("course_big_data", "数组")
    first_after_publish = next(item for item in definitions if item["definition_id"] == first["definition_id"])
    assert first_after_publish["status"] == "draft"


def test_published_definition_index_reads_user_state_rows_only_for_target_course():
    rows = [
        {
            "username": "quiz_definitions::course_big_data::数组",
            "payload_json": {
                "definitions": [
                    {
                        "definition_id": "draft_a",
                        "course_id": "course_big_data",
                        "node_id": "数组",
                        "status": "draft",
                    },
                    {
                        "definition_id": "published_a",
                        "course_id": "course_big_data",
                        "node_id": "数组",
                        "status": "published",
                        "published_at": "2026-06-28T10:00:00",
                    },
                ]
            },
        },
        {
            "username": "quiz_definitions::other_course::数组",
            "payload_json": {
                "definitions": [
                    {
                        "definition_id": "other_published",
                        "course_id": "other_course",
                        "node_id": "数组",
                        "status": "published",
                    }
                ]
            },
        },
    ]

    index = published_definition_index_from_state_rows(rows, "course_big_data")

    assert set(index.keys()) == {"数组"}
    assert index["数组"]["definition_id"] == "published_a"


def test_start_quiz_prefers_published_definition(monkeypatch):
    import app as backend_app

    fake_store = FakeStateStore()
    service = QuizDefinitionService(fake_store)
    definition = service.save_definition(
        {
            "course_id": "course_big_data",
            "node_id": "数组",
            "title": "数组正式测验",
            "status": "published",
            "questions": [sample_question("数组")],
        },
        teacher_username="teacher",
    )

    class ShouldNotGenerateQuizAgent:
        def prepare_quiz_questions(self, *args, **kwargs):
            raise AssertionError("generated quiz fallback should not be used")

    monkeypatch.setattr(backend_app, "database_store", fake_store)
    monkeypatch.setattr(backend_app, "get_quiz_agent", lambda: ShouldNotGenerateQuizAgent())
    monkeypatch.setattr(backend_app.session_manager, "get_current_pdf", lambda session_id: None)

    response = asyncio.run(
        backend_app.start_quiz(
            backend_app.QuizStart(subject="数组", node_id="数组", course_id="course_big_data", lang_choice="中文"),
            session_id=None,
        )
    )

    assert response["definition_status"] == "published"
    assert response["definition_source"] == "published_definition"
    assert response["definition_id"] == definition["definition_id"]
    assert response["question"]["question"].startswith("以下哪一项")
    assert response["state"]["definition_id"] == definition["definition_id"]


def test_start_quiz_generated_fallback_marks_source(monkeypatch):
    import app as backend_app

    class FakeQuizAgent:
        def prepare_quiz_questions(self, *args, **kwargs):
            return [sample_question("数组")], False

    monkeypatch.setattr(backend_app, "database_store", FakeStateStore())
    monkeypatch.setattr(backend_app, "get_quiz_agent", lambda: FakeQuizAgent())
    monkeypatch.setattr(backend_app, "get_retriever", lambda: None)
    monkeypatch.setattr(backend_app.session_manager, "get_current_pdf", lambda session_id: None)

    response = asyncio.run(
        backend_app.start_quiz(
            backend_app.QuizStart(subject="数组", node_id="数组", course_id="course_big_data", lang_choice="中文"),
            session_id=None,
        )
    )

    assert response["definition_status"] == "generated_fallback"
    assert response["definition_source"] == "generated"
    assert response["state"]["definition_status"] == "generated_fallback"


def test_complete_quiz_persists_definition_metadata(monkeypatch):
    import app as backend_app

    recorded = {}

    class FakeStore:
        def record_quiz_attempt(self, **kwargs):
            recorded.update(kwargs)
            return 1

    monkeypatch.setattr(backend_app, "database_store", FakeStore())
    monkeypatch.setattr(
        backend_app,
        "_load_course_graph_entity_only",
        lambda session: (
            "course_big_data",
            {
                "name": "课程",
                "children": [
                    {
                        "name": "章节",
                        "flag": "0",
                        "grandchildren": [
                            {
                                "name": "Kafka 数据接入",
                                "flag": "0",
                                "grandchildren": [],
                            }
                        ],
                    }
                ],
            },
        ),
    )
    monkeypatch.setattr(
        backend_app,
        "_resolve_course_sync_meta",
        lambda course_id, graph_data: ("课程", None),
    )
    monkeypatch.setattr(
        backend_app.session_manager,
        "get_session",
        lambda session_id: {
            "username": "zyh",
            "user_id": 7,
            "user_type": "student",
        },
    )
    monkeypatch.setattr(
        FakeStore,
        "sync_course_from_graph",
        lambda self, **kwargs: None,
        raising=False,
    )

    response = asyncio.run(
        backend_app.complete_quiz(
            backend_app.QuizComplete(
                node_name="Kafka 数据接入",
                score=1,
                total=1,
                definition_id="quizdef_001",
                definition_status="published",
                definition_source="published_definition",
            ),
            session_id="session-1",
        )
    )

    assert response["success"] is True
    assert recorded["username"] == "zyh"
    assert recorded["extra_payload"]["definition_id"] == "quizdef_001"
    assert recorded["extra_payload"]["definition_status"] == "published"
    assert recorded["extra_payload"]["definition_source"] == "published_definition"
    assert recorded["extra_payload"]["evidence_policy"] == "published_quiz_definition"

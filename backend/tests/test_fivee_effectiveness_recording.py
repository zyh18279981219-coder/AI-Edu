from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fiveE import effectiveness_service, service
from fiveE.models.chat_request import ChatRequest
from fiveE.models.chat_response import ChatResponse


class _Store:
    def __init__(self) -> None:
        self.records = []
        self.updated = []

    def record_fivee_effectiveness(self, **kwargs):
        self.records.append(kwargs)
        return 101

    def list_fivee_effectiveness_records(self, *, course_id, student_username, limit):
        return [
            {
                "record_id": 101,
                "student_username": student_username,
                "course_id": course_id,
                "node_id": "Kafka 数据接入",
                "stage": "evaluation",
                "interaction_count": 1,
                "valid_interaction_count": 1,
                "completion_rate": 100,
                "quiz_score_before": None,
                "quiz_score_after": None,
                "path_continue_rate": None,
                "effectiveness_score": 80,
                "payload": {
                    "evidence_status": "process_only",
                    "mastery_update_policy": "not_updated_by_5e_effectiveness",
                },
            }
        ]

    def update_fivee_effectiveness_outcome(self, **kwargs):
        self.updated.append(kwargs)
        return True


def test_record_effectiveness_from_successful_stream(monkeypatch):
    store = _Store()
    monkeypatch.setattr(effectiveness_service, "get_database_store", lambda: store)

    response = ChatResponse(
        role="assistant",
        content="我们先用一个真实案例理解 Kafka 数据接入，然后完成一个小测验。",
        buttons=[],
        resources=[{"show_text": "Kafka 入门资料", "id": "res-1"}],
        tests=[{"show_text": "Kafka 小测", "id": "quiz-1"}],
        timestamp=1,
    )
    request = ChatRequest(
        user_id="zyh",
        course_id="course_big_data",
        node_id="Kafka 数据接入",
        content="我不太懂 Kafka 数据接入",
    )

    service._record_effectiveness_from_stream(request, [response.model_dump_json()])

    assert len(store.records) == 1
    record = store.records[0]
    assert record["user_identifier"] == "zyh"
    assert record["student_username"] == "zyh"
    assert record["course_id"] == "course_big_data"
    assert record["node_id"] == "Kafka 数据接入"
    assert record["stage"] == "evaluation"
    assert record["interaction_count"] == 1
    assert record["valid_interaction_count"] == 1
    assert record["completion_rate"] == 100
    assert 0 < record["effectiveness_score"] <= 100
    assert record["payload"]["evidence_status"] == "process_only"
    assert record["payload"]["effectiveness_level"] in {"引导有效", "基本有效", "效果一般", "效果较弱"}
    assert record["payload"]["dimension_scores"]["stage_completion"] == 100
    assert record["payload"]["dimension_scores"]["learning_gain"] is None
    assert record["payload"]["mastery_update_policy"] == "not_updated_by_5e_effectiveness"


def test_link_quiz_outcome_updates_recent_record_as_auxiliary_evidence(monkeypatch):
    store = _Store()
    monkeypatch.setattr(effectiveness_service, "get_database_store", lambda: store)

    result = effectiveness_service.link_quiz_outcome(
        student_username="zyh",
        course_id="course_big_data",
        node_id="Kafka 数据接入",
        quiz_score_after=86,
        quiz_score_before=60,
    )

    assert result["updated"] is True
    assert result["record_id"] == 101
    assert result["evidence_status"] == "outcome_supported"
    assert result["mastery_update_policy"] == "not_updated_by_5e_effectiveness"
    assert len(store.updated) == 1
    update = store.updated[0]
    assert update["quiz_score_before"] == 60
    assert update["quiz_score_after"] == 86
    assert update["effectiveness_score"] is not None
    assert update["payload"]["evidence_status"] == "outcome_supported"
    assert update["payload"]["mastery_update_policy"] == "not_updated_by_5e_effectiveness"
    assert update["payload"]["outcome_link"]["type"] == "quiz_outcome"


def test_chat_stream_unavailable_runtime_returns_fallback(monkeypatch):
    def unavailable():
        raise RuntimeError("runtime missing")

    monkeypatch.setattr(service, "_load_runtime", unavailable)
    request = ChatRequest(user_id="zyh", course_id="course_big_data", content="hello")

    async def collect():
        chunks = []
        async for chunk in service.chat_message_stream(request):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect())

    assert len(chunks) == 1
    assert "runtime missing" in chunks[0]

from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class AbilityImportStore:
    def __init__(self) -> None:
        self.saved_candidates = []
        self.generated_calls = []

    def upsert_career_abilities(self, position_id, candidates):
        self.saved_candidates = list(candidates)
        return {
            "position_id": position_id,
            "saved": len(self.saved_candidates),
            "ability_ids": [101 + index for index, _ in enumerate(self.saved_candidates)],
        }

    def generate_course_ability_mapping_candidates(
        self,
        course_id,
        *,
        updated_by=None,
        max_candidates_per_ability=3,
        min_score=0.24,
    ):
        self.generated_calls.append(
            {
                "course_id": course_id,
                "updated_by": updated_by,
                "max_candidates_per_ability": max_candidates_per_ability,
                "min_score": min_score,
            }
        )
        return {
            "course_id": course_id,
            "generated": 2,
            "candidate_count": 2,
            "skipped": [],
            "rejected": [],
        }

    def list_course_ability_mappings(self, course_id):
        return [
            {
                "mapping_id": 1,
                "course_id": course_id,
                "ability_id": 101,
                "node_id": "kafka-basic",
                "review_status": "draft",
                "evidence": {"requires_teacher_review": True},
            }
        ]

    def list_course_abilities(self, course_id):
        return [
            {
                "ability_id": 101,
                "course_id": course_id,
                "ability_name": item["ability_name"],
                "evidence": item["evidence"],
            }
            for item in self.saved_candidates
        ]


def test_teacher_industry_ability_import_can_generate_draft_mapping_candidates(monkeypatch):
    import app as backend_app

    store = AbilityImportStore()
    monkeypatch.setattr(backend_app, "database_store", store)
    monkeypatch.setattr(
        backend_app,
        "_require_teacher_or_admin",
        lambda session_id=None: {"username": "teacher", "user_id": 9, "user_type": "teacher"},
    )

    result = asyncio.run(
        backend_app.import_course_digital_twin_abilities(
            backend_app.CourseAbilityImportRequest(
                course_id="course_big_data",
                position_id=7,
                abilities=[
                    {
                        "ability_name": "Kafka 数据接入能力",
                        "ability_category": "数据采集",
                        "demand_level": 6,
                        "source_evidence": {
                            "source": "industry_intelligence",
                            "job_count": 4,
                        },
                    }
                ],
                industry_payload={"keyword": "大数据工程师"},
                generate_mapping_candidates=True,
                max_candidates_per_ability=2,
                min_mapping_score=0.3,
            ),
            session_id="teacher-session",
        )
    )

    assert result["success"] is True
    assert result["import_result"]["saved"] == 1
    assert result["mapping_candidate_result"]["generated"] == 2
    assert result["mappings"][0]["review_status"] == "draft"
    assert result["mappings"][0]["evidence"]["requires_teacher_review"] is True
    assert store.generated_calls == [
        {
            "course_id": "course_big_data",
            "updated_by": 9,
            "max_candidates_per_ability": 2,
            "min_score": 0.3,
        }
    ]


def test_teacher_industry_ability_import_does_not_generate_mapping_candidates_by_default(monkeypatch):
    import app as backend_app

    store = AbilityImportStore()
    monkeypatch.setattr(backend_app, "database_store", store)
    monkeypatch.setattr(
        backend_app,
        "_require_teacher_or_admin",
        lambda session_id=None: {"username": "teacher", "user_id": 9, "user_type": "teacher"},
    )

    result = asyncio.run(
        backend_app.import_course_digital_twin_abilities(
            backend_app.CourseAbilityImportRequest(
                course_id="course_big_data",
                position_id=7,
                abilities=[{"ability_name": "Flink 实时计算能力"}],
            ),
            session_id="teacher-session",
        )
    )

    assert result["success"] is True
    assert result["mapping_candidate_result"] is None
    assert result["mappings"] is None
    assert store.generated_calls == []

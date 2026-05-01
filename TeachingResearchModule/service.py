from __future__ import annotations

from typing import Any, Dict, List, Optional

from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from TeachingResearchModule.repository import TeachingResearchRepository


EVENT_TYPE_MAP = {
    "research_post": "research_post",
    "shared_courseware": "shared_courseware",
    "co_preparation": "co_preparation",
}


class TeachingResearchService:
    def __init__(self, repository: Optional[TeachingResearchRepository] = None) -> None:
        self.repository = repository or TeachingResearchRepository()
        self.teacher_event_repo = get_teacher_event_repository()

    def create_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self.repository.create_record(payload)
        event_type = EVENT_TYPE_MAP.get(record["activity_type"], record["activity_type"])
        self.teacher_event_repo.record_research_event(
            teacher_username=record["teacher_username"],
            event_type=event_type,
            resource_id=record["id"],
            payload={
                "title": record["title"],
                "description": record["description"],
                "resource_link": record["resource_link"],
                "class_name": record["class_name"],
                "course_id": record["course_id"],
            },
            created_at=record["happened_at"],
        )
        return record

    def list_records(self, teacher_username: str) -> List[Dict[str, Any]]:
        return self.repository.list_records(teacher_username)


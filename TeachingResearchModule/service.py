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

    def update_record(self, teacher_username: str, record_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.repository.get_record(record_id)
        if not existing:
            raise ValueError("教研记录不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权编辑该教研记录")
        updated = self.repository.update_record(record_id, payload)
        if not updated:
            raise ValueError("教研记录不存在")
        self.teacher_event_repo.record_research_event(
            teacher_username=teacher_username,
            event_type=EVENT_TYPE_MAP.get(updated["activity_type"], updated["activity_type"]),
            resource_id=updated["id"],
            payload={
                "title": updated["title"],
                "description": updated["description"],
                "resource_link": updated["resource_link"],
                "class_name": updated["class_name"],
                "course_id": updated["course_id"],
                "action": "updated",
            },
            created_at=updated["updated_at"],
        )
        return updated

    def delete_record(self, teacher_username: str, record_id: str) -> bool:
        existing = self.repository.get_record(record_id)
        if not existing:
            raise ValueError("教研记录不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权删除该教研记录")
        deleted = self.repository.delete_record(record_id)
        if deleted:
            self.teacher_event_repo.record_research_event(
                teacher_username=teacher_username,
                event_type=EVENT_TYPE_MAP.get(existing["activity_type"], existing["activity_type"]),
                resource_id=record_id,
                payload={"title": existing.get("title"), "action": "deleted"},
            )
        return deleted

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from TeachingInteractionModule.repository import TeachingInteractionRepository


class TeachingInteractionService:
    def __init__(self, repository: Optional[TeachingInteractionRepository] = None) -> None:
        self.repository = repository or TeachingInteractionRepository()
        self.teacher_event_repo = get_teacher_event_repository()

    def create_announcement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self.repository.create_announcement(payload)
        self.teacher_event_repo.record_interaction_event(
            teacher_username=record["teacher_username"],
            event_type="announcement_published",
            course_id=record.get("course_id"),
            class_name=record.get("class_name"),
            target_id=record["id"],
            payload={
                "title": record["title"],
                "published_on_time": True,
                "content_length": len(record["content"]),
            },
            created_at=record["published_at"],
        )
        return record

    def list_announcements(self, teacher_username: str) -> List[Dict[str, Any]]:
        return self.repository.list_announcements(teacher_username)

    def create_topic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self.repository.create_topic(payload)
        self.teacher_event_repo.record_interaction_event(
            teacher_username=record["teacher_username"],
            event_type="discussion_topic",
            course_id=record.get("course_id"),
            class_name=record.get("class_name"),
            target_id=record["id"],
            payload={"title": record["title"], "content_length": len(record["content"])},
            created_at=record["created_at"],
        )
        return record

    def list_topics(self, teacher_username: str) -> List[Dict[str, Any]]:
        return self._attach_posts(self.repository.list_topics(teacher_username))

    def list_topics_all(self) -> List[Dict[str, Any]]:
        return self._attach_posts(self.repository.list_topics_all())

    def list_announcements_all(self) -> List[Dict[str, Any]]:
        return self.repository.list_announcements_all()

    def _attach_posts(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for topic in topics:
            item = dict(topic)
            item["posts"] = self.repository.list_posts(str(topic["id"]))
            result.append(item)
        return result

    def add_post(
        self,
        *,
        teacher_username: str,
        topic_id: str,
        author_username: str,
        author_role: str,
        content: str,
        replied_to_post_id: Optional[str] = None,
        replied_to_created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        topic = self.repository.get_topic(topic_id)
        if not topic:
            raise ValueError("讨论话题不存在")
        if str(topic.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权操作该讨论话题")

        response_minutes = None
        if replied_to_created_at and author_role == "teacher":
            base = self._parse_time(replied_to_created_at)
            if base:
                response_minutes = round((datetime.now() - base).total_seconds() / 60.0, 2)

        record = self.repository.create_post(
            {
                "topic_id": topic_id,
                "author_username": author_username,
                "author_role": author_role,
                "content": content,
                "replied_to_post_id": replied_to_post_id,
                "response_minutes": response_minutes,
            }
        )
        if author_role == "student":
            self.repository.update_topic_counters(topic_id, student_question_delta=1)
            self.teacher_event_repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="student_question",
                course_id=topic.get("course_id"),
                class_name=topic.get("class_name"),
                target_id=topic_id,
                student_username=author_username,
                payload={"post_id": record["id"], "content_length": len(content)},
                created_at=record["created_at"],
            )
        else:
            self.repository.update_topic_counters(topic_id, teacher_reply_delta=1)
            self.teacher_event_repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="teacher_reply",
                course_id=topic.get("course_id"),
                class_name=topic.get("class_name"),
                target_id=topic_id,
                student_username=author_username if author_role == "student" else None,
                response_minutes=response_minutes,
                payload={"post_id": record["id"], "content_length": len(content)},
                created_at=record["created_at"],
            )
        return record

    def _parse_time(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

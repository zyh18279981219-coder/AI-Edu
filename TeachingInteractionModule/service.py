from __future__ import annotations

from datetime import datetime, timedelta
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

    def update_announcement(self, teacher_username: str, announcement_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.repository.get_announcement(announcement_id)
        if not existing:
            raise ValueError("公告不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权编辑该公告")
        updated = self.repository.update_announcement(announcement_id, payload)
        if not updated:
            raise ValueError("公告不存在")
        self.teacher_event_repo.record_interaction_event(
            teacher_username=teacher_username,
            event_type="announcement_updated",
            course_id=updated.get("course_id"),
            class_name=updated.get("class_name"),
            target_id=updated["id"],
            payload={"title": updated.get("title"), "content_length": len(str(updated.get("content") or ""))},
            created_at=updated.get("updated_at"),
        )
        return updated

    def delete_announcement(self, teacher_username: str, announcement_id: str) -> bool:
        existing = self.repository.get_announcement(announcement_id)
        if not existing:
            raise ValueError("公告不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权删除该公告")
        deleted = self.repository.delete_announcement(announcement_id)
        if deleted:
            self.teacher_event_repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="announcement_deleted",
                course_id=existing.get("course_id"),
                class_name=existing.get("class_name"),
                target_id=announcement_id,
                payload={"title": existing.get("title")},
                created_at=datetime.now().isoformat(),
            )
        return deleted

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

    def update_topic(self, teacher_username: str, topic_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.repository.get_topic(topic_id)
        if not existing:
            raise ValueError("讨论话题不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权编辑该讨论话题")
        updated = self.repository.update_topic(topic_id, payload)
        if not updated:
            raise ValueError("讨论话题不存在")
        self.teacher_event_repo.record_interaction_event(
            teacher_username=teacher_username,
            event_type="discussion_topic_updated",
            course_id=updated.get("course_id"),
            class_name=updated.get("class_name"),
            target_id=updated["id"],
            payload={"title": updated.get("title")},
            created_at=updated.get("updated_at"),
        )
        return updated

    def delete_topic(self, teacher_username: str, topic_id: str) -> bool:
        existing = self.repository.get_topic(topic_id)
        if not existing:
            raise ValueError("讨论话题不存在")
        if str(existing.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权删除该讨论话题")
        deleted = self.repository.delete_topic(topic_id)
        if deleted:
            self.teacher_event_repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="discussion_topic_deleted",
                course_id=existing.get("course_id"),
                class_name=existing.get("class_name"),
                target_id=topic_id,
                payload={"title": existing.get("title")},
                created_at=datetime.now().isoformat(),
            )
        return deleted

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

        replied_post = self.repository.get_post(replied_to_post_id) if replied_to_post_id else None
        response_minutes = None
        if author_role == "teacher":
            base = None
            if replied_to_created_at:
                base = self._parse_time(replied_to_created_at)
            if base is None and replied_post:
                base = self._parse_time(str(replied_post.get("created_at") or ""))
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
            target_student_username = None
            if replied_post and str(replied_post.get("author_role") or "") == "student":
                target_student_username = str(replied_post.get("author_username") or "").strip() or None
            self.repository.update_topic_counters(topic_id, teacher_reply_delta=1)
            self.teacher_event_repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="teacher_reply",
                course_id=topic.get("course_id"),
                class_name=topic.get("class_name"),
                target_id=topic_id,
                student_username=target_student_username,
                response_minutes=response_minutes,
                payload={
                    "post_id": record["id"],
                    "content_length": len(content),
                    "replied_to_post_id": replied_to_post_id,
                    "reply_mode": "targeted" if target_student_username else "direct",
                },
                created_at=record["created_at"],
            )
        return record

    def update_post(
        self,
        *,
        teacher_username: str,
        post_id: str,
        actor_username: str,
        actor_role: str,
        content: str,
    ) -> Dict[str, Any]:
        post = self.repository.get_post(post_id)
        if not post:
            raise ValueError("帖子不存在")
        topic = self.repository.get_topic(str(post.get("topic_id") or ""))
        if not topic:
            raise ValueError("讨论话题不存在")
        if str(topic.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权操作该讨论话题")

        is_teacher_topic_owner = actor_role == "teacher" and actor_username == teacher_username
        is_student_author = actor_role == "student" and actor_username == str(post.get("author_username") or "")
        if not (is_teacher_topic_owner or is_student_author):
            raise PermissionError("无权编辑该帖子")

        updated = self.repository.update_post(post_id, content)
        if not updated:
            raise ValueError("帖子不存在")
        return updated

    def delete_post(
        self,
        *,
        teacher_username: str,
        post_id: str,
        actor_username: str,
        actor_role: str,
    ) -> bool:
        post = self.repository.get_post(post_id)
        if not post:
            raise ValueError("帖子不存在")
        topic = self.repository.get_topic(str(post.get("topic_id") or ""))
        if not topic:
            raise ValueError("讨论话题不存在")
        if str(topic.get("teacher_username") or "") != teacher_username:
            raise PermissionError("无权操作该讨论话题")

        is_teacher_topic_owner = actor_role == "teacher" and actor_username == teacher_username
        is_student_author = actor_role == "student" and actor_username == str(post.get("author_username") or "")
        if not (is_teacher_topic_owner or is_student_author):
            raise PermissionError("无权删除该帖子")

        return self.repository.delete_post(post_id)

    def build_interaction_analytics(self, teacher_username: str, window_days: int = 30) -> Dict[str, Any]:
        topics = self.list_topics(teacher_username)
        announcements = self.list_announcements(teacher_username)
        since = datetime.now() - timedelta(days=max(1, window_days))

        def within(value: Optional[str]) -> bool:
            if not value:
                return False
            try:
                return datetime.fromisoformat(value) >= since
            except Exception:
                return False

        recent_announcements = [item for item in announcements if within(str(item.get("published_at") or ""))]
        all_posts = [post for topic in topics for post in (topic.get("posts") or [])]
        recent_posts = [item for item in all_posts if within(str(item.get("created_at") or ""))]
        recent_student_posts = [item for item in recent_posts if str(item.get("author_role") or "") == "student"]
        recent_teacher_posts = [item for item in recent_posts if str(item.get("author_role") or "") == "teacher"]
        response_minutes = [
            float(item.get("response_minutes"))
            for item in recent_teacher_posts
            if item.get("response_minutes") is not None
        ]
        avg_response = round(sum(response_minutes) / len(response_minutes), 2) if response_minutes else None

        class_counter: Dict[str, int] = {}
        for item in topics:
            class_name = str(item.get("class_name") or "未指定")
            class_counter[class_name] = class_counter.get(class_name, 0) + 1

        top_classes = [
            {"class_name": key, "topic_count": value}
            for key, value in sorted(class_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ]

        return {
            "window_days": int(window_days),
            "announcement_count": len(announcements),
            "topic_count": len(topics),
            "post_count": len(all_posts),
            "recent_announcement_count": len(recent_announcements),
            "recent_student_question_count": len(recent_student_posts),
            "recent_teacher_reply_count": len(recent_teacher_posts),
            "avg_teacher_response_minutes": avg_response,
            "top_active_classes": top_classes,
        }

    def _parse_time(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

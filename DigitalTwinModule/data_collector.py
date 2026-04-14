from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.course_tree import CourseTree
from DigitalTwinModule.models import KnowledgeNodeScore, TwinProfile, ensure_data_dirs
from DigitalTwinModule.score_calculator import ScoreCalculator
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from tools.session_manager import get_session_manager
from tools.user_manager import UserManager

logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self) -> None:
        ensure_data_dirs()
        self.sqlite_store = get_sqlite_store()
        self.user_manager = UserManager()
        self.store = TwinProfileStore()
        self.calculator = ScoreCalculator()
        self.course_tree = CourseTree()
        self.trend_tracker = TrendTracker()
        self.session_manager = get_session_manager()

    def _resolve_student_username(self, identifier: str) -> str | None:
        user = self.sqlite_store.get_user_by_identifier("student", identifier)
        if user and user.get("username"):
            return str(user["username"])
        logger.warning("collect-source: unresolved student identifier=%s", identifier)
        return None

    def _get_or_create_node(self, profile: TwinProfile, node_id: str) -> tuple[TwinProfile, KnowledgeNodeScore]:
        for node in profile.knowledge_nodes:
            if node.node_id == node_id:
                return profile, node

        node_path = self.course_tree.get_node_path(node_id)
        if not node_path:
            logger.warning("node_id '%s' not found in CourseTree, using [node_id] as path", node_id)
            node_path = [node_id]

        new_node = KnowledgeNodeScore(
            node_id=node_id,
            node_path=node_path,
            quiz_score=None,
            progress=0.0,
            study_duration_minutes=0.0,
            llm_interaction_count=0,
            mastery_score=0.0,
        )
        updated_profile = profile.model_copy(update={"knowledge_nodes": profile.knowledge_nodes + [new_node]})
        return updated_profile, new_node

    def _update_node(self, profile: TwinProfile, node_id: str, **kwargs) -> TwinProfile:
        updated_nodes = []
        for node in profile.knowledge_nodes:
            if node.node_id == node_id:
                updated_nodes.append(node.model_copy(update=kwargs))
            else:
                updated_nodes.append(node)
        return profile.model_copy(update={"knowledge_nodes": updated_nodes})

    def _save_profile(self, profile: TwinProfile) -> TwinProfile:
        profile = self.calculator.recalculate_profile(profile)
        profile = profile.model_copy(update={"last_updated": datetime.now().isoformat()})
        self.store.save(profile)
        return profile

    def collect_quiz_score(self, username: str, node_id: str, score: float) -> None:
        username = self._resolve_student_username(username)
        if not username:
            return
        profile = self.store.load_or_create(username)
        profile, _ = self._get_or_create_node(profile, node_id)
        profile = self._update_node(profile, node_id, quiz_score=score)
        self._save_profile(profile)
        logger.info("collect_quiz_score: %s / %s = %.1f", username, node_id, score)

    def collect_progress(self, username: str) -> None:
        username = self._resolve_student_username(username)
        if not username:
            return
        raw_students: list[dict] = self.user_manager._load_users(Path("data/Users/student.json"))
        student = next((s for s in raw_students if s.get("username") == username), None)
        if student is None:
            logger.warning("collect_progress: username '%s' not found in student data", username)
            return

        progress_list: list[dict] = student.get("progress", [])
        if not progress_list:
            logger.warning("collect_progress: no progress data for '%s'", username)
            return

        profile = self.store.load_or_create(username)

        for progress_item in progress_list:
            topic: str = progress_item.get("topic", "")
            date_entries: list = progress_item.get("date", [])

            latest_value: float | None = None
            for entry in reversed(date_entries):
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[0] is not None and entry[1] is not None:
                    latest_value = float(entry[1])
                    break

            if latest_value is None:
                logger.warning("collect_progress: no valid progress value for topic '%s' of '%s'", topic, username)
                continue

            matched_leaf_ids = [
                nid for nid in self.course_tree.get_all_leaf_nodes()
                if len(self.course_tree.get_node_path(nid)) > 1 and self.course_tree.get_node_path(nid)[1] == topic
            ]

            if not matched_leaf_ids:
                logger.warning("collect_progress: no leaf nodes found for topic '%s'", topic)
                continue

            for leaf_id in matched_leaf_ids:
                if any(node.node_id == leaf_id for node in profile.knowledge_nodes):
                    profile = self._update_node(profile, leaf_id, progress=latest_value)

        self._save_profile(profile)
        logger.info("collect_progress: done for '%s'", username)

    def collect_llm_interactions(self, username: str) -> None:
        username = self._resolve_student_username(username)
        if not username:
            return
        try:
            raw_logs: list[dict] = self.sqlite_store.list_llm_logs_for_user(username, user_type="student")
        except Exception:
            raw_logs = []

        if not raw_logs:
            logger.warning("collect_llm_interactions: llm logs are empty")
            return

        all_leaf_ids = set(self.course_tree.get_all_leaf_nodes())
        node_counts: dict[str, int] = {}

        for entry in raw_logs:
            metadata = entry.get("metadata", {}) or {}
            topic = metadata.get("topic", "")
            module = entry.get("module", "") or ""
            matched_node: str | None = None

            if topic and topic in all_leaf_ids:
                matched_node = topic
            elif topic:
                for leaf_id in all_leaf_ids:
                    if topic in leaf_id or leaf_id in topic:
                        matched_node = leaf_id
                        break

            if matched_node is None and module:
                for leaf_id in all_leaf_ids:
                    if leaf_id in module or module in leaf_id:
                        matched_node = leaf_id
                        break

            if matched_node:
                node_counts[matched_node] = node_counts.get(matched_node, 0) + 1

        if not node_counts:
            logger.info("collect_llm_interactions: no matching nodes found for '%s'", username)
            return

        profile = self.store.load_or_create(username)
        for node_id, count in node_counts.items():
            if any(node.node_id == node_id for node in profile.knowledge_nodes):
                existing_node = next(node for node in profile.knowledge_nodes if node.node_id == node_id)
                new_count = existing_node.llm_interaction_count + count
                profile = self._update_node(profile, node_id, llm_interaction_count=new_count)

        self._save_profile(profile)
        logger.info("collect_llm_interactions: updated %d nodes for '%s'", len(node_counts), username)

    def collect_session_duration(self, username: str) -> None:
        username = self._resolve_student_username(username)
        if not username:
            return
        user_sessions: list[dict] = []
        try:
            user_sessions = self.sqlite_store.list_sessions_for_user("student", username)
        except Exception:
            user_sessions = []

        if not user_sessions:
            logger.info("collect_session_duration: no sessions found for '%s'", username)
            return

        profile = self.store.load_or_create(username)
        all_leaf_ids_set = set(self.course_tree.get_all_leaf_nodes())

        for session in user_sessions:
            created_at_str = session.get("created_at", "")
            last_accessed_str = session.get("last_accessed", "")
            current_node = session.get("current_node")

            if not created_at_str or not last_accessed_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
                last_accessed = datetime.fromisoformat(last_accessed_str)
            except ValueError as exc:
                logger.warning("collect_session_duration: invalid datetime in session: %s", exc)
                continue

            duration_minutes = (last_accessed - created_at).total_seconds() / 60.0
            if duration_minutes <= 0:
                continue

            if current_node and current_node in all_leaf_ids_set:
                if any(node.node_id == current_node for node in profile.knowledge_nodes):
                    existing_node = next(node for node in profile.knowledge_nodes if node.node_id == current_node)
                    new_duration = existing_node.study_duration_minutes + duration_minutes
                    profile = self._update_node(profile, current_node, study_duration_minutes=new_duration)
            else:
                existing_ids = [node.node_id for node in profile.knowledge_nodes]
                if not existing_ids:
                    continue
                per_node_duration = duration_minutes / len(existing_ids)
                for leaf_id in existing_ids:
                    existing_node = next(node for node in profile.knowledge_nodes if node.node_id == leaf_id)
                    new_duration = existing_node.study_duration_minutes + per_node_duration
                    profile = self._update_node(profile, leaf_id, study_duration_minutes=new_duration)

        self._save_profile(profile)
        logger.info("collect_session_duration: done for '%s', processed %d sessions", username, len(user_sessions))

    def collect_all(self, username: str) -> None:
        username = self._resolve_student_username(username)
        if not username:
            return
        logger.info("collect_all: start for '%s'", username)
        try:
            self.collect_progress(username)
        except Exception as exc:
            logger.warning("collect_all: collect_progress failed for '%s': %s", username, exc)

        try:
            self.collect_llm_interactions(username)
        except Exception as exc:
            logger.warning("collect_all: collect_llm_interactions failed for '%s': %s", username, exc)

        try:
            self.collect_session_duration(username)
        except Exception as exc:
            logger.warning("collect_all: collect_session_duration failed for '%s': %s", username, exc)

        try:
            profile = self.store.load_or_create(username)
            self.trend_tracker.record_daily_snapshot(username, profile.overall_mastery)
        except Exception as exc:
            logger.error("collect_all: trend_tracker.record_daily_snapshot failed for '%s': %s", username, exc)

        logger.info("collect_all: done for '%s'", username)

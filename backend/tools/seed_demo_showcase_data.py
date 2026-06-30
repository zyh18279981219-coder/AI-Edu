from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for item in (PROJECT_ROOT, BACKEND_ROOT):
    value = str(item)
    if value not in sys.path:
        sys.path.insert(0, value)

from DatabaseModule.database_factory import DatabaseFactory
from HomeworkModule.repository import HomeworkRepository


SEED_TAG = "ai_education_showcase_20260629"
TEACHER = "teacher"
COURSE_ID = "course_big_data"

DEMO_STUDENTS = [
    ("zyh", "zyh", 64.0),
    ("stu_liuyiming", "刘一鸣", 78.0),
    ("stu_wangqiyu", "王启宇", 56.0),
    ("stu_chenxi", "陈曦", 84.0),
    ("stu_zhaomeng", "赵萌", 47.0),
]

DEMO_COURSE_NODES = [
    ("数据采集流程", "数据采集流程", ["大数据工程实践", "数据采集", "数据采集流程"], 2, "数据采集"),
    ("日志数据清洗", "日志数据清洗", ["大数据工程实践", "数据预处理", "日志数据清洗"], 2, "数据预处理"),
    ("Kafka 数据接入", "Kafka 数据接入", ["大数据工程实践", "数据接入", "Kafka 数据接入"], 2, "数据接入"),
    ("Spark 指标统计", "Spark 指标统计", ["大数据工程实践", "批处理分析", "Spark 指标统计"], 2, "批处理分析"),
    ("可视化报表解读", "可视化报表解读", ["大数据工程实践", "数据可视化", "可视化报表解读"], 2, "数据可视化"),
    ("数据质量评估", "数据质量评估", ["大数据工程实践", "数据治理", "数据质量评估"], 2, "数据治理"),
    ("数仓分层建模", "数仓分层建模", ["大数据工程实践", "数据仓库", "数仓分层建模"], 2, "数据仓库"),
    ("实时监控指标", "实时监控指标", ["大数据工程实践", "实时计算", "实时监控指标"], 2, "实时计算"),
]


def _now() -> datetime:
    return datetime.now()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _table_exists(cursor: Any, table: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table,))
    return cursor.fetchone() is not None


def _table_columns(cursor: Any, table: str) -> set[str]:
    if not _table_exists(cursor, table):
        return set()
    cursor.execute(f"SHOW COLUMNS FROM {table}")
    return {str(row["Field"]) for row in cursor.fetchall()}


def _delete_seed_rows(store: Any) -> dict[str, int]:
    deleted: dict[str, int] = {}
    demo_usernames = [item[0] for item in DEMO_STUDENTS]
    demo_placeholders = ",".join(["%s"] * len(demo_usernames))
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for table in [
                "teaching_interaction_events",
                "teaching_research_events",
                "teaching_announcements",
                "teaching_discussion_posts",
                "teaching_discussion_topics",
                "teaching_research_records",
                "homework_grading_events",
                "teacher_intervention_events",
                "resource_learning_events",
                "fivee_effectiveness_records",
                "user_interaction",
                "events",
                "quiz_attempts",
            ]:
                if not _table_exists(cursor, table):
                    continue
                columns = _table_columns(cursor, table)
                if "payload_json" in columns:
                    cursor.execute(f"DELETE FROM {table} WHERE payload_json LIKE %s", (f"%{SEED_TAG}%",))
                elif table == "events":
                    cursor.execute("DELETE FROM events WHERE event_data LIKE %s", (f"%{SEED_TAG}%",))
                elif table == "teaching_announcements":
                    cursor.execute("DELETE FROM teaching_announcements WHERE id LIKE %s OR content LIKE %s", ("showcase_%", f"%{SEED_TAG}%"))
                elif table == "teaching_discussion_posts":
                    cursor.execute("DELETE FROM teaching_discussion_posts WHERE id LIKE %s OR content LIKE %s", ("showcase_%", f"%{SEED_TAG}%"))
                elif table == "teaching_discussion_topics":
                    cursor.execute("DELETE FROM teaching_discussion_topics WHERE id LIKE %s OR content LIKE %s", ("showcase_%", f"%{SEED_TAG}%"))
                elif table == "teaching_research_records":
                    cursor.execute("DELETE FROM teaching_research_records WHERE id LIKE %s OR description LIKE %s", ("showcase_%", f"%{SEED_TAG}%"))
                deleted[table] = int(cursor.rowcount or 0)

            if _table_exists(cursor, "diagnosis_reports"):
                cursor.execute(
                    f"""
                    DELETE FROM diagnosis_reports
                    WHERE report_id LIKE %s
                       OR payload_json LIKE %s
                       OR (username IN ({demo_placeholders}) AND report_id LIKE %s)
                    """,
                    (f"demo_showcase_%", f"%{SEED_TAG}%", *demo_usernames, "diag_%"),
                )
                deleted["diagnosis_reports"] = int(cursor.rowcount or 0)

            if _table_exists(cursor, "learning_plans"):
                learning_plan_columns = _table_columns(cursor, "learning_plans")
                if "payload_json" in learning_plan_columns:
                    cursor.execute(
                        f"""
                        SELECT plan_id FROM learning_plans
                        WHERE filename LIKE %s
                           OR filename LIKE %s
                           OR payload_json LIKE %s
                           OR (username IN ({demo_placeholders}) AND filename LIKE %s)
                        """,
                        ("showcase_path_%", "showcase_plan_%", f"%{SEED_TAG}%", *demo_usernames, "%_path_%"),
                    )
                else:
                    cursor.execute(
                        f"""
                        SELECT plan_id FROM learning_plans
                        WHERE filename LIKE %s
                           OR filename LIKE %s
                           OR description LIKE %s
                           OR (username IN ({demo_placeholders}) AND filename LIKE %s)
                        """,
                        ("showcase_path_%", "showcase_plan_%", f"%{SEED_TAG}%", *demo_usernames, "%_path_%"),
                    )
                plan_ids = [int(row["plan_id"]) for row in cursor.fetchall()]
                if plan_ids:
                    placeholders = ",".join(["%s"] * len(plan_ids))
                    cursor.execute(f"DELETE FROM learning_path_node_status WHERE plan_id IN ({placeholders})", tuple(plan_ids))
                    deleted["learning_path_node_status"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM learning_plan_nodes WHERE plan_id IN ({placeholders})", tuple(plan_ids))
                    deleted["learning_plan_nodes"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM learning_plans WHERE plan_id IN ({placeholders})", tuple(plan_ids))
                    deleted["learning_plans"] = int(cursor.rowcount or 0)

            if _table_exists(cursor, "homework_assignments"):
                cursor.execute("SELECT id FROM homework_assignments WHERE id LIKE %s OR description LIKE %s", ("showcase_hw_%", f"%{SEED_TAG}%"))
                assignment_ids = [str(row["id"]) for row in cursor.fetchall()]
                if assignment_ids:
                    placeholders = ",".join(["%s"] * len(assignment_ids))
                    cursor.execute(f"DELETE FROM homework_submissions WHERE assignment_id IN ({placeholders})", tuple(assignment_ids))
                    deleted["homework_submissions"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM homework_assignment_knowledge_points WHERE assignment_id IN ({placeholders})", tuple(assignment_ids))
                    deleted["homework_assignment_knowledge_points"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM homework_assignments WHERE id IN ({placeholders})", tuple(assignment_ids))
                    deleted["homework_assignments"] = int(cursor.rowcount or 0)

            if _table_exists(cursor, "resource_learning_events"):
                cursor.execute("DELETE FROM resource_learning_events WHERE course_id=%s AND node_id LIKE %s", (COURSE_ID, "showcase_%"))
                deleted["resource_learning_events_legacy_showcase"] = int(cursor.rowcount or 0)
            if _table_exists(cursor, "quiz_attempts"):
                cursor.execute("DELETE FROM quiz_attempts WHERE course_id=%s AND node_id LIKE %s", (COURSE_ID, "showcase_%"))
                deleted["quiz_attempts_legacy_showcase"] = int(cursor.rowcount or 0)
            if _table_exists(cursor, "twin_profile_nodes"):
                cursor.execute("DELETE FROM twin_profile_nodes WHERE course_id=%s AND node_id LIKE %s", (COURSE_ID, "showcase_%"))
                deleted["twin_profile_nodes_legacy_showcase"] = int(cursor.rowcount or 0)
            if _table_exists(cursor, "resources"):
                cursor.execute("DELETE FROM resources WHERE course_id=%s AND node_id LIKE %s", (COURSE_ID, "showcase_%"))
                deleted["resources_legacy_showcase"] = int(cursor.rowcount or 0)
            if _table_exists(cursor, "course_nodes"):
                cursor.execute("DELETE FROM course_nodes WHERE course_id=%s AND node_id LIKE %s", (COURSE_ID, "showcase_%"))
                deleted["course_nodes_legacy_showcase"] = int(cursor.rowcount or 0)

            if _table_exists(cursor, "intervention_packages"):
                cursor.execute("SELECT package_id FROM intervention_packages WHERE package_id LIKE %s OR payload_json LIKE %s", ("showcase_pkg_%", f"%{SEED_TAG}%"))
                package_ids = [str(row["package_id"]) for row in cursor.fetchall()]
                if package_ids:
                    placeholders = ",".join(["%s"] * len(package_ids))
                    cursor.execute(f"DELETE FROM intervention_package_student_records WHERE package_id IN ({placeholders})", tuple(package_ids))
                    deleted["intervention_package_student_records"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM intervention_package_items WHERE package_id IN ({placeholders})", tuple(package_ids))
                    deleted["intervention_package_items"] = int(cursor.rowcount or 0)
                    cursor.execute(f"DELETE FROM intervention_packages WHERE package_id IN ({placeholders})", tuple(package_ids))
                    deleted["intervention_packages"] = int(cursor.rowcount or 0)
    return {key: value for key, value in deleted.items() if value}


def _fetch_course_nodes(store: Any) -> list[dict[str, Any]]:
    demo_node_ids = [item[0] for item in DEMO_COURSE_NODES]
    placeholders = ",".join(["%s"] * len(demo_node_ids))
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT course_id, node_id, node_name, node_path_json, depth
                FROM course_nodes
                WHERE course_id = %s AND node_id IN ({placeholders})
                ORDER BY FIELD(node_id, {placeholders})
                LIMIT 18
                """,
                (COURSE_ID, *demo_node_ids, *demo_node_ids),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            if rows:
                return rows
            cursor.execute(
                """
                SELECT course_id, node_id, node_name, node_path_json, depth
                FROM course_nodes
                WHERE course_id = %s
                ORDER BY depth DESC, node_detail_id
                LIMIT 18
                """,
                (COURSE_ID,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        raise RuntimeError("course_big_data has no course_nodes; publish or sync the course first")
    return rows


def _seed_readable_course_nodes(store: Any) -> None:
    now = _now().strftime("%Y-%m-%d %H:%M:%S")
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO courses
                (course_id, course_name, source_path, description, lifecycle_status, published_at, published_by, payload_json, created_at, updated_at)
                VALUES (%s, '大数据工程实践', 'showcase://course_big_data', %s, 'published', %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    lifecycle_status='published',
                    description=COALESCE(description, VALUES(description)),
                    published_at=COALESCE(published_at, VALUES(published_at)),
                    published_by=COALESCE(published_by, VALUES(published_by)),
                    updated_at=VALUES(updated_at)
                """,
                (COURSE_ID, f"{SEED_TAG} 演示课程节点补充。", now, TEACHER, _json({"seed_tag": SEED_TAG}), now, now),
            )
            for node_id, node_name, path, depth, parent in DEMO_COURSE_NODES:
                cursor.execute(
                    """
                    INSERT INTO course_nodes
                    (course_id, node_id, node_name, node_path_json, depth, parent_node_id, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        node_name=VALUES(node_name),
                        node_path_json=VALUES(node_path_json),
                        depth=VALUES(depth),
                        parent_node_id=VALUES(parent_node_id),
                        payload_json=VALUES(payload_json),
                        updated_at=VALUES(updated_at)
                    """,
                    (
                        COURSE_ID,
                        node_id,
                        node_name,
                        _json(path),
                        depth,
                        parent,
                        _json({"seed_tag": SEED_TAG, "name": node_name, "is_showcase": True}),
                        now,
                        now,
                    ),
                )
                for suffix, resource_type, title in [
                    ("video", "video", f"{node_name} 微课视频"),
                    ("doc", "pdf", f"{node_name} 操作讲义"),
                ]:
                    resource_path = f"demo://{node_id}/{suffix}"
                    cursor.execute(
                        """
                        INSERT INTO resources
                        (course_id, node_id, resource_path, resource_type, title, payload_json,
                         resource_source, quality_status, review_status, is_enabled, is_deleted, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 'showcase', 'passed', 'enabled', 1, 0, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            resource_type=VALUES(resource_type),
                            title=VALUES(title),
                            payload_json=VALUES(payload_json),
                            resource_source=VALUES(resource_source),
                            quality_status=VALUES(quality_status),
                            review_status=VALUES(review_status),
                            is_enabled=VALUES(is_enabled),
                            is_deleted=0,
                            updated_at=VALUES(updated_at)
                        """,
                        (
                            COURSE_ID,
                            node_id,
                            resource_path,
                            resource_type,
                            title,
                            _json({"seed_tag": SEED_TAG, "node_name": node_name}),
                            now,
                            now,
                        ),
                    )


def _seed_career_ability_mappings(store: Any, nodes: list[dict[str, Any]], teacher_id: int) -> dict[str, Any]:
    node_ids = {str(node.get("node_id") or "") for node in nodes}

    def existing_node(*candidates: str) -> str | None:
        for node_id in candidates:
            if node_id in node_ids:
                return node_id
        return None

    position = store.upsert_career_position(
        COURSE_ID,
        "大数据开发工程师",
        position_type="primary",
        target_rank=1,
        source_keyword=SEED_TAG,
        created_by=teacher_id,
    )
    ability_items = [
        {
            "ability_name": "数据采集与接入实现",
            "ability_category": "数据工程",
            "demand_level": 9,
            "support_level": "high",
            "evidence": {"seed_tag": SEED_TAG, "source": "demo_position_profile"},
        },
        {
            "ability_name": "数据清洗与质量评估",
            "ability_category": "数据治理",
            "demand_level": 8,
            "support_level": "high",
            "evidence": {"seed_tag": SEED_TAG, "source": "demo_position_profile"},
        },
        {
            "ability_name": "批处理指标开发",
            "ability_category": "计算分析",
            "demand_level": 8,
            "support_level": "high",
            "evidence": {"seed_tag": SEED_TAG, "source": "demo_position_profile"},
        },
        {
            "ability_name": "业务报表解读与表达",
            "ability_category": "数据应用",
            "demand_level": 7,
            "support_level": "medium",
            "evidence": {"seed_tag": SEED_TAG, "source": "demo_position_profile"},
        },
    ]
    saved = store.upsert_career_abilities(int(position["position_id"]), ability_items)
    abilities_by_name = {
        str(item.get("ability_name")): item
        for item in store.list_course_abilities(COURSE_ID)
        if str(item.get("ability_name")) in {str(ability["ability_name"]) for ability in ability_items}
    }
    mapping_specs = [
        ("数据采集与接入实现", existing_node("数据采集流程"), "high"),
        ("数据采集与接入实现", existing_node("Kafka 数据接入"), "high"),
        ("数据清洗与质量评估", existing_node("日志数据清洗"), "high"),
        ("数据清洗与质量评估", existing_node("数据质量评估"), "medium"),
        ("批处理指标开发", existing_node("Spark 指标统计"), "high"),
        ("批处理指标开发", existing_node("数仓分层建模", "实时监控指标"), "medium"),
        ("业务报表解读与表达", existing_node("可视化报表解读"), "high"),
    ]
    mappings = []
    for ability_name, node_id, support_level in mapping_specs:
        ability = abilities_by_name.get(ability_name)
        if not ability or not node_id:
            continue
        mappings.append(
            {
                "node_id": node_id,
                "ability_id": ability["ability_id"],
                "support_level": support_level,
                "review_status": "confirmed",
                "match_reason": "演示课程底座已发布，教师确认该叶子知识点支撑岗位能力达成。",
                "evidence": {"seed_tag": SEED_TAG, "source": "teacher_confirmed_demo_mapping"},
            }
        )
    mapping_result = store.upsert_course_ability_mappings(COURSE_ID, mappings, updated_by=teacher_id)
    return {
        "position_id": int(position["position_id"]),
        "abilities_saved": int(saved.get("saved") or 0),
        "mappings_saved": int(mapping_result.get("saved") or 0),
        "mappings_rejected": mapping_result.get("rejected") or [],
    }


def _node_path(row: dict[str, Any]) -> list[str]:
    raw = row.get("node_path_json")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            pass
    return [str(row.get("node_name") or row.get("node_id") or "知识点")]


def _upsert_users_and_links(store: Any) -> dict[str, int]:
    now = _now().strftime("%Y-%m-%d %H:%M:%S")
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (login_id, user_type, username, password, display_name, email, created_at, updated_at)
                VALUES (%s, 'teacher', %s, '123456', 'teacher', 'teacher@example.com', %s, %s)
                ON DUPLICATE KEY UPDATE password='123456', display_name=VALUES(display_name), updated_at=VALUES(updated_at)
                """,
                (TEACHER, TEACHER, now, now),
            )
            cursor.execute("SELECT user_id FROM users WHERE user_type='teacher' AND username=%s", (TEACHER,))
            teacher_id = int(cursor.fetchone()["user_id"])
            for username, display_name, _mastery in DEMO_STUDENTS:
                cursor.execute(
                    """
                    INSERT INTO users (login_id, user_type, username, password, display_name, teacher_id, email, created_at, updated_at)
                    VALUES (%s, 'student', %s, '123456', %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE password='123456', display_name=VALUES(display_name), teacher_id=VALUES(teacher_id), updated_at=VALUES(updated_at)
                    """,
                    (username, username, display_name, teacher_id, f"{username}@example.com", now, now),
                )
                cursor.execute("SELECT user_id FROM users WHERE user_type='student' AND username=%s", (username,))
                student_id = int(cursor.fetchone()["user_id"])
                cursor.execute(
                    """
                    INSERT INTO teacher_student_links (teacher_username, student_username, teacher_user_id, student_user_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE teacher_user_id=VALUES(teacher_user_id), student_user_id=VALUES(student_user_id), updated_at=VALUES(updated_at)
                    """,
                    (TEACHER, username, teacher_id, student_id, now),
                )
    return {"teacher_id": teacher_id, "student_count": len(DEMO_STUDENTS)}


def _student_id_map(store: Any) -> dict[str, int]:
    usernames = [item[0] for item in DEMO_STUDENTS]
    placeholders = ",".join(["%s"] * len(usernames))
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT username, user_id FROM users WHERE user_type='student' AND username IN ({placeholders})", tuple(usernames))
            return {str(row["username"]): int(row["user_id"]) for row in cursor.fetchall()}


def _seed_twin_quiz_resource_and_diagnosis(store: Any, nodes: list[dict[str, Any]], student_ids: dict[str, int]) -> None:
    now = _now()
    today = now.date()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for s_idx, (username, display_name, overall) in enumerate(DEMO_STUDENTS):
                user_id = student_ids[username]
                knowledge_nodes: list[dict[str, Any]] = []
                weak_nodes: list[dict[str, Any]] = []
                selected = nodes[s_idx : s_idx + 8] if len(nodes) >= s_idx + 8 else nodes[:8]
                for n_idx, node in enumerate(selected):
                    node_id = str(node["node_id"])
                    node_name = str(node.get("node_name") or node_id)
                    mastery = max(22.0, min(96.0, overall + ((n_idx % 5) - 2) * 8 - (10 if n_idx in {1, 5} else 0)))
                    quiz_score = max(10.0, min(100.0, mastery + (6 if n_idx % 2 == 0 else -7)))
                    progress = max(8.0, min(100.0, mastery + 14))
                    path = _node_path(node)
                    knowledge_nodes.append(
                        {
                            "course_id": COURSE_ID,
                            "node_id": node_id,
                            "node_path": path,
                            "quiz_score": quiz_score,
                            "progress": progress,
                            "study_duration_minutes": 25 + n_idx * 9 + s_idx * 3,
                            "llm_interaction_count": 2 + ((n_idx + s_idx) % 9),
                            "mastery_score": mastery,
                        }
                    )
                    if mastery < 65:
                        weak_nodes.append({"node_id": node_id, "node_name": node_name, "mastery_score": round(mastery, 2), "node_path": path})
                    if n_idx < 5:
                        payload = {
                            "seed_tag": SEED_TAG,
                            "question_set": f"{node_name} 随堂测",
                            "correct": int(max(1, round(quiz_score / 20))),
                            "total_questions": 5,
                        }
                        cursor.execute(
                            """
                            INSERT INTO quiz_attempts (user_id, username, course_id, node_id, score, total, passed, payload_json, created_at)
                            VALUES (%s, %s, %s, %s, %s, 100, %s, %s, %s)
                            """,
                            (user_id, username, COURSE_ID, node_id, round(quiz_score, 2), 1 if quiz_score >= 60 else 0, _json(payload), now - timedelta(days=5 - n_idx)),
                        )
                    if n_idx < 4:
                        event_payload = {
                            "seed_tag": SEED_TAG,
                            "node_name": node_name,
                            "event_type": "completed" if mastery >= 70 else "viewed",
                            "progress_percent": min(100, progress),
                        }
                        cursor.execute(
                            """
                            INSERT INTO resource_learning_events
                            (username, user_id, course_id, node_id, resource_id, resource_path, event_type, duration_seconds, progress_percent, is_completed, payload_json, created_at)
                            VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                username,
                                user_id,
                                COURSE_ID,
                                node_id,
                                f"demo://resource/{node_id}",
                                "completed" if mastery >= 70 else "viewed",
                                int(900 + n_idx * 420),
                                round(min(100, progress), 2),
                                1 if mastery >= 70 else 0,
                                _json(event_payload),
                                now - timedelta(days=4 - n_idx),
                            ),
                        )

                store.save_twin_profile(
                    username,
                    {
                        "username": username,
                        "user_id": user_id,
                        "course_id": COURSE_ID,
                        "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "overall_mastery": overall,
                        "knowledge_nodes": knowledge_nodes,
                    },
                )
                for day_offset in range(13, -1, -1):
                    score = max(18.0, min(98.0, overall - day_offset * 0.8 + ((s_idx % 3) - 1) * 1.5))
                    payload = {
                        "seed_tag": SEED_TAG,
                        "study_minutes": 35 + (13 - day_offset) * 5 + s_idx * 3,
                        "weak_node_count": len(weak_nodes),
                        "quiz_avg": round(min(99.0, score + 4), 2),
                    }
                    cursor.execute(
                        """
                        INSERT INTO twin_history (username, user_id, snapshot_date, overall_mastery, payload_json, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), overall_mastery=VALUES(overall_mastery), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                        """,
                        (username, user_id, today - timedelta(days=day_offset), round(score, 2), _json(payload), now, now),
                    )

                report_payload = {
                    "seed_tag": SEED_TAG,
                    "student": display_name,
                    "risk_level": "高" if overall < 55 else "中" if overall < 72 else "低",
                    "weak_nodes": weak_nodes[:5],
                    "summary": f"{display_name} 当前掌握度 {overall:.1f}，建议优先处理 {len(weak_nodes)} 个薄弱点。",
                    "evidence": ["测验记录", "资源学习", "作业提交", "画像趋势"],
                }
                cursor.execute(
                    """
                    INSERT INTO diagnosis_reports
                    (report_id, user_id, username, course_id, report_date, persona_summary, evidence_level, confidence, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, '充分', %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE persona_summary=VALUES(persona_summary), confidence=VALUES(confidence), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                    """,
                    (
                        f"demo_showcase_{username}",
                        user_id,
                        username,
                        COURSE_ID,
                        today,
                        report_payload["summary"],
                        86 if overall >= 60 else 74,
                        _json(report_payload),
                        now,
                        now,
                    ),
                )


def _seed_learning_paths(store: Any, nodes: list[dict[str, Any]], student_ids: dict[str, int]) -> None:
    now = _now().strftime("%Y-%m-%d %H:%M:%S")
    with store.connection() as conn:
        with conn.cursor() as cursor:
            learning_plan_columns = _table_columns(cursor, "learning_plans")
            for s_idx, (username, display_name, overall) in enumerate(DEMO_STUDENTS):
                user_id = student_ids[username]
                filename = f"showcase_path_{username}.json"
                title = f"{display_name} 补弱学习路径"
                payload = {
                    "seed_tag": SEED_TAG,
                    "title": title,
                    "student": username,
                    "generated_by": "诊断智能体",
                    "overall_mastery": overall,
                    "path_summary": "按薄弱知识点、资源复习、随堂测验和作业练习组织。",
                }
                if "payload_json" in learning_plan_columns:
                    cursor.execute(
                        """
                        INSERT INTO learning_plans
                        (username, user_id, filename, plan_path, category, title, description, status, created_at, updated_at, payload_json)
                        VALUES (%s, %s, %s, %s, 'path', %s, %s, 'active', %s, %s, %s)
                        ON DUPLICATE KEY UPDATE title=VALUES(title), description=VALUES(description), status=VALUES(status), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                        """,
                        (username, user_id, filename, f"data/learning_plans/{filename}", title, f"{SEED_TAG} 演示数据：诊断后生成的个性化补学路径。", now, now, _json(payload)),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO learning_plans
                        (username, user_id, filename, plan_path, category, title, description, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, 'path', %s, %s, 'active', %s, %s)
                        ON DUPLICATE KEY UPDATE title=VALUES(title), description=VALUES(description), status=VALUES(status), updated_at=VALUES(updated_at)
                        """,
                        (username, user_id, filename, f"data/learning_plans/{filename}", title, f"{SEED_TAG} 演示数据：诊断后生成的个性化补学路径。", now, now),
                    )
                cursor.execute("SELECT plan_id FROM learning_plans WHERE username=%s AND filename=%s", (username, filename))
                plan_id = int(cursor.fetchone()["plan_id"])
                cursor.execute("DELETE FROM learning_plan_nodes WHERE plan_id=%s", (plan_id,))
                selected = nodes[s_idx : s_idx + 4] if len(nodes) >= s_idx + 4 else nodes[:4]
                for order, node in enumerate(selected, start=1):
                    node_id = str(node["node_id"])
                    node_name = str(node.get("node_name") or node_id)
                    content = {
                        "seed_tag": SEED_TAG,
                        "course_id": COURSE_ID,
                        "node_id": node_id,
                        "node_name": node_name,
                        "reason": "诊断提示该知识点需要复习" if order <= 2 else "用于巩固后续知识点",
                        "resource_hint": f"{node_name} 讲义与视频",
                    }
                    cursor.execute(
                        """
                        INSERT INTO learning_plan_nodes
                        (plan_id, node_key, node_name, node_type, sequence_order, content, metadata, created_at, updated_at)
                        VALUES (%s, %s, %s, 'weak_node', %s, %s, %s, %s, %s)
                        """,
                        (plan_id, node_id, node_name, order, _json(content), _json({"seed_tag": SEED_TAG, "priority": order}), now, now),
                    )


def _seed_regular_learning_plans(store: Any, nodes: list[dict[str, Any]], student_ids: dict[str, int]) -> None:
    now = _now()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            learning_plan_columns = _table_columns(cursor, "learning_plans")
            for s_idx, (username, display_name, overall) in enumerate(DEMO_STUDENTS):
                user_id = student_ids[username]
                filename = f"showcase_plan_{username}.json"
                title = f"{display_name} 本周学习计划"
                start = now.date()
                selected = nodes[s_idx : s_idx + 4] if len(nodes) >= s_idx + 4 else nodes[:4]
                entries: list[dict[str, Any]] = []
                for day, node in enumerate(selected, start=1):
                    node_id = str(node["node_id"])
                    node_name = str(node.get("node_name") or node_id)
                    entries.append(
                        {
                            "date": (start + timedelta(days=day - 1)).isoformat(),
                            "topic": node_name,
                            "priority": "基础补强" if day <= 2 else "实践巩固",
                            "deadline": (start + timedelta(days=day + 1)).isoformat(),
                            "materials": [
                                f"复习课程讲义：{node_name}",
                                f"观看微课视频：{node_name} 核心概念",
                                "完成对应小测并记录错题原因",
                                "在学习路径中标记节点进度",
                            ],
                            "course_id": COURSE_ID,
                            "node_id": node_id,
                            "seed_tag": SEED_TAG,
                        }
                    )
                description = f"{SEED_TAG} 演示数据：学生端普通学习计划，用于学习中心列表和日历展示。"
                if "payload_json" in learning_plan_columns:
                    cursor.execute(
                        """
                        INSERT INTO learning_plans
                        (username, user_id, filename, plan_path, category, title, description, status, created_at, updated_at, payload_json)
                        VALUES (%s, %s, %s, %s, 'user', %s, %s, 'active', %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title=VALUES(title),
                            description=VALUES(description),
                            status=VALUES(status),
                            payload_json=VALUES(payload_json),
                            updated_at=VALUES(updated_at)
                        """,
                        (
                            username,
                            user_id,
                            filename,
                            f"data/learning_plans/{filename}",
                            title,
                            description,
                            now,
                            now,
                            _json({"seed_tag": SEED_TAG, "title": title, "data": entries, "overall_mastery": overall}),
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO learning_plans
                        (username, user_id, filename, plan_path, category, title, description, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, 'user', %s, %s, 'active', %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title=VALUES(title),
                            description=VALUES(description),
                            status=VALUES(status),
                            updated_at=VALUES(updated_at)
                        """,
                        (username, user_id, filename, f"data/learning_plans/{filename}", title, description, now, now),
                    )
                cursor.execute("SELECT plan_id FROM learning_plans WHERE username=%s AND filename=%s", (username, filename))
                plan_id = int(cursor.fetchone()["plan_id"])
                cursor.execute(
                    """
                    INSERT INTO learning_plan_nodes
                    (plan_id, node_key, node_name, node_type, sequence_order, content, metadata, created_at, updated_at)
                    VALUES (%s, 'payload', %s, 'payload', 0, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        node_name=VALUES(node_name),
                        content=VALUES(content),
                        metadata=VALUES(metadata),
                        updated_at=VALUES(updated_at)
                    """,
                    (
                        plan_id,
                        title,
                        _json(entries),
                        _json({"seed_tag": SEED_TAG, "plan_kind": "weekly_showcase"}),
                        now,
                        now,
                    ),
                )


def _seed_homework(store: Any, nodes: list[dict[str, Any]]) -> list[str]:
    repo = HomeworkRepository()
    now = _now()
    assignments = [
        ("showcase_hw_subjective", "数据采集流程分析", "subjective", nodes[0]),
        ("showcase_hw_choice", "数据清洗概念测验", "choice", nodes[1 if len(nodes) > 1 else 0]),
        ("showcase_hw_code", "日志字段统计代码题", "code", nodes[2 if len(nodes) > 2 else 0]),
    ]
    created_ids: list[str] = []
    for idx, (assignment_id, title, assignment_type, node) in enumerate(assignments):
        node_id = str(node["node_id"])
        node_name = str(node.get("node_name") or node_id)
        questions = [
            {
                "title": title,
                "prompt": "请结合课程内容完成作答。" if assignment_type != "code" else "读取若干行日志，统计包含 ERROR 的行数。",
                "options": ["A. 数据采集", "B. 数据清洗", "C. 数据可视化", "D. 模型部署"] if assignment_type == "choice" else [],
                "correct_answer": "B" if assignment_type == "choice" else "",
                "reference_answer": "答案应包含关键步骤、证据和结论。",
                "rubric": "按完整性、准确性和表达评分。",
                "test_cases": [{"input": "INFO\\nERROR\\nERROR\\n", "expected": "2"}] if assignment_type == "code" else [],
            }
        ]
        assignment = repo.create_assignment(
            {
                "id": assignment_id,
                "title": title,
                "description": f"{SEED_TAG} 演示作业，用于填充教师端和学生端作业数据。",
                "assignment_type": assignment_type,
                "class_name": "大数据2201",
                "course_id": COURSE_ID,
                "node_id": node_id,
                "node_name": node_name,
                "node_path": _node_path(node),
                "chapter_context": "大数据课程演示章节",
                "objective_result_mode": "immediate",
                "due_at": (now + timedelta(days=idx + 3)).strftime("%Y-%m-%d %H:%M:%S"),
                "allow_late": True,
                "total_score": 100,
                "rubric": "按知识点覆盖、步骤完整和结果正确性评分。",
                "questions": questions,
                "covered_knowledge_points": [
                    {
                        "course_id": COURSE_ID,
                        "node_id": node_id,
                        "coverage_source": "teacher_confirmed",
                        "recommended_by_system": True,
                        "confirmed_by_teacher": True,
                        "confidence": 90,
                        "reason": "演示作业覆盖该叶子知识点。",
                    }
                ],
                "status": "published",
                "publish_now": True,
                "created_by": TEACHER,
            }
        )
        created_ids.append(assignment["id"])
        for s_idx, (username, display_name, overall) in enumerate(DEMO_STUDENTS):
            if idx == 2 and s_idx in {2, 4}:
                continue
            submitted = repo.create_submission(
                {
                    "assignment_id": assignment["id"],
                    "student_username": username,
                    "answers": [{"question_id": "q1", "answer": f"{display_name} 的演示作答：围绕 {node_name} 给出分析。"}],
                    "status": "submitted",
                }
            )
            score = max(35, min(98, overall + idx * 4 - (s_idx % 2) * 6))
            repo.update_submission(
                submitted["id"],
                {
                    "status": "graded" if s_idx != 4 else "submitted",
                    "ai_score": round(score - 2, 2),
                    "ai_feedback": "AI 初评：结构完整，需补充细节。" if score < 70 else "AI 初评：完成质量较好。",
                    "ai_rationale": f"{SEED_TAG}: 根据答案完整度和关键点命中评分。",
                    "teacher_score": round(score, 2) if s_idx != 4 else None,
                    "teacher_comment": "已完成批改，建议按路径继续复习。" if s_idx != 4 else "",
                    "graded_at": now.strftime("%Y-%m-%d %H:%M:%S") if s_idx != 4 else None,
                    "grader_username": TEACHER if s_idx != 4 else None,
                },
            )
    return created_ids


def _seed_teacher_events(store: Any, assignment_ids: list[str]) -> None:
    now = _now()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for idx, (_username, display_name, _overall) in enumerate(DEMO_STUDENTS):
                payload = {"seed_tag": SEED_TAG, "student": display_name, "topic": "课后答疑"}
                cursor.execute(
                    """
                    INSERT INTO teaching_interaction_events
                    (teacher_username, course_id, class_name, event_type, target_id, student_username, response_minutes, payload_json, created_at, occurred_at)
                    VALUES (%s, %s, '大数据2201', 'student_question_reply', %s, %s, %s, %s, %s, %s)
                    """,
                    (TEACHER, COURSE_ID, f"demo_reply_{idx}", DEMO_STUDENTS[idx][0], 8 + idx * 6, _json(payload), (now - timedelta(days=idx)).isoformat(), now - timedelta(days=idx)),
                )
            for idx, title in enumerate(["共备数据采集案例", "设计章节实践评分量规", "整理行业岗位能力样例"]):
                cursor.execute(
                    """
                    INSERT INTO teaching_research_events
                    (teacher_username, event_type, resource_id, payload_json, created_at, occurred_at)
                    VALUES (%s, 'research_activity', %s, %s, %s, %s)
                    """,
                    (TEACHER, f"demo_research_{idx}", _json({"seed_tag": SEED_TAG, "title": title}), (now - timedelta(days=idx + 1)).isoformat(), now - timedelta(days=idx + 1)),
                )
            for idx, assignment_id in enumerate(assignment_ids):
                cursor.execute(
                    """
                    INSERT INTO homework_grading_events
                    (assignment_id, submission_id, teacher_username, student_username, event_type, grading_minutes, is_ai_recommended, is_ai_executed, payload_json, created_at, occurred_at)
                    VALUES (%s, NULL, %s, NULL, 'batch_grading', %s, 1, 1, %s, %s, %s)
                    """,
                    (assignment_id, TEACHER, 18 + idx * 4, _json({"seed_tag": SEED_TAG, "assignment_id": assignment_id}), (now - timedelta(hours=idx + 2)).isoformat(), now - timedelta(hours=idx + 2)),
                )


def _seed_teaching_interaction_content(store: Any) -> None:
    now = _now()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            announcements = [
                ("showcase_ann_1", "本周实践任务安排", "请先完成日志数据清洗资源学习，再提交代码题作业。"),
                ("showcase_ann_2", "课堂测验说明", "Kafka 数据接入小测只读取已发布题目定义，未发布草稿不进入正式评价。"),
            ]
            for idx, (ann_id, title, content) in enumerate(announcements):
                published_at = now - timedelta(days=idx)
                cursor.execute(
                    """
                    INSERT INTO teaching_announcements
                    (id, teacher_username, title, content, class_name, course_id, status,
                     published_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, '大数据201', %s, 'published', %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        content=VALUES(content),
                        status=VALUES(status),
                        published_at=VALUES(published_at),
                        updated_at=VALUES(updated_at)
                    """,
                    (ann_id, TEACHER, title, f"{content}\n\n{SEED_TAG}", COURSE_ID, published_at, published_at, now),
                )

            topics = [
                ("showcase_topic_1", "日志清洗作业容易漏掉哪些异常值？", "围绕空值、重复记录和异常时间戳交流处理思路。"),
                ("showcase_topic_2", "实时指标监控应该先看吞吐还是延迟？", "结合课堂案例讨论指标优先级。"),
            ]
            for idx, (topic_id, title, content) in enumerate(topics):
                created_at = now - timedelta(days=idx + 1)
                cursor.execute(
                    """
                    INSERT INTO teaching_discussion_topics
                    (id, teacher_username, title, content, class_name, course_id, status,
                     student_question_count, teacher_reply_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, '大数据201', %s, 'open', 1, 1, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        content=VALUES(content),
                        student_question_count=VALUES(student_question_count),
                        teacher_reply_count=VALUES(teacher_reply_count),
                        updated_at=VALUES(updated_at)
                    """,
                    (topic_id, TEACHER, title, f"{content}\n\n{SEED_TAG}", COURSE_ID, created_at, now),
                )
                student_post_id = f"showcase_post_{idx}_student"
                teacher_post_id = f"showcase_post_{idx}_teacher"
                cursor.execute(
                    """
                    INSERT INTO teaching_discussion_posts
                    (id, topic_id, author_username, author_role, content, replied_to_post_id,
                     response_minutes, created_at, updated_at)
                    VALUES (%s, %s, %s, 'student', %s, NULL, NULL, %s, %s)
                    ON DUPLICATE KEY UPDATE content=VALUES(content), updated_at=VALUES(updated_at)
                    """,
                    (student_post_id, topic_id, "zyh", f"老师，这里我想确认一下具体判断口径。{SEED_TAG}", created_at, now),
                )
                cursor.execute(
                    """
                    INSERT INTO teaching_discussion_posts
                    (id, topic_id, author_username, author_role, content, replied_to_post_id,
                     response_minutes, created_at, updated_at)
                    VALUES (%s, %s, %s, 'teacher', %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE content=VALUES(content), response_minutes=VALUES(response_minutes), updated_at=VALUES(updated_at)
                    """,
                    (
                        teacher_post_id,
                        topic_id,
                        TEACHER,
                        f"先看证据是否充分，再结合已发布课程节点判断。{SEED_TAG}",
                        student_post_id,
                        18 + idx * 7,
                        created_at + timedelta(minutes=18 + idx * 7),
                        now,
                    ),
                )

            records = [
                ("showcase_research_1", "collective_prepare", "共备数据采集案例", "围绕采集链路、清洗任务和评价证据统一教学口径。"),
                ("showcase_research_2", "resource_review", "资源绑定复核", "复核候选资源，只将教师确认后的资源用于学生端展示。"),
            ]
            for idx, (record_id, activity_type, title, description) in enumerate(records):
                happened_at = now - timedelta(days=idx + 2)
                cursor.execute(
                    """
                    INSERT INTO teaching_research_records
                    (id, teacher_username, activity_type, title, description, resource_link,
                     class_name, course_id, happened_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, '大数据201', %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title=VALUES(title),
                        description=VALUES(description),
                        happened_at=VALUES(happened_at),
                        updated_at=VALUES(updated_at)
                    """,
                    (
                        record_id,
                        TEACHER,
                        activity_type,
                        title,
                        f"{description}\n\n{SEED_TAG}",
                        f"demo://teaching-research/{record_id}",
                        COURSE_ID,
                        happened_at,
                        happened_at,
                        now,
                    ),
                )


def _seed_fivee_records(store: Any, nodes: list[dict[str, Any]], student_ids: dict[str, int]) -> None:
    now = _now()
    stages = ["engagement", "exploration", "explanation", "elaboration", "evaluation"]
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for s_idx, (username, _display_name, overall) in enumerate(DEMO_STUDENTS[:4]):
                user_id = student_ids[username]
                node = nodes[s_idx % len(nodes)]
                node_id = str(node["node_id"])
                for stage_idx, stage in enumerate(stages[:3]):
                    occurred_at = now - timedelta(hours=s_idx * 5 + stage_idx)
                    payload = {
                        "seed_tag": SEED_TAG,
                        "stage": stage,
                        "node_id": node_id,
                        "summary": "5E 演示互动记录，用于学生画像证据时间线和教师端有效性分析。",
                        "mastery_update_policy": "not_updated_by_5e_effectiveness",
                    }
                    cursor.execute(
                        """
                        INSERT INTO events
                        (id, app_name, user_id, session_id, invocation_id, timestamp, event_data)
                        VALUES (%s, 'fivee-agent', %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE event_data=VALUES(event_data), timestamp=VALUES(timestamp)
                        """,
                        (
                            f"showcase_event_{username}_{stage_idx}",
                            username,
                            f"showcase_session_{username}",
                            f"showcase_invocation_{username}_{stage_idx}",
                            occurred_at,
                            _json(payload),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO user_interaction
                        (user_identifier, student_user_id, student_username, course_id, session_id,
                         stage, question_type, question_count, error, payload_json, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 'learning_support', %s, NULL, %s, %s)
                        """,
                        (
                            username,
                            user_id,
                            username,
                            COURSE_ID,
                            f"showcase_session_{username}",
                            stage,
                            1 + stage_idx,
                            _json(payload),
                            occurred_at,
                        ),
                    )
                    before = max(20.0, overall - 12 + stage_idx * 2)
                    after = min(100.0, before + 8 + stage_idx * 2)
                    effectiveness = min(95.0, 58 + stage_idx * 9 + s_idx * 4)
                    cursor.execute(
                        """
                        INSERT INTO fivee_effectiveness_records
                        (user_identifier, student_user_id, student_username, course_id, node_id,
                         session_id, stage, interaction_count, valid_interaction_count,
                         completion_rate, quiz_score_before, quiz_score_after, path_continue_rate,
                         effectiveness_score, payload_json, calculated_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            username,
                            user_id,
                            username,
                            COURSE_ID,
                            node_id,
                            f"showcase_session_{username}",
                            stage,
                            100.0,
                            before,
                            after if stage == "evaluation" else None,
                            80.0 if stage == "elaboration" else None,
                            effectiveness,
                            _json(
                                {
                                    **payload,
                                    "evidence_status": "outcome_supported" if stage in {"elaboration", "evaluation"} else "process_only",
                                    "effectiveness_level": "基本有效" if effectiveness >= 60 else "效果一般",
                                    "dimension_scores": {
                                        "stage_completion": 60 + stage_idx * 10,
                                        "valid_interaction": 100,
                                        "learning_gain": after - before if stage == "evaluation" else None,
                                        "learning_transfer": 80 if stage == "elaboration" else None,
                                    },
                                }
                            ),
                            occurred_at,
                            occurred_at,
                        ),
                    )


def _seed_intervention_packages(store: Any, nodes: list[dict[str, Any]], student_ids: dict[str, int], teacher_id: int) -> None:
    now = _now()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for idx, (username, display_name, overall) in enumerate(DEMO_STUDENTS[:3]):
                package_id = f"showcase_pkg_{username}"
                node = nodes[idx]
                node_id = str(node["node_id"])
                node_name = str(node.get("node_name") or node_id)
                payload = {
                    "seed_tag": SEED_TAG,
                    "id": package_id,
                    "student_username": username,
                    "strategy_summary": f"围绕 {node_name} 安排资源复习、测验和一道练习题。",
                    "questions": [{"id": "q1", "title": f"{node_name} 巩固题", "question_type": "subjective"}],
                }
                cursor.execute(
                    """
                    INSERT INTO intervention_packages
                    (package_id, teacher_username, teacher_user_id, student_username, student_user_id, course_id, diagnosis_report_id,
                     package_title, status, risk_level, pushed_at, completed_at, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at)
                    """,
                    (
                        package_id,
                        TEACHER,
                        teacher_id,
                        username,
                        student_ids[username],
                        COURSE_ID,
                        f"demo_showcase_{username}",
                        f"{display_name} 薄弱点干预任务包",
                        "completed" if overall >= 60 else "pushed",
                        "中" if overall >= 55 else "高",
                        now - timedelta(days=2),
                        now - timedelta(days=1) if overall >= 60 else None,
                        _json(payload),
                        now - timedelta(days=2),
                        now,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO intervention_package_items
                    (package_id, item_type, course_id, node_id, reminder_text, sequence_order, required, payload_json, created_at, updated_at)
                    VALUES (%s, 'practice_question', %s, %s, %s, 1, 1, %s, %s, %s)
                    """,
                    (package_id, COURSE_ID, node_id, f"完成 {node_name} 巩固题", _json({"seed_tag": SEED_TAG, "question_id": "q1"}), now - timedelta(days=2), now),
                )
                cursor.execute(
                    """
                    INSERT INTO intervention_package_student_records
                    (package_id, student_username, student_user_id, status, score, feedback, started_at, completed_at, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        package_id,
                        username,
                        student_ids[username],
                        "completed" if overall >= 60 else "in_progress",
                        overall if overall >= 60 else None,
                        "已完成并进入观察。" if overall >= 60 else "已接受，待完成练习。",
                        now - timedelta(days=2),
                        now - timedelta(days=1) if overall >= 60 else None,
                        _json({"seed_tag": SEED_TAG, "completion_rate": 1 if overall >= 60 else 0.45}),
                        now - timedelta(days=2),
                        now,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO teacher_intervention_events
                    (package_id, teacher_username, student_username, event_type, weak_node_count, completion_rate, payload_json, created_at, occurred_at)
                    VALUES (%s, %s, %s, %s, 2, %s, %s, %s, %s)
                    """,
                    (
                        package_id,
                        TEACHER,
                        username,
                        "package_completed" if overall >= 60 else "package_pushed",
                        1.0 if overall >= 60 else 0.45,
                        _json({"seed_tag": SEED_TAG, "node_name": node_name}),
                        now.isoformat(),
                        now,
                    ),
                )


def _summary(store: Any) -> dict[str, int]:
    tables = [
        "users",
        "teacher_student_links",
        "twin_profiles",
        "twin_profile_nodes",
        "twin_history",
        "quiz_attempts",
        "resource_learning_events",
        "homework_assignments",
        "homework_submissions",
        "learning_plans",
        "learning_plan_nodes",
        "diagnosis_reports",
        "diagnosis_corrections",
        "career_positions",
        "career_abilities",
        "course_ability_mappings",
        "events",
        "user_interaction",
        "fivee_effectiveness_records",
        "intervention_packages",
        "teacher_intervention_events",
        "teaching_announcements",
        "teaching_discussion_topics",
        "teaching_discussion_posts",
        "teaching_research_records",
        "teaching_interaction_events",
        "teaching_research_events",
    ]
    result: dict[str, int] = {}
    with store.connection() as conn:
        with conn.cursor() as cursor:
            for table in tables:
                if not _table_exists(cursor, table):
                    continue
                cursor.execute(f"SELECT COUNT(*) AS c FROM {table}")
                result[table] = int(cursor.fetchone()["c"])
    return result


def main() -> None:
    store = DatabaseFactory.get_store()
    deleted = _delete_seed_rows(store)
    user_stats = _upsert_users_and_links(store)
    student_ids = _student_id_map(store)
    _seed_readable_course_nodes(store)
    nodes = _fetch_course_nodes(store)
    career_mapping_stats = _seed_career_ability_mappings(store, nodes, int(user_stats["teacher_id"]))
    _seed_twin_quiz_resource_and_diagnosis(store, nodes, student_ids)
    _seed_learning_paths(store, nodes, student_ids)
    _seed_regular_learning_plans(store, nodes, student_ids)
    assignment_ids = _seed_homework(store, nodes)
    _seed_teacher_events(store, assignment_ids)
    _seed_teaching_interaction_content(store)
    _seed_fivee_records(store, nodes, student_ids)
    _seed_intervention_packages(store, nodes, student_ids, int(user_stats["teacher_id"]))
    print(
        json.dumps(
            {
                "seed_tag": SEED_TAG,
                "deleted_previous_seed_rows": deleted,
                "students": [item[0] for item in DEMO_STUDENTS],
                "assignments": assignment_ids,
                "career_mapping_stats": career_mapping_stats,
                "summary": _summary(store),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

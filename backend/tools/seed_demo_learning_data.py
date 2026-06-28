from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
SEED_TAG = "ai_education_demo_20260521"


def load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def mysql_base_cmd(env: dict[str, str]) -> list[str]:
    return [
        "mysql",
        "-h",
        env.get("DB_HOST", "localhost"),
        "-P",
        env.get("DB_PORT", "3306"),
        "-u",
        env.get("DB_USER", "root"),
        "--default-character-set=utf8mb4",
        "--batch",
        "--raw",
        env.get("DB_NAME", "ai_education"),
    ]


def run_mysql(env: dict[str, str], sql: str) -> str:
    proc_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        proc_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    proc = subprocess.run(
        mysql_base_cmd(env) + ["-e", sql],
        cwd=ROOT,
        env=proc_env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "mysql command failed")
    return proc.stdout


def run_mysql_file(env: dict[str, str], sql: str) -> None:
    proc_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        proc_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8", delete=False) as fp:
        fp.write(sql)
        temp_path = Path(fp.name)
    try:
        proc = subprocess.run(
            mysql_base_cmd(env),
            cwd=ROOT,
            env=proc_env,
            input=temp_path.read_text(encoding="utf-8"),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "mysql seed failed")
    finally:
        temp_path.unlink(missing_ok=True)


def rows_from_tsv(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return list(csv.DictReader(lines, delimiter="\t"))


def q(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"


def q_json(value: Any) -> str:
    return q(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def mastery_for(student_index: int, node_index: int) -> float:
    base = [82, 76, 69, 58, 44, 91, 63, 37, 72, 55, 88, 49]
    offset = [0, -8, 6, -14, 10, -4, 12, -18, 4][student_index % 9]
    return max(18.0, min(96.0, float(base[node_index % len(base)] + offset + (node_index % 3) * 2)))


def build_seed_sql(students: list[dict[str, str]], nodes: list[dict[str, str]], resources: list[dict[str, str]]) -> str:
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = [
        "SET NAMES utf8mb4;",
        "START TRANSACTION;",
        "UPDATE resources SET resource_type='video' WHERE resource_type LIKE 'm3u8?%' OR resource_path LIKE '%.m3u8%';",
        "UPDATE resources SET resource_type='pdf' WHERE LOWER(resource_path) LIKE '%.pdf%' OR LOWER(title) LIKE '%.pdf%';",
        f"DELETE FROM quiz_attempts WHERE JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.seed_tag')) = {q(SEED_TAG)};",
        f"DELETE FROM teacher_intervention_events WHERE payload_json LIKE {q('%' + SEED_TAG + '%')};",
    ]

    resource_by_node: dict[str, list[dict[str, str]]] = {}
    for item in resources:
        resource_by_node.setdefault(item["node_id"], []).append(item)

    for s_idx, student in enumerate(students):
        username = student["username"]
        user_id = int(student["user_id"])
        display_name = student.get("display_name") or username
        selected_nodes = nodes[s_idx % 4 : s_idx % 4 + 10]
        if len(selected_nodes) < 10:
            selected_nodes = nodes[:10]
        scores = [mastery_for(s_idx, idx) for idx, _ in enumerate(selected_nodes)]
        overall = round(sum(scores) / len(scores), 2)
        weak_nodes = []

        lines.append(
            "INSERT INTO twin_profiles (username,user_id,last_updated,overall_mastery,created_at,updated_at) "
            f"VALUES ({q(username)},{user_id},{q(now)},{overall},{q(now)},{q(now)}) "
            "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), last_updated=VALUES(last_updated), "
            "overall_mastery=VALUES(overall_mastery), updated_at=VALUES(updated_at);"
        )
        lines.append(
            "INSERT INTO teacher_student_links (teacher_username,student_username,teacher_user_id,student_user_id,updated_at) "
            f"VALUES ('teacher',{q(username)},2,{user_id},{q(now)}) "
            "ON DUPLICATE KEY UPDATE teacher_user_id=VALUES(teacher_user_id), student_user_id=VALUES(student_user_id), updated_at=VALUES(updated_at);"
        )

        for n_idx, node in enumerate(selected_nodes):
            score = scores[n_idx]
            node_id = node["node_id"]
            node_name = node.get("node_name") or node_id
            course_id = node.get("course_id") or "course_big_data"
            path = [course_id, node_name]
            quiz_score = max(0.0, min(100.0, score + (-6 if n_idx % 2 else 4)))
            progress = max(5.0, min(100.0, score + 10))
            duration = 18 + n_idx * 6 + s_idx * 3
            llm_count = 1 + (n_idx + s_idx) % 9
            lines.append(
                "INSERT INTO twin_profile_nodes "
                "(username,user_id,node_id,node_path_json,quiz_score,progress,study_duration_minutes,llm_interaction_count,mastery_score,created_at,updated_at) "
                f"VALUES ({q(username)},{user_id},{q(node_id)},{q_json(path)},{quiz_score:.2f},{progress:.2f},{duration:.2f},{llm_count},{score:.2f},{q(now)},{q(now)}) "
                "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), node_path_json=VALUES(node_path_json), "
                "quiz_score=VALUES(quiz_score), progress=VALUES(progress), study_duration_minutes=VALUES(study_duration_minutes), "
                "llm_interaction_count=VALUES(llm_interaction_count), mastery_score=VALUES(mastery_score), updated_at=VALUES(updated_at);"
            )
            if n_idx < 4:
                payload = {
                    "seed_tag": SEED_TAG,
                    "username": username,
                    "display_name": display_name,
                    "course_id": course_id,
                    "node_id": node_id,
                    "node_name": node_name,
                    "score": round(quiz_score, 2),
                    "total": 100,
                    "passed": quiz_score >= 60,
                }
                lines.append(
                    "INSERT INTO quiz_attempts (user_id,username,course_id,node_id,score,total,passed,payload_json,created_at) "
                    f"VALUES ({user_id},{q(username)},{q(course_id)},{q(node_id)},{quiz_score:.2f},100,{1 if quiz_score >= 60 else 0},{q_json(payload)},{q(now)});"
                )
            if score < 65:
                weak_nodes.append((node, score))

        for day_offset in range(13, -1, -1):
            snap_date = today - timedelta(days=day_offset)
            trend_score = max(15.0, min(98.0, overall - day_offset * 0.9 + ((s_idx % 3) - 1) * 1.2))
            payload = {
                "seed_tag": SEED_TAG,
                "date": snap_date.isoformat(),
                "username": username,
                "overall_mastery": round(trend_score, 2),
                "weak_node_count": len(weak_nodes),
                "study_minutes": 40 + (13 - day_offset) * 4 + s_idx * 2,
                "quiz_avg": round(min(96.0, trend_score + 3), 2),
            }
            lines.append(
                "INSERT INTO twin_history (username,user_id,snapshot_date,overall_mastery,payload_json,created_at,updated_at) "
                f"VALUES ({q(username)},{user_id},{q(snap_date.isoformat())},{trend_score:.2f},{q_json(payload)},{q(now)},{q(now)}) "
                "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), overall_mastery=VALUES(overall_mastery), "
                "payload_json=VALUES(payload_json), updated_at=VALUES(updated_at);"
            )

        plan_nodes = weak_nodes[:6] or [(selected_nodes[-1], scores[-1])]
        plan_payload_nodes = []
        for order, (node, score) in enumerate(plan_nodes, start=1):
            node_id = node["node_id"]
            matched_resources = resource_by_node.get(node_id, [])[:3]
            plan_payload_nodes.append(
                {
                    "node_id": node_id,
                    "node_name": node.get("node_name") or node_id,
                    "mastery_score": round(score, 2),
                    "priority": order,
                    "reason": "掌握度低于阈值，建议优先巩固",
                    "resources": [
                        {
                            "title": r.get("title") or r.get("resource_path"),
                            "type": r.get("resource_type") or "resource",
                            "url": r.get("resource_path"),
                            "source": "本地课程资源",
                        }
                        for r in matched_resources
                    ],
                }
            )

        plan_payload = {
            "seed_tag": SEED_TAG,
            "username": username,
            "generated_at": now,
            "status": "active",
            "title": f"{display_name} 个性化补弱学习路径",
            "weak_nodes": plan_payload_nodes,
            "llm_advice": "建议先处理掌握度低于 65 分的知识点，按路径顺序完成讲义、视频、测验三步闭环。",
            "llm_order_reason": "排序依据为掌握度、测验通过情况、学习进度和资源可用性。",
        }
        filename = f"demo_path_{username}.json"
        lines.append(
            "INSERT INTO learning_plans "
            "(username,user_id,filename,plan_path,category,title,description,status,created_at,updated_at,payload_json) "
            f"VALUES ({q(username)},{user_id},{q(filename)},{q('data/learning_plans/' + filename)},'path',"
            f"{q(plan_payload['title'])},{q('演示数据：根据薄弱知识点自动生成的学习路径。')},'active',{q(now)},{q(now)},{q_json(plan_payload)}) "
            "ON DUPLICATE KEY UPDATE user_id=VALUES(user_id), category=VALUES(category), title=VALUES(title), "
            "description=VALUES(description), status=VALUES(status), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at);"
        )
        lines.append(f"SET @plan_id := (SELECT plan_id FROM learning_plans WHERE username={q(username)} AND filename={q(filename)} LIMIT 1);")
        lines.append("DELETE FROM learning_plan_nodes WHERE plan_id=@plan_id;")
        lines.append(
            "INSERT INTO learning_plan_nodes "
            "(plan_id,node_key,node_name,node_type,sequence_order,mastery_score,priority,content,metadata,created_at,updated_at) "
            f"VALUES (@plan_id,'payload',{q(filename)},'payload',0,NULL,NULL,{q_json(plan_payload)},{q_json({'seed_tag': SEED_TAG})},{q(now)},{q(now)});"
        )
        for order, plan_node in enumerate(plan_payload_nodes, start=1):
            lines.append(
                "INSERT INTO learning_plan_nodes "
                "(plan_id,node_key,node_name,node_type,sequence_order,mastery_score,priority,content,metadata,created_at,updated_at) "
                f"VALUES (@plan_id,{q(plan_node['node_id'])},{q(plan_node['node_name'])},'weak_node',{order},"
                f"{plan_node['mastery_score']:.2f},{order},{q_json(plan_node)},{q_json({'seed_tag': SEED_TAG, 'resource_count': len(plan_node['resources'])})},{q(now)},{q(now)});"
            )

        report_payload = {
            "seed_tag": SEED_TAG,
            "overall_mastery": overall,
            "risk_level": "高" if overall < 55 else "中" if overall < 75 else "低",
            "weak_nodes": [item["node_name"] for item in plan_payload_nodes],
            "recommendation": "按照个性化路径完成补弱，并在下一次测验后刷新画像。",
        }
        report_id = f"demo-{username}-{today.isoformat()}"
        lines.append(
            "INSERT INTO diagnosis_reports (report_id,user_id,course_id,report_date,persona_summary,payload_json,updated_at) "
            f"VALUES ({q(report_id)},{user_id},'course_big_data',{q(today.isoformat())},"
            f"{q(f'{display_name} 当前整体掌握度 {overall:.2f}，存在 {len(plan_payload_nodes)} 个优先补弱点。')},"
            f"{q_json(report_payload)},{q(now)}) "
            "ON DUPLICATE KEY UPDATE persona_summary=VALUES(persona_summary), payload_json=VALUES(payload_json), updated_at=VALUES(updated_at);"
        )

        if s_idx < 6:
            event_payload = {
                "seed_tag": SEED_TAG,
                "student": username,
                "summary": f"针对 {display_name} 的薄弱点安排课后辅导与资源包。",
                "weak_nodes": [item["node_name"] for item in plan_payload_nodes[:3]],
            }
            lines.append(
                "INSERT INTO teacher_intervention_events "
                "(package_id,teacher_username,student_username,event_type,weak_node_count,completion_rate,payload_json,created_at) "
                f"VALUES ({q('demo_pkg_' + username)},'teacher',{q(username)},'path_intervention',{len(plan_payload_nodes)},"
                f"{min(0.95, max(0.25, overall / 100)):.2f},{q_json(event_payload)},{q(now)});"
            )

    lines.extend(["COMMIT;"])
    return "\n".join(lines) + "\n"


def main() -> None:
    env = load_env(ENV_PATH)
    if env.get("DB_TYPE", "mysql").lower() != "mysql":
        raise SystemExit("当前 .env 不是 MySQL 模式，已停止。")
    students = rows_from_tsv(
        run_mysql(
            env,
            "SELECT user_id, username, COALESCE(display_name, username) AS display_name "
            "FROM users WHERE user_type='student' ORDER BY user_id;",
        )
    )
    nodes = rows_from_tsv(
        run_mysql(
            env,
            "SELECT course_id, node_id, COALESCE(node_name,node_id) AS node_name "
            "FROM course_nodes WHERE course_id='course_big_data' ORDER BY depth, node_detail_id LIMIT 24;",
        )
    )
    if not nodes:
        nodes = rows_from_tsv(
            run_mysql(env, "SELECT course_id, node_id, COALESCE(node_name,node_id) AS node_name FROM course_nodes ORDER BY course_id, node_id LIMIT 24;")
        )
    resources = rows_from_tsv(
        run_mysql(
            env,
            "SELECT course_id,node_id,resource_type,title,resource_path FROM resources "
            "WHERE is_deleted=0 ORDER BY resource_id;",
        )
    )
    if not students or not nodes:
        raise SystemExit("缺少学生或课程节点，无法补演示数据。")
    sql = build_seed_sql(students, nodes, resources)
    run_mysql_file(env, sql)
    print(json.dumps({"seed_tag": SEED_TAG, "students_seeded": len(students), "nodes_available": len(nodes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

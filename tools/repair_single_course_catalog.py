from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
MAIN_COURSE_ID = "course_big_data"
MAIN_COURSE_NAME = "大数据分析"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def mysql_cmd(env: dict[str, str]) -> list[str]:
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


def run_sql(env: dict[str, str], sql: str) -> None:
    proc_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        proc_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8", delete=False) as fp:
        fp.write(sql)
        path = Path(fp.name)
    try:
        proc = subprocess.run(
            mysql_cmd(env),
            cwd=ROOT,
            env=proc_env,
            input=path.read_text(encoding="utf-8"),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip())
        if proc.stdout.strip():
            print(proc.stdout)
    finally:
        path.unlink(missing_ok=True)


def main() -> None:
    env = load_env()
    if env.get("DB_TYPE", "sqlite").lower() != "mysql":
        raise SystemExit("当前不是 MySQL 模式，停止修复。")

    sql = f"""
SET NAMES utf8mb4;
START TRANSACTION;

UPDATE courses
SET course_name = '{MAIN_COURSE_NAME}',
    description = '面向大数据分析课程的统一知识图谱课程，包含知识点、资源、测验、画像和个性化学习路径。',
    difficulty_level = 'intermediate',
    estimated_hours = 48.00,
    updated_at = NOW()
WHERE course_id = '{MAIN_COURSE_ID}';

UPDATE resources
SET course_id = '{MAIN_COURSE_ID}',
    updated_at = NOW()
WHERE course_id IN ('1', '2', '3', '4');

UPDATE diagnosis_reports
SET course_id = '{MAIN_COURSE_ID}',
    updated_at = NOW()
WHERE course_id <> '{MAIN_COURSE_ID}';

UPDATE homework_submissions
SET course_id = '{MAIN_COURSE_ID}',
    updated_at = NOW()
WHERE course_id IS NULL OR course_id = '' OR course_id <> '{MAIN_COURSE_ID}';

UPDATE teaching_interaction_events
SET course_id = '{MAIN_COURSE_ID}'
WHERE course_id IS NULL OR course_id = '' OR course_id <> '{MAIN_COURSE_ID}';

UPDATE quiz_attempts
SET course_id = '{MAIN_COURSE_ID}'
WHERE course_id IS NULL OR course_id = '' OR course_id <> '{MAIN_COURSE_ID}';

DELETE FROM course_nodes
WHERE course_id <> '{MAIN_COURSE_ID}';

DELETE FROM course_node_relations
WHERE course_id <> '{MAIN_COURSE_ID}';

DELETE FROM course_metadata
WHERE course_id <> '{MAIN_COURSE_ID}';

DELETE cm
FROM course_metadata cm
JOIN (
    SELECT course_id, MAX(metadata_id) AS keep_id
    FROM course_metadata
    WHERE course_id = '{MAIN_COURSE_ID}'
    GROUP BY course_id
) latest
  ON latest.course_id = cm.course_id
WHERE cm.metadata_id <> latest.keep_id;

DELETE FROM courses
WHERE course_id <> '{MAIN_COURSE_ID}';

COMMIT;

SELECT course_id, course_name, description, difficulty_level, estimated_hours
FROM courses
ORDER BY course_id;
SELECT course_id, COUNT(*) AS node_count FROM course_nodes GROUP BY course_id;
SELECT course_id, resource_type, COUNT(*) AS resource_count FROM resources GROUP BY course_id, resource_type ORDER BY course_id, resource_type;
SELECT course_id, COUNT(*) AS metadata_count FROM course_metadata GROUP BY course_id;
SELECT course_id, COUNT(*) AS reports FROM diagnosis_reports GROUP BY course_id;
SELECT course_id, COUNT(*) AS submissions FROM homework_submissions GROUP BY course_id;
"""
    run_sql(env, sql)


if __name__ == "__main__":
    main()

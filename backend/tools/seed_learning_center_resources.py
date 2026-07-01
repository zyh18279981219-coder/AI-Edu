from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

try:
    import pymysql
except ImportError as exc:  # pragma: no cover - local operator feedback
    raise SystemExit("pymysql is required to seed learning center resources") from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    for env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local.mysql"):
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_education_design"),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def resources_for_node(node_name: str) -> list[dict[str, str]]:
    keyword = quote(f"{node_name} 教程")
    return [
        {
            "resource_path": f"https://search.bilibili.com/all?keyword={keyword}&order=totalrank",
            "resource_type": "video",
            "title": f"B站：{node_name}教程",
            "resource_source": "external",
            "provider": "bilibili",
        },
        {
            "resource_path": f"https://www.youtube.com/results?search_query={keyword}",
            "resource_type": "video",
            "title": f"YouTube：{node_name}教程",
            "resource_source": "external",
            "provider": "youtube",
        },
        {
            "resource_path": f"https://so.csdn.net/so/search?q={keyword}&t=blog",
            "resource_type": "article",
            "title": f"CSDN：{node_name}教程",
            "resource_source": "external",
            "provider": "csdn",
        },
    ]


def main() -> int:
    load_env()
    course_id = os.getenv("RESOURCE_SEED_COURSE_ID", "course_big_data")
    node_names = [
        "大数据的概念",
        "大数据的渗透与影响",
        "大数据的量化进程",
    ]
    inserted_or_updated = 0
    missing_nodes: list[str] = []

    with connection() as conn:
        with conn.cursor() as cursor:
            for node_name in node_names:
                cursor.execute(
                    """
                    SELECT node_id
                    FROM course_nodes
                    WHERE course_id = %s AND node_name = %s
                    ORDER BY depth DESC, node_id
                    LIMIT 1
                    """,
                    (course_id, node_name),
                )
                row = cursor.fetchone()
                if not row:
                    missing_nodes.append(node_name)
                    continue
                node_id = str(row["node_id"])
                for resource in resources_for_node(node_name):
                    payload = {
                        "title": resource["title"],
                        "provider": resource["provider"],
                        "node_name": node_name,
                        "seed": "learning_center_resources_20260701",
                    }
                    cursor.execute(
                        """
                        INSERT INTO resources
                        (course_id, node_id, resource_path, resource_type, title, payload_json,
                         resource_source, quality_status, review_status, is_enabled,
                         is_deleted, deleted_at, deleted_by, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s,
                                %s, 'passed', 'enabled', 1,
                                0, NULL, NULL, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                            resource_type = VALUES(resource_type),
                            title = VALUES(title),
                            payload_json = VALUES(payload_json),
                            resource_source = VALUES(resource_source),
                            quality_status = 'passed',
                            review_status = 'enabled',
                            is_enabled = 1,
                            is_deleted = 0,
                            deleted_at = NULL,
                            deleted_by = NULL,
                            updated_at = NOW()
                        """,
                        (
                            course_id,
                            node_id,
                            resource["resource_path"],
                            resource["resource_type"],
                            resource["title"],
                            json.dumps(payload, ensure_ascii=False),
                            resource["resource_source"],
                        ),
                    )
                    inserted_or_updated += 1
        conn.commit()

    print(
        json.dumps(
            {
                "course_id": course_id,
                "resources_bound": inserted_or_updated,
                "missing_nodes": missing_nodes,
            },
            ensure_ascii=False,
        )
    )
    return 1 if missing_nodes else 0


if __name__ == "__main__":
    sys.exit(main())

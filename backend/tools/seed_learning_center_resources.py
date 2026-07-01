from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

from PathPlannerModule.resource_recommender import ResourceRecommender, YOUTUBE_HEADERS, YOUTUBE_SEARCH_API
from tools.env_loader import load_project_env

try:
    import pymysql
except ImportError as exc:  # pragma: no cover - local operator feedback
    raise SystemExit("pymysql is required to seed learning center resources") from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    load_project_env()
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


def resource_to_row(resource, node_name: str) -> dict[str, str]:
    provider = str(resource.provider or resource.source or "").lower()
    return {
        "resource_path": resource.url,
        "resource_type": resource.type,
        "title": resource.title or f"{resource.provider}：{node_name}",
        "resource_source": resource.source or "external",
        "provider": provider,
        "embed_url": resource.embed_url or "",
        "reason": resource.reason or "",
        "score": "" if resource.score is None else str(resource.score),
    }


def resources_for_node(recommender: ResourceRecommender, node_name: str) -> list[dict[str, str]]:
    core_words = recommender._core_words(node_name)
    keyword = quote(f"{node_name} 教程")
    search_keyword = f"{node_name} 教程"
    resources: list[dict[str, str]] = []

    for getter in (recommender._get_bilibili_video, recommender._get_csdn_blog):
        resource = getter(search_keyword, core_words)
        if resource and resource.url:
            resources.append(resource_to_row(resource, node_name))

    youtube_resource = fast_youtube_resource(recommender, search_keyword, core_words, node_name)
    if youtube_resource:
        resources.append(youtube_resource)

    if not any(resource["provider"] == "csdn" for resource in resources):
        resources.append({
            "resource_path": f"https://so.csdn.net/so/search?q={keyword}&t=blog",
            "resource_type": "article",
            "title": f"CSDN：{node_name}教程",
            "resource_source": "csdn_search",
            "provider": "csdn",
            "embed_url": "",
            "reason": "未拿到稳定的文章详情，提供 CSDN 搜索入口。",
            "score": "0.4",
        })
    return resources


def fast_youtube_resource(
    recommender: ResourceRecommender,
    keyword: str,
    core_words: list[str],
    node_name: str,
) -> dict[str, str] | None:
    try:
        resp = requests.get(
            YOUTUBE_SEARCH_API,
            params={"search_query": keyword},
            headers=YOUTUBE_HEADERS,
            timeout=6,
        )
        resp.raise_for_status()
    except Exception:
        return None

    best: tuple[float, dict[str, str]] | None = None
    for item in recommender._extract_youtube_results(resp.text):
        video_id = item["video_id"]
        title = item["title"] or f"YouTube：{node_name}教程"
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            continue
        score = recommender._score_title(title, core_words, base=0.5)
        row = {
            "resource_path": f"https://www.youtube.com/watch?v={video_id}",
            "resource_type": "video",
            "title": title,
            "resource_source": "youtube",
            "provider": "youtube",
            "embed_url": f"https://www.youtube.com/embed/{video_id}?rel=0",
            "reason": "按知识点关键词从 YouTube 检索，并绑定可内嵌的视频地址。",
            "score": str(round(score, 2)),
        }
        if best is None or score > best[0]:
            best = (score, row)
    return best[1] if best else None


def main() -> int:
    load_env()
    course_id = os.getenv("RESOURCE_SEED_COURSE_ID", "course_big_data")
    limit = int(os.getenv("RESOURCE_SEED_LIMIT", "0") or "0")
    inserted_or_updated = 0
    disabled_search_resources = 0
    recommender = ResourceRecommender()

    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE resources
                SET is_deleted = 1,
                    is_enabled = 0,
                    review_status = 'disabled',
                    updated_at = NOW()
                WHERE course_id = %s
                  AND JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.seed')) = 'learning_center_resources_20260701'
                  AND (
                    resource_path LIKE 'https://search.bilibili.com/%%'
                    OR resource_path LIKE 'https://www.youtube.com/results%%'
                  )
                """,
                (course_id,),
            )
            disabled_search_resources = int(cursor.rowcount or 0)
            cursor.execute(
                """
                SELECT n.node_id, n.node_name
                FROM course_nodes n
                WHERE n.course_id = %s
                ORDER BY n.depth, n.node_id
                LIMIT %s
                """,
                (course_id, limit if limit > 0 else 1000000),
            )
            rows = cursor.fetchall()
            for row in rows:
                node_id = str(row["node_id"])
                node_name = str(row["node_name"])
                for resource in resources_for_node(recommender, node_name):
                    payload = {
                        "title": resource["title"],
                        "provider": resource["provider"],
                        "node_name": node_name,
                        "embed_url": resource["embed_url"],
                        "reason": resource["reason"],
                        "score": resource["score"],
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
                "disabled_search_resources": disabled_search_resources,
                "nodes": len(rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

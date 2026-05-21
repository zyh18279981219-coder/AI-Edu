import html
import logging
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

from DatabaseModule.database_factory import DatabaseFactory
from DigitalTwinModule.models import Resource

logger = logging.getLogger(__name__)

BILI_API = "https://api.bilibili.com/x/web-interface/search/all/v2"
YOUTUBE_SEARCH_API = "https://www.youtube.com/results"
BILI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}
YOUTUBE_HEADERS = {
    "User-Agent": BILI_HEADERS["User-Agent"],
    "Referer": "https://www.youtube.com/",
}
YOUTUBE_PLAYER_API = "https://www.youtube.com/youtubei/v1/player"
YOUTUBE_PLAYER_CLIENT = {
    "clientName": "WEB",
    "clientVersion": "2.20260519.07.00",
}
DEFAULT_COURSE_ID = "course_big_data"


class ResourceRecommender:
    def __init__(self):
        try:
            self.store = DatabaseFactory.get_store()
        except Exception:
            logger.exception("ResourceRecommender: database store unavailable")
            self.store = None
        self._youtube_playability_cache: dict[str, bool] = {}

    def recommend(self, node_id: str, node_name: str = "") -> list[Resource]:
        name = (node_name or node_id or "").strip()
        if not name:
            return []

        core_words = self._core_words(name)
        keyword = f"{name} 教程"
        resources: list[Resource] = []

        resources.extend(self._get_local_resources(name))

        bilibili = self._get_bilibili_video(keyword, core_words)
        if bilibili:
            resources.append(bilibili)
        else:
            resources.append(
                Resource(
                    type="video",
                    title=f"B站搜索：{keyword}",
                    url=f"https://search.bilibili.com/all?keyword={quote(keyword)}&order=totalrank",
                    source="bilibili_search",
                    provider="Bilibili",
                    score=0.45,
                    reason="未拿到稳定的视频详情，提供 B 站搜索入口。",
                )
            )

        youtube = self._get_youtube_video(keyword, core_words)
        if youtube:
            resources.append(youtube)
        else:
            logger.info("No embeddable YouTube video found for %s", keyword)

        blog = self._get_csdn_blog(keyword, core_words)
        if blog:
            resources.append(blog)
        else:
            resources.append(
                Resource(
                    type="article",
                    title=f"CSDN搜索：{keyword}",
                    url=f"https://so.csdn.net/so/search?q={quote(keyword)}&t=blog",
                    source="csdn_search",
                    provider="CSDN",
                    score=0.4,
                    reason="未拿到稳定的文章详情，提供 CSDN 搜索入口。",
                )
            )

        deduped: dict[str, Resource] = {}
        for resource in resources:
            if resource.url and resource.url not in deduped:
                deduped[resource.url] = resource

        return sorted(
            deduped.values(),
            key=lambda item: item.score if item.score is not None else 0,
            reverse=True,
        )[:6]

    def _get_local_resources(self, node_name: str) -> list[Resource]:
        if self.store is None:
            return []
        try:
            paths = self.store.list_resources_for_node_name(DEFAULT_COURSE_ID, node_name)
        except Exception:
            logger.exception("ResourceRecommender: local resources failed for %s", node_name)
            return []

        resources: list[Resource] = []
        for path in paths[:3]:
            resource_type = self._resource_type(path)
            resources.append(
                Resource(
                    type=resource_type,
                    title=self._local_title(path, resource_type),
                    url=path,
                    source="course_resource",
                    provider="课程资源库",
                    score=0.92 if resource_type == "document" else 0.86,
                    reason="来自本课程资源库，和当前知识点直接绑定。",
                )
            )
        return resources

    def _get_bilibili_video(self, keyword: str, core_words: list[str]) -> Resource | None:
        try:
            time.sleep(0.2)
            resp = requests.get(
                BILI_API,
                params={"keyword": keyword, "page": 1},
                headers=BILI_HEADERS,
                timeout=8,
            )
            resp.raise_for_status()
            grouped = resp.json().get("data", {}).get("result", []) or []
            results = []
            for group in grouped:
                if group.get("result_type") == "video":
                    results = group.get("data", []) or []
                    break
        except Exception as exc:
            logger.warning("bilibili API failed for %s: %s", keyword, exc)
            return None

        best: tuple[float, Resource] | None = None
        for item in results:
            bvid = str(item.get("bvid") or "").strip()
            title = self._clean_title(str(item.get("title") or ""))
            if not bvid or not title:
                continue
            score = self._score_title(title, core_words, base=0.55)
            resource = Resource(
                type="video",
                title=title,
                url=f"https://www.bilibili.com/video/{bvid}",
                source="bilibili",
                provider="Bilibili",
                embed_url=f"https://player.bilibili.com/player.html?bvid={bvid}&page=1",
                score=round(score, 2),
                reason="按知识点关键词从 B 站检索，并优先选择标题相关的视频。",
            )
            if best is None or score > best[0]:
                best = (score, resource)
        return best[1] if best else None

    def _get_youtube_video(self, keyword: str, core_words: list[str]) -> Resource | None:
        try:
            time.sleep(0.2)
            resp = requests.get(
                YOUTUBE_SEARCH_API,
                params={"search_query": keyword},
                headers=YOUTUBE_HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("YouTube search failed for %s: %s", keyword, exc)
            return None

        candidates = self._extract_youtube_results(resp.text)
        best: tuple[float, Resource] | None = None
        for item in candidates:
            video_id = item["video_id"]
            title = item["title"]
            if not self._is_youtube_video_recommendable(video_id):
                continue
            score = self._score_title(title, core_words, base=0.5)
            resource = Resource(
                type="video",
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                source="youtube",
                provider="YouTube",
                embed_url=f"https://www.youtube.com/embed/{video_id}?rel=0",
                score=round(score, 2),
                reason="按知识点关键词从 YouTube 检索，并优先选择标题相关的视频。",
            )
            if best is None or score > best[0]:
                best = (score, resource)
            if score >= 0.72:
                return resource
        return best[1] if best else None

    def _is_youtube_video_recommendable(self, video_id: str) -> bool:
        if video_id in self._youtube_playability_cache:
            return self._youtube_playability_cache[video_id]

        try:
            resp = requests.post(
                YOUTUBE_PLAYER_API,
                params={"prettyPrint": "false"},
                headers={
                    **YOUTUBE_HEADERS,
                    "Content-Type": "application/json",
                    "Origin": "https://www.youtube.com",
                },
                json={
                    "context": {"client": YOUTUBE_PLAYER_CLIENT},
                    "videoId": video_id,
                    "contentCheckOk": True,
                    "racyCheckOk": True,
                },
                timeout=5,
            )
            resp.raise_for_status()
            status = resp.json().get("playabilityStatus", {}) or {}
        except Exception as exc:
            logger.warning("YouTube playability check failed for %s: %s", video_id, exc)
            self._youtube_playability_cache[video_id] = False
            return False

        state = str(status.get("status") or "").upper()
        reason = str(status.get("reason") or "")
        reason_lower = reason.lower()
        blocked_reason = "age" in reason_lower or "sign in" in reason_lower or "login" in reason_lower
        if state in {"LOGIN_REQUIRED", "AGE_VERIFICATION_REQUIRED"} or blocked_reason:
            logger.info("Skip YouTube video %s: %s / %s", video_id, state, reason)
            self._youtube_playability_cache[video_id] = False
            return False
        self._youtube_playability_cache[video_id] = True
        return True

    def _extract_youtube_results(self, html_text: str) -> list[dict[str, str]]:
        pattern = re.compile(
            r'"videoRenderer":\{.*?"videoId":"(?P<video_id>[A-Za-z0-9_-]{11})".*?'
            r'"title":\{"runs":\[\{"text":"(?P<title>.*?)"\}\]',
            re.S,
        )
        seen: set[str] = set()
        items: list[dict[str, str]] = []
        for match in pattern.finditer(html_text):
            video_id = match.group("video_id")
            if video_id in seen:
                continue
            seen.add(video_id)
            title = self._clean_title(match.group("title"))
            if title:
                items.append({"video_id": video_id, "title": title})
        return items[:12]

    def _get_csdn_blog(self, keyword: str, core_words: list[str]) -> Resource | None:
        try:
            time.sleep(0.2)
            resp = requests.get(
                "https://so.csdn.net/api/v3/search",
                params={"q": keyword, "t": "blog", "p": 1, "s": 0, "cl": 3},
                headers={
                    "User-Agent": BILI_HEADERS["User-Agent"],
                    "Referer": "https://www.csdn.net",
                },
                timeout=8,
            )
            resp.raise_for_status()
            items = resp.json().get("result_vos", []) or []
        except Exception as exc:
            logger.warning("CSDN API failed for %s: %s", keyword, exc)
            return None

        best: tuple[float, Resource] | None = None
        for item in items:
            url = str(item.get("url") or "").split("?")[0]
            title = self._clean_title(str(item.get("title") or ""))
            if not url.startswith("https://blog.csdn.net/") or not title:
                continue
            score = self._score_title(title, core_words, base=0.48)
            resource = Resource(
                type="article",
                title=title,
                url=url,
                source="csdn",
                provider="CSDN",
                score=round(score, 2),
                reason="按知识点关键词从 CSDN 检索，适合作为文字补充资料。",
            )
            if best is None or score > best[0]:
                best = (score, resource)
        return best[1] if best else None

    def _core_words(self, text: str) -> list[str]:
        cleaned = re.sub(r"[()（）\[\]【】,，:：/\\-]+", " ", text)
        parts = [part.strip() for part in cleaned.split() if len(part.strip()) > 1]
        words = [text.strip(), *parts]
        return list(dict.fromkeys(word for word in words if word))

    def _score_title(self, title: str, core_words: list[str], base: float) -> float:
        lowered = title.lower()
        score = base
        for word in core_words:
            if word.lower() in lowered:
                score += 0.22 if len(word) >= 4 else 0.12
        for marker in ("教程", "讲解", "入门", "详解", "实战", "原理"):
            if marker in title:
                score += 0.05
        return min(score, 0.99)

    def _clean_title(self, value: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

    def _resource_type(self, value: str) -> str:
        lowered = value.lower()
        if lowered.endswith(".pdf"):
            return "document"
        if ".m3u8" in lowered or lowered.endswith((".mp4", ".webm")):
            return "video"
        return "link"

    def _local_title(self, value: str, resource_type: str) -> str:
        name = Path(value.split("?", 1)[0]).name or value
        label = {
            "document": "课程讲义",
            "video": "课程视频",
            "link": "课程资料",
        }.get(resource_type, "课程资料")
        return f"{label}：{name}"

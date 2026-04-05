import logging
import os
import requests
import time
from urllib.parse import quote
from dotenv import load_dotenv
from DigitalTwinModule.models import Resource

logger = logging.getLogger(__name__)

BILI_API = "https://api.bilibili.com/x/web-interface/search/type"
BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Cookie": "buvid3=; b_nut=1; CURRENT_FNVAL=4048;",
}


class ResourceRecommender:

    def __init__(self):
        self._llm = None

    def recommend(self, node_id: str, node_name: str = "") -> list[Resource]:
        name = node_name or node_id
        logger.info("ResourceRecommender: node='%s'", name)

        # 用节点名本身作为搜索词，相关性校验也锚定在节点名
        # 不依赖LLM改写，避免关键词漂移导致搜出不相关内容
        stop_words = {"教程", "入门", "学习", "讲解", "详解", "基础", "视频"}
        core_words = [w for w in name.replace("，", " ").split() if w not in stop_words and len(w) > 1]
        if not core_words:
            core_words = [name[:4]]

        search_keyword = f"{name} 教程"

        video = self._get_bilibili_video(search_keyword, core_words) or Resource(
            type="video",
            title=f"B站：{search_keyword}",
            url=f"https://search.bilibili.com/all?keyword={quote(search_keyword)}&order=totalrank",
            source="bilibili_search"
        )
        blog = self._get_csdn_blog(search_keyword, core_words) or Resource(
            type="blog",
            title=f"CSDN：{search_keyword}",
            url=f"https://so.csdn.net/so/search?q={quote(search_keyword)}&t=blog",
            source="csdn_search"
        )
        return [video, blog]

    def _get_bilibili_video(self, keyword: str, core_words: list[str] | None = None) -> Resource | None:
        # 提取核心词用于相关性校验（去掉"教程""入门"等通用词）
        if not core_words:
            stop_words = {"教程", "入门", "学习", "讲解", "详解", "基础", "视频"}
            core_words = [w for w in keyword.replace("，", " ").split() if w not in stop_words and len(w) > 1]
            if not core_words:
                core_words = [keyword[:4]]

        try:
            time.sleep(0.3)
            resp = requests.get(
                BILI_API,
                params={"search_type": "video", "keyword": keyword, "page": 1, "page_size": 10, "order": "totalrank"},
                headers=BILI_HEADERS,
                timeout=6,
            )
            data = resp.json()
            results = data.get("data", {}).get("result", [])
            best = None
            for item in results:
                bvid = item.get("bvid", "")
                raw_title = item.get("title", "")
                title = raw_title.replace('<em class="keyword">', "").replace("</em>", "")
                if not bvid or not title:
                    continue
                title_lower = title.lower()
                # 标题必须包含至少一个核心词
                if any(w.lower() in title_lower for w in core_words):
                    return Resource(
                        type="video",
                        title=title,
                        url=f"https://www.bilibili.com/video/{bvid}",
                        source="bilibili"
                    )
                # 记录第一条作为兜底（无相关结果时用）
                if best is None:
                    best = Resource(
                        type="video",
                        title=title,
                        url=f"https://www.bilibili.com/video/{bvid}",
                        source="bilibili"
                    )
            # 没有相关结果，返回第一条（总比搜索页好）
            return best
        except Exception as e:
            logger.warning("bilibili API failed for '%s': %s", keyword, e)
        return None

    def _get_csdn_blog(self, keyword: str, core_words: list[str] | None = None) -> Resource | None:
        try:
            time.sleep(0.3)
            resp = requests.get(
                "https://so.csdn.net/api/v3/search",
                params={"q": keyword, "t": "blog", "p": 1, "s": 0, "cl": 3},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.csdn.net",
                },
                timeout=6,
            )
            data = resp.json()
            items = data.get("result_vos", [])
            best = None
            for item in items:
                url: str = item.get("url", "")
                title: str = item.get("title", "")
                if not url.startswith("https://blog.csdn.net/") or not title:
                    continue
                clean_url = url.split("?")[0]
                # 相关性校验
                if core_words and any(w.lower() in title.lower() for w in core_words):
                    return Resource(type="blog", title=title, url=clean_url, source="csdn")
                if best is None:
                    best = Resource(type="blog", title=title, url=clean_url, source="csdn")
            return best
        except Exception as e:
            logger.warning("CSDN API failed for '%s': %s", keyword, e)
        return None

    def _get_search_keyword(self, node_name: str) -> str:
        try:
            load_dotenv()
            from langchain_openai import ChatOpenAI
            if self._llm is None:
                self._llm = ChatOpenAI(
                    model=os.environ.get("model_name"),
                    temperature=0,
                    base_url=os.environ.get("base_url"),
                    api_key=os.environ.get("api_key"),
                )
            resp = self._llm.invoke(
                f"为大数据课程知识点「{node_name}」生成一个适合搜索教学视频的关键词，"
                f"5-10字，面向初学者，只返回关键词本身。"
            )
            kw = resp.content.strip().strip("「」《》""''。，")
            return kw if kw else f"{node_name} 教程"
        except Exception as e:
            logger.warning("LLM keyword failed for '%s': %s", node_name, e)
            return f"{node_name} 教程"

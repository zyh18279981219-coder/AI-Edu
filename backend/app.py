from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form,
    status,
    Cookie,
    Response,
)
from fastapi.responses import FileResponse, RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Set
import json
import os
import re
import shutil
import logging
import base64
import math
import socket
import sys
import httpx
import threading
import time
from datetime import date, timedelta, datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse, quote

# 关闭 chromadb 遥测，避免启动时出现 posthog 错误日志
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (BACKEND_ROOT, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from DashboardModule.dashboard_api import router as dashboard_router
from DigitalTwinModule.digital_twin_api import router as twin_router
from IndustryIntelligenceModule.api import router as industry_intelligence_router
from HomeworkModule.api import router as homework_router
from TeachingInteractionModule.api import router as teaching_interaction_router
from TeachingResearchModule.api import router as teaching_research_router
from TeacherInterventionModule.api import router as intervention_router
from fiveE.apis import fiveE_router
from AgentModule.qa_agent import QA_Agent
from QuizModule.quiz_agent import Quiz_Agent
from QuizModule.definition_service import QuizDefinitionService
from LearningPlanModule.plan_agent import Plan_Agent
from SummaryModule.summary_agent import Summary_Agent
from CoordinatorAgentModule.coordinator_agent import Coordinator_Agent
from QuizModule import generate_learning_plan_from_quiz
from tools.language_handler import LanguageHandler
from tools.rag_service import get_rag_service
from tools.covert_resource import convert_to_pdf
from tools.llm_logger import get_llm_logger
from tools.ocr_service import get_ocr_service
from tools.user_manager import UserManager
from tools.quiz_summary_prompts import generate_quiz_summary_prompt
from langchain_openai import ChatOpenAI
import asyncio
import copy
from tools.session_manager import get_session_manager
from DatabaseModule.database_factory import DatabaseFactory
from DatabaseModule.learning_streak_service import LearningStreakService
from DatabaseModule.notification_service import NotificationService
from tools.runtime_config import load_runtime_config

LOG_DIR = Path("data/Log")
LOG_DIR.mkdir(parents=True, exist_ok=True)
TRACE_LOG_FILE = LOG_DIR / "storage_trace.log"

_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)
_file_handler = RotatingFileHandler(
    TRACE_LOG_FILE,
    maxBytes=2 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[_console_handler, _file_handler],
    force=True,
)

# 屏蔽 chromadb posthog 遥测错误日志（版本兼容问题，不影响功能）
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

app = FastAPI(title="AI-Education API")

# 添加Gzip压缩中间件
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 压缩大于1KB的响应

runtime_config = load_runtime_config()


def _parse_cors_origins() -> list[str]:
    cors_config = runtime_config.get("cors", {}) if isinstance(runtime_config.get("cors"), dict) else {}
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    if origins:
        return origins
    cfg_origins = cors_config.get("allow_origins")
    if isinstance(cfg_origins, list):
        clean = [str(item).strip() for item in cfg_origins if str(item).strip()]
        if clean:
            return clean
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


default_cors_regex = r"https?://(localhost|127\.0\.0\.1|.+\.githubpreview\.dev|.+\.app\.github\.dev)(:\d+)?$"
cors_config = runtime_config.get("cors", {}) if isinstance(runtime_config.get("cors"), dict) else {}
cors_origin_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX", str(cors_config.get("allow_origin_regex", default_cors_regex)))
cors_origins = _parse_cors_origins()

quiz_summary_model_name = os.environ.get("model_name")
quiz_summary_base_url = os.environ.get("base_url")
quiz_summary_api_key = os.environ.get("api_key")

quiz_summary_llm = None
if quiz_summary_model_name and quiz_summary_base_url and quiz_summary_api_key:
    try:
        import httpx
        quiz_summary_llm = ChatOpenAI(
            model=quiz_summary_model_name,
            temperature=0,
            base_url=quiz_summary_base_url,
            api_key=quiz_summary_api_key,
            http_client=httpx.Client(verify=False),
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to initialize quiz summary llm: %s", exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(twin_router)
app.include_router(industry_intelligence_router)
app.include_router(homework_router)
app.include_router(teaching_interaction_router)
app.include_router(teaching_research_router)
app.include_router(intervention_router)
app.include_router(fiveE_router)

rag_service = get_rag_service()
logger = logging.getLogger(__name__)

# 懒加载：retriever 首次使用时才初始化
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        logger.info("Initializing RAG retriever...")
        _retriever = rag_service.get_retriever()
    return _retriever
BASE_DIR = BACKEND_ROOT
RUNTIME_DATA_DIR = BACKEND_ROOT / "data"
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
# 注意：CURRENT_NODE 和 CURRENT_PDF_PATH 已移至 session_manager 中按用户存储

user_manager = UserManager()
session_manager = get_session_manager()
database_store = DatabaseFactory.get_store()

# 课程数据缓存
_course_cache = {}
_course_cache_lock = threading.RLock()
CACHE_TTL = 300  # 缓存5分钟
_api_read_cache: dict[tuple[str, str, str], tuple[float, Any]] = {}
_api_read_cache_lock = threading.RLock()
API_READ_CACHE_TTL = int(os.getenv("API_READ_CACHE_SECONDS", "30"))


def _get_api_read_cache(cache_key: tuple[str, str, str]) -> Optional[Any]:
    with _api_read_cache_lock:
        cached = _api_read_cache.get(cache_key)
        if not cached:
            return None
        created_at, data = cached
        if time.time() - created_at > API_READ_CACHE_TTL:
            _api_read_cache.pop(cache_key, None)
            return None
        return data


def _set_api_read_cache(cache_key: tuple[str, str, str], data: Any) -> None:
    with _api_read_cache_lock:
        _api_read_cache[cache_key] = (time.time(), data)

# 懒加载：所有 Agent 首次请求时才初始化，避免启动时串行加载拖慢速度
_qa_agent = None
_quiz_agent = None
_summary_agent = None
_plan_agent = None
_coordinator_agent = None

def get_qa_agent():
    global _qa_agent
    if _qa_agent is None:
        logger.info("Initializing QA agent...")
        _qa_agent = QA_Agent()
    return _qa_agent

def get_quiz_agent():
    global _quiz_agent
    if _quiz_agent is None:
        logger.info("Initializing Quiz agent...")
        _quiz_agent = Quiz_Agent()
    return _quiz_agent

def get_summary_agent():
    global _summary_agent
    if _summary_agent is None:
        logger.info("Initializing Summary agent...")
        _summary_agent = Summary_Agent()
    return _summary_agent

def get_plan_agent():
    global _plan_agent
    if _plan_agent is None:
        logger.info("Initializing Plan agent...")
        _plan_agent = Plan_Agent()
    return _plan_agent

def get_coordinator_agent():
    global _coordinator_agent
    if _coordinator_agent is None:
        logger.info("Initializing Coordinator agent...")
        _coordinator_agent = Coordinator_Agent()
    return _coordinator_agent

LEGACY_STATIC_REDIRECTS = {
    "mainpage.html": "/",
    "mylearning.html": "/learning",
    "coursecontent.html": "/course-content",
    "student-twin.html": "/student-twin",
    "industry-intelligence.html": "/industry-intelligence",
    "quizpage.html": "/quiz",
    "profile.html": "/profile",
    "login.html": "/login",
    "teacher.html": "/teacher/dashboard",
    "admin.html": "/admin/dashboard",
}


class LegacyAwareStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        normalized = path.lstrip("/")
        redirect_target = LEGACY_STATIC_REDIRECTS.get(normalized)
        if redirect_target:
            return RedirectResponse(url=redirect_target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        if normalized.endswith(".bak-encoding-fix"):
            return PlainTextResponse("Retired legacy backup page", status_code=410)
        return await super().get_response(path, scope)


def frontend_index_response():
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    return PlainTextResponse(
        "Frontend bundle not found. Please run npm run build in frontend.",
        status_code=503,
    )


app.mount("/static", LegacyAwareStaticFiles(directory=str(BACKEND_ROOT / "static")), name="static")
app.mount("/data", StaticFiles(directory=str(RUNTIME_DATA_DIR)), name="data")
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")


# 保存后台任务引用，用于优雅关闭
_background_tasks: List[asyncio.Task] = []

# 应用启动时预热，避免第一次请求慢
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 预热 RAG 服务...")
    try:
        # 预热向量数据库
        rag_service._get_vectorstore()
        logger.info("✅ RAG 服务预热完成")
    except Exception as e:
        logger.warning(f"⚠️ RAG 预热失败: {e}")

    # 启动数字孪生数据采集定时任务（每10分钟）
    async def _collect_all_loop():
        from DigitalTwinModule.data_collector import DataCollector
        collector = DataCollector()
        while True:
            try:
                await asyncio.sleep(600)
            except asyncio.CancelledError:
                logger.info("🛑 定时采集任务已取消")
                break
            try:
                usernames = [
                    str(profile.get("user_id"))
                    for profile in database_store.list_twin_profiles()
                    if profile.get("user_id") is not None
                ]
            except Exception:
                usernames = []
            for username in usernames:
                try:
                    collector.collect_all(username)
                except Exception as exc:
                    logger.warning(f"⚠️ 定时采集失败 [{username}]: {exc}")

    task = asyncio.create_task(_collect_all_loop())
    _background_tasks.append(task)

    try:
        _ensure_default_course_seed()
        existing_user_count = (
            len(database_store.list_users("student"))
            + len(database_store.list_users("teacher"))
            + len(database_store.list_users("admin"))
        )
        logger.info("Database warmup complete: users=%s", existing_user_count)
    except Exception as exc:
        logger.warning("Database warmup skipped: %s", exc)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 正在关闭后台任务...")
    for task in _background_tasks:
        if not task.done():
            task.cancel()
    # 等待所有后台任务完成取消（最多 5 秒）
    if _background_tasks:
        await asyncio.wait(_background_tasks, timeout=5)
    logger.info("✅ 后台任务已全部关闭")

def get_current_user(
    session_id: Optional[str] = Cookie(None),
) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    return session_manager.get_session(session_id)


def _public_user_data(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not user:
        return {}
    cleaned = dict(user)
    cleaned.pop("password", None)
    return cleaned


def _public_student_record(student: Dict[str, Any], teacher_by_student: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    item = _public_user_data(student)
    username = str(item.get("username") or "").strip()
    item.setdefault("stu_name", item.get("display_name") or username)
    item.setdefault("learning_goals", [])
    item.setdefault("preference", {})
    if teacher_by_student and username and not item.get("teacher"):
        item["teacher"] = teacher_by_student.get(username, "")
    return item


def _public_teacher_record(teacher: Dict[str, Any]) -> Dict[str, Any]:
    item = _public_user_data(teacher)
    username = str(item.get("username") or "").strip()
    item.setdefault("name", item.get("display_name") or username)
    students = item.get("students")
    if not isinstance(students, list):
        try:
            links = database_store.list_teacher_students(username)
            students = [
                str(link.get("student_username") or "").strip()
                for link in links
                if str(link.get("student_username") or "").strip()
            ]
        except Exception as exc:
            logger.warning("Failed to load teacher student links for %s: %s", username, exc)
            students = []
    item["students"] = students
    return item


def _ensure_default_course_seed() -> None:
    course_id = "course_big_data"
    auto_seed = os.getenv("AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE", "1").strip().lower()
    if auto_seed in {"0", "false", "no", "off"}:
        logger.info("Default course seed skipped by AI_EDUCATION_AUTO_SEED_DEFAULT_COURSE=%s", auto_seed)
        return
    try:
        summary = database_store.get_course_summary(course_id)
        if summary and int(summary.get("node_count") or 0) > 0 and database_store.get_course_payload(course_id):
            return
        seed_path = RUNTIME_DATA_DIR / "course" / "big_data.json"
        if not seed_path.exists():
            logger.warning("Default course seed file not found: %s", seed_path)
            return
        with seed_path.open("r", encoding="utf-8") as file:
            graph_data = json.load(file)
        if not isinstance(graph_data, dict):
            logger.warning("Default course seed is not a graph object: %s", seed_path)
            return
        course_name = str(graph_data.get("name") or "大数据分析")
        result = database_store.sync_course_from_graph(
            course_id=course_id,
            graph_data=graph_data,
            course_name=course_name,
            source_path=str(seed_path),
            lifecycle_status="published",
            updated_by="system",
        )
        logger.info("Default course seed synced: course_id=%s result=%s", course_id, result)
    except Exception as exc:
        logger.warning("Default course seed skipped: %s", exc)


def _require_teacher_or_admin(session_id: Optional[str]) -> Dict[str, Any]:
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if session.get("user_type") not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Only teachers or admins can manage course base")
    return session


def _quiz_definition_service() -> QuizDefinitionService:
    return QuizDefinitionService(database_store)


def _iter_course_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("children", "grandchildren", "great-grandchildren"):
        children = node.get(key)
        if isinstance(children, list):
            return [item for item in children if isinstance(item, dict)]
    return []


def _validate_course_graph(graph_data: Dict[str, Any]) -> Dict[str, int]:
    if not isinstance(graph_data, dict):
        raise HTTPException(status_code=400, detail="graph_data must be an object")
    if not str(graph_data.get("name") or "").strip():
        raise HTTPException(status_code=400, detail="graph_data.name is required")

    node_count = 0
    leaf_count = 0
    max_depth = 0
    errors: List[str] = []

    def walk(node: Dict[str, Any], depth: int, path: List[str]) -> None:
        nonlocal node_count, leaf_count, max_depth
        name = str(node.get("name") or "").strip()
        if not name:
            errors.append("存在空节点名称")
            return
        node_count += 1
        max_depth = max(max_depth, depth)
        children = _iter_course_children(node)
        if not children:
            leaf_count += 1
        for child in children:
            walk(child, depth + 1, path + [name])

    for child in _iter_course_children(graph_data):
        walk(child, 1, [])

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors[:5]))
    if node_count == 0:
        raise HTTPException(status_code=400, detail="course graph must contain at least one chapter or knowledge node")
    if leaf_count == 0:
        raise HTTPException(status_code=400, detail="course graph must contain at least one leaf knowledge node")
    return {"node_count": node_count, "leaf_node_count": leaf_count, "max_depth": max_depth}


def _clean_outline_title(line: str) -> str:
    value = str(line or "").strip()
    value = re.sub(r"^[-*+\u2022]\s*", "", value)
    value = re.sub(r"^\(?\d+(?:\.\d+){0,3}\)?[、.)\s]+", "", value)
    value = re.sub(r"^第[一二三四五六七八九十百千万\d]+[章节讲]\s*", "", value)
    return value.strip(" \t:：-")


def _infer_outline_level(raw_line: str) -> int:
    line = str(raw_line or "").rstrip()
    stripped = line.strip()
    if not stripped:
        return 0
    if re.match(r"^第[一二三四五六七八九十百千万\d]+章", stripped):
        return 1
    if re.match(r"^第[一二三四五六七八九十百千万\d]+节", stripped):
        return 2
    number_match = re.match(r"^\(?(\d+(?:\.\d+){0,3})\)?[、.)\s]+", stripped)
    if number_match:
        return min(number_match.group(1).count(".") + 1, 3)
    indent = len(line) - len(line.lstrip(" \t"))
    if indent >= 4:
        return 3
    if indent >= 2:
        return 2
    return 1


def _build_initial_course_graph(course_name: str, outline_text: str) -> Dict[str, Any]:
    root = {"name": course_name, "children": []}
    current_chapter: Optional[Dict[str, Any]] = None
    current_section: Optional[Dict[str, Any]] = None

    for raw_line in str(outline_text or "").splitlines():
        title = _clean_outline_title(raw_line)
        if not title:
            continue
        level = _infer_outline_level(raw_line)
        if level <= 1:
            current_chapter = {"name": title, "grandchildren": []}
            root["children"].append(current_chapter)
            current_section = None
            continue
        if current_chapter is None:
            current_chapter = {"name": "课程知识点", "grandchildren": []}
            root["children"].append(current_chapter)
        if level == 2:
            current_section = {"name": title, "great-grandchildren": []}
            current_chapter.setdefault("grandchildren", []).append(current_section)
            continue
        if current_section is None:
            current_section = {"name": "基础知识点", "great-grandchildren": []}
            current_chapter.setdefault("grandchildren", []).append(current_section)
        current_section.setdefault("great-grandchildren", []).append({"name": title})

    if not root["children"]:
        raise HTTPException(status_code=400, detail="outline_text must contain at least one course node")
    return root


def _iter_graph_nodes_with_parent_key(node: Dict[str, Any]):
    for key in ("children", "grandchildren", "great-grandchildren"):
        children = node.get(key)
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    yield child


def _leaf_graph_nodes(graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    leaves: List[Dict[str, Any]] = []

    def walk(node: Dict[str, Any]) -> None:
        children = list(_iter_graph_nodes_with_parent_key(node))
        if not children and str(node.get("name") or "").strip():
            leaves.append(node)
            return
        for child in children:
            walk(child)

    walk(graph_data)
    return leaves


def _graph_with_enabled_resources(course_id: str, graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the graph whose resource_path values reflect enabled DB resources."""
    if not isinstance(graph_data, dict):
        return graph_data
    hydrated_graph = copy.deepcopy(graph_data)
    resources_by_name: Dict[str, List[str]] = {}
    resources_by_node_id: Dict[str, List[str]] = {}
    for item in database_store.list_course_resources(course_id):
        if item.get("is_deleted") or not item.get("is_enabled"):
            continue
        resource_path = str(item.get("resource_path") or "").strip()
        if not resource_path:
            continue
        node_name = str(item.get("node_name") or "").strip()
        node_id = str(item.get("node_id") or "").strip()
        if node_name:
            resources_by_name.setdefault(node_name, []).append(resource_path)
        if node_id:
            resources_by_node_id.setdefault(node_id, []).append(resource_path)

    def unique(values: List[str]) -> List[str]:
        seen: Set[str] = set()
        result: List[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def walk(node: Dict[str, Any]) -> None:
        node_name = str(node.get("name") or "").strip()
        node_id = str(node.get("node_id") or node.get("id") or "").strip()
        resources = []
        if node_id:
            resources.extend(resources_by_node_id.get(node_id, []))
        if node_name:
            resources.extend(resources_by_name.get(node_name, []))
        if resources:
            node["resource_path"] = unique(resources)
        for child in _iter_graph_nodes_with_parent_key(node):
            walk(child)

    walk(hydrated_graph)
    return hydrated_graph


def _resource_candidates_for_node(node_name: str, max_count: int) -> List[str]:
    keyword = f"{node_name} 教程"
    candidates = [
        f"https://search.bilibili.com/all?keyword={quote(keyword)}&order=totalrank",
        f"https://so.csdn.net/so/search?q={quote(keyword)}&t=blog",
        f"https://www.bing.com/search?q={quote(keyword)}",
    ]
    return candidates[: max(1, min(int(max_count or 2), 3))]


def _attach_resource_candidates_to_graph(
    graph_data: Dict[str, Any],
    *,
    max_resources_per_leaf: int = 2,
    overwrite: bool = False,
) -> Dict[str, Any]:
    attached = 0
    skipped = 0
    attached_resource_paths: List[str] = []
    for node in _leaf_graph_nodes(graph_data):
        node_name = str(node.get("name") or "").strip()
        raw_resources = node.get("resource_path", [])
        if isinstance(raw_resources, str):
            resources = [raw_resources] if raw_resources else []
        elif isinstance(raw_resources, list):
            resources = [str(item).strip() for item in raw_resources if str(item or "").strip()]
        else:
            resources = []
        if resources and not overwrite:
            skipped += 1
            node["resource_path"] = resources
            continue
        candidates = _resource_candidates_for_node(node_name, max_resources_per_leaf)
        node["resource_path"] = candidates
        attached_resource_paths.extend(candidates)
        attached += len(candidates)
    return {
        "leaf_nodes": len(_leaf_graph_nodes(graph_data)),
        "attached_resources": attached,
        "skipped_leaf_nodes": skipped,
        "attached_resource_paths": attached_resource_paths,
    }


def _mark_auto_bound_resources_for_review(
    course_id: str,
    graph_data: Dict[str, Any],
    review_status: str,
    resource_paths: Optional[Set[str]] = None,
) -> int:
    status = str(review_status or "pending").strip().lower()
    if status not in {"enabled", "disabled", "pending", "rejected"}:
        status = "pending"
    is_enabled = status == "enabled"
    updated = 0
    for node in _leaf_graph_nodes(graph_data):
        node_id = str(node.get("node_id") or node.get("id") or node.get("name") or "").strip()
        raw_resources = node.get("resource_path", [])
        if isinstance(raw_resources, str):
            resources = [raw_resources] if raw_resources else []
        elif isinstance(raw_resources, list):
            resources = [str(item).strip() for item in raw_resources if str(item or "").strip()]
        else:
            resources = []
        for resource_path in resources:
            if resource_paths is not None and resource_path not in resource_paths:
                continue
            if database_store.set_resource_review_status(
                course_id=course_id,
                node_id=node_id,
                resource_path=resource_path,
                is_enabled=is_enabled,
                review_status=status,
                quality_status="candidate",
            ):
                updated += 1
    return updated


def _extract_ability_candidates(
    explicit_abilities: Optional[List[Dict[str, Any]]] = None,
    industry_payload: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Extract practical ability candidates from explicit rows or industry analysis payload."""
    candidates: Dict[str, Dict[str, Any]] = {}

    def add_candidate(name: Any, *, demand_level: Any = None, evidence: Optional[Dict[str, Any]] = None):
        ability_name = str(name or "").strip()
        if not ability_name:
            return
        key = ability_name.lower()
        if key not in candidates:
            candidates[key] = {
                "ability_name": ability_name,
                "ability_category": "industry_skill",
                "demand_level": demand_level,
                "support_level": "medium",
                "evidence": evidence or {},
            }
        else:
            existing = candidates[key]
            if existing.get("demand_level") is None and demand_level is not None:
                existing["demand_level"] = demand_level

    for item in explicit_abilities or []:
        if isinstance(item, dict):
            name = item.get("ability_name") or item.get("name")
            add_candidate(name, demand_level=item.get("demand_level") or item.get("count"), evidence=item)

    payload = industry_payload if isinstance(industry_payload, dict) else {}
    skill_rows = ((payload.get("charts") or {}).get("skill_ranking") or []) if payload else []
    for row in skill_rows:
        if isinstance(row, dict):
            add_candidate(row.get("name"), demand_level=row.get("value"), evidence={"source": "skill_ranking", **row})

    for job in payload.get("jobs", []) if isinstance(payload.get("jobs"), list) else []:
        if not isinstance(job, dict):
            continue
        for skill in job.get("skills") or []:
            add_candidate(
                skill,
                evidence={
                    "source": job.get("source"),
                    "title": job.get("title"),
                    "company": job.get("company"),
                    "relevance_score": job.get("relevance_score"),
                },
            )

    return list(candidates.values())


def _resolve_course_id_for_session(session: Optional[Dict[str, Any]]) -> str:
    # 暂时让所有用户使用默认课程，避免找不到课程的问题
    # TODO: 未来支持多课程时，需要根据用户配置返回对应的course_id
    return "course_big_data"


def _resolve_course_sync_meta(course_id: str, graph_data: Dict[str, Any]) -> tuple[str, str]:
    course_name = str(graph_data.get("name") or course_id or "default_course")
    source_path = f"entity://courses/{course_id}"
    return course_name, source_path


def _resolve_requested_course_id_for_session(
    session: Optional[Dict[str, Any]],
    requested_course_id: Optional[str] = None,
) -> str:
    requested = str(requested_course_id or "").strip()
    if requested:
        return requested
    username = str((session or {}).get("username") or "").strip()
    if username and (session or {}).get("user_type") == "student":
        try:
            list_student_courses = getattr(database_store, "list_student_courses", None)
            if callable(list_student_courses):
                courses = list_student_courses(username)
                first = next((item for item in courses if item.get("course_id")), None)
                if first:
                    return str(first["course_id"])
        except Exception as exc:
            logging.warning("Failed to resolve student default course for %s: %s", username, exc)
    return _resolve_course_id_for_session(session)


def _student_can_access_published_course_base(
    session: Optional[Dict[str, Any]],
    course_id: str,
) -> bool:
    """Return whether this session may read student-facing course-base data."""
    if not session or session.get("user_type") != "student":
        return True
    username = str(session.get("username") or "").strip()
    try:
        summary = database_store.get_course_summary(course_id)
        if not summary:
            logging.info("Student attempted to read missing course base: course_id=%s", course_id)
            return False
        if summary.get("lifecycle_status") != "published":
            logging.info("Student attempted to read unpublished course base: course_id=%s", course_id)
            return False
        list_student_courses = getattr(database_store, "list_student_courses", None)
        if username and callable(list_student_courses):
            courses = list_student_courses(username)
            visible_ids = {str(item.get("course_id") or "").strip() for item in courses}
            if visible_ids and course_id not in visible_ids:
                logging.info(
                    "Student attempted to read course outside enrollment: username=%s course_id=%s",
                    username,
                    course_id,
                )
                return False
    except Exception as exc:
        logging.warning("Failed to check course publish status for %s: %s", course_id, exc)
        return False
    return True


def _load_course_graph_entity_only(
    session: Optional[Dict[str, Any]],
    requested_course_id: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    """加载课程数据（带缓存）"""
    course_id = _resolve_requested_course_id_for_session(session, requested_course_id)
    cache_scope = "student" if session and session.get("user_type") == "student" else "staff"
    cache_key = (course_id, cache_scope)
    
    # 检查缓存
    with _course_cache_lock:
        cache_status = f"缓存状态: 共{len(_course_cache)}项"
        if cache_key in _course_cache:
            cached_data, cached_time = _course_cache[cache_key]
            age = time.time() - cached_time
            # 检查缓存是否过期
            if age < CACHE_TTL:
                logging.info(f"✅ 从缓存加载课程数据: course_id={course_id}, scope={cache_scope}, 缓存年龄={age:.1f}秒")
                return course_id, cached_data
            else:
                logging.info(f"⏰ 缓存已过期: course_id={course_id}, scope={cache_scope}, 年龄={age:.1f}秒 > TTL={CACHE_TTL}秒")
        else:
            logging.info(f"❌ 缓存未命中: course_id={course_id}, {cache_status}")
    
    # 缓存未命中或已过期，从数据库读取
    logging.info(f"📥 从数据库加载课程数据: course_id={course_id}")
    if not _student_can_access_published_course_base(session, course_id):
        return course_id, {}
    payload = database_store.get_course_payload(course_id)
    
    if isinstance(payload, dict):
        # 更新缓存
        with _course_cache_lock:
            _course_cache[cache_key] = (payload, time.time())
            logging.info(f"💾 已缓存课程数据: course_id={course_id}")
        return course_id, payload
    
    return course_id, {}


def _clear_course_cache_for_course(course_id: str) -> None:
    target = str(course_id or "").strip()
    if not target:
        return
    with _course_cache_lock:
        for key in list(_course_cache.keys()):
            key_course_id = key[0] if isinstance(key, tuple) else key
            if key_course_id == target:
                _course_cache.pop(key, None)


class ChatMessage(BaseModel):
    message: str
    history: List[List[str]] = []
    lang_choice: str = "auto"


class QuizStart(BaseModel):
    subject: str
    lang_choice: str = "auto"
    course_id: str = "course_big_data"
    node_id: Optional[str] = None


class QuizDefinitionQuestion(BaseModel):
    topic: Optional[str] = None
    question: str
    correct: str


class QuizDefinitionUpsert(BaseModel):
    course_id: str = "course_big_data"
    node_id: str
    title: Optional[str] = None
    status: str = "draft"
    definition_id: Optional[str] = None
    questions: List[QuizDefinitionQuestion]


class QuizDefinitionPublish(BaseModel):
    course_id: str = "course_big_data"
    node_id: str


class QuizAnswer(BaseModel):
    choice: str
    state: Dict[str, Any]


class LearningPlanRequest(BaseModel):
    name: str
    goals: str
    lang_choice: str = "auto"
    priority: str = "基础知识"
    deadline_days: int = 7


class LearningPlanFromQuiz(BaseModel):
    name: str
    state: Dict[str, Any]
    lang_choice: str = "auto"


class SummaryRequest(BaseModel):
    topic: str
    lang_choice: str = "auto"


class NodeSelection(BaseModel):
    node_name: str
    course_id: Optional[str] = None


class PDFSelection(BaseModel):
    pdf_path: str


class QuizComplete(BaseModel):
    node_name: str
    score: int
    total: int
    definition_id: Optional[str] = None
    definition_status: Optional[str] = None
    definition_source: Optional[str] = None


class QuizSummaryRequest(BaseModel):
    topic: str
    score: int
    total: int
    user_answers: List[Dict[str, Any]]
    questions: List[Dict[str, Any]]


class LoginRequest(BaseModel):
    username: str
    password: str
    user_type: str = "student"


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    email: Optional[str] = ""
    user_type: str
    teacher: Optional[str] = ""


class LLMLogRequest(BaseModel):
    messages: List[Dict[str, str]]
    response: Dict[str, Any]
    model: str
    module: str
    metadata: Optional[Dict] = None


class DeleteResourceRequest(BaseModel):
    node_name: str
    resource_index: int


class RestoreResourceRequest(BaseModel):
    course_id: str
    node_id: str
    resource_path: str


class ResourceLearningEventRequest(BaseModel):
    course_id: str
    node_id: str
    resource_id: Optional[int] = None
    resource_path: Optional[str] = None
    event_type: str
    duration_seconds: int = 0
    progress_percent: Optional[float] = None
    is_completed: bool = False
    payload: Dict[str, Any] = {}


class CourseStructureUpsertRequest(BaseModel):
    course_id: str
    course_name: str
    graph_data: Dict[str, Any]
    lifecycle_status: str = "draft"


class CourseInitialGraphGenerateRequest(BaseModel):
    course_id: str
    course_name: str
    outline_text: str
    lifecycle_status: str = "draft"
    bind_resource_candidates: bool = False
    max_resources_per_leaf: int = 2


class CoursePublishRequest(BaseModel):
    course_id: str


class CourseResourceReviewRequest(BaseModel):
    course_id: str
    node_id: str
    resource_path: str
    is_enabled: bool
    review_status: str = "enabled"
    quality_status: Optional[str] = None


class CourseResourceCandidateBindRequest(BaseModel):
    course_id: str
    max_resources_per_leaf: int = 2
    overwrite: bool = False
    review_status: str = "pending"


class CoursePositionRequest(BaseModel):
    course_id: str
    position_name: str
    position_type: str = "related"
    target_rank: int = 0
    source_keyword: Optional[str] = None


class CourseAbilityImportRequest(BaseModel):
    course_id: str
    position_id: int
    abilities: List[Dict[str, Any]] = []
    industry_payload: Optional[Dict[str, Any]] = None
    generate_mapping_candidates: bool = False
    max_candidates_per_ability: int = 3
    min_mapping_score: float = 0.24


class CourseAbilityMappingUpsertRequest(BaseModel):
    course_id: str
    mappings: List[Dict[str, Any]]


class CourseAbilityMappingCandidateGenerateRequest(BaseModel):
    course_id: str
    max_candidates_per_ability: int = 3
    min_score: float = 0.24


class CourseAbilityMappingReviewItem(BaseModel):
    mapping_id: int
    review_status: str
    support_level: Optional[str] = None


class CourseAbilityMappingReviewRequest(BaseModel):
    course_id: str
    mappings: List[CourseAbilityMappingReviewItem]


@app.get("/")
async def root():
    return frontend_index_response()


@app.get("/teacher.html")
async def get_teacher_page():
    return RedirectResponse(url="/teacher/dashboard", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/admin.html")
async def get_admin_page():
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.post("/login/student")
async def login_student(
    response: Response,
    student_id: str = Form(..., alias="student_id"),
    password: str = Form(...),
):
    user = user_manager.authenticate_student(student_id, password)
    if user:
        session_id = session_manager.create_session(user.get("username", student_id), "student", _public_user_data(user))
        redirect_response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key="session_id", value=session_id, httponly=True, max_age=86400, path="/"
        )
        return redirect_response
    else:
        return RedirectResponse(url="/login?error=login_failed", status_code=status.HTTP_302_FOUND)


@app.post("/login/teacher")
async def login_teacher(
    response: Response,
    teacher_id: str = Form(..., alias="teacher_id"),
    password: str = Form(...),
):
    user = user_manager.authenticate_teacher(teacher_id, password)
    if user:
        session_id = session_manager.create_session(user.get("username", teacher_id), "teacher", _public_user_data(user))
        redirect_response = RedirectResponse(url="/teacher/dashboard", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key="session_id", value=session_id, httponly=True, max_age=86400, path="/"
        )
        return redirect_response
    else:
        return RedirectResponse(url="/login?error=login_failed", status_code=status.HTTP_302_FOUND)


@app.post("/login/admin")
async def login_admin(
    response: Response,
    admin_username: str = Form(..., alias="admin_username"),
    password: str = Form(...),
):
    user = user_manager.authenticate_admin(admin_username, password)
    if user:
        session_id = session_manager.create_session(user.get("username", admin_username), "admin", _public_user_data(user))
        redirect_response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key="session_id", value=session_id, httponly=True, max_age=86400, path="/"
        )
        return redirect_response
    else:
        return RedirectResponse(url="/login?error=login_failed", status_code=status.HTTP_302_FOUND)


@app.post("/api/register")
async def register_user(data: RegisterRequest):
    try:
        if data.user_type == "student":
            user = user_manager.register_student(
                username=data.username,
                password=data.password,
                stu_name=data.name,
                email=data.email,
                teacher=data.teacher,
            )
        elif data.user_type == "teacher":
            user = user_manager.register_teacher(
                username=data.username,
                password=data.password,
                name=data.name,
                email=data.email,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid user type")

        return {
            "success": True,
            "message": "User registered successfully",
            "user": user,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/api/auth/login")
async def login_json(data: LoginRequest, response: Response):
    """供前后端分离前端使用的 JSON 登录接口"""
    user_type = (data.user_type or "student").lower()

    if user_type == "student":
        user = user_manager.authenticate_student(data.username, data.password)
    elif user_type == "teacher":
        user = user_manager.authenticate_teacher(data.username, data.password)
    elif user_type == "admin":
        user = user_manager.authenticate_admin(data.username, data.password)
    else:
        raise HTTPException(status_code=400, detail="Invalid user type")

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    canonical_username = user.get("username", data.username)
    public_user = _public_user_data(user)
    session_id = session_manager.create_session(canonical_username, user_type, public_user)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,
        path="/",
    )
    
    # 记录学生登录活动
    if user_type == "student":
        try:
            streak_service = LearningStreakService()
            streak_service.log_activity(canonical_username, "login", "用户登录")
        except Exception as e:
            logger.warning(f"记录登录活动失败: {e}")
    
    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "username": canonical_username,
            "user_id": user.get("user_id"),
            "login_id": user.get("login_id"),
            "user_type": user_type,
            "user_data": public_user,
        },
    }


@app.post("/api/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id:
        session_manager.delete_session(session_id)
    response.delete_cookie(key="session_id")
    return {"success": True, "message": "Logged out successfully"}


@app.get("/api/current-user")
async def get_current_user_info(session_id: Optional[str] = Cookie(None)):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "username": session["username"],
        "user_id": session.get("user_id"),
        "login_id": session.get("login_id"),
        "user_type": session["user_type"],
        "user_data": _public_user_data(session.get("user_data")),
    }


@app.get("/api/health/llm")
async def llm_health_check(session_id: Optional[str] = Cookie(None)):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    model_name = os.environ.get("model_name", "").strip()
    base_url = os.environ.get("base_url", "").strip()
    api_key = os.environ.get("api_key", "").strip()
    embedding_model = os.environ.get("embedding_model", "").strip()

    diagnostics: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str, extra: Optional[dict[str, Any]] = None):
        item = {"name": name, "ok": ok, "detail": detail}
        if extra:
            item["extra"] = extra
        diagnostics.append(item)

    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) >= 10 else ""
    config_ok = bool(model_name and base_url and api_key)
    add_check(
        "config",
        config_ok,
        "模型配置已读取" if config_ok else "缺少 model_name、base_url 或 api_key 配置",
        {
            "model_name": model_name,
            "base_url": base_url,
            "embedding_model": embedding_model,
            "api_key_masked": masked_key,
        },
    )
    if not config_ok:
        return {
            "ok": False,
            "stage": "config",
            "summary": "LLM 配置不完整",
            "checks": diagnostics,
        }

    parsed = urlparse(base_url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not host:
        add_check("network", False, "base_url 无法解析出主机名")
        return {
            "ok": False,
            "stage": "network",
            "summary": "base_url 配置格式有问题",
            "checks": diagnostics,
        }

    try:
        socket.getaddrinfo(host, port)
        add_check("dns", True, f"域名 {host} 解析成功")
    except Exception as exc:
        add_check("dns", False, f"域名解析失败：{exc}")
        return {
            "ok": False,
            "stage": "dns",
            "summary": "无法解析模型服务域名",
            "checks": diagnostics,
        }

    try:
        with socket.create_connection((host, port), timeout=8):
            pass
        add_check("tcp", True, f"已连通 {host}:{port}")
    except Exception as exc:
        add_check("tcp", False, f"无法连接 {host}:{port}：{exc}")
        return {
            "ok": False,
            "stage": "network",
            "summary": "网络或系统权限阻止了模型服务连接",
            "checks": diagnostics,
        }

    models_url = f"{base_url.rstrip('/')}/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    available_models: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(models_url, headers=headers)
        status_code = response.status_code
        response_text = response.text[:500]

        if status_code == 200:
            add_check("auth", True, "API Key 鉴权成功")
            try:
                payload = response.json()
                available_models = [
                    item.get("id", "")
                    for item in payload.get("data", [])
                    if isinstance(item, dict) and item.get("id")
                ]
            except Exception:
                available_models = []
        elif status_code in {401, 403}:
            add_check("auth", False, f"API Key 鉴权失败，状态码 {status_code}")
            return {
                "ok": False,
                "stage": "auth",
                "summary": "API Key 无效或没有权限",
                "checks": diagnostics,
                "response_preview": response_text,
            }
        else:
            add_check("auth", False, f"模型服务返回异常状态码 {status_code}")
            return {
                "ok": False,
                "stage": "service",
                "summary": "模型服务已连通，但接口返回异常",
                "checks": diagnostics,
                "response_preview": response_text,
            }
    except httpx.ConnectError as exc:
        add_check("auth", False, f"连接模型服务失败：{exc}")
        return {
            "ok": False,
            "stage": "network",
            "summary": "到模型服务的 HTTP 连接失败",
            "checks": diagnostics,
        }
    except Exception as exc:
        add_check("auth", False, f"请求模型服务失败：{exc}")
        return {
            "ok": False,
            "stage": "service",
            "summary": "模型服务请求失败",
            "checks": diagnostics,
        }

    model_exists = True
    if available_models:
        model_exists = model_name in available_models
        add_check(
            "model",
            model_exists,
            "当前模型名可用" if model_exists else "当前模型名不在可用模型列表中",
            {
                "configured_model": model_name,
                "available_model_count": len(available_models),
                "available_model_examples": available_models[:20],
            },
        )
    else:
        add_check(
            "model",
            True,
            "未拿到模型列表，无法严格校验模型名；但鉴权已成功",
            {"configured_model": model_name},
        )

    return {
        "ok": model_exists,
        "stage": "done" if model_exists else "model",
        "summary": "LLM 服务可用" if model_exists else "模型配置可能有误",
        "checks": diagnostics,
    }


class UpdateProfileRequest(BaseModel):
    learning_goals: Optional[List[str]] = None
    email: Optional[str] = None
    teacher: Optional[str] = None
    preference: Optional[Dict[str, Any]] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/update-profile")
async def update_profile(data: UpdateProfileRequest, session_id: Optional[str] = Cookie(None)):
    """更新用户资料"""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if session["user_type"] != "student":
        raise HTTPException(status_code=403, detail="Only students can update profile")
    
    updates = {}
    if data.learning_goals is not None:
        updates["learning_goals"] = data.learning_goals
    if data.email is not None:
        updates["email"] = data.email
    if data.teacher is not None:
        updates["teacher"] = data.teacher
    if data.preference is not None:
        updates["preference"] = data.preference
    
    if updates:
        success = user_manager.update_student_profile(session["username"], updates)
        if success:
            # 更新 session 中的数据
            session["user_data"].update(_public_user_data(updates))
            return {"success": True, "message": "Profile updated"}
    
    return {"success": False, "message": "No updates provided"}


@app.post("/api/change-password")
async def change_password(data: ChangePasswordRequest, session_id: Optional[str] = Cookie(None)):
    """修改密码"""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = session["username"]
    auth_identifier = str(session.get("user_id") or "")
    user_type = session["user_type"]
    
    # 验证当前密码
    if user_type == "student":
        user = user_manager.authenticate_student(auth_identifier, data.current_password)
    elif user_type == "teacher":
        user = user_manager.authenticate_teacher(auth_identifier, data.current_password)
    else:
        user = user_manager.authenticate_admin(auth_identifier, data.current_password)
    
    if not user:
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    # 更新密码
    if user_type == "student":
        success = user_manager.update_student_profile(username, {"password": data.new_password})
    else:
        # 教师和管理员暂不支持修改密码
        raise HTTPException(status_code=400, detail="暂不支持修改密码")
    
    if success:
        return {"success": True, "message": "Password changed"}
    
    raise HTTPException(status_code=500, detail="密码修改失败")


@app.post("/api/chat")
async def chat(data: ChatMessage, session_id: Optional[str] = Cookie(None)):
    """处理聊天消息 - 启用RAG检索"""
    message = data.message
    history = data.history
    lang_choice = data.lang_choice

    session = get_current_user(session_id)
    username = session["username"] if session else "anonymous"
    
    # 从会话中获取当前用户的PDF路径
    current_pdf_path = session_manager.get_current_pdf(session_id) if session_id else None

    logger.info(f"📨 Chat request: {message[:50]}...")
    logger.info(f"📄 Current PDF for user {username}: {current_pdf_path}")

    internal_history = []
    for user_msg, assistant_msg in history:
        internal_history.append({"role": "user", "content": user_msg})
        if assistant_msg:
            internal_history.append({"role": "assistant", "content": assistant_msg})

    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(message)

    current_retriever = None
    if current_pdf_path and os.path.exists(current_pdf_path):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        class FilteredRetriever(VectorStoreRetriever):
            """只检索当前PDF的retriever"""

            pdf_path: str

            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
            ):

                vectorstore = rag_service._get_vectorstore()

                docs = vectorstore.similarity_search(
                    query, k=4, filter={"source": self.pdf_path}
                )
                logger.info(
                    f"🔍 Filtered retrieval: found {len(docs)} docs from {self.pdf_path}"
                )
                return docs

        current_retriever = FilteredRetriever(
            vectorstore=rag_service._get_vectorstore(),
            search_kwargs={"k": 4},
            pdf_path=current_pdf_path,
        )
        logger.info(f"✅ Created filtered retriever for: {current_pdf_path}")
    else:
        current_retriever = get_retriever()
        logger.info(f"⚠️ No current PDF, using global retriever")

    result, used_fallback, used_retriever = get_qa_agent().chat(
        message, retriever=current_retriever, return_details=True, username=username
    )

    logger.info(
        f"✅ Response generated. Used RAG: {used_retriever}, Fallback: {used_fallback}"
    )

    result = LanguageHandler.ensure_language(result, language)

    return {
        "response": result,
        "used_fallback": used_fallback,
        "used_retriever": used_retriever,
    }


def find_children_index_for_pdf(
    pdf_path: str, knowledge_path: str = None
) -> Optional[int]:
    """Locate the top-level children index for a PDF using entity-stored graph payload."""
    if not pdf_path:
        return None

    course_id = database_store.get_course_id_by_resource_path(pdf_path) or "course_big_data"
    graph_data = database_store.get_course_payload(course_id) or {}
    if not graph_data:
        return None

    for i, child in enumerate(graph_data.get("children", [])):
        for grandchild in child.get("grandchildren", []):
            resources = grandchild.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            if pdf_path in resources:
                return i

            for great_grandchild in grandchild.get("great-grandchildren", []):
                resources = great_grandchild.get("resource_path", [])
                if isinstance(resources, str):
                    resources = [resources] if resources else []
                if pdf_path in resources:
                    return i

                for ggc in great_grandchild.get("great-grandchildren", []):
                    resources = ggc.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                    if pdf_path in resources:
                        return i

    return None


def find_grandchild_and_collect_pdfs(
    pdf_path: str, knowledge_path: str = None
) -> List[str]:
    """Find sibling PDFs under the same grandchild branch from entity-stored graph payload."""
    if not pdf_path:
        return []

    course_id = database_store.get_course_id_by_resource_path(pdf_path) or "course_big_data"
    graph_data = database_store.get_course_payload(course_id) or {}
    if not graph_data:
        return []

    all_pdfs = []

    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):

            found_in_this_grandchild = False

            resources = grandchild.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            if pdf_path in resources:
                found_in_this_grandchild = True

            for great_grandchild in grandchild.get("great-grandchildren", []):
                resources = great_grandchild.get("resource_path", [])
                if isinstance(resources, str):
                    resources = [resources] if resources else []
                if pdf_path in resources:
                    found_in_this_grandchild = True

            if found_in_this_grandchild:
                for great_grandchild in grandchild.get("great-grandchildren", []):
                    resources = great_grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                    for res in resources:
                        if res.endswith(".pdf") and os.path.exists(res):
                            all_pdfs.append(res)

                logger.info(
                    f"Found {len(all_pdfs)} PDFs in grandchild '{grandchild.get('name')}'"
                )
                return all_pdfs

    return []


@app.get("/api/quiz/definitions")
async def list_quiz_definitions(
    course_id: str = "course_big_data",
    node_id: Optional[str] = None,
    status: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    _require_teacher_or_admin(session_id)
    if not node_id:
        raise HTTPException(status_code=400, detail="node_id is required")
    try:
        definitions = _quiz_definition_service().list_definitions(
            course_id=course_id,
            node_id=node_id,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"definitions": definitions}


@app.post("/api/quiz/definitions")
async def save_quiz_definition(
    data: QuizDefinitionUpsert,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    try:
        definition = _quiz_definition_service().save_definition(
            data.dict(),
            teacher_username=str(session.get("username") or session.get("user_id") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "definition": definition}


@app.post("/api/quiz/definitions/{definition_id}/publish")
async def publish_quiz_definition(
    definition_id: str,
    data: QuizDefinitionPublish,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    try:
        definition = _quiz_definition_service().publish_definition(
            definition_id=definition_id,
            course_id=data.course_id,
            node_id=data.node_id,
            teacher_username=str(session.get("username") or session.get("user_id") or ""),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "definition": definition}


@app.post("/api/quiz/start")
async def start_quiz(data: QuizStart, session_id: Optional[str] = Cookie(None)):
    """开始测验"""
    session = get_current_user(session_id)
    username = session["username"] if session else "anonymous"
    
    # 从会话中获取当前用户的PDF路径
    current_pdf_path = session_manager.get_current_pdf(session_id) if session_id else None

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = (
        code if code != "auto" else LanguageHandler.choose_or_detect(data.subject)
    )

    course_id = str(data.course_id or "course_big_data").strip() or "course_big_data"
    node_id = str(data.node_id or data.subject or "").strip()
    published_definition = None
    if node_id:
        try:
            published_definition = _quiz_definition_service().get_published_definition(
                course_id=course_id,
                node_id=node_id,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load published quiz definition for %s/%s: %s",
                course_id,
                node_id,
                exc,
            )

    if published_definition:
        questions = list(published_definition.get("questions") or [])
        if not questions:
            raise HTTPException(status_code=400, detail="Published quiz definition has no questions")
        state = {
            "subject": data.subject,
            "language": language,
            "questions": questions,
            "index": 0,
            "scores": {},
            "correct_total": 0,
            "course_id": course_id,
            "node_id": node_id,
            "definition_id": published_definition.get("definition_id"),
            "definition_status": "published",
            "definition_source": "published_definition",
        }
        return {
            "question": questions[0],
            "state": state,
            "used_retriever": False,
            "definition_id": published_definition.get("definition_id"),
            "definition_status": "published",
            "definition_source": "published_definition",
        }

    current_retriever = None
    if current_pdf_path and os.path.exists(current_pdf_path):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        children_index = find_children_index_for_pdf(current_pdf_path)
        logger.info(f"🔍 Current PDF belongs to children[{children_index}]")

        question_file_path = None
        if children_index is not None and 0 <= children_index <= 5:
            question_file_path = f"data/Question/Q{children_index + 1}.txt"
            if os.path.exists(question_file_path):
                logger.info(f"📄 Using question file: {question_file_path}")
            else:
                logger.warning(f"⚠️ Question file not found: {question_file_path}")
                question_file_path = None

        class QuizFilteredRetriever(VectorStoreRetriever):
            """Quiz专用retriever：检索当前PDF和对应的Question文件"""

            pdf_path: str
            question_file_content: str = ""

            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
            ):

                vectorstore = rag_service._get_vectorstore()

                docs = vectorstore.similarity_search(
                    query, k=3, filter={"source": self.pdf_path}
                )
                logger.info(f"🔍 Found {len(docs)} docs from current PDF")

                if self.question_file_content:
                    from langchain_core.documents import Document

                    question_doc = Document(
                        page_content=self.question_file_content[:2000],
                        metadata={"source": "question_bank"},
                    )
                    docs.append(question_doc)
                    logger.info("✅ Added question bank content to context")

                return docs

        question_content = ""
        if question_file_path and os.path.exists(question_file_path):
            with open(question_file_path, "r", encoding="utf-8") as f:
                question_content = f.read()

        current_retriever = QuizFilteredRetriever(
            vectorstore=rag_service._get_vectorstore(),
            search_kwargs={"k": 3},
            pdf_path=current_pdf_path,
            question_file_content=question_content,
        )
        logger.info(f"✅ Created quiz retriever for: {current_pdf_path}")
    else:
        current_retriever = get_retriever()
        logger.info(f"⚠️ No current PDF, using global retriever")

    questions, used_retriever = get_quiz_agent().prepare_quiz_questions(
        data.subject, language=language, retriever=current_retriever, username=username
    )

    if not questions:
        raise HTTPException(status_code=400, detail="Failed to generate quiz")

    state = {
        "subject": data.subject,
        "language": language,
        "questions": questions,
        "index": 0,
        "scores": {},
        "correct_total": 0,
        "course_id": course_id,
        "node_id": node_id,
        "definition_status": "generated_fallback",
        "definition_source": "generated",
    }

    first_q = questions[0]
    return {
        "question": first_q,
        "state": state,
        "used_retriever": used_retriever,
        "definition_status": "generated_fallback",
        "definition_source": "generated",
    }


@app.post("/api/quiz/answer")
async def answer_quiz(data: QuizAnswer):
    """回答测验问题"""
    state = data.state
    choice = data.choice.lower()

    if not state or state.get("index") is None:
        raise HTTPException(status_code=400, detail="Quiz not started")

    idx = state["index"]
    questions = state["questions"]

    if idx >= len(questions):
        return {"finished": True, "results": _compile_results(state)}

    current = questions[idx]
    topic = current["topic"]
    correct = current["correct"]

    if topic not in state["scores"]:
        state["scores"][topic] = [0, 0]

    state["scores"][topic][1] += 1

    if choice == correct or correct == "?":
        state["scores"][topic][0] += 1
        state["correct_total"] += 1
        is_correct = True
    else:
        is_correct = False

    state["index"] += 1

    if state["index"] >= len(questions):
        return {
            "finished": True,
            "is_correct": is_correct,
            "correct_answer": correct,
            "results": _compile_results(state),
            "state": state,
        }

    next_q = questions[state["index"]]
    return {
        "finished": False,
        "is_correct": is_correct,
        "correct_answer": correct,
        "next_question": next_q,
        "state": state,
    }


def _compile_results(state: Dict) -> str:
    lines = []
    total_questions = 0
    total_correct = state.get("correct_total", 0)

    for topic, (corr, tot) in state.get("scores", {}).items():
        perc = (corr / tot) * 100 if tot else 0
        lines.append(f"{topic}: {corr}/{tot} ({perc:.2f}%)")
        total_questions += tot

    if lines:
        overall = (total_correct / total_questions) * 100 if total_questions > 0 else 0
        lines.append(
            f"\nOverall Score: {total_correct}/{total_questions} ({overall:.2f}%)"
        )

    result = "\n".join(lines)
    lang = state.get("language", "auto")
    return LanguageHandler.ensure_language(result, lang)


@app.post("/api/learning-plan")
async def create_learning_plan(
    data: LearningPlanRequest, session_id: Optional[str] = Cookie(None)
):
    """生成学习计划"""
    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(data.goals)

    username = data.name
    session = get_current_user(session_id)
    if session and session["user_type"] == "student":
        username = session["username"]

    plan_agent = Plan_Agent(user_name=username, user_language=language)
    goals_list = [g.strip() for g in data.goals.split(";") if g.strip()]
    user_input = {"goals": goals_list}

    plan_agent_instance = get_plan_agent()
    plan_agent_instance.generate_plan_from_prompt(user_input)

    deadline_days = data.deadline_days if hasattr(data, "deadline_days") else 7
    deadline_date = (datetime.now() + timedelta(days=deadline_days)).strftime(
        "%Y-%m-%d"
    )
    priority = data.priority if hasattr(data, "priority") else "基础知识"

    for entry in plan_agent_instance.learning_plan:
        entry["deadline"] = deadline_date
        entry["priority"] = priority

    plan_agent_instance.save_to_file()

    return {
        "message": "Learning plan generated successfully",
        "plan": plan_agent_instance.learning_plan,
    }


@app.post("/api/learning-plan/from-quiz")
async def create_learning_plan_from_quiz(
    data: LearningPlanFromQuiz, session_id: Optional[str] = Cookie(None)
):
    """根据测验结果生成学习计划"""
    if not data.state or not data.state.get("scores"):
        raise HTTPException(status_code=400, detail="No quiz results available")

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else data.state.get("language", "en")

    username = data.name
    session = get_current_user(session_id)
    if session and session["user_type"] == "student":
        username = session["username"]

    plan_agent = Plan_Agent(user_name=username, user_language=language)
    generated_plan = plan_agent.generate_plan_from_quiz(data.state["scores"])
    plan_agent.save_to_file()

    return {
        "message": "Learning plan generated from quiz results",
        "plan": generated_plan,
    }


@app.post("/api/quiz/summary")
async def generate_quiz_summary(data: QuizSummaryRequest, session_id: Optional[str] = Cookie(None)):
    """根据测验结果生成总结报告"""
    if not quiz_summary_llm:
        raise HTTPException(status_code=503, detail="Quiz summary model is not configured")

    choice_lines = []
    text_lines = []
    for index, question in enumerate(data.questions):
        answer_info = data.user_answers[index] if index < len(data.user_answers) else {}
        if answer_info.get("type") == "choice":
            choice_lines.append(f"题目 {index + 1}: {question.get('question', '')}")
            choice_lines.append(f"学生选择: {answer_info.get('selected', '未作答')}")
            choice_lines.append(f"正确答案: {answer_info.get('correct_answer', question.get('correct', ''))}")
            choice_lines.append(
                f"结果: {'正确' if answer_info.get('is_correct') else '错误'}"
            )
            choice_lines.append("")
        elif answer_info.get("type") == "text":
            text_lines.append(f"题目 {index + 1}: {question.get('question', '')}")
            text_lines.append(f"学生答案: {answer_info.get('answer', '')}")
            text_lines.append(f"得分: {answer_info.get('score', 0)}")
            text_lines.append("")

    prompt = generate_quiz_summary_prompt().format(
        topic=data.topic,
        score=data.score,
        total=data.total,
        choice_details="\n".join(choice_lines) if choice_lines else "无选择题",
        text_details="\n".join(text_lines) if text_lines else "无简答题",
    )

    result = quiz_summary_llm.invoke(prompt)
    session = get_current_user(session_id)
    username = session["username"] if session else "anonymous"
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        messages=[{"role": "user", "content": prompt}],
        response=result,
        model=quiz_summary_model_name,
        module="QuizModule.quiz_summary",
        metadata={
            "function": "generate_quiz_summary",
            "topic": data.topic,
            "score": data.score,
            "total": data.total,
        },
        username=username,
    )
    return {"summary": result.content}


@app.post("/api/summary")
async def generate_summary(
    data: SummaryRequest, session_id: Optional[str] = Cookie(None)
):
    """生成知识总结（流式输出）"""
    session = get_current_user(session_id)
    username = session["username"] if session else "anonymous"
    
    # 从会话中获取当前用户的PDF路径
    current_pdf_path = session_manager.get_current_pdf(session_id) if session_id else None

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(data.topic)

    current_retriever = None
    if current_pdf_path and os.path.exists(current_pdf_path):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        related_pdfs = find_grandchild_and_collect_pdfs(current_pdf_path)

        if related_pdfs:
            logger.info(f"📚 Summary will use {len(related_pdfs)} related PDFs")

            class SummaryFilteredRetriever(VectorStoreRetriever):
                """Summary专用retriever：检索grandchild下所有great-grandchildren的PDF"""

                pdf_paths: List[str]

                def _get_relevant_documents(
                    self,
                    query: str,
                    *,
                    run_manager: CallbackManagerForRetrieverRun = None,
                ):

                    vectorstore = rag_service._get_vectorstore()

                    all_docs = []
                    for pdf_path in self.pdf_paths:
                        docs = vectorstore.similarity_search(
                            query, k=2, filter={"source": pdf_path}
                        )
                        all_docs.extend(docs)

                    logger.info(
                        f"🔍 Summary retrieval: found {len(all_docs)} docs from {len(self.pdf_paths)} PDFs"
                    )

                    return all_docs[:8]

            current_retriever = SummaryFilteredRetriever(
                vectorstore=rag_service._get_vectorstore(),
                search_kwargs={"k": 8},
                pdf_paths=related_pdfs,
            )
            logger.info(f"✅ Created summary retriever for {len(related_pdfs)} PDFs")
        else:
            logger.info(f"⚠️ No related PDFs found, using current PDF only")

            from langchain_core.vectorstores import VectorStoreRetriever
            from langchain_core.callbacks import CallbackManagerForRetrieverRun

            class SinglePDFRetriever(VectorStoreRetriever):
                pdf_path: str

                def _get_relevant_documents(
                    self,
                    query: str,
                    *,
                    run_manager: CallbackManagerForRetrieverRun = None,
                ):
                    vectorstore = rag_service._get_vectorstore()
                    docs = vectorstore.similarity_search(
                        query, k=4, filter={"source": self.pdf_path}
                    )
                    return docs

            current_retriever = SinglePDFRetriever(
                vectorstore=rag_service._get_vectorstore(),
                search_kwargs={"k": 4},
                pdf_path=current_pdf_path,
            )
    else:
        current_retriever = get_retriever()
        logger.info(f"⚠️ No current PDF, using global retriever")

    # 先用非流式版本确保功能正常
    try:
        summary, used_retriever = get_summary_agent().generate_summary(
            data.topic, language=language, retriever=current_retriever, username=username
        )
        return {"summary": summary, "used_retriever": used_retriever}
    except Exception as e:
        logger.error(f"Summary error: {e}")
        return {"summary": f"生成失败: {str(e)}", "used_retriever": False}


@app.get("/api/student/courses")
async def list_student_visible_courses(session_id: Optional[str] = Cookie(None)):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if session.get("user_type") == "student":
        list_student_courses = getattr(database_store, "list_student_courses", None)
        courses = list_student_courses(session.get("username")) if callable(list_student_courses) else []
    else:
        courses = [
            item for item in database_store.list_courses()
            if item.get("lifecycle_status") == "published"
        ]
    default_course_id = (
        str(courses[0].get("course_id"))
        if courses and courses[0].get("course_id")
        else "course_big_data"
    )
    return {"courses": courses, "default_course_id": default_course_id}


@app.get("/api/knowledge-graph")
async def get_knowledge_graph(
    course_id: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    """Return knowledge graph payload (从数据库读取，带缓存)."""
    try:
        session = get_current_user(session_id)
        course_id, graph_data = _load_course_graph_entity_only(session, course_id)
        if not graph_data:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")
        try:
            return _graph_with_enabled_resources(course_id, graph_data)
        except Exception as exc:
            logging.warning("Failed to hydrate knowledge graph resources for %s: %s", course_id, exc)
            return graph_data
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"加载课程数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load knowledge graph: {str(e)}")


@app.get("/api/course-digital-twin/courses")
async def list_course_digital_twin_courses(session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    return {"courses": database_store.list_courses()}


@app.get("/api/course-digital-twin/{course_id}")
async def get_course_digital_twin_summary(course_id: str, session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    summary = database_store.get_course_summary(course_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Course not found")
    payload = database_store.get_course_payload(course_id)
    return {"summary": summary, "graph_data": payload or {}}


@app.get("/api/course-digital-twin/{course_id}/runtime-evaluation")
async def evaluate_course_digital_twin_runtime(
    course_id: str,
    window_days: int = 30,
    min_quiz_attempts: int = 3,
    session_id: Optional[str] = Cookie(None),
):
    _require_teacher_or_admin(session_id)
    result = database_store.evaluate_course_runtime(
        course_id,
        window_days=window_days,
        min_quiz_attempts=min_quiz_attempts,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"evaluation": result}


@app.post("/api/course-digital-twin/structure")
async def upsert_course_digital_twin_structure(
    data: CourseStructureUpsertRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    course_id = str(data.course_id or "").strip()
    course_name = str(data.course_name or "").strip()
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    if not course_name:
        raise HTTPException(status_code=400, detail="course_name is required")

    graph_data = dict(data.graph_data or {})
    graph_data["name"] = str(graph_data.get("name") or course_name)
    validation = _validate_course_graph(graph_data)
    lifecycle_status = str(data.lifecycle_status or "draft").strip().lower()
    if lifecycle_status not in {"draft", "published"}:
        lifecycle_status = "draft"

    result = database_store.sync_course_from_graph(
        course_id=course_id,
        graph_data=graph_data,
        course_name=course_name,
        source_path=f"entity://courses/{course_id}",
        lifecycle_status=lifecycle_status,
        updated_by=session.get("username"),
    )
    _clear_course_cache_for_course(course_id)
    return {
        "success": True,
        "course_id": course_id,
        "lifecycle_status": lifecycle_status,
        "validation": validation,
        "sync_result": result,
        "summary": database_store.get_course_summary(course_id),
    }


@app.post("/api/course-digital-twin/initial-graph")
async def generate_course_digital_twin_initial_graph(
    data: CourseInitialGraphGenerateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    course_id = str(data.course_id or "").strip()
    course_name = str(data.course_name or "").strip()
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    if not course_name:
        raise HTTPException(status_code=400, detail="course_name is required")

    graph_data = _build_initial_course_graph(course_name, data.outline_text)
    resource_bind_result = None
    if data.bind_resource_candidates:
        resource_bind_result = _attach_resource_candidates_to_graph(
            graph_data,
            max_resources_per_leaf=data.max_resources_per_leaf,
            overwrite=True,
        )
    validation = _validate_course_graph(graph_data)
    lifecycle_status = str(data.lifecycle_status or "draft").strip().lower()
    if lifecycle_status not in {"draft", "published"}:
        lifecycle_status = "draft"
    sync_result = database_store.sync_course_from_graph(
        course_id=course_id,
        graph_data=graph_data,
        course_name=course_name,
        source_path=f"entity://courses/{course_id}",
        lifecycle_status=lifecycle_status,
        updated_by=session.get("username"),
    )
    review_marked_count = 0
    if data.bind_resource_candidates:
        review_marked_count = _mark_auto_bound_resources_for_review(
            course_id,
            graph_data,
            "pending",
            set(resource_bind_result.get("attached_resource_paths") or []) if resource_bind_result else set(),
        )
    _clear_course_cache_for_course(course_id)
    return {
        "success": True,
        "course_id": course_id,
        "lifecycle_status": lifecycle_status,
        "graph_data": graph_data,
        "validation": validation,
        "resource_bind_result": resource_bind_result,
        "review_marked_count": review_marked_count,
        "sync_result": sync_result,
        "summary": database_store.get_course_summary(course_id),
    }


@app.post("/api/course-digital-twin/resource-candidates/bind")
async def bind_course_digital_twin_resource_candidates(
    data: CourseResourceCandidateBindRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    course_id = str(data.course_id or "").strip()
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    summary = database_store.get_course_summary(course_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Course not found")
    graph_data = database_store.get_course_payload(course_id)
    if not isinstance(graph_data, dict) or not graph_data:
        raise HTTPException(status_code=404, detail="Course graph not found")
    bind_result = _attach_resource_candidates_to_graph(
        graph_data,
        max_resources_per_leaf=data.max_resources_per_leaf,
        overwrite=data.overwrite,
    )
    course_name = str(summary.get("course_name") or graph_data.get("name") or course_id)
    sync_result = database_store.sync_course_from_graph(
        course_id=course_id,
        graph_data=graph_data,
        course_name=course_name,
        source_path=f"entity://courses/{course_id}",
        lifecycle_status=str(summary.get("lifecycle_status") or "draft"),
        updated_by=session.get("username"),
    )
    review_marked_count = _mark_auto_bound_resources_for_review(
        course_id,
        graph_data,
        data.review_status,
        set(bind_result.get("attached_resource_paths") or []),
    )
    _clear_course_cache_for_course(course_id)
    return {
        "success": True,
        "course_id": course_id,
        "graph_data": graph_data,
        "bind_result": bind_result,
        "review_marked_count": review_marked_count,
        "sync_result": sync_result,
        "summary": database_store.get_course_summary(course_id),
        "resources": database_store.list_course_resources(course_id),
    }


@app.get("/api/course-digital-twin/{course_id}/resources")
async def list_course_digital_twin_resources(course_id: str, session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    return {"resources": database_store.list_course_resources(course_id)}


@app.post("/api/course-digital-twin/resource-review")
async def review_course_digital_twin_resource(
    data: CourseResourceReviewRequest,
    session_id: Optional[str] = Cookie(None),
):
    _require_teacher_or_admin(session_id)
    success = database_store.set_resource_review_status(
        course_id=data.course_id,
        node_id=data.node_id,
        resource_path=data.resource_path,
        is_enabled=data.is_enabled,
        review_status=data.review_status,
        quality_status=data.quality_status,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    _clear_course_cache_for_course(data.course_id)
    return {"success": True, "summary": database_store.get_course_summary(data.course_id)}


@app.post("/api/course-digital-twin/publish")
async def publish_course_digital_twin(data: CoursePublishRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher_or_admin(session_id)
    summary = database_store.get_course_summary(data.course_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Course not found")
    if int(summary.get("leaf_node_count") or 0) <= 0:
        raise HTTPException(status_code=400, detail="Course must contain leaf knowledge points before publishing")
    success = database_store.publish_course(data.course_id, published_by=session.get("username"))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to publish course")
    _clear_course_cache_for_course(data.course_id)
    return {"success": True, "summary": database_store.get_course_summary(data.course_id)}


@app.get("/api/course-digital-twin/{course_id}/positions")
async def list_course_digital_twin_positions(course_id: str, session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    return {"positions": database_store.list_course_positions(course_id)}


@app.post("/api/course-digital-twin/positions")
async def upsert_course_digital_twin_position(
    data: CoursePositionRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    position_type = str(data.position_type or "related").strip().lower()
    if position_type not in {"primary", "related"}:
        raise HTTPException(status_code=400, detail="position_type must be primary or related")
    if position_type == "primary":
        existing = database_store.list_course_positions(data.course_id)
        primary_positions = [
            item for item in existing
            if item.get("position_type") == "primary"
            and str(item.get("position_name") or "").strip() != str(data.position_name or "").strip()
        ]
        if len(primary_positions) >= 3:
            raise HTTPException(status_code=400, detail="A course can have at most 3 primary target positions")
    try:
        position = database_store.upsert_career_position(
            data.course_id,
            data.position_name,
            position_type=position_type,
            target_rank=data.target_rank,
            source_keyword=data.source_keyword,
            created_by=session.get("user_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"success": True, "position": position, "positions": database_store.list_course_positions(data.course_id)}


@app.post("/api/course-digital-twin/abilities/import")
async def import_course_digital_twin_abilities(
    data: CourseAbilityImportRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    candidates = _extract_ability_candidates(data.abilities, data.industry_payload)
    if not candidates:
        raise HTTPException(status_code=400, detail="No ability candidates were provided or extracted")
    try:
        result = database_store.upsert_career_abilities(data.position_id, candidates)
        mapping_candidate_result = None
        mappings = None
        if data.generate_mapping_candidates:
            mapping_candidate_result = database_store.generate_course_ability_mapping_candidates(
                data.course_id,
                updated_by=session.get("user_id"),
                max_candidates_per_ability=data.max_candidates_per_ability,
                min_score=data.min_mapping_score,
            )
            mappings = database_store.list_course_ability_mappings(data.course_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "success": True,
        "import_result": result,
        "abilities": database_store.list_course_abilities(data.course_id),
        "mapping_candidate_result": mapping_candidate_result,
        "mappings": mappings,
    }


@app.get("/api/course-digital-twin/{course_id}/abilities")
async def list_course_digital_twin_abilities(course_id: str, session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    return {"abilities": database_store.list_course_abilities(course_id)}


@app.get("/api/course-digital-twin/{course_id}/ability-mappings")
async def list_course_digital_twin_ability_mappings(course_id: str, session_id: Optional[str] = Cookie(None)):
    _require_teacher_or_admin(session_id)
    return {"mappings": database_store.list_course_ability_mappings(course_id)}


@app.post("/api/course-digital-twin/ability-mappings")
async def upsert_course_digital_twin_ability_mappings(
    data: CourseAbilityMappingUpsertRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    if not data.mappings:
        raise HTTPException(status_code=400, detail="mappings are required")
    try:
        result = database_store.upsert_course_ability_mappings(
            data.course_id,
            data.mappings,
            updated_by=session.get("user_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "success": True,
        "mapping_result": result,
        "mappings": database_store.list_course_ability_mappings(data.course_id),
    }


@app.post("/api/course-digital-twin/ability-mappings/candidates/generate")
async def generate_course_digital_twin_ability_mapping_candidates(
    data: CourseAbilityMappingCandidateGenerateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    if not data.course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    try:
        result = database_store.generate_course_ability_mapping_candidates(
            data.course_id,
            updated_by=session.get("user_id"),
            max_candidates_per_ability=data.max_candidates_per_ability,
            min_score=data.min_score,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "success": True,
        "candidate_result": result,
        "mappings": database_store.list_course_ability_mappings(data.course_id),
    }


@app.post("/api/course-digital-twin/ability-mappings/review")
async def review_course_digital_twin_ability_mappings(
    data: CourseAbilityMappingReviewRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    if not data.mappings:
        raise HTTPException(status_code=400, detail="mappings are required")
    updated = 0
    for item in data.mappings:
        if database_store.review_course_ability_mapping(
            item.mapping_id,
            review_status=item.review_status,
            support_level=item.support_level,
            reviewed_by=session.get("user_id"),
        ):
            updated += 1
    return {
        "success": True,
        "updated": updated,
        "mappings": database_store.list_course_ability_mappings(data.course_id),
    }


@app.post("/api/clear-course-cache")
async def clear_course_cache(session_id: Optional[str] = Cookie(None)):
    """清除课程数据缓存（管理员功能）"""
    session = get_current_user(session_id)
    # 可以添加权限检查
    # if session.get("user_type") != "teacher":
    #     raise HTTPException(status_code=403, detail="Only teachers can clear cache")
    
    with _course_cache_lock:
        cleared_count = len(_course_cache)
        _course_cache.clear()
    
    logging.info(f"课程缓存已清除，共清除 {cleared_count} 个缓存项")
    return {"message": f"Cache cleared successfully. {cleared_count} items removed."}


@app.get("/api/graph-visualization")
async def get_graph_visualization(session_id: Optional[str] = Cookie(None)):
    """获取用户的可视化图谱数据"""
    session = get_current_user(session_id)
    if session and session["user_type"] == "student":
        graph_path = user_manager.get_user_graph_path(session["username"])
    else:
        graph_path = "backend/static/vendor/graph.json"

    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"nodes": [], "links": []}


@app.get("/api/learning-nodes")
async def get_learning_nodes(
    course_id: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    """Return learning node names (entity-only)."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session, course_id)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return database_store.list_learning_nodes_for_course(course_id)


@app.post("/api/node/resources")
async def get_node_resources(
    data: NodeSelection, session_id: Optional[str] = Cookie(None)
):
    """Return resource paths for a node (entity-only)."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session, data.course_id)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return database_store.list_resources_for_node_name(course_id, data.node_name)


@app.post("/api/resource-learning/events")
async def record_resource_learning_event(
    data: ResourceLearningEventRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="请先登录")
    if session.get("user_type") != "student":
        raise HTTPException(status_code=403, detail="仅学生端可记录资源学习事件")
    if not _student_can_access_published_course_base(session, data.course_id):
        raise HTTPException(status_code=404, detail="Published course base not found")
    try:
        event_id = database_store.record_resource_learning_event(
            username=str(session.get("username") or ""),
            user_id=session.get("user_id"),
            course_id=data.course_id,
            node_id=data.node_id,
            resource_id=data.resource_id,
            resource_path=data.resource_path,
            event_type=data.event_type,
            duration_seconds=data.duration_seconds,
            progress_percent=data.progress_percent,
            is_completed=data.is_completed,
            payload=data.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "event_id": event_id}


@app.get("/api/resource-learning/summary")
async def get_resource_learning_summary(
    course_id: str,
    node_id: Optional[str] = None,
    username: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="请先登录")
    if session.get("user_type") == "student":
        username = str(session.get("username") or "")
        if not _student_can_access_published_course_base(session, course_id):
            raise HTTPException(status_code=404, detail="Published course base not found")
    elif session.get("user_type") not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="无权查看资源学习汇总")
    return database_store.summarize_resource_learning_events(
        course_id=course_id,
        node_id=node_id,
        username=username,
    )


@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    node_name: str = "",
    session_id: Optional[str] = Cookie(None),
):
    """Upload files to a node and persist via entity tables."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if not node_name:
        raise HTTPException(status_code=400, detail="No node selected")

    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    save_dir = Path("data/RAG_files")
    save_dir.mkdir(parents=True, exist_ok=True)

    supported_conversion_exts = [".doc", ".docx", ".ppt", ".pptx"]
    newly_added_paths = []

    for file in files:
        filename = file.filename
        file_ext = Path(filename).suffix.lower()
        temp_path = save_dir / filename

        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_ext == ".pdf":
            newly_added_paths.append(str(temp_path))
        elif file_ext in supported_conversion_exts:
            pdf_path = convert_to_pdf(str(temp_path), str(save_dir))
            if pdf_path:
                newly_added_paths.append(pdf_path)

    if not newly_added_paths:
        raise HTTPException(status_code=400, detail="No valid files processed")

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if grandchild.get("name") == node_name:
                if "resource_path" not in grandchild:
                    grandchild["resource_path"] = []
                grandchild["resource_path"].extend(newly_added_paths)
                updated = True
                break

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == node_name:
                    if "resource_path" not in great_grandchild:
                        great_grandchild["resource_path"] = []
                    great_grandchild["resource_path"].extend(newly_added_paths)
                    updated = True
                    break

            if updated:
                break
        if updated:
            break

    if updated:
        course_name, source_path = _resolve_course_sync_meta(course_id, graph_data)
        database_store.sync_course_from_graph(
            course_id=course_id,
            course_name=course_name,
            graph_data=graph_data,
            source_path=source_path,
        )

        ingest_error = rag_service.ingest_paths(newly_added_paths)
        if ingest_error:
            return {
                "message": "Files uploaded but RAG indexing failed",
                "error": ingest_error,
            }

        return {
            "message": f"Successfully uploaded {len(newly_added_paths)} files",
            "paths": newly_added_paths,
        }

    raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")


@app.post("/api/delete-resource")
async def delete_resource(
    data: DeleteResourceRequest, session_id: Optional[str] = Cookie(None)
):
    """Soft delete one resource from a node (mark as deleted, not permanently remove)."""
    session = get_current_user(session_id)
    username = session.get("username", "unknown")
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    deleted_resource = None
    node_id = None
    
    # Find the resource in the graph
    def find_and_get_resource(node: Dict[str, Any]) -> Optional[tuple[str, str]]:
        nonlocal deleted_resource, node_id
        if node.get("name") == data.node_name:
            resources = node.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            if 0 <= data.resource_index < len(resources):
                deleted_resource = resources[data.resource_index]
                node_id = str(node.get("node_id") or node.get("id") or data.node_name)
                return (node_id, deleted_resource)
        
        for child in node.get("grandchildren", []) or []:
            result = find_and_get_resource(child)
            if result:
                return result
        
        for child in node.get("great-grandchildren", []) or []:
            result = find_and_get_resource(child)
            if result:
                return result
        
        return None
    
    # Search in all children
    for child in graph_data.get("children", []):
        result = find_and_get_resource(child)
        if result:
            break
    
    if not deleted_resource or not node_id:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{data.node_name}' not found or invalid resource index",
        )
    
    # Soft delete in database
    success = database_store.soft_delete_resource(
        course_id=course_id,
        node_id=node_id,
        resource_path=deleted_resource,
        deleted_by=username,
    )
    
    if success:
        logger.info(
            f"Soft deleted resource: {deleted_resource} from node: {data.node_name} by user: {username}"
        )
        
        # Also remove from graph and sync
        updated = False
        for child in graph_data.get("children", []):
            for grandchild in child.get("grandchildren", []):
                if grandchild.get("name") == data.node_name:
                    resources = grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                        grandchild["resource_path"] = resources
                    if 0 <= data.resource_index < len(resources):
                        resources.pop(data.resource_index)
                        updated = True
                        break

                for great_grandchild in grandchild.get("great-grandchildren", []):
                    if great_grandchild.get("name") == data.node_name:
                        resources = great_grandchild.get("resource_path", [])
                        if isinstance(resources, str):
                            resources = [resources] if resources else []
                            great_grandchild["resource_path"] = resources
                        if 0 <= data.resource_index < len(resources):
                            resources.pop(data.resource_index)
                            updated = True
                            break
                if updated:
                    break
            if updated:
                break
        
        if updated:
            course_name, source_path = _resolve_course_sync_meta(course_id, graph_data)
            database_store.sync_course_from_graph(
                course_id=course_id,
                course_name=course_name,
                graph_data=graph_data,
                source_path=source_path,
            )
        
        return {
            "success": True,
            "message": "Resource moved to recycle bin",
            "resource_path": deleted_resource,
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete resource",
        )


@app.get("/api/recycle-bin")
async def get_recycle_bin(
    course_id: Optional[str] = None,
    node_id: Optional[str] = None,
    limit: Optional[int] = 100,
    session_id: Optional[str] = Cookie(None),
):
    """Get list of deleted resources (recycle bin)."""
    get_current_user(session_id)  # Verify user is logged in
    
    deleted_resources = database_store.list_deleted_resources(
        course_id=course_id,
        node_id=node_id,
        limit=limit,
    )
    
    return {
        "success": True,
        "count": len(deleted_resources),
        "resources": deleted_resources,
    }


@app.post("/api/restore-resource")
async def restore_resource(
    data: RestoreResourceRequest, session_id: Optional[str] = Cookie(None)
):
    """Restore a soft-deleted resource from recycle bin."""
    session = get_current_user(session_id)
    username = session.get("username", "unknown")
    
    # Restore in database
    success = database_store.restore_resource(
        course_id=data.course_id,
        node_id=data.node_id,
        resource_path=data.resource_path,
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Resource not found in recycle bin or already restored",
        )
    
    logger.info(
        f"Restored resource: {data.resource_path} to node: {data.node_id} by user: {username}"
    )
    
    # Reload graph and add resource back
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    
    # Find the node and add resource back
    updated = False
    
    def add_resource_to_node(node: Dict[str, Any]) -> bool:
        nonlocal updated
        node_id_check = str(node.get("node_id") or node.get("id") or node.get("name", ""))
        if node_id_check == data.node_id:
            resources = node.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            
            # Add resource if not already present
            if data.resource_path not in resources:
                resources.append(data.resource_path)
                node["resource_path"] = resources
                updated = True
            return True
        
        for child in node.get("grandchildren", []) or []:
            if add_resource_to_node(child):
                return True
        
        for child in node.get("great-grandchildren", []) or []:
            if add_resource_to_node(child):
                return True
        
        return False
    
    # Search in all children
    for child in graph_data.get("children", []):
        if add_resource_to_node(child):
            break
    
    if updated:
        course_name, source_path = _resolve_course_sync_meta(data.course_id, graph_data)
        database_store.sync_course_from_graph(
            course_id=data.course_id,
            course_name=course_name,
            graph_data=graph_data,
            source_path=source_path,
        )
    
    return {
        "success": True,
        "message": "Resource restored successfully",
        "resource_path": data.resource_path,
    }


@app.post("/api/pdf/select")
async def select_pdf(data: PDFSelection, session_id: Optional[str] = Cookie(None)):
    raw_path = data.pdf_path.lstrip("/")

    cleaned_path = raw_path.replace("backend/data/", "data/")

    full_pdf_path = PROJECT_ROOT / cleaned_path

    if not full_pdf_path.exists():

        if full_pdf_path.suffix == ".PDF":
            full_pdf_path = full_pdf_path.with_suffix(".pdf")
            if full_pdf_path.exists():
                logger.warning(f"🔧 Auto-fixed case: {full_pdf_path.name}")

    if not full_pdf_path.exists():

        fallback_path = BASE_DIR / cleaned_path
        if fallback_path.exists():
            full_pdf_path = fallback_path
        else:
            logger.error(f"❌ PDF really not found at: {full_pdf_path}")
            raise HTTPException(
                status_code=404, detail=f"PDF not found: {cleaned_path}"
            )

    # 将PDF路径存储到用户会话中，而不是全局变量
    pdf_path_str = str(full_pdf_path)
    if session_id:
        session_manager.set_current_pdf(session_id, pdf_path_str)
        session = get_current_user(session_id)
        username = session["username"] if session else "anonymous"
        logger.info(f"✅ Selected PDF for user {username}: {pdf_path_str}")
    else:
        logger.warning(f"⚠️ No session, PDF selection not saved: {pdf_path_str}")

    return {"success": True, "pdf_path": cleaned_path}


@app.get("/api/pdf/{path:path}")
async def get_pdf(path: str):

    cleaned_path = path.lstrip("/").replace("backend/data/", "data/")

    full_path = PROJECT_ROOT / cleaned_path

    if not full_path.exists():

        if full_path.suffix == ".PDF":
            fixed_path = full_path.with_suffix(".pdf")
            if fixed_path.exists():
                return FileResponse(str(fixed_path), media_type="application/pdf")

        fallback_path = BASE_DIR / cleaned_path
        if fallback_path.exists():
            return FileResponse(str(fallback_path), media_type="application/pdf")

        logger.error(f"❌ GET failed. Tried: {full_path}")
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(str(full_path), media_type="application/pdf")


@app.get("/api/languages")
async def get_languages():
    """获取支持的语言列表"""
    return LanguageHandler.dropdown_choices()


@app.get("/api/students")
async def get_students(session_id: Optional[str] = Cookie(None)):
    """获取所有学生信息"""
    try:
        students = database_store.list_users("student")
        logger.info("API /api/students: read students from %s (%d)", type(database_store).__name__, len(students))
        session = get_current_user(session_id)
        teacher_by_student: Dict[str, str] = {}
        try:
            for teacher in database_store.list_users("teacher"):
                teacher_username = str(teacher.get("username") or "").strip()
                if not teacher_username:
                    continue
                for link in database_store.list_teacher_students(teacher_username):
                    student_username = str(link.get("student_username") or "").strip()
                    if student_username:
                        teacher_by_student.setdefault(student_username, teacher_username)
        except Exception as exc:
            logger.warning("Failed to build teacher-student map: %s", exc)

        if session and session["user_type"] == "teacher":
            teacher_identifiers = [
                str(session.get("username") or "").strip(),
                str(session.get("user_id") or "").strip(),
            ]
            teacher_students: set[str] = set()
            for teacher_identifier in teacher_identifiers:
                if not teacher_identifier:
                    continue
                teacher_students.update(
                    str(item.get("student_username") or "").strip()
                    for item in database_store.list_teacher_students(teacher_identifier)
                    if str(item.get("student_username") or "").strip()
                )
                if teacher_students:
                    break
            students = [s for s in students if s.get("username") in teacher_students]

        if not (session and session["user_type"] == "admin"):
            for student in students:
                username = student.get("username")
                if username:
                    user_course_path = user_manager.get_user_course_path(username)
                    try:
                        with open(user_course_path, "r", encoding="utf-8") as f:
                            user_graph = json.load(f)
                            student["user_progress_data"] = user_graph
                    except FileNotFoundError:
                        # 用户课程文件不存在，跳过
                        pass
                    except Exception as e:
                        logging.warning(f"加载用户课程数据失败 {username}: {e}")

        return [_public_student_record(student, teacher_by_student) for student in students]
    except FileNotFoundError:
        return []


@app.get("/api/teachers")
async def get_teachers():
    """获取所有教师信息"""
    try:
        teachers = database_store.list_users("teacher")
        logger.info("API /api/teachers: read teachers from %s (%d)", type(database_store).__name__, len(teachers))
        return [_public_teacher_record(teacher) for teacher in teachers]
    except FileNotFoundError:
        return []


@app.get("/api/llm-logs")
async def get_llm_logs():
    """获取所有LLM调用日志"""
    try:
        logs = database_store.list_llm_logs()
        logger.info("API /api/llm-logs: read logs from %s (%d)", type(database_store).__name__, len(logs))
        return logs
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse llm_log.json")
        return []


@app.get("/api/learning-plans")
async def get_learning_plans(session_id: Optional[str] = Cookie(None)):
    """获取所有学习计划文件列表"""
    session = get_current_user(session_id)
    if session and session["user_type"] == "student":
        plans = database_store.list_learning_plans(session["username"], categories=["global", "user"])
        plans = [plan for plan in plans if "_path_" not in str(plan.get("filename", ""))]
        logger.info("API /api/learning-plans: read student plans from %s for %s (%d)", type(database_store).__name__, session["username"], len(plans))
        return plans
    else:
        plans = database_store.list_learning_plans(categories=["global", "user"])
        plans = [plan for plan in plans if "_path_" not in str(plan.get("filename", ""))]
        logger.info("API /api/learning-plans: read plans from %s (%d)", type(database_store).__name__, len(plans))
        return plans


def update_flags_recursive(node):
    """递归更新节点的flag，如果所有子节点都为1，则父节点也为1"""
    if "great-grandchildren" in node and node["great-grandchildren"]:
        all_complete = all(
            child.get("flag") == "1" for child in node["great-grandchildren"]
        )
        if all_complete:
            node["flag"] = "1"
            return True
        else:
            node["flag"] = "0"
            return False
    return node.get("flag") == "1"


def find_and_update_node(node, target_name):
    """递归查找并更新节点flag"""
    if node.get("name") == target_name:
        node["flag"] = "1"
        return True

    if "great-grandchildren" in node and node["great-grandchildren"]:
        for child in node["great-grandchildren"]:
            if find_and_update_node(child, target_name):

                all_complete = all(
                    c.get("flag") == "1" for c in node["great-grandchildren"]
                )
                if all_complete:
                    node["flag"] = "1"
                return True

    return False


@app.get("/api/learning-progress")
async def get_learning_progress(session_id: Optional[str] = Cookie(None)):
    """Return learning progress statistics from user's twin_profile_nodes."""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = session.get("username")
    if not username:
        return {"error": "Username not found in session"}
    
    # 获取课程ID
    course_id = _resolve_course_id_for_session(session)
    if not _student_can_access_published_course_base(session, course_id):
        raise HTTPException(status_code=404, detail="Published course base not found")
    cache_key = ("learning-progress", str(username), str(course_id))
    cached = _get_api_read_cache(cache_key)
    if cached is not None:
        return cached
    
    # Query course-node depth statistics from MySQL.
    try:
        with database_store._lock, database_store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT depth, COUNT(*) as count FROM course_nodes WHERE course_id = %s GROUP BY depth",
                    (course_id,),
                )
                depth_counts = cursor.fetchall()
                cursor.execute(
                    "SELECT node_id, depth FROM course_nodes WHERE course_id = %s",
                    (course_id,),
                )
                all_nodes = cursor.fetchall()
            depth_map = {row["depth"]: row["count"] for row in depth_counts}
            node_depth_map = {row["node_id"]: row["depth"] for row in all_nodes}
    except Exception as e:
        logger.warning("get_learning_progress: failed to query course_nodes: %s", e)
        depth_map = {}
        node_depth_map = {}
    
    # depth=0: 章节, depth=1: 小节, depth>=2: 知识点
    total_chapters = depth_map.get(0, 0)
    total_sections = depth_map.get(1, 0)
    total_points = sum(count for depth, count in depth_map.items() if depth >= 2)
    
    # 获取用户的学习进度数据
    user_nodes_map = database_store._load_twin_nodes_for_usernames([username])
    user_nodes = user_nodes_map.get(username, [])
    
    # 如果用户没有学习进度数据，返回0
    if not user_nodes:
        result = {
            "overall": {
                "progress": 0.0,
                "completed": 0,
                "total": total_chapters + total_sections + total_points,
            },
            "chapters": {
                "progress": 0.0,
                "completed": 0,
                "total": total_chapters,
            },
            "sections": {
                "progress": 0.0,
                "completed": 0,
                "total": total_sections,
            },
            "points": {
                "progress": 0.0,
                "completed": 0,
                "total": total_points,
            },
        }
        _set_api_read_cache(cache_key, result)
        return result
    
    # 统计各层级的完成情况
    completed_chapters = 0
    completed_sections = 0
    completed_points = 0
    
    for node in user_nodes:
        node_id = node.get("node_id")
        progress = node.get("progress", 0)
        depth = node_depth_map.get(node_id)
        
        if depth is None:
            continue
        
        # 进度>=100表示已完成
        if progress >= 100:
            if depth == 0:
                completed_chapters += 1
            elif depth == 1:
                completed_sections += 1
            else:  # depth >= 2
                completed_points += 1
    
    chapter_progress = (completed_chapters / total_chapters * 100) if total_chapters > 0 else 0
    section_progress = (completed_sections / total_sections * 100) if total_sections > 0 else 0
    point_progress = (completed_points / total_points * 100) if total_points > 0 else 0
    
    overall_progress = (chapter_progress + section_progress + point_progress) / 3

    result = {
        "overall": {
            "progress": round(overall_progress, 1),
            "completed": completed_chapters + completed_sections + completed_points,
            "total": total_chapters + total_sections + total_points,
        },
        "chapters": {
            "progress": round(chapter_progress, 1),
            "completed": completed_chapters,
            "total": total_chapters,
        },
        "sections": {
            "progress": round(section_progress, 1),
            "completed": completed_sections,
            "total": total_sections,
        },
        "points": {
            "progress": round(point_progress, 1),
            "completed": completed_points,
            "total": total_points,
        },
    }
    _set_api_read_cache(cache_key, result)
    return result


@app.get("/api/learning-streak")
async def get_learning_streak(session_id: Optional[str] = Cookie(None)):
    """获取用户的学习连续天数"""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = session.get("username")
    if not username:
        return {"error": "Username not found in session"}
    
    streak_service = LearningStreakService()
    streak_data = streak_service.get_streak(username)
    
    return streak_data


@app.get("/api/notifications/recent")
async def get_recent_notifications(
    limit: int = 10,
    session_id: Optional[str] = Cookie(None)
):
    """获取用户最近的通知"""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = session.get("username")
    if not username:
        return {"error": "Username not found in session"}
    
    notification_service = NotificationService()
    notifications = notification_service.get_recent_notifications(username, limit)
    
    return {
        "success": True,
        "notifications": notifications,
        "count": len(notifications)
    }


@app.post("/api/learning-activity")
async def log_learning_activity(
    data: dict,
    session_id: Optional[str] = Cookie(None)
):
    """记录用户学习活动"""
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    username = session.get("username")
    if not username:
        return {"success": False, "error": "Username not found in session"}
    
    activity_type = data.get("activity_type", "general")
    activity_details = data.get("activity_details")
    
    streak_service = LearningStreakService()
    success = streak_service.log_activity(username, activity_type, activity_details)
    
    if success:
        # 返回更新后的连续天数
        streak_data = streak_service.get_streak(username)
        return {
            "success": True,
            "streak": streak_data
        }
    else:
        return {"success": False, "error": "Failed to log activity"}


@app.post("/api/quiz/complete")
async def complete_quiz(data: QuizComplete, session_id: Optional[str] = Cookie(None)):
    """Complete quiz, update node flags, and persist through entity tables."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    pass_threshold = 0.8
    score_ratio = data.score / data.total if data.total > 0 else 0
    passed = score_ratio >= pass_threshold
    username_for_attempt = session["username"] if session else None
    user_id_for_attempt = session.get("user_id") if session else None

    try:
        database_store.record_quiz_attempt(
            username=username_for_attempt,
            user_id=user_id_for_attempt,
            course_id=course_id,
            node_id=data.node_name,
            score=float(data.score),
            total=float(data.total),
            passed=bool(passed),
            extra_payload={
                "score_ratio": score_ratio,
                "definition_id": data.definition_id,
                "definition_status": data.definition_status or "unknown",
                "definition_source": data.definition_source or "unknown",
                "evidence_policy": (
                    "published_quiz_definition"
                    if data.definition_status == "published" or data.definition_source == "published_definition"
                    else "generated_quiz_is_supplemental_evidence"
                ),
            },
        )
    except Exception as exc:
        logger.warning("quiz-attempt persist failed node=%s error=%s", data.node_name, exc)

    if not passed:
        return {
            "success": False,
            "message": f"Score {data.score}/{data.total} is below passing threshold",
            "passed": False,
        }

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if find_and_update_node(grandchild, data.node_name):
                updated = True

                all_grandchildren_complete = all(
                    gc.get("flag") == "1" for gc in child.get("grandchildren", [])
                )
                if all_grandchildren_complete:
                    child["flag"] = "1"
                break

        if updated:
            break

    if updated:

        all_children_complete = all(
            c.get("flag") == "1" for c in graph_data.get("children", [])
        )
        if all_children_complete:
            graph_data["flag"] = "1"

        course_name, source_path = _resolve_course_sync_meta(course_id, graph_data)
        database_store.sync_course_from_graph(
            course_id=course_id,
            course_name=course_name,
            graph_data=graph_data,
            source_path=source_path,
        )

        # Sync quiz score back into digital twin module.
        if session:
            try:
                from DigitalTwinModule.data_collector import DataCollector
                DataCollector().collect_quiz_score(
                    session["username"], data.node_name, data.score
                )
            except Exception as _twin_exc:
                logger.warning(f"digital twin quiz sync failed: {_twin_exc}")

            try:
                from fiveE.effectiveness_service import link_quiz_outcome
                link_quiz_outcome(
                    student_username=session["username"],
                    course_id=course_id,
                    node_id=data.node_name,
                    quiz_score_after=float(data.score),
                )
            except Exception as _fivee_exc:
                logger.warning("5E quiz outcome link failed: %s", _fivee_exc)
            
            # 记录测验活动
            try:
                streak_service = LearningStreakService()
                streak_service.log_activity(
                    session["username"], 
                    "quiz", 
                    f"完成测验: {data.node_name}, 得分: {data.score}/{data.total}"
                )
            except Exception as e:
                logger.warning(f"记录测验活动失败: {e}")

        return {
            "success": True,
            "message": "Quiz completed successfully",
            "passed": True,
        }

    raise HTTPException(status_code=404, detail=f"Node '{data.node_name}' not found")


@app.post("/api/llm-log")
async def log_llm_call(data: LLMLogRequest, session_id: Optional[str] = Cookie(None)):
    """Log LLM call from frontend or backend"""
    try:
        session = get_current_user(session_id)
        username = session["username"] if session else "anonymous"

        llm_logger = get_llm_logger()
        response_obj = type(
            "Response",
            (),
            {
                "content": data.response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", ""),
                "response_metadata": {
                    "id": data.response.get("id", ""),
                    "object": data.response.get("object", ""),
                    "created": data.response.get("created", 0),
                    "model": data.response.get("model", ""),
                    "finish_reason": data.response.get("choices", [{}])[0].get(
                        "finish_reason", ""
                    ),
                    "token_usage": data.response.get("usage", {}),
                    "system_fingerprint": data.response.get("system_fingerprint", ""),
                },
            },
        )()

        llm_logger.log_llm_call(
            messages=data.messages,
            response=response_obj,
            model=data.model,
            module=data.module,
            metadata=data.metadata,
            username=username,
        )
        return {"success": True, "message": "LLM call logged"}
    except Exception as e:
        logger.error(f"Error logging LLM call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log LLM call: {str(e)}")


@app.post("/api/ocr/extract")
async def extract_text_from_image(image: UploadFile = File(...)):
    """从上传的图片中提取文本"""
    try:
        image_data = await image.read()

        ocr_service = get_ocr_service()
        extracted_text = ocr_service.extract_text_from_image(image_data)

        logger.info(f"✅ OCR extraction successful, text length: {len(extracted_text)}")

        return {"success": True, "text": extracted_text, "message": "图片识别成功"}
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")


@app.get("/api/heatmap")
async def get_heatmap(session_id: Optional[str] = Cookie(None)):
    """获取课程热度数据：各知识点的班级平均掌握度 + 学习人数"""
    session = get_current_user(session_id)
    if not session or session["user_type"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可访问")

    node_scores: dict[str, list[float]] = {}
    try:
        twins = database_store.list_twin_profiles()
        logger.info("API /api/heatmap: read twin profiles from %s (%d)", type(database_store).__name__, len(twins))
    except Exception:
        twins = []
        logger.exception("API /api/heatmap: failed reading twin profiles from %s", type(database_store).__name__)

    allowed_students: set[str] = set()
    teacher_identifiers = [
        str(session.get("username") or "").strip(),
        str(session.get("user_id") or "").strip(),
    ]
    for teacher_identifier in teacher_identifiers:
        if not teacher_identifier:
            continue
        try:
            allowed_students.update(
                str(item.get("student_username") or "").strip()
                for item in database_store.list_teacher_students(teacher_identifier)
                if str(item.get("student_username") or "").strip()
            )
        except Exception:
            logger.exception("API /api/heatmap: failed reading authorized students for %s", teacher_identifier)
        if allowed_students:
            break
    if not allowed_students:
        return {"nodes": []}

    for twin in twins:
        if str(twin.get("username") or "").strip() not in allowed_students:
            continue
        for node in twin.get("knowledge_nodes", []):
            nid = node.get("node_id", "")
            score = node.get("mastery_score", 0)
            if nid:
                node_scores.setdefault(nid, []).append(score)

    result = []
    for node_id, scores in node_scores.items():
        result.append({
            "node_id": node_id,
            "avg_mastery": round(sum(scores) / len(scores), 1),
            "student_count": len(scores),
        })
    result.sort(key=lambda x: x["avg_mastery"])
    return {"nodes": result}


@app.get("/{full_path:path}")
async def frontend_spa(full_path: str):
    if full_path.startswith(("api/", "static/", "data/", "assets/")):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = FRONTEND_DIST_DIR / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return frontend_index_response()


if __name__ == "__main__":
    import uvicorn
    print("INFO:     访问地址：http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

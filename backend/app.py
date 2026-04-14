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
from typing import List, Optional, Dict, Any
import json
import os
import shutil
import logging
import base64
import math
import socket
import httpx
from datetime import date, timedelta, datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse

# 关闭 chromadb 遥测，避免启动时出现 posthog 错误日志
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

from DashboardModule.dashboard_api import router as dashboard_router
from DigitalTwinModule.digital_twin_api import router as twin_router
from IndustryIntelligenceModule.api import router as industry_intelligence_router
from HomeworkModule.api import router as homework_router
from AgentModule.qa_agent import QA_Agent
from QuizModule.quiz_agent import Quiz_Agent
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
from tools.session_manager import get_session_manager
from DatabaseModule.sqlite_store import get_sqlite_store
from DatabaseModule.migrate_json_to_sqlite import migrate_all

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

quiz_summary_model_name = os.environ.get("model_name")
quiz_summary_base_url = os.environ.get("base_url")
quiz_summary_api_key = os.environ.get("api_key")

quiz_summary_llm = None
if quiz_summary_model_name and quiz_summary_base_url and quiz_summary_api_key:
    try:
        quiz_summary_llm = ChatOpenAI(
            model=quiz_summary_model_name,
            temperature=0,
            base_url=quiz_summary_base_url,
            api_key=quiz_summary_api_key,
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to initialize quiz summary llm: %s", exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(twin_router)
app.include_router(industry_intelligence_router)
app.include_router(homework_router)

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
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "backend" else BASE_DIR
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend-vue" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
# 注意：CURRENT_NODE 和 CURRENT_PDF_PATH 已移至 session_manager 中按用户存储

user_manager = UserManager()
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()

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
        "Frontend bundle not found. Please run npm run build in frontend-vue.",
        status_code=503,
    )


app.mount("/static", LegacyAwareStaticFiles(directory="backend/static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")


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
            await asyncio.sleep(600)
            try:
                usernames = [
                    str(profile.get("user_id"))
                    for profile in sqlite_store.list_twin_profiles()
                    if profile.get("user_id") is not None
                ]
            except Exception:
                usernames = []
            for username in usernames:
                try:
                    collector.collect_all(username)
                except Exception as exc:
                    logger.warning(f"⚠️ 定时采集失败 [{username}]: {exc}")

    asyncio.create_task(_collect_all_loop())
    try:
        existing_user_count = (
            len(sqlite_store.list_users("student"))
            + len(sqlite_store.list_users("teacher"))
            + len(sqlite_store.list_users("admin"))
        )
        if existing_user_count == 0:
            logger.info("SQLite migration summary: %s", migrate_all())
        else:
            logger.info("SQLite migration skipped: users already present (%s)", existing_user_count)
    except Exception as exc:
        logger.warning("SQLite migration skipped: %s", exc)

def get_current_user(
    session_id: Optional[str] = Cookie(None),
) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    return session_manager.get_session(session_id)


def _resolve_course_id_for_session(session: Optional[Dict[str, Any]]) -> str:
    if session and session.get("user_type") == "student":
        username = str(session.get("username") or "").strip()
        if username:
            return f"course_user_{username}"
    return "course_big_data"


def _resolve_course_sync_meta(course_id: str, graph_data: Dict[str, Any]) -> tuple[str, str]:
    course_name = str(graph_data.get("name") or course_id or "default_course")
    source_path = f"entity://courses/{course_id}"
    return course_name, source_path


def _load_course_graph_entity_only(
    session: Optional[Dict[str, Any]],
) -> tuple[str, Dict[str, Any]]:
    course_id = _resolve_course_id_for_session(session)
    payload = sqlite_store.get_course_payload(course_id)
    if isinstance(payload, dict):
        return course_id, payload
    return course_id, {}


class ChatMessage(BaseModel):
    message: str
    history: List[List[str]] = []
    lang_choice: str = "auto"


class QuizStart(BaseModel):
    subject: str
    lang_choice: str = "auto"


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


class PDFSelection(BaseModel):
    pdf_path: str


class QuizComplete(BaseModel):
    node_name: str
    score: int
    total: int


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
        session_id = session_manager.create_session(user.get("username", student_id), "student", user)
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
        session_id = session_manager.create_session(user.get("username", teacher_id), "teacher", user)
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
        session_id = session_manager.create_session(user.get("username", admin_username), "admin", user)
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
    session_id = session_manager.create_session(canonical_username, user_type, user)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,
        path="/",
    )
    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "username": canonical_username,
            "user_id": user.get("user_id"),
            "login_id": user.get("login_id"),
            "user_type": user_type,
            "user_data": user,
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
        "user_data": session["user_data"],
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
            session["user_data"].update(updates)
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

    course_id = sqlite_store.get_course_id_by_resource_path(pdf_path) or "course_big_data"
    graph_data = sqlite_store.get_course_payload(course_id) or {}
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

    course_id = sqlite_store.get_course_id_by_resource_path(pdf_path) or "course_big_data"
    graph_data = sqlite_store.get_course_payload(course_id) or {}
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
    }

    first_q = questions[0]
    return {"question": first_q, "state": state, "used_retriever": used_retriever}


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


@app.get("/api/knowledge-graph")
async def get_knowledge_graph(session_id: Optional[str] = Cookie(None)):
    """Return knowledge graph payload (entity-only)."""
    session = get_current_user(session_id)
    _, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return graph_data


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
async def get_learning_nodes(session_id: Optional[str] = Cookie(None)):
    """Return learning node names (entity-only)."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return sqlite_store.list_learning_nodes_for_course(course_id)


@app.post("/api/node/resources")
async def get_node_resources(
    data: NodeSelection, session_id: Optional[str] = Cookie(None)
):
    """Return resource paths for a node (entity-only)."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return sqlite_store.list_resources_for_node_name(course_id, data.node_name)


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
        sqlite_store.sync_course_from_graph(
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
    """Delete one resource from a node and persist via entity tables."""
    session = get_current_user(session_id)
    course_id, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if grandchild.get("name") == data.node_name:
                resources = grandchild.get("resource_path", [])
                if isinstance(resources, str):
                    resources = [resources] if resources else []
                    grandchild["resource_path"] = resources
                if 0 <= data.resource_index < len(resources):
                    deleted_resource = resources.pop(data.resource_index)
                    logger.info(
                        f"Deleted resource: {deleted_resource} from node: {data.node_name}"
                    )
                    updated = True
                    break

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == data.node_name:
                    resources = great_grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                        great_grandchild["resource_path"] = resources
                    if 0 <= data.resource_index < len(resources):
                        deleted_resource = resources.pop(data.resource_index)
                        logger.info(
                            f"Deleted resource: {deleted_resource} from node: {data.node_name}"
                        )
                        updated = True
                        break
            if updated:
                break
        if updated:
            break

    if updated:
        course_name, source_path = _resolve_course_sync_meta(course_id, graph_data)
        sqlite_store.sync_course_from_graph(
            course_id=course_id,
            course_name=course_name,
            graph_data=graph_data,
            source_path=source_path,
        )
        return {"success": True, "message": "Resource deleted successfully"}

    raise HTTPException(
        status_code=404,
        detail=f"Node '{data.node_name}' not found or invalid resource index",
    )


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
        students = sqlite_store.list_users("student")
        logger.info("API /api/students: read students from SQLite (%d)", len(students))

        session = get_current_user(session_id)
        if session and session["user_type"] == "teacher":
            teacher_username = str(session.get("user_id") or "")
            teacher_students = {
                item.get("student_username")
                for item in sqlite_store.list_teacher_students(teacher_username)
                if item.get("student_username")
            }
            if teacher_students:
                students = [s for s in students if s.get("username") in teacher_students]

        for student in students:
            username = student.get("username")
            if username:
                user_course_path = user_manager.get_user_course_path(username)
                try:
                    with open(user_course_path, "r", encoding="utf-8") as f:
                        user_graph = json.load(f)
                        student["user_progress_data"] = user_graph
                except:
                    pass

        return students
    except FileNotFoundError:
        return []


@app.get("/api/teachers")
async def get_teachers():
    """获取所有教师信息"""
    try:
        teachers = sqlite_store.list_users("teacher")
        logger.info("API /api/teachers: read teachers from SQLite (%d)", len(teachers))
        return teachers
    except FileNotFoundError:
        return []


@app.get("/api/llm-logs")
async def get_llm_logs():
    """获取所有LLM调用日志"""
    try:
        logs = sqlite_store.list_llm_logs()
        logger.info("API /api/llm-logs: read logs from SQLite (%d)", len(logs))
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
        plans = sqlite_store.list_learning_plans(session["username"], categories=["global", "user"])
        plans = [plan for plan in plans if "_path_" not in str(plan.get("filename", ""))]
        logger.info("API /api/learning-plans: read student plans from SQLite for %s (%d)", session["username"], len(plans))
        return plans
    else:
        plans = sqlite_store.list_learning_plans(categories=["global", "user"])
        plans = [plan for plan in plans if "_path_" not in str(plan.get("filename", ""))]
        logger.info("API /api/learning-plans: read plans from SQLite (%d)", len(plans))
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
    """Return learning progress statistics from entity-stored graph payload."""
    session = get_current_user(session_id)
    _, graph_data = _load_course_graph_entity_only(session)
    if not graph_data:
        return {"error": "Knowledge graph not found"}

    children = graph_data.get("children", [])

    total_chapters = len(children)
    completed_chapters = sum(1 for c in children if c.get("flag") == "1")
    chapter_progress = (
        (completed_chapters / total_chapters * 100) if total_chapters > 0 else 0
    )

    total_sections = 0
    completed_sections = 0
    for child in children:
        grandchildren = child.get("grandchildren", [])
        total_sections += len(grandchildren)
        completed_sections += sum(1 for gc in grandchildren if gc.get("flag") == "1")
    section_progress = (
        (completed_sections / total_sections * 100) if total_sections > 0 else 0
    )

    total_points = 0
    completed_points = 0

    def count_knowledge_points(node):
        nonlocal total_points, completed_points
        great_grandchildren = node.get("great-grandchildren", [])
        if great_grandchildren:
            for ggc in great_grandchildren:
                total_points += 1
                if ggc.get("flag") == "1":
                    completed_points += 1
                count_knowledge_points(ggc)

    for child in children:
        for grandchild in child.get("grandchildren", []):
            count_knowledge_points(grandchild)

    point_progress = (completed_points / total_points * 100) if total_points > 0 else 0

    overall_progress = (chapter_progress + section_progress + point_progress) / 3

    return {
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
        sqlite_store.record_quiz_attempt(
            username=username_for_attempt,
            user_id=user_id_for_attempt,
            course_id=course_id,
            node_id=data.node_name,
            score=float(data.score),
            total=float(data.total),
            passed=bool(passed),
            extra_payload={"score_ratio": score_ratio},
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
        sqlite_store.sync_course_from_graph(
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
        twins = sqlite_store.list_twin_profiles()
        logger.info("API /api/heatmap: read twin profiles from SQLite (%d)", len(twins))
    except Exception:
        twins = []
        logger.exception("API /api/heatmap: failed reading twin profiles from SQLite")

    for twin in twins:
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

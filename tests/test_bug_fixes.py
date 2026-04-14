"""
针对 bug 修复的自测用例，不依赖外部服务（数据库、LLM、网络）。
覆盖以下修复点：
  1. 5E/session.py       — load_dotenv 顺序 & 环境变量 None 检查
  2. 5E/agents/entrance  — is_initial() 缺少 await（逻辑验证）
  3. 5E/models/          — OrchestratorResponse 新增 agent_instruction 字段
  4. DashboardModule     — teacher_username 使用 username 而非 user_id
"""

import ast
import asyncio
import importlib.util
import os
import pathlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH_5E = os.path.join(ROOT, "5E")


def _mock_google_modules():
    """在 sys.modules 中注入 google.adk / google.genai 的 mock，避免 ImportError"""
    mocks = {
        "google": MagicMock(),
        "google.adk": MagicMock(),
        "google.adk.agents": MagicMock(),
        "google.adk.events": MagicMock(),
        "google.adk.runners": MagicMock(),
        "google.adk.sessions": MagicMock(),
        "google.adk.sessions.database_session_service": MagicMock(),
        "google.genai": MagicMock(),
        "google.genai.types": MagicMock(),
        "sqlalchemy": MagicMock(),
        "sqlalchemy.ext": MagicMock(),
        "sqlalchemy.ext.asyncio": MagicMock(),
        "sqlalchemy.orm": MagicMock(),
    }
    for name, mock in mocks.items():
        if name not in sys.modules:
            sys.modules[name] = mock
    return mocks


# =============================================================================
# 1. session.py — load_dotenv 顺序 & None 检查
# =============================================================================
class TestSessionEnvOrder(unittest.TestCase):

    def _import_session_module(self, env: dict):
        """在指定环境变量下重新导入 session 模块（完全隔离）"""
        _mock_google_modules()

        # 构造假的 DatabaseSessionService
        fake_dss_cls = MagicMock(return_value=MagicMock())
        sys.modules["google.adk.sessions.database_session_service"].DatabaseSessionService = fake_dss_cls

        # 构造假的 sqlalchemy async engine
        fake_engine = MagicMock()
        sys.modules["sqlalchemy.ext.asyncio"].create_async_engine = MagicMock(return_value=fake_engine)
        sys.modules["sqlalchemy.ext.asyncio"].async_sessionmaker = MagicMock()
        sys.modules["sqlalchemy.ext.asyncio"].AsyncSession = MagicMock()

        # 移除缓存
        sys.modules.pop("session", None)

        # 把 5E 目录加入 path
        if PATH_5E not in sys.path:
            sys.path.insert(0, PATH_5E)

        with patch.dict(os.environ, env, clear=True):
            # dotenv 的 load_dotenv 不做任何事（避免读取真实 .env）
            with patch("dotenv.load_dotenv", return_value=None):
                spec = importlib.util.spec_from_file_location(
                    "session", os.path.join(PATH_5E, "session.py")
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod

    def test_missing_session_db_url_raises(self):
        """SESSION_DB_URL 未设置时应抛出 RuntimeError"""
        with self.assertRaises(RuntimeError) as ctx:
            self._import_session_module({"DATABASE_URL": "sqlite+aiosqlite:///test.db"})
        self.assertIn("SESSION_DB_URL", str(ctx.exception))

    def test_missing_database_url_raises(self):
        """DATABASE_URL 未设置时应抛出 RuntimeError"""
        with self.assertRaises(RuntimeError) as ctx:
            self._import_session_module({"SESSION_DB_URL": "mysql+aiomysql://x:x@localhost/db"})
        self.assertIn("DATABASE_URL", str(ctx.exception))

    def test_both_env_vars_set_ok(self):
        """两个环境变量都设置时不应抛出异常"""
        try:
            self._import_session_module({
                "SESSION_DB_URL": "mysql+aiomysql://x:x@localhost/db",
                "DATABASE_URL": "sqlite+aiosqlite:///test.db",
            })
        except RuntimeError as e:
            self.fail(f"不应抛出 RuntimeError，但抛出了: {e}")

    def test_session_service_uses_env_not_hardcoded(self):
        """session.py 源码中不应再出现硬编码的 root:password"""
        src = pathlib.Path(PATH_5E) / "session.py"
        content = src.read_text(encoding="utf-8")
        self.assertNotIn("root:password", content, "session.py 中仍有硬编码密码")
        self.assertNotIn("127.0.0.1:3306", content, "session.py 中仍有硬编码地址")


# =============================================================================
# 2. entrance.py — is_initial 必须被 await（源码静态分析）
# =============================================================================
class TestIsInitialAwait(unittest.TestCase):
    """用 AST 静态分析验证 _run_async_implementation 中 is_initial 有 await"""

    def _parse_entrance(self):
        src = pathlib.Path(PATH_5E) / "agents" / "entrance.py"
        return ast.parse(src.read_text(encoding="utf-8"))

    def test_is_initial_is_defined_as_async(self):
        """is_initial 必须是 async def"""
        tree = self._parse_entrance()
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "is_initial":
                return  # 找到了
        self.fail("is_initial 不是 async def")

    def test_run_async_implementation_awaits_is_initial(self):
        """_run_async_implementation 中调用 is_initial 时必须有 await"""
        tree = self._parse_entrance()
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) \
                    and node.name == "_run_async_implementation":
                func_src = ast.unparse(node)
                # 检查 await is_initial(...) 存在
                self.assertIn("await is_initial", func_src,
                              "_run_async_implementation 中 is_initial 缺少 await")
                return
        self.fail("未找到 _run_async_implementation 函数")

    def test_get_lesson_description_returns_str_not_none(self):
        """get_lesson_description 函数体不应只有 pass（会返回 None）"""
        tree = self._parse_entrance()
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_lesson_description":
                body = node.body
                # 只有一个 Pass 节点 => 返回 None
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    self.fail("get_lesson_description 仍是空函数（pass），会返回 None")
                return
        self.fail("未找到 get_lesson_description 函数")


# =============================================================================
# 3. OrchestratorResponse — agent_instruction 字段
# =============================================================================
class TestOrchestratorResponse(unittest.TestCase):

    def _load_model(self):
        spec = importlib.util.spec_from_file_location(
            "orchestrator_response",
            os.path.join(PATH_5E, "models", "orchestrator_response.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.OrchestratorResponse

    def test_has_agent_instruction_field(self):
        OrchestratorResponse = self._load_model()
        self.assertIn("agent_instruction", OrchestratorResponse.model_fields)

    def test_default_values(self):
        OrchestratorResponse = self._load_model()
        obj = OrchestratorResponse()
        self.assertEqual(obj.target_agent, "none")
        self.assertEqual(obj.agent_instruction, "")

    def test_parse_full_json(self):
        OrchestratorResponse = self._load_model()
        obj = OrchestratorResponse.model_validate_json(
            '{"target_agent": "engagement", "agent_instruction": "引导学生"}'
        )
        self.assertEqual(obj.target_agent, "engagement")
        self.assertEqual(obj.agent_instruction, "引导学生")

    def test_parse_partial_json_uses_default(self):
        OrchestratorResponse = self._load_model()
        obj = OrchestratorResponse.model_validate_json('{"target_agent": "exploration"}')
        self.assertEqual(obj.target_agent, "exploration")
        self.assertEqual(obj.agent_instruction, "")


# =============================================================================
# 4. DashboardModule — teacher_username 使用 session["username"]（AST 分析）
# =============================================================================
class TestDashboardTeacherUsername(unittest.TestCase):

    def _parse_dashboard(self):
        src = pathlib.Path(ROOT) / "DashboardModule" / "dashboard_api.py"
        return ast.parse(src.read_text(encoding="utf-8"))

    def _get_func_src(self, tree, name: str) -> str:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.unparse(node)
        self.fail(f"未找到函数: {name}")

    def test_get_teacher_twin_uses_username_not_user_id(self):
        tree = self._parse_dashboard()
        src = self._get_func_src(tree, "get_teacher_twin")
        self.assertNotIn("get('user_id')", src)
        self.assertNotIn('get("user_id")', src)
        self.assertIn("username", src)

    def test_ai_suggestions_uses_username_not_user_id(self):
        tree = self._parse_dashboard()
        src = self._get_func_src(tree, "generate_teacher_twin_ai_suggestions")
        self.assertNotIn("get('user_id')", src)
        self.assertNotIn('get("user_id")', src)
        self.assertIn("username", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)

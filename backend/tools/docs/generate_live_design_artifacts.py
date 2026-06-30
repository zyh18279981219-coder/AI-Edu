from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
for item in (ROOT, BACKEND):
    value = str(item)
    if value not in sys.path:
        sys.path.insert(0, value)

from DatabaseModule.database_factory import DatabaseFactory  # noqa: E402
from tools.env_loader import load_project_env  # noqa: E402


OUT_DIR = ROOT / "docs" / "detailed-design" / "generated"
REQ_DOC = ROOT / "docs" / "requirements" / "AI-Education需求分析文档-图件美化版-2026-06-28.docx"
DETAIL_DOC = ROOT / "docs" / "detailed-design" / "AI-Education系统详细设计说明书-开发基线版-2026-06-28.md"


MODULES: dict[str, dict[str, Any]] = {
    "课程数字孪生与课程资源": {
        "requirement": "3.1",
        "path_prefixes": ["/api/course-digital-twin", "/api/knowledge-graph", "/api/upload"],
        "tables": ["courses", "course_metadata", "course_nodes", "course_node_relations", "resources", "resource_learning_events"],
        "note": "维护课程底座、资源候选、发布版本和课程运行评估；下游只读已发布课程底座。",
    },
    "学生学习空间": {
        "requirement": "3.2",
        "path_prefixes": ["/api/learning-nodes", "/api/learning-progress", "/api/learning-streak", "/api/learning-plans", "/api/notifications", "/api/graph-visualization", "/api/pdf", "/api/node/resources"],
        "tables": ["sessions", "user_activity_log", "user_states", "resource_learning_events", "learning_plans"],
        "note": "承载学生学习入口，展示课程、资源、作业、路径和画像摘要，并回传学习行为。",
    },
    "在线测验": {
        "requirement": "3.3",
        "path_prefixes": ["/api/quiz"],
        "tables": ["quiz_attempts"],
        "note": "围绕知识点生成/发布/提交测验，测验结果作为叶子知识点强证据。",
    },
    "学生数字孪生": {
        "requirement": "3.4",
        "path_prefixes": ["/api/digital-twin/student-profile", "/api/digital-twin/profile", "/api/digital-twin/collect", "/api/digital-twin/quiz-score", "/api/digital-twin/student-course-profile", "/api/homework/twin"],
        "tables": ["twin_profiles", "twin_profile_nodes", "twin_history", "resource_learning_events", "homework_assignment_knowledge_points"],
        "note": "维护学生画像状态、掌握度、章节实践能力、风险和能力达成；不直接解释根因或生成路径。",
    },
    "诊断智能体": {
        "requirement": "3.5",
        "path_prefixes": ["/api/digital-twin/diagnosis", "/api/digital-twin/diagnosis-corrections"],
        "tables": ["diagnosis_reports", "diagnosis_corrections", "twin_profile_nodes", "quiz_attempts", "homework_submissions"],
        "note": "解释薄弱原因、证据等级和建议动作；证据不足时只提示补证，不强行诊断。",
    },
    "个性化学习路径": {
        "requirement": "3.6",
        "path_prefixes": ["/api/digital-twin/path", "/api/learning-plan"],
        "tables": ["learning_plans", "learning_plan_nodes", "learning_path_node_status"],
        "note": "基于画像和诊断生成路径版本；正式节点必须来自已发布课程图谱。",
    },
    "5E 教学智能体": {
        "requirement": "3.7",
        "path_prefixes": ["/api/5e"],
        "tables": ["events", "user_interaction", "fivee_effectiveness_records"],
        "note": "提供 5E 阶段化学习引导和 EES 有效度，作为过程性辅助证据。",
    },
    "作业与实践评测": {
        "requirement": "3.8",
        "path_prefixes": ["/api/homework"],
        "tables": ["homework_assignments", "homework_submissions", "homework_assignment_knowledge_points", "homework_grading_events"],
        "note": "支持四类作业、提交、批改、教师终审和证据回流；覆盖知识点必须教师确认。",
    },
    "教师智能干预任务包": {
        "requirement": "3.9",
        "path_prefixes": ["/api/intervention"],
        "tables": ["intervention_packages", "intervention_package_items", "intervention_package_student_records", "teacher_intervention_events"],
        "note": "读取诊断结果生成线上任务包草稿，教师审核后下发，学生完成后回流。",
    },
    "教师看板与教师数字孪生": {
        "requirement": "3.10",
        "path_prefixes": ["/api/dashboard", "/api/digital-twin/teacher"],
        "tables": ["teaching_interaction_events", "teaching_research_events", "homework_grading_events", "teacher_intervention_events", "user_activity_log", "llm_logs"],
        "note": "展示班级学情、风险和教师六维画像；AI 建议必须教师手动触发。",
    },
    "教学互动": {
        "requirement": "3.11",
        "path_prefixes": ["/api/teaching-interaction", "/api/teaching-research"],
        "tables": ["teaching_announcements", "teaching_discussion_topics", "teaching_discussion_posts", "teaching_research_records", "teaching_interaction_events", "teaching_research_events"],
        "note": "人工教学沟通和教研记录层；教师行为稳定回流教师数字孪生。",
    },
    "行业情报与能力对接": {
        "requirement": "3.12",
        "path_prefixes": ["/api/industry-intelligence", "/api/course-digital-twin/positions", "/api/course-digital-twin/abilities", "/api/course-digital-twin/ability-mappings"],
        "tables": ["career_positions", "career_abilities", "course_ability_mappings"],
        "note": "检索岗位、提取能力候选，教师确认后交课程数字孪生发布。",
    },
}

PATH_MODULE_OVERRIDES = {
    "/api/learning-plan": "个性化学习路径",
    "/api/learning-plan/from-quiz": "个性化学习路径",
    "/api/resource-learning/events": "学习行为证据支撑接口",
    "/api/resource-learning/summary": "学习行为证据支撑接口",
    "/api/delete-resource": "资源文件与课程运行支撑接口",
    "/api/recycle-bin": "资源文件与课程运行支撑接口",
    "/api/restore-resource": "资源文件与课程运行支撑接口",
    "/api/clear-course-cache": "资源文件与课程运行支撑接口",
    "/api/heatmap": "教师看板与教师数字孪生",
    "/api/students": "用户、权限与会话",
    "/api/teachers": "用户、权限与会话",
}

SUPPORT_MODULES = {
    "用户、权限与会话",
    "学习行为证据支撑接口",
    "资源文件与课程运行支撑接口",
    "LLM、OCR 与日志支撑接口",
    "前端页面与历史兼容接口",
    "通用/历史接口",
}

INDUSTRY_COURSE_PATH_MARKERS = (
    "/api/course-digital-twin/positions",
    "/api/course-digital-twin/abilities",
    "/api/course-digital-twin/ability-mappings",
)


TABLE_DESCRIPTIONS = {
    "users": "用户主表，保存学生、教师、管理员账号及登录标识。",
    "user_profiles": "用户扩展资料。",
    "teacher_student_links": "教师与学生关系。",
    "sessions": "登录会话与学习上下文。",
    "user_states": "运行态键值状态。",
    "llm_logs": "大模型调用日志。",
    "user_activity_log": "用户活动日志。",
    "courses": "课程数字孪生课程主表。",
    "course_metadata": "课程扩展结构数据。",
    "course_nodes": "课程章节、小节、叶子知识点节点。",
    "course_node_relations": "课程节点关系扩展表。",
    "resources": "课程资源和外部资源绑定表。",
    "resource_learning_events": "资源学习事件表。",
    "career_positions": "课程目标岗位配置。",
    "career_abilities": "职业能力候选。",
    "course_ability_mappings": "职业能力与叶子知识点支撑关系。",
    "twin_profiles": "学生数字孪生总画像。",
    "twin_profile_nodes": "学生知识点画像节点。",
    "twin_history": "学生画像历史快照。",
    "quiz_attempts": "在线测验作答记录。",
    "diagnosis_reports": "诊断报告。",
    "diagnosis_corrections": "诊断人工修正记录。",
    "learning_plans": "学习计划和个性化路径版本主表。",
    "learning_plan_nodes": "学习计划/路径节点与载荷。",
    "learning_path_node_status": "路径节点执行状态。",
    "homework_assignments": "作业主表。",
    "homework_submissions": "作业提交与评分结果。",
    "homework_assignment_knowledge_points": "作业覆盖知识点确认表。",
    "homework_grading_events": "作业批改行为事件。",
    "intervention_packages": "教师干预任务包主表。",
    "intervention_package_items": "干预任务包任务项。",
    "intervention_package_student_records": "学生干预任务包执行记录。",
    "teacher_intervention_events": "教师干预事件。",
    "teaching_announcements": "教学公告。",
    "teaching_discussion_topics": "教学讨论主题。",
    "teaching_discussion_posts": "教学讨论回复。",
    "teaching_research_records": "教研记录。",
    "teaching_interaction_events": "教学互动事件。",
    "teaching_research_events": "教研行为事件。",
    "events": "5E 底层事件记录。",
    "user_interaction": "5E 或学习交互统计记录。",
    "fivee_effectiveness_records": "5E 引导有效性记录。",
}


def load_openapi_operations() -> list[dict[str, Any]]:
    from app import app  # noqa: WPS433

    schema = app.openapi()
    operations: list[dict[str, Any]] = []
    for path, methods in sorted(schema.get("paths", {}).items()):
        for method, spec in sorted(methods.items()):
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            operations.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": spec.get("summary") or "",
                    "tags": spec.get("tags") or [],
                    "operation_id": spec.get("operationId") or "",
                    "request_body": _request_body_summary(spec),
                    "responses": ",".join(sorted((spec.get("responses") or {}).keys())),
                }
            )
    return operations


def _request_body_summary(spec: dict[str, Any]) -> str:
    body = spec.get("requestBody")
    if not isinstance(body, dict):
        return ""
    content = body.get("content")
    if not isinstance(content, dict):
        return "requestBody"
    return ",".join(content.keys())


def load_database_schema() -> dict[str, Any]:
    load_project_env()
    DatabaseFactory.reset_instance()
    store = DatabaseFactory.get_store()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db")
            database = cursor.fetchone()["db"]
            cursor.execute("SHOW FULL TABLES WHERE Table_type='BASE TABLE'")
            tables = [list(row.values())[0] for row in cursor.fetchall()]
            result: dict[str, Any] = {"database": database, "tables": {}}
            for table in sorted(tables):
                cursor.execute(f"SELECT COUNT(*) AS n FROM `{table}`")
                row_count = int(cursor.fetchone()["n"])
                cursor.execute(f"SHOW FULL COLUMNS FROM `{table}`")
                columns = [dict(row) for row in cursor.fetchall()]
                cursor.execute(f"SHOW INDEX FROM `{table}`")
                indexes = [dict(row) for row in cursor.fetchall()]
                result["tables"][table] = {
                    "row_count": row_count,
                    "columns": columns,
                    "indexes": indexes,
                }
    return result


def classify_operation(operation: dict[str, Any]) -> str:
    path = operation["path"]
    if path in PATH_MODULE_OVERRIDES:
        return PATH_MODULE_OVERRIDES[path]
    if path in {"/api/chat", "/api/summary", "/api/health/llm", "/api/llm-log", "/api/llm-logs", "/api/ocr/extract", "/api/languages"}:
        return "LLM、OCR 与日志支撑接口"
    if path in {"/", "/teacher.html", "/admin.html", "/{full_path}"}:
        return "前端页面与历史兼容接口"
    if path.startswith(INDUSTRY_COURSE_PATH_MARKERS):
        return "行业情报与能力对接"
    if path.startswith("/api/course-digital-twin/{course_id}/positions") or path.startswith(
        "/api/course-digital-twin/{course_id}/abilities"
    ) or path.startswith("/api/course-digital-twin/{course_id}/ability-mappings"):
        return "行业情报与能力对接"
    for module, config in MODULES.items():
        if any(path.startswith(prefix) for prefix in config["path_prefixes"]):
            return module
    if path.startswith("/api/auth") or path in {
        "/api/current-user",
        "/api/logout",
        "/api/register",
        "/api/update-profile",
        "/api/change-password",
    } or path.startswith("/login/"):
        return "用户、权限与会话"
    return "通用/历史接口"


def classify_table(table: str, include_consumers: bool = True) -> list[str]:
    result = []
    for module, config in MODULES.items():
        if table in config["tables"]:
            result.append(module)
    if include_consumers:
        result.extend(TABLE_CONSUMERS.get(table, []))
    return _unique(result) or ["通用/支撑表"]


TABLE_CONSUMERS = {
    "resource_learning_events": ["学习行为证据支撑接口"],
    "homework_assignment_knowledge_points": ["诊断智能体"],
    "homework_submissions": ["学生数字孪生"],
    "quiz_attempts": ["学生数字孪生", "教师看板与教师数字孪生"],
    "course_ability_mappings": ["课程数字孪生与课程资源", "学生数字孪生"],
    "career_positions": ["课程数字孪生与课程资源"],
    "career_abilities": ["课程数字孪生与课程资源"],
    "llm_logs": ["LLM、OCR 与日志支撑接口"],
    "user_activity_log": ["用户、权限与会话"],
}


TABLE_PRIMARY_MODULE = {
    "llm_logs": "LLM、OCR 与日志支撑接口",
    "homework_assignment_knowledge_points": "作业与实践评测",
    "homework_submissions": "作业与实践评测",
    "homework_grading_events": "教师看板与教师数字孪生证据事件",
    "teaching_interaction_events": "教师看板与教师数字孪生证据事件",
    "teaching_research_events": "教师看板与教师数字孪生证据事件",
    "teacher_intervention_events": "教师看板与教师数字孪生证据事件",
    "user_activity_log": "通用活动支撑",
    "events": "5E 教学智能体底层事件",
    "user_interaction": "5E 教学智能体交互统计",
    "fivee_effectiveness_records": "5E 教学智能体有效性记录",
}


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        cleaned = [str(item).replace("\n", " ").replace("|", "\\|") for item in row]
        lines.append("| " + " | ".join(cleaned) + " |")
    return lines


def write_prompt_and_plan() -> Path:
    path = OUT_DIR / "设计文档重构提示词与执行计划.md"
    lines = [
        "# 设计文档重构提示词与执行计划",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## 可直接交给其他 AI 的提示词",
        "",
        "```text",
        "你正在接手 AI-Education2 项目的设计文档重构。请以当前代码和当前数据库为准，而不是凭需求文档臆写。",
        "",
        "工作目录：D:\\pythonFile\\AI-Education2",
        f"需求基准：{REQ_DOC}",
        f"现有详细设计底稿：{DETAIL_DOC}",
        "生成材料目录：D:\\pythonFile\\AI-Education2\\docs\\detailed-design\\generated",
        "",
        "目标：把详细设计文档改成能够对应当前 FastAPI 接口和当前 MySQL 数据库的版本。",
        "",
        "执行顺序：先看 generated 目录下的机器生成材料，再看现有详细设计；先修 Markdown 候选稿，不要直接覆盖 Word；所有模块结论都要能回指到接口或数据库表。",
        "",
        "硬性要求：",
        "1. 接口章节必须以 FastAPI app.openapi() 生成结果为准，不能只写核心接口。",
        "2. 数据库章节必须以当前 MySQL SHOW TABLES / SHOW COLUMNS / SHOW INDEX 为准。",
        "3. 每个模块都要列：职责边界、对应接口、涉及表、核心流程、当前实现状态、和需求差距。",
        "4. 学生数字孪生、诊断、个性化路径、教师干预、教师看板、5E 的职责边界不能混。",
        "5. 课程底座、职业能力映射、作业覆盖知识点、干预下发必须保留教师确认边界。",
        "6. 不要把 smoke/demo 数据当正式业务数据；行数只能作为当前快照。",
        "7. 优先更新 Markdown，再由 Markdown 生成/同步 Word。",
        "8. 对空表、演示数据、smoke 数据要明确标注，不能把“有结构”写成“已完整产品化”。",
        "9. 发现需求与实现冲突时，先写差距清单，再决定是改系统还是改设计描述。",
        "10. 图件、Word 排版和正式交付版更新应放在 Markdown 内容稳定之后。",
        "",
        "必须参考这些生成文件：",
        "- fastapi接口清单-当前实现.md",
        "- mysql真实表结构-当前实现.md",
        "- 模块-接口-数据表映射矩阵.md",
        "- AI-Education系统详细设计说明书-实现对齐候选稿.md",
        "- 需求-实现差距初查清单.md",
        "- live_design_artifacts_summary.json",
        "",
        "建议输出：",
        "1. 更新后的详细设计 Markdown。",
        "2. 单独接口说明 Markdown。",
        "3. 单独数据库表结构说明 Markdown。",
        "4. 一份差距清单，标注哪些功能只是基础实现、哪些还未实现。",
        "```",
        "",
        "## 执行计划",
        "",
        "1. 生成 FastAPI 当前接口清单。",
        "2. 生成 MySQL 当前表结构清单。",
        "3. 生成模块-接口-数据表映射矩阵。",
        "4. 生成实现对齐版详细设计 Markdown 候选稿。",
        "5. 生成需求-实现差距清单。",
        "6. 人工检查候选稿后，再同步正式 Markdown 与 Word。",
        "7. 最后用需求文档逐模块审计，列剩余差距。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_api_doc(operations: list[dict[str, Any]]) -> Path:
    path = OUT_DIR / "fastapi接口清单-当前实现.md"
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for operation in operations:
        grouped[classify_operation(operation)].append(operation)
    lines = [
        "# FastAPI 接口清单（当前实现）",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        f"接口操作数：{len(operations)}",
        "",
        "说明：本文件由 `backend/tools/docs/generate_live_design_artifacts.py` 读取 `app.openapi()` 自动生成。",
        "",
    ]
    for module in sorted(grouped):
        rows = [
            [
                item["method"],
                item["path"],
                item["summary"],
                ",".join(item["tags"]),
                item["request_body"],
                item["responses"],
            ]
            for item in sorted(grouped[module], key=lambda x: (x["path"], x["method"]))
        ]
        lines.extend([f"## {module}", ""])
        lines.extend(md_table(["方法", "路径", "摘要", "Tag", "请求体", "响应码"], rows))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_db_doc(schema: dict[str, Any]) -> Path:
    path = OUT_DIR / "mysql真实表结构-当前实现.md"
    tables = schema["tables"]
    lines = [
        "# MySQL 真实表结构（当前实现）",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        f"数据库：`{schema['database']}`",
        f"表数量：{len(tables)}",
        "",
        "说明：本文件由当前 MySQL `SHOW TABLES`、`SHOW FULL COLUMNS`、`SHOW INDEX` 自动生成。",
        "",
        "## 表清单",
        "",
    ]
    rows = []
    for table, info in tables.items():
        modules = "、".join(classify_table(table))
        primary = TABLE_PRIMARY_MODULE.get(table) or "、".join(classify_table(table, include_consumers=False))
        rows.append([table, info["row_count"], len(info["columns"]), primary, modules, TABLE_DESCRIPTIONS.get(table, "")])
    lines.extend(md_table(["表名", "当前行数", "字段数", "主责/主用途", "关联或消费模块", "用途说明"], rows))
    lines.append("")
    for table, info in tables.items():
        lines.extend([f"## `{table}`", "", f"当前行数：{info['row_count']}", ""])
        col_rows = [
            [
                col.get("Field", ""),
                col.get("Type", ""),
                col.get("Null", ""),
                col.get("Key", ""),
                col.get("Default", ""),
                col.get("Extra", ""),
                col.get("Comment", ""),
            ]
            for col in info["columns"]
        ]
        lines.extend(md_table(["字段", "类型", "可空", "键", "默认值", "额外", "注释"], col_rows))
        index_rows = [
            [
                idx.get("Key_name", ""),
                idx.get("Column_name", ""),
                idx.get("Non_unique", ""),
                idx.get("Seq_in_index", ""),
                idx.get("Index_type", ""),
            ]
            for idx in info["indexes"]
        ]
        if index_rows:
            lines.extend(["", "索引：", ""])
            lines.extend(md_table(["索引名", "字段", "非唯一", "顺序", "类型"], index_rows))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_mapping_doc(operations: list[dict[str, Any]], schema: dict[str, Any]) -> Path:
    path = OUT_DIR / "模块-接口-数据表映射矩阵.md"
    grouped_operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for operation in operations:
        grouped_operations[classify_operation(operation)].append(operation)

    lines = [
        "# 模块-接口-数据表映射矩阵",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "说明：本文件用于重写详细设计文档时对齐需求模块、FastAPI 接口和真实数据库表。",
        "",
    ]
    rows = []
    for module, config in MODULES.items():
        ops = grouped_operations.get(module, [])
        existing_tables = [table for table in config["tables"] if table in schema["tables"]]
        rows.append(
            [
                config["requirement"],
                module,
                config["note"],
                len(ops),
                "<br>".join(f"{item['method']} {item['path']}" for item in sorted(ops, key=lambda x: (x["path"], x["method"]))),
                "<br>".join(existing_tables),
                _status_from_tables(existing_tables, schema),
            ]
        )
    lines.extend(md_table(["需求章节", "模块", "职责边界", "接口数", "当前接口", "当前表", "数据状态"], rows))
    lines.append("")
    support_groups = {
        module: ops
        for module, ops in grouped_operations.items()
        if module not in MODULES
    }
    unmapped_ops = []
    for module, ops in sorted(support_groups.items()):
        unmapped_ops.extend(ops)
    if unmapped_ops:
        lines.extend(["## 支撑、通用或历史兼容接口", ""])
        for module, ops in sorted(support_groups.items()):
            lines.extend([f"### {module}", ""])
            lines.extend(md_table(["方法", "路径", "摘要"], [[item["method"], item["path"], item["summary"]] for item in sorted(ops, key=lambda x: (x["path"], x["method"]))]))
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_aligned_design_candidate(operations: list[dict[str, Any]], schema: dict[str, Any]) -> Path:
    path = OUT_DIR / "AI-Education系统详细设计说明书-实现对齐候选稿.md"
    grouped_operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for operation in operations:
        grouped_operations[classify_operation(operation)].append(operation)

    tables = schema["tables"]
    lines = [
        "# AI-Education 系统详细设计说明书（实现对齐候选稿）",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "## 1. 编制依据",
        "",
        f"- 需求基准：`{REQ_DOC}`",
        f"- 现有详细设计底稿：`{DETAIL_DOC}`",
        "- 接口依据：当前 `backend/app.py` 运行时 `app.openapi()`。",
        f"- 数据库依据：当前 MySQL `{schema['database']}` 的 `SHOW TABLES`、`SHOW FULL COLUMNS`、`SHOW INDEX`。",
        "- 本文为候选稿，不直接覆盖正式 Word；正式交付前应再做人工审阅、排版和需求逐条审计。",
        "",
        "## 2. 当前实现总览",
        "",
        f"当前 FastAPI 共暴露 `{len(operations)}` 个接口操作，当前 MySQL 数据库共有 `{len(tables)}` 张业务/支撑表。"
        "数据库行数只代表本地演示与验证快照，不能等同于正式生产数据量。",
        "",
        "系统主链路已经覆盖课程数字孪生、在线测验、学生数字孪生、诊断、个性化路径、作业、教师干预、教师看板、教学互动和行业情报等模块。"
        "其中部分模块仍处于基础实现或结构已建状态，尤其是 5E 有效性、教学互动内容数据、教研记录、部分教师画像事件仍需要继续产品化。",
        "",
        "## 3. 模块职责边界",
        "",
        "学生端负责查看画像、触发诊断结果消费和生成/执行个性化学习路径；教师端负责课程建设、资源与能力映射审核、作业发布、看板查看和干预任务下发。"
        "诊断智能体是计算与解释服务，向学生数字孪生、个性化路径和教师看板提供薄弱点、证据等级和建议动作；它不直接替代学生端路径生成，也不直接替代教师端干预。",
        "",
        "课程数字孪生发布课程底座、资源绑定和能力支撑关系；下游模块读取已发布课程底座。作业覆盖知识点、职业能力映射、干预任务包下发等关键动作必须保留教师确认边界。",
        "",
        "需要注意，本文的接口归类采用“业务主责 + 支撑接口 + 交叉引用”的方式。部分接口由于历史路由命名仍挂在 `/api/digital-twin` 或 `/api/course-digital-twin` 下，但设计文档按真实业务边界归类。",
        "",
        "## 4. 模块-接口-数据表映射",
        "",
    ]

    rows = []
    for module, config in MODULES.items():
        module_ops = sorted(grouped_operations.get(module, []), key=lambda item: (item["path"], item["method"]))
        module_tables = [table for table in config["tables"] if table in tables]
        rows.append(
            [
                config["requirement"],
                module,
                config["note"],
                len(module_ops),
                "<br>".join(f"`{item['method']} {item['path']}`" for item in module_ops),
                "<br>".join(f"`{table}`({tables[table]['row_count']})" for table in module_tables),
                _implementation_status(module, module_ops, module_tables, schema),
            ]
        )
    lines.extend(md_table(["章节", "模块", "职责边界", "接口数", "主要接口", "相关表(行数)", "当前状态"], rows))
    lines.append("")

    lines.extend(
        [
            "## 5. 数据库设计基线",
            "",
            f"当前库名：`{schema['database']}`。当前表数量：`{len(tables)}`。",
            "",
        ]
    )
    table_rows = [
        [
            table,
            info["row_count"],
            len(info["columns"]),
            TABLE_PRIMARY_MODULE.get(table) or "、".join(classify_table(table, include_consumers=False)),
            "、".join(classify_table(table)),
            TABLE_DESCRIPTIONS.get(table, ""),
            "结构已建未产品化" if info["row_count"] == 0 else "已有本地数据",
        ]
        for table, info in tables.items()
    ]
    lines.extend(md_table(["表名", "当前行数", "字段数", "主责/主用途", "关联或消费模块", "用途说明", "数据状态"], table_rows))
    lines.extend(
        [
            "",
            "### 5.1 外键与一致性说明",
            "",
            "本候选稿的表结构来自 `SHOW FULL COLUMNS` 与 `SHOW INDEX`，只能稳定反映字段、索引和当前行数。正式数据库设计还应继续补充 `SHOW CREATE TABLE` 或 `information_schema.KEY_COLUMN_USAGE`，区分普通索引、唯一约束和真实外键。",
            "",
            "当前若干表采用弱引用或依赖迁移脚本补强约束，例如资源与课程节点、测验/诊断证据与课程节点、教学互动事件与教师/学生账号、5E 过程证据与课程上下文。详细设计中应明确哪些关系由数据库外键保证，哪些由服务层校验保证。",
            "",
        ]
    )
    lines.append("")

    lines.extend(
        [
            "## 6. 接口设计基线",
            "",
            "接口清单来自 OpenAPI 自动生成结果。正式接口说明应继续补充请求字段、响应字段、权限角色和错误码；本候选稿先解决接口覆盖和模块归属问题。",
            "",
        ]
    )
    ordered_modules = list(MODULES)
    ordered_modules.extend(
        sorted(module for module in grouped_operations if module not in MODULES)
    )
    section_index = 1
    for module in ordered_modules:
        module_ops = sorted(grouped_operations.get(module, []), key=lambda item: (item["path"], item["method"]))
        if not module_ops:
            continue
        lines.extend([f"### 6.{section_index} {module}", ""])
        section_index += 1
        lines.extend(
            md_table(
                ["方法", "路径", "摘要", "请求体", "响应码"],
                [[item["method"], item["path"], item["summary"], item["request_body"], item["responses"]] for item in module_ops],
            )
        )
        lines.append("")

    lines.extend(
        [
            "## 7. 后续落地顺序",
            "",
            "1. 先把正式详细设计 Markdown 的接口章、数据库章替换为本候选稿对应内容。",
            "2. 再按模块补充请求/响应字段、权限控制、状态流转和异常分支。",
            "3. 对 5E、教学互动、教研记录、教师画像事件等空表模块补齐产品化说明或实现任务。",
            "4. 对照需求文档逐章标注“已实现 / 基础实现 / 未实现 / 设计冲突”。",
            "5. Markdown 稳定后，再生成 Word 版并做目录、表格、图题和格式审计。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_gap_doc(operations: list[dict[str, Any]], schema: dict[str, Any]) -> Path:
    path = OUT_DIR / "需求-实现差距初查清单.md"
    grouped_operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for operation in operations:
        grouped_operations[classify_operation(operation)].append(operation)

    lines = [
        "# 需求-实现差距初查清单",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "说明：本清单根据当前 OpenAPI 与真实数据库快照自动形成初查结论，用于继续人工验收和详细设计修订。",
        "",
        "## 总体结论",
        "",
        "- 主链路接口已经具备，但不少模块仍是“基础实现 + 演示数据”，不能在设计文档里写成完整产品态。",
        "- 详细设计必须以 164 个 OpenAPI operation 和 42 张 MySQL 表为准，旧文档中的接口数、表行数和 smoke 数据说明已经过期。",
        "- 需求边界要继续强调：学生端生成/执行补学路径，教师端进行干预任务审核与下发，诊断智能体提供计算服务，课程数字孪生发布课程底座和能力映射。",
        "- 生成材料只能证明“有接口、有表、有数据快照”，不能证明权限、发布态过滤、学生/教师视图隔离和证据回流已经闭环；这些必须进入后续代码级验收。",
        "",
        "## 分模块差距",
        "",
    ]
    manual_gaps = {
        "课程数字孪生与课程资源": [
            "课程结构、资源绑定、发布和运行评估已有接口，但资源自动检索质量、RAG 入库、资源审核体验仍需按真实页面验收。",
            "能力映射接口已归入行业情报与能力对接，但课程发布仍依赖该映射，需要在设计中写清跨模块依赖。",
            "当前材料不能证明所有下游接口只读取已发布课程底座，需代码级检查 `courses.lifecycle_status`、`resources.review_status`、`course_ability_mappings.review_status` 的过滤边界。",
        ],
        "学生学习空间": [
            "学习入口和学习行为记录接口存在，但需继续核对首页、课程资源、作业、测验、画像摘要是否形成统一学生工作台。",
            "通知与学习计划已有接口，需确认前端是否完整消费真实数据。",
            "需确认学生端接口不暴露教师审核过程、证据权重调整和后台备注。",
        ],
        "在线测验": [
            "测验定义、发布、开始、作答、完成已有接口；需补充测验定义表或说明当前测验定义存储方式。",
            "测验作为知识点强证据的回流规则需要在详细设计里写成字段级流程。",
            "需确认异常测验、未发布测验或未绑定已发布叶子知识点的测验不会进入强诊断。",
        ],
        "学生数字孪生": [
            "画像、知识点掌握、历史快照、作业结果接口已有；职业能力达成、证据下钻和学生/教师视图差异仍需继续验收。",
            "学生数字孪生不应承担根因解释和路径生成，设计文档需避免职责越界。",
            "需确认能力达成只读取教师确认并发布后的 `course_ability_mappings`，并按学生叶子知识点掌握度折算。",
        ],
        "诊断智能体": [
            "诊断报告与修正接口已有，但修正表当前为空或数据少，需标注为基础能力。",
            "证据不足分支、证据等级、教师端证据时间线需要用真实接口响应继续补字段说明。",
        ],
        "个性化学习路径": [
            "路径生成、当前路径、版本和节点状态接口已有；需确认前端是否由学生端触发并展示执行状态。",
            "教师端不应生成学生补学路径，只能基于诊断进行干预任务安排。",
            "`POST /api/digital-twin/path/generate/{username}` 存在以 username 为参数的角色边界风险，需确认权限层禁止非授权用户替学生生成正式路径。",
        ],
        "5E 教学智能体": [
            "聊天和有效性汇总接口存在，但 `events`、`user_interaction`、`fivee_effectiveness_records` 当前为空，应标注为结构已建未产品化。",
            "5E 证据只能作为过程性辅助证据，不能替代测验和作业。",
        ],
        "作业与实践评测": [
            "作业创建、发布、提交、AI 批改、教师终审、覆盖知识点接口已有；需补权限、状态流转和代码题稳定性说明。",
            "作业覆盖知识点必须教师确认后才影响叶子知识点画像。",
            "需代码级确认画像、诊断、路径服务只采纳 `confirmed_by_teacher=1` 的覆盖知识点记录。",
        ],
        "教师智能干预任务包": [
            "草稿生成、教师修改、下发、学生反馈、进度和评分接口已有；需核对任务完成结果是否稳定回流画像和看板。",
            "干预是教师端动作，不应写成学生路径推荐模块的一部分。",
            "需确认 `POST /api/intervention/teacher/diagnose` 调用统一诊断服务，而不是形成另一套诊断口径。",
        ],
        "教师看板与教师数字孪生": [
            "班级概览、学生趋势、教师画像、AI 建议、事件写入接口已有；教师画像依赖的部分事件仍需补完整演示和产品入口。",
            "AI 建议必须教师手动触发，设计文档不能写成系统自动替教师决策。",
            "需代码级确认所有看板接口按 `teacher_student_links` 或课程授权过滤，避免教师读取非授权学生。",
        ],
        "教学互动": [
            "公告、讨论、教研接口已有，但公告/讨论/教研记录表当前多为空，需要补演示数据和前端验收。",
            "教学互动是人工沟通和教研记录层，不应归入智能学习支持或诊断智能体。",
        ],
        "行业情报与能力对接": [
            "行业分析任务接口和课程岗位/能力/映射接口存在；需写清行业任务、能力候选、教师确认、课程发布之间的状态流。",
            "职业能力映射只使用教师确认发布后的叶子知识点关系。",
            "3.12 产生岗位/能力候选，3.1 完成审核发布；详细设计应避免把行业情报模块写成课程底座发布者。",
        ],
    }
    for module, config in MODULES.items():
        module_ops = grouped_operations.get(module, [])
        module_tables = [table for table in config["tables"] if table in schema["tables"]]
        empty_tables = [table for table in module_tables if schema["tables"][table]["row_count"] == 0]
        lines.extend([f"### {config['requirement']} {module}", ""])
        lines.append(f"- 当前接口数：{len(module_ops)}；相关表：{', '.join(module_tables) or '无'}。")
        if empty_tables:
            lines.append(f"- 当前空表：{', '.join(empty_tables)}，详细设计应标注为结构已建或待产品化。")
        for item in manual_gaps[module]:
            lines.append(f"- {item}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _implementation_status(module: str, operations: list[dict[str, Any]], tables: list[str], schema: dict[str, Any]) -> str:
    if not operations and not tables:
        return "缺少接口与表，需要重新核对实现范围"
    empty_tables = [table for table in tables if schema["tables"][table]["row_count"] == 0]
    if module == "5E 教学智能体":
        return "接口存在，核心事件表为空，属于结构已建未产品化"
    if empty_tables:
        return "基础实现，部分数据表为空：" + "、".join(empty_tables)
    return "已有接口和本地数据，仍需按页面与业务流验收"


def _status_from_tables(tables: list[str], schema: dict[str, Any]) -> str:
    if not tables:
        return "无直接表"
    empty = [table for table in tables if schema["tables"][table]["row_count"] == 0]
    if not empty:
        return "相关表均有数据"
    if len(empty) == len(tables):
        return "相关表均为空"
    return "部分表为空：" + "、".join(empty)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    operations = load_openapi_operations()
    schema = load_database_schema()
    paths = [
        write_prompt_and_plan(),
        write_api_doc(operations),
        write_db_doc(schema),
        write_mapping_doc(operations, schema),
        write_aligned_design_candidate(operations, schema),
        write_gap_doc(operations, schema),
    ]
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(OUT_DIR),
        "operation_count": len(operations),
        "table_count": len(schema["tables"]),
        "files": [str(path) for path in paths],
    }
    (OUT_DIR / "live_design_artifacts_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

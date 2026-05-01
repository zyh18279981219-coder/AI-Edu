from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from HomeworkModule.models import AssignmentQuestionGenerateRequest
from HomeworkModule.repository import HomeworkRepository
from HomeworkModule.sandbox_service import SandboxService
from tools.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


class HomeworkService:
    def __init__(self, repository: Optional[HomeworkRepository] = None) -> None:
        self.repository = repository or HomeworkRepository()
        self.sandbox_service = SandboxService()
        self.model_name = os.environ.get("model_name", "")
        self.base_url = os.environ.get("base_url", "")
        self.api_key = os.environ.get("api_key", "")
        self.llm = self._build_llm()
        self.llm_logger = get_llm_logger()

    def _build_llm(self) -> Optional[ChatOpenAI]:
        if not (self.model_name and self.base_url and self.api_key):
            logger.warning("LLM not configured: model_name=%s base_url=%s", self.model_name, self.base_url)
            return None
        try:
            import httpx
            http_client = httpx.Client(verify=False)
            return ChatOpenAI(
                model=self.model_name,
                temperature=0.2,
                # max_tokens=40000,
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=http_client,
            )
        except Exception as exc:
            logger.error("Failed to build LLM: %s", exc)
            return None

    def _normalize_assignment_type(self, value: str) -> str:
        raw = str(value or "subjective").strip().lower()
        if raw == "code_practice":
            return "code"
        if raw not in {"subjective", "objective", "choice", "code"}:
            return "subjective"
        return raw

    def _normalize_objective_result_mode(self, value: str) -> str:
        raw = str(value or "immediate").strip().lower()
        if raw not in {"immediate", "manual_review"}:
            return "immediate"
        return raw

    def create_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        payload["status"] = "published" if payload.get("publish_now") else "draft"
        return self.repository.create_assignment(payload)

    def create_builtin_oj_smoke_assignment(self, created_by: str = "system") -> Dict[str, Any]:
        title = "OJ三语言连通性测试（内置）"
        existing = self.repository.list_assignments(include_statuses=["draft", "published", "closed"])
        for item in existing:
            if str(item.get("title", "")).strip() == title and item.get("assignment_type") == "code":
                return {"created": False, "assignment": item}

        prompt = (
            "请在学生端代码编辑器中选择对应语言，并直接粘贴下方标准答案代码运行。\n"
            "题目：从标准输入读取两个整数 a 和 b，输出它们的和。\n\n"
            "Python 标准答案：\n"
            "```python\n"
            "a, b = map(int, input().split())\n"
            "print(a + b)\n"
            "```\n\n"
            "C++ 标准答案：\n"
            "```cpp\n"
            "#include <bits/stdc++.h>\n"
            "using namespace std;\n"
            "int main() {\n"
            "    long long a, b;\n"
            "    if (!(cin >> a >> b)) return 0;\n"
            "    cout << (a + b) << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
            "```\n\n"
            "Java 标准答案：\n"
            "```java\n"
            "import java.util.*;\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Scanner sc = new Scanner(System.in);\n"
            "        long a = sc.nextLong();\n"
            "        long b = sc.nextLong();\n"
            "        System.out.println(a + b);\n"
            "    }\n"
            "}\n"
            "```\n"
        )

        payload = {
            "title": title,
            "description": "用于验证 OJ 三语言判题链路是否打通。可在学生端直接粘贴题目内标准答案运行。",
            "assignment_type": "code",
            "class_name": "系统内置",
            "due_at": None,
            "allow_late": True,
            "total_score": 100,
            "rubric": "共4个测试点，每点25分；通过一个测试点获得对应分值。",
            "questions": [
                {
                    "title": "两数求和（OJ烟雾测试）",
                    "prompt": prompt,
                    "options": [],
                    "correct_answer": "",
                    "reference_answer": "题干已内置 Python/C++/Java 三种标准答案代码。",
                    "rubric": "通过测试点得分。",
                    "test_cases": [
                        {"input": "1 2\\n", "expected": "3", "weight": 25, "is_file_io": False},
                        {"input": "100 250\\n", "expected": "350", "weight": 25, "is_file_io": False},
                        {"input": "-5 8\\n", "expected": "3", "weight": 25, "is_file_io": False},
                        {"input": "0 0\\n", "expected": "0", "weight": 25, "is_file_io": False},
                    ],
                }
            ],
            "publish_now": True,
            "created_by": str(created_by or "system"),
        }

        created = self.create_assignment(payload)
        return {"created": True, "assignment": created}

    def create_teacher_owned_oj_smoke_assignments(self, teacher_username: str) -> Dict[str, Any]:
        owner = str(teacher_username or "teacher").strip() or "teacher"
        existing = self.repository.list_assignments(created_by=owner, include_statuses=["draft", "published", "closed"])
        existing_titles = {str(item.get("title", "")).strip() for item in existing}

        prompts: Dict[str, str] = {
            "python": (
                "请读取两个整数 a 和 b，输出它们的和。\n\n"
                "参考答案（Python）：\n"
                "```python\n"
                "a, b = map(int, input().split())\n"
                "print(a + b)\n"
                "```\n"
            ),
            "cpp": (
                "请读取两个整数 a 和 b，输出它们的和。\n\n"
                "参考答案（C++）：\n"
                "```cpp\n"
                "#include <bits/stdc++.h>\n"
                "using namespace std;\n"
                "int main() {\n"
                "    long long a, b;\n"
                "    if (!(cin >> a >> b)) return 0;\n"
                "    cout << (a + b) << \"\\n\";\n"
                "    return 0;\n"
                "}\n"
                "```\n"
            ),
            "java": (
                "请读取两个整数 a 和 b，输出它们的和。\n\n"
                "参考答案（Java）：\n"
                "```java\n"
                "import java.util.*;\n"
                "public class Main {\n"
                "    public static void main(String[] args) {\n"
                "        Scanner sc = new Scanner(System.in);\n"
                "        long a = sc.nextLong();\n"
                "        long b = sc.nextLong();\n"
                "        System.out.println(a + b);\n"
                "    }\n"
                "}\n"
                "```\n"
            ),
        }

        created_items: List[Dict[str, Any]] = []
        for lang in ["python", "cpp", "java"]:
            title = f"OJ连通测试（{lang.upper()}）"
            if title in existing_titles:
                continue
            created = self.create_assignment(
                {
                    "title": title,
                    "description": f"用于验证 {lang.upper()} 语言判题链路是否正常。",
                    "assignment_type": "code",
                    "class_name": "系统内置",
                    "due_at": None,
                    "allow_late": True,
                    "total_score": 100,
                    "rubric": "共4个测试点，每点25分。",
                    "questions": [
                        {
                            "title": f"两数求和（{lang.upper()}）",
                            "prompt": prompts[lang],
                            "options": [],
                            "correct_answer": "",
                            "reference_answer": "题干中已提供标准答案。",
                            "rubric": "通过测试点得分。",
                            "test_cases": [
                                {"input": "1 2\\n", "expected": "3", "weight": 25, "is_file_io": False},
                                {"input": "100 250\\n", "expected": "350", "weight": 25, "is_file_io": False},
                                {"input": "-5 8\\n", "expected": "3", "weight": 25, "is_file_io": False},
                                {"input": "0 0\\n", "expected": "0", "weight": 25, "is_file_io": False},
                            ],
                        }
                    ],
                    "publish_now": True,
                    "created_by": owner,
                }
            )
            created_items.append(created)

        return {
            "created_count": len(created_items),
            "created_assignments": created_items,
            "owner": owner,
        }

    def list_assignments(
        self,
        created_by: Optional[str] = None,
        status: Optional[str] = None,
        include_statuses: Optional[List[str]] = None,
        course_id: Optional[str] = None,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_assignments(
            created_by=created_by,
            status=status,
            include_statuses=include_statuses,
            course_id=course_id,
            node_id=node_id,
            node_name=node_name,
        )

    def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        return self.repository.get_assignment(assignment_id)

    def update_assignment(self, assignment_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assignment = self.repository.get_assignment(assignment_id)
        if not assignment:
            return None
        status = assignment.get("status", "draft")
        return self.repository.update_assignment(assignment_id, {**payload, "status": status})

    def publish_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        assignment = self.repository.get_assignment(assignment_id)
        if not assignment:
            return None
        if assignment.get("status") == "closed":
            return self.repository.update_assignment(assignment_id, {"status": "published"})
        return self.repository.update_assignment(assignment_id, {"status": "published"})

    def close_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        if not self.repository.get_assignment(assignment_id):
            return None
        return self.repository.update_assignment(assignment_id, {"status": "closed"})

    def reopen_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        if not self.repository.get_assignment(assignment_id):
            return None
        return self.repository.update_assignment(assignment_id, {"status": "published"})

    def submit_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assignment_id = str(payload.get("assignment_id", ""))
        student_username = str(payload.get("student_username", ""))
        assignment = self.repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError("作业不存在")

        if assignment.get("status") != "published":
            raise PermissionError("当前作业未发布，暂不可提交")

        due_at = assignment.get("due_at")
        if due_at and not assignment.get("allow_late", False):
            due_dt = self._parse_datetime(due_at)
            if due_dt and datetime.now() > due_dt:
                raise PermissionError("已超过截止时间，且该作业不允许逾期提交")

        latest = self.repository.get_latest_submission(assignment_id=assignment_id, student_username=student_username)
        if latest and latest.get("status") != "graded":
            updated = self.repository.update_submission(
                latest["id"],
                {
                    "answers": payload.get("answers", []),
                    "submitted_at": datetime.now().isoformat(),
                    "status": "submitted",
                    "ai_score": None,
                    "ai_feedback": "",
                    "ai_rationale": "",
                    "teacher_score": None,
                    "teacher_comment": "",
                    "graded_at": None,
                    "grader_username": "",
                },
            )
            submitted = updated or latest
            return self._auto_grade_on_submit(assignment, submitted)

        created = self.repository.create_submission(payload)
        return self._auto_grade_on_submit(assignment, created)

    def _auto_grade_on_submit(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
        assignment_type = str(assignment.get("assignment_type") or "")
        if assignment_type == "code":
            return self._auto_grade_code_submission(assignment, submission)
        if assignment_type not in {"objective", "choice"}:
            return submission
        mode = self._normalize_objective_result_mode(str(assignment.get("objective_result_mode", "immediate")))
        if mode != "immediate":
            return submission
        return self._auto_grade_objective_submission(assignment, submission)

    def _auto_grade_code_submission(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
        judge_report = self._build_code_judge_report(assignment, submission)
        passed = int(judge_report.get("passed", 0) or 0)
        total = int(judge_report.get("total", 0) or 0)
        earned_score = float(judge_report.get("earned_score", 0.0) or 0.0)
        total_score = float(judge_report.get("total_score", 0.0) or 0.0)
        score = round(min(total_score, max(0.0, earned_score)), 2)
        feedback = f"系统自动判题：通过 {passed}/{total} 个测试点，得分 {score}/{round(total_score, 2)}。"

        updated = self.repository.update_submission(
            submission["id"],
            {
                "status": "graded",
                "ai_score": score,
                "ai_feedback": feedback,
                "ai_rationale": json.dumps(judge_report, ensure_ascii=False),
                "teacher_score": score,
                "teacher_comment": "代码题已由沙箱自动判题。",
                "grader_username": "sandbox",
                "graded_at": datetime.now().isoformat(),
            },
        )
        return updated or submission

    def _auto_grade_objective_submission(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
        score, feedback, rationale = self._grade_objective_like(assignment, submission)
        updated = self.repository.update_submission(
            submission["id"],
            {
                "status": "graded",
                "ai_score": round(float(score), 2),
                "ai_feedback": feedback,
                "ai_rationale": rationale,
                "graded_at": datetime.now().isoformat(),
                "grader_username": "auto_objective",
            },
        )
        return updated or submission

    def list_submissions(
        self,
        assignment_id: Optional[str] = None,
        student_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_submissions(
            assignment_id=assignment_id,
            student_username=student_username,
        )

    def get_student_twin_homework_snapshot(
        self,
        *,
        student_username: str,
        assignment_id: Optional[str] = None,
        teacher_owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        submissions = self.list_submissions(
            assignment_id=assignment_id,
            student_username=student_username,
        )

        items: List[Dict[str, Any]] = []
        score_values: List[float] = []
        assignment_cache: Dict[str, Dict[str, Any]] = {}

        for sub in submissions:
            aid = str(sub.get("assignment_id", ""))
            if not aid:
                continue
            assignment = assignment_cache.get(aid)
            if assignment is None:
                assignment = self.get_assignment(aid) or {}
                assignment_cache[aid] = assignment
            if not assignment:
                continue
            if teacher_owner and str(assignment.get("created_by", "")) != teacher_owner:
                continue

            score = sub.get("teacher_score")
            if score is None:
                score = sub.get("ai_score")
            if isinstance(score, (int, float)):
                score_values.append(float(score))

            question_results: List[Dict[str, Any]] = []
            assignment_type = str(assignment.get("assignment_type", "subjective"))

            if assignment_type == "code":
                judge_report = self._extract_judge_report(sub.get("ai_rationale", ""))
                question_results = self._build_code_question_results(judge_report)
            elif assignment_type in {"objective", "choice"}:
                question_results = self._build_objective_question_results(assignment, sub)
            else:
                question_results = self._build_subjective_question_results(assignment, sub)

            items.append(
                {
                    "submission_id": sub.get("id"),
                    "assignment_id": aid,
                    "assignment_title": assignment.get("title", ""),
                    "assignment_type": assignment_type,
                    "submitted_at": sub.get("submitted_at"),
                    "status": sub.get("status"),
                    "score": score,
                    "total_score": assignment.get("total_score"),
                    "question_results": question_results,
                }
            )

        average_score = round(sum(score_values) / len(score_values), 2) if score_values else None
        return {
            "student_username": student_username,
            "submission_count": len(items),
            "graded_count": sum(1 for item in items if item.get("score") is not None),
            "average_score": average_score,
            "items": items,
        }

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        return self.repository.get_submission(submission_id)

    def grade_with_ai(
        self,
        assignment: Dict[str, Any],
        submission: Dict[str, Any],
        teacher_username: str,
    ) -> Dict[str, Any]:
        result = self._grade_with_llm(assignment, submission, teacher_username)
        if result is None:
            result = self._grade_with_heuristic(assignment, submission)

        updated = self.repository.update_submission(
            submission["id"],
            {
                "ai_score": result["score"],
                "ai_feedback": result["feedback"],
                "ai_rationale": result.get("rationale", ""),
            },
        )
        return updated or submission

    def finalize_grade(
        self,
        submission_id: str,
        teacher_score: float,
        teacher_comment: str,
        grader_username: str,
    ) -> Optional[Dict[str, Any]]:
        return self.repository.update_submission(
            submission_id,
            {
                "status": "graded",
                "teacher_score": round(float(teacher_score), 2),
                "teacher_comment": teacher_comment,
                "grader_username": grader_username,
                "graded_at": datetime.now().isoformat(),
            },
        )

    def generate_assignment_draft(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        class_name: str,
        teacher_username: str,
        course_id: str = "course_big_data",
        node_id: str = "",
        node_name: str = "",
        node_path: Optional[List[str]] = None,
        chapter_context: str = "",
        objective_result_mode: str = "immediate",
    ) -> Dict[str, Any]:
        normalized_assignment_type = self._normalize_assignment_type(assignment_type)
        normalized_objective_result_mode = self._normalize_objective_result_mode(objective_result_mode)
        result = self._generate_assignment_draft_with_llm(
            assignment_type=normalized_assignment_type,
            topic=topic,
            difficulty=difficulty,
            class_name=class_name,
            teacher_username=teacher_username,
            course_id=course_id,
            node_id=node_id,
            node_name=node_name,
            node_path=node_path or [],
            chapter_context=chapter_context,
            objective_result_mode=normalized_objective_result_mode,
        )
        if result and result.get("ok"):
            return {"ok": True, "draft": result["draft"], "generated_at": datetime.now().isoformat()}

        error_detail = (result or {}).get("error", "ai_unavailable") if result else "ai_unavailable"
        error_message = (result or {}).get("message", "AI 服务不可用，已使用模板兜底。") if result else "AI 服务不可用，已使用模板兜底。"

        return {
            "ok": False,
            "message": error_message,
            "error": error_detail,
            "draft": self._fallback_assignment_draft(
                normalized_assignment_type,
                topic,
                difficulty,
                class_name,
                course_id=course_id,
                node_id=node_id,
                node_name=node_name,
                node_path=node_path or [],
                chapter_context=chapter_context,
                objective_result_mode=normalized_objective_result_mode,
            ),
            "generated_at": datetime.now().isoformat(),
        }

    def generate_questions(
        self,
        request: AssignmentQuestionGenerateRequest,
        teacher_username: str,
    ) -> List[Dict[str, Any]]:
        generated = self._generate_questions_with_llm(request, teacher_username)
        if generated:
            return generated
        return self._generate_questions_fallback(request)

    def _generate_questions_with_llm(
        self,
        request: AssignmentQuestionGenerateRequest,
        teacher_username: str,
    ) -> Optional[List[Dict[str, Any]]]:
        if not self.llm:
            logger.warning("LLM not available for question generation")
            return None

        chapter_ctx = request.chapter_context or "无"
        assignment_type = self._normalize_assignment_type(request.assignment_type)
        if assignment_type == "objective":
            item_template = (
                '{"title":"题目标题","prompt":"题面（判断题）","options":["A. 正确","B. 错误"],'
                '"correct_answer":"A","reference_answer":"解析","rubric":"评分规则","test_cases":[]}'
            )
        elif assignment_type == "choice":
            item_template = (
                '{"title":"题目标题","prompt":"题面（选择题）","options":["A.xxx","B.xxx","C.xxx","D.xxx"],'
                '"correct_answer":"A 或 A,C","reference_answer":"解析","rubric":"评分规则","test_cases":[]}'
            )
        elif assignment_type == "code":
            item_template = (
                '{"title":"题目标题","prompt":"题面（编程题，说明输入输出）","options":[],"correct_answer":"",'
                '"reference_answer":"解题思路","rubric":"评分规则",'
                '"test_cases":[{"input":"示例输入1","expected":"示例输出1","weight":50,"is_file_io":false},'
                '{"input":"示例输入2","expected":"示例输出2","weight":50,"is_file_io":false}]}'
            )
        else:
            item_template = (
                '{"title":"题目标题","prompt":"题面（主观题）","options":[],"correct_answer":"",'
                '"reference_answer":"要点","rubric":"评分规则","test_cases":[]}'
            )
        prompt = (
            f"你是课程助教。请生成{request.count}道{assignment_type}类型题目，严格输出 JSON 数组（不要 markdown）：\n\n"
            f"【主题】{request.topic}\n"
            f"【难度】{request.difficulty}\n"
            f"【语言】{request.language}\n"
            f"【章节上下文】{chapter_ctx}\n"
            f"【额外要求】{request.extra_requirements or '无'}\n\n"
            "每个元素格式：\n"
            f"{item_template}\n\n"
            "只输出 JSON 数组，不要解释。"
        )
        try:
            logger.info("LLM question generation: type=%s topic=%s count=%d", request.assignment_type, request.topic, request.count)
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", "") or ""
            content_len = len(content)

            finish_reason = ""
            if hasattr(response, "response_metadata"):
                finish_reason = str(response.response_metadata.get("finish_reason", ""))
            logger.info("LLM question response: len=%d finish_reason=%s", content_len, finish_reason)

            if finish_reason == "length":
                logger.warning("LLM question output truncated (finish_reason=length), len=%d", content_len)
                return None

            if content_len < 10:
                logger.warning("LLM question output too short: len=%d", content_len)
                return None

            parsed = self._extract_json_array(content)
            if not parsed:
                preview = content[:500]
                logger.error("Failed to parse LLM question response as JSON array. Preview: %s", preview)
                return None

            self.llm_logger.log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=response,
                model=self.model_name,
                module="HomeworkModule.question_generation",
                metadata={
                    "action": "generate_assignment_questions",
                    "assignment_type": request.assignment_type,
                    "topic": request.topic,
                    "count": request.count,
                },
                username=teacher_username,
            )
            return parsed[: request.count]
        except Exception as exc:
            logger.exception("LLM question generation failed: %s", exc)
            return None

    def _generate_questions_fallback(
        self,
        request: AssignmentQuestionGenerateRequest,
    ) -> List[Dict[str, Any]]:
        questions: List[Dict[str, Any]] = []
        assignment_type = self._normalize_assignment_type(request.assignment_type)
        for idx in range(request.count):
            if assignment_type == "code":
                questions.append(
                    {
                        "title": f"{request.topic} 代码实践 {idx + 1}",
                        "prompt": f"请使用你熟悉的语言实现与{request.topic}相关的小程序，并给出复杂度说明。",
                        "options": [],
                        "correct_answer": "",
                        "reference_answer": "参考答案可包含函数设计、关键算法步骤、复杂度分析。",
                        "rubric": "功能正确40分，代码规范20分，复杂度与边界处理20分，说明文档20分。",
                        "test_cases": [
                            {"input": "示例输入1", "expected": "示例输出1", "weight": 50, "is_file_io": False},
                            {"input": "边界输入", "expected": "边界输出", "weight": 50, "is_file_io": False},
                        ],
                    }
                )
            elif assignment_type == "choice":
                questions.append(
                    {
                        "title": f"{request.topic} 选择题 {idx + 1}",
                        "prompt": f"关于 {request.topic}，请选择最符合题意的选项。",
                        "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
                        "correct_answer": "A",
                        "reference_answer": "可解释各选项依据。",
                        "rubric": "选择正确给满分，解释充分可酌情加分。",
                        "test_cases": [],
                    }
                )
            elif assignment_type == "objective":
                questions.append(
                    {
                        "title": f"{request.topic} 客观题 {idx + 1}",
                        "prompt": f"判断下列陈述是否正确：{request.topic} 的关键原理可直接应用于所有场景。",
                        "options": ["A. 正确", "B. 错误"],
                        "correct_answer": "B",
                        "reference_answer": "应结合适用边界说明。",
                        "rubric": "判断正确并说明原因。",
                        "test_cases": [],
                    }
                )
            else:
                questions.append(
                    {
                        "title": f"{request.topic} 主观题 {idx + 1}",
                        "prompt": f"请围绕{request.topic}进行论述，包含概念、方法与应用场景。",
                        "options": [],
                        "correct_answer": "",
                        "reference_answer": "参考答案应覆盖核心概念、关键步骤、案例分析与局限性。",
                        "rubric": "概念准确40分，结构逻辑30分，案例深度20分，表达规范10分。",
                        "test_cases": [],
                    }
                )
        return questions

    def _build_draft_prompt(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        chapter_ctx: str,
    ) -> str:
        """根据题型构建不同的 prompt，避免所有题型都用选择题模板."""
        type_label_map = {
            "choice": "选择题",
            "objective": "客观题（选择题/判断题）",
            "subjective": "主观题（简答/论述题）",
            "code": "编程题",
        }
        type_label = type_label_map.get(assignment_type, "题目")

        if assignment_type == "choice":
            question_template = (
                '    {\n'
                '      "title": "题目小标题",\n'
                '      "prompt": "题面描述",\n'
                '      "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],\n'
                '      "correct_answer": "A 或 A,C",\n'
                '      "reference_answer": "参考答案解析",\n'
                '      "rubric": "该题评分规则",\n'
                '      "test_cases": []\n'
                '    }\n'
            )
            extra_notes = (
                "注意：options 必须是4个选项；correct_answer 用选项字母，单选如 A，多选如 A,C；"
            )
        elif assignment_type == "objective":
            question_template = (
                '    {\n'
                '      "title": "题目小标题",\n'
                '      "prompt": "题面描述（判断题）",\n'
                '      "options": ["A. 正确", "B. 错误"],\n'
                '      "correct_answer": "A",\n'
                '      "reference_answer": "参考答案解析",\n'
                '      "rubric": "该题评分规则",\n'
                '      "test_cases": []\n'
                '    }\n'
            )
            extra_notes = (
                "注意：objective 为判断题，options 固定为 A.正确 / B.错误；correct_answer 只能是 A 或 B；"
            )
        elif assignment_type == "code":
            question_template = (
                '    {\n'
                '      "title": "题目小标题",\n'
                '      "prompt": "题面描述，说明输入输出格式",\n'
                '      "options": [],\n'
                '      "correct_answer": "",\n'
                '      "reference_answer": "参考答案代码思路或关键算法说明",\n'
                '      "rubric": "该题评分规则",\n'
                '      "test_cases": [\n'
                '        {"input": "示例输入1", "expected": "示例输出1", "weight": 50, "is_file_io": false},\n'
                '        {"input": "示例输入2", "expected": "示例输出2", "weight": 50, "is_file_io": false}\n'
                '      ]\n'
                '    }\n'
            )
            extra_notes = (
                "注意：test_cases 至少给2组，weight 之和为100；options 和 correct_answer 留空；"
            )
        else:  # subjective
            question_template = (
                '    {\n'
                '      "title": "题目小标题",\n'
                '      "prompt": "题面描述（论述/简答题目）",\n'
                '      "options": [],\n'
                '      "correct_answer": "",\n'
                '      "reference_answer": "参考答案要点（列出关键评分点）",\n'
                '      "rubric": "该题评分规则（如：观点明确30分，论证充分40分，语言表达30分）",\n'
                '      "test_cases": []\n'
                '    }\n'
            )
            extra_notes = (
                "注意：主观题不需要 options 和 correct_answer，重点写清楚评分规则 rubric；"
            )

        prompt = (
            f"你是课程助教。请根据以下信息生成一道{type_label}作业草稿，"
            f"严格输出 JSON（不要 markdown 包裹，直接输出纯 JSON 对象）：\n\n"
            f"【题型】{assignment_type}\n"
            f"【主题】{topic}\n"
            f"【难度】{difficulty}\n"
            f"【章节上下文】{chapter_ctx}\n\n"
            "JSON 格式要求：\n"
            "{\n"
            '  "title": "作业标题",\n'
            '  "description": "作业描述，1-2句话",\n'
            f'  "assignment_type": "{assignment_type}",\n'
            '  "due_at": null,\n'
            '  "allow_late": false,\n'
            '  "objective_result_mode": "immediate",\n'
            '  "total_score": 100,\n'
            '  "rubric": "评分标准，如：每题XX分",\n'
            '  "questions": [\n'
            f"{question_template}"
            '  ]\n'
            '}\n\n'
            f"{extra_notes}"
            "allow_late 为布尔值；objective_result_mode 仅可为 immediate 或 manual_review；直接输出 JSON，不要加任何解释。"
        )
        return prompt

    def _generate_assignment_draft_with_llm(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        class_name: str,
        teacher_username: str,
        course_id: str,
        node_id: str,
        node_name: str,
        node_path: List[str],
        chapter_context: str,
        objective_result_mode: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return {"ok": False, "error": "llm_not_configured", "message": "LLM 未配置，请检查 model_name/base_url/api_key 环境变量。"}

        chapter_path_str = " > ".join([str(item) for item in (node_path or [])]) or "未指定"
        chapter_ctx = chapter_context or f"章节路径：{chapter_path_str}"

        prompt = self._build_draft_prompt(assignment_type, topic, difficulty, chapter_ctx)
        try:
            logger.info("LLM draft request: type=%s topic=%s difficulty=%s", assignment_type, topic, difficulty)
            response = self._invoke_llm_for_json(prompt)
            raw_content = getattr(response, "content", "") or ""
            content_len = len(raw_content)

            # 检测截断
            finish_reason = ""
            if hasattr(response, "response_metadata"):
                finish_reason = str(response.response_metadata.get("finish_reason", ""))
            logger.info("LLM draft response: len=%d finish_reason=%s", content_len, finish_reason)

            if finish_reason == "length":
                logger.warning("LLM output truncated (finish_reason=length), len=%d", content_len)
                self.llm_logger.log_llm_call(
                    messages=[{"role": "user", "content": prompt}],
                    response=response,
                    model=self.model_name,
                    module="HomeworkModule.assignment_draft",
                    metadata={"action": "generate_assignment_draft", "status": "truncated", "assignment_type": assignment_type, "topic": topic},
                    username=teacher_username,
                )
                return {"ok": False, "error": "llm_output_truncated", "message": "AI 输出被截断（finish_reason=length），可能是模型生成内容过长或质量异常。请重试。"}

            if self._has_garbled_output(raw_content):
                logger.warning("LLM output appears garbled (repetitive pattern detected), len=%d", content_len)
                self.llm_logger.log_llm_call(
                    messages=[{"role": "user", "content": prompt}],
                    response=response,
                    model=self.model_name,
                    module="HomeworkModule.assignment_draft",
                    metadata={"action": "generate_assignment_draft", "status": "garbled", "assignment_type": assignment_type, "topic": topic},
                    username=teacher_username,
                )
                return {"ok": False, "error": "llm_garbled_output", "message": "AI 输出疑似乱码（检测到大量重复模式），可能是模型质量异常。建议更换模型重试。"}

            if content_len < 20:
                logger.warning("LLM returned too short content: len=%d", content_len)
                return {"ok": False, "error": "llm_output_too_short", "message": f"AI 返回内容过短（{content_len}字符），可能是 API 异常。"}

            parsed = self._extract_json_object(raw_content)
            if not parsed:
                repaired_content = self._retry_force_json_output(raw_content, prompt)
                if repaired_content:
                    parsed = self._extract_json_object(repaired_content)
                    if parsed:
                        raw_content = repaired_content
                        logger.info("LLM draft JSON repaired successfully via retry")
            if not parsed:
                # 记录原始响应 + 提取到的 JSON 块用于排障
                preview = raw_content[:500]
                extracted_block = self._extract_json_block(raw_content)
                block_preview = (extracted_block or "")[:300] if extracted_block else "(none)"
                logger.error(
                    "Failed to parse LLM response as JSON. raw_preview=%s, extracted_block=%s",
                    preview, block_preview,
                )
                self.llm_logger.log_llm_call(
                    messages=[{"role": "user", "content": prompt}],
                    response=response,
                    model=self.model_name,
                    module="HomeworkModule.assignment_draft",
                    metadata={"action": "generate_assignment_draft", "status": "parse_failed", "assignment_type": assignment_type, "topic": topic, "raw_preview": preview},
                    username=teacher_username,
                )
                return {"ok": False, "error": "llm_json_parse_failed", "message": f"AI 返回内容无法解析为 JSON。原始响应预览：{preview[:200]}..."}

            questions = parsed.get("questions")
            if not isinstance(questions, list) or not questions:
                logger.warning("No valid questions in LLM response")
                return {"ok": False, "error": "llm_no_questions", "message": "AI 返回的 JSON 中缺少 questions 字段或为空。"}

            normalized_questions = []
            for idx, item in enumerate(questions):
                if not isinstance(item, dict):
                    continue
                normalized_questions.append(
                    {
                        "title": str(item.get("title", f"题目{idx + 1}")).strip() or f"题目{idx + 1}",
                        "prompt": str(item.get("prompt", "")).strip(),
                        "options": item.get("options") if isinstance(item.get("options"), list) else [],
                        "correct_answer": str(item.get("correct_answer", "")).strip(),
                        "reference_answer": str(item.get("reference_answer", "")).strip(),
                        "rubric": str(item.get("rubric", "")).strip(),
                        "test_cases": item.get("test_cases") if isinstance(item.get("test_cases"), list) else [],
                    }
                )
            if not normalized_questions:
                logger.warning("All questions filtered out after normalization")
                return {"ok": False, "error": "llm_invalid_questions", "message": "AI 返回的题目数据格式不正确。"}

            assignment_type_value = str(parsed.get("assignment_type", assignment_type)).strip().lower()
            if assignment_type_value not in {"subjective", "objective", "choice", "code"}:
                assignment_type_value = assignment_type
            draft = {
                "title": str(parsed.get("title", "")).strip() or f"{topic}作业（{difficulty}）",
                "description": str(parsed.get("description", "")).strip(),
                "assignment_type": assignment_type_value,
                "course_id": str(course_id or "course_big_data"),
                "node_id": str(node_id or ""),
                "node_name": str(node_name or ""),
                "node_path": [str(item).strip() for item in (node_path or []) if str(item).strip()],
                "chapter_context": chapter_ctx,
                "objective_result_mode": self._normalize_objective_result_mode(
                    str(parsed.get("objective_result_mode", objective_result_mode))
                ),
                "due_at": parsed.get("due_at") if isinstance(parsed.get("due_at"), str) else None,
                "allow_late": bool(parsed.get("allow_late", False)),
                "total_score": round(float(parsed.get("total_score", 100) or 100), 2),
                "rubric": str(parsed.get("rubric", "")).strip(),
                "questions": normalized_questions,
            }

            self.llm_logger.log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=response,
                model=self.model_name,
                module="HomeworkModule.assignment_draft",
                metadata={
                    "action": "generate_assignment_draft",
                    "assignment_type": assignment_type,
                    "topic": topic,
                    "status": "success",
                },
                username=teacher_username,
            )
            return {"ok": True, "draft": draft}
        except Exception as exc:
            logger.exception("LLM draft generation failed: %s", exc)
            return {"ok": False, "error": "llm_exception", "message": f"AI 调用异常：{str(exc)[:200]}"}

    def _invoke_llm_for_json(self, prompt: str):
        """优先请求 JSON 输出，若上游不支持 response_format 则自动降级。"""
        try:
            json_llm = self.llm.bind(response_format={"type": "json_object"})
            return json_llm.invoke(prompt)
        except Exception as exc:
            logger.warning("LLM json_object mode unsupported, fallback to plain invoke: %s", exc)
            return self.llm.invoke(prompt)

    def _retry_force_json_output(self, raw_content: str, original_prompt: str) -> Optional[str]:
        """在首次解析失败时，进行一次修复重试。"""
        if not self.llm:
            return None
        repair_prompt = (
            "你是 JSON 修复器。请将下面内容整理为一个可被 json.loads 解析的 JSON 对象。\n"
            "要求：\n"
            "1) 只输出 JSON 对象本体，不要任何解释；\n"
            "2) 保留原有字段语义，字段缺失时尽量从上下文补全；\n"
            "3) 禁止输出 markdown 代码块；\n\n"
            "原始任务提示：\n"
            f"{original_prompt}\n\n"
            "待修复内容：\n"
            f"{raw_content}\n"
        )
        try:
            response = self._invoke_llm_for_json(repair_prompt)
            content = getattr(response, "content", "") or ""
            return str(content).strip() or None
        except Exception as exc:
            logger.warning("LLM JSON repair retry failed: %s", exc)
            return None

    def _fallback_assignment_draft(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        class_name: str,
        *,
        course_id: str,
        node_id: str,
        node_name: str,
        node_path: List[str],
        chapter_context: str,
        objective_result_mode: str,
    ) -> Dict[str, Any]:
        chapter_meta = {
            "course_id": str(course_id or "course_big_data"),
            "node_id": str(node_id or ""),
            "node_name": str(node_name or ""),
            "node_path": [str(item).strip() for item in (node_path or []) if str(item).strip()],
            "chapter_context": str(chapter_context or ""),
            "objective_result_mode": self._normalize_objective_result_mode(objective_result_mode),
        }
        if assignment_type == "code":
            return {
                **chapter_meta,
                "title": f"{topic}编程实践（{difficulty}）",
                "description": f"面向{class_name or '课程场景'}的代码实践题。",
                "assignment_type": "code",
                "due_at": None,
                "allow_late": False,
                "total_score": 100,
                "rubric": "功能正确40分，边界处理20分，可读性20分，复杂度与说明20分。",
                "questions": [
                    {
                        "title": f"{topic}代码题",
                        "prompt": "输入一行两个整数a b，输出它们的和。",
                        "options": [],
                        "correct_answer": "",
                        "reference_answer": "读取标准输入并输出a+b，注意输入解析。",
                        "rubric": "通过测试用例、处理异常输入、代码清晰。",
                        "test_cases": [
                            {"input": "1 2\\n", "expected": "3", "weight": 30, "is_file_io": False},
                            {"input": "10 20\\n", "expected": "30", "weight": 30, "is_file_io": False},
                            {"input": "-5 3\\n", "expected": "-2", "weight": 40, "is_file_io": False},
                        ],
                    }
                ],
            }
        if assignment_type == "choice":
            return {
                **chapter_meta,
                "title": f"{topic}选择题（{difficulty}）",
                "description": f"面向{class_name or '课程场景'}的选择题作业。",
                "assignment_type": "choice",
                "due_at": None,
                "allow_late": False,
                "total_score": 100,
                "rubric": "选择正确并说明理由。",
                "questions": [
                    {
                        "title": f"{topic}选择题",
                        "prompt": "以下哪项最能描述该知识点的核心特点？",
                        "options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"],
                        "correct_answer": "A",
                        "reference_answer": "说明为什么A最符合。",
                        "rubric": "选项正确80分，理由充分20分。",
                        "test_cases": [],
                    }
                ],
            }
        if assignment_type == "objective":
            return {
                **chapter_meta,
                "title": f"{topic}客观题（{difficulty}）",
                "description": f"面向{class_name or '课程场景'}的客观题作业。",
                "assignment_type": "objective",
                "due_at": None,
                "allow_late": False,
                "total_score": 100,
                "rubric": "判断正确并给出简要说明。",
                "questions": [
                    {
                        "title": f"{topic}客观判断题",
                        "prompt": "该知识点的关键方法适用于任何场景。",
                        "options": ["A. 正确", "B. 错误"],
                        "correct_answer": "B",
                        "reference_answer": "存在适用条件与边界。",
                        "rubric": "判断正确80分，说明20分。",
                        "test_cases": [],
                    }
                ],
            }
        return {
            **chapter_meta,
            "title": f"{topic}分析与反思（{difficulty}）",
            "description": f"围绕{class_name or '课程场景'}的{topic}完成结构化分析。",
            "assignment_type": "subjective",
            "due_at": None,
            "allow_late": False,
            "total_score": 100,
            "rubric": "概念准确40分，论证逻辑30分，案例与反思20分，表达规范10分。",
            "questions": [
                {
                    "title": f"{topic}主观题",
                    "prompt": "请从概念解释、应用案例和改进建议三个方面完成作答。",
                    "options": [],
                    "correct_answer": "",
                    "reference_answer": "应覆盖定义、案例分析与可执行建议。",
                    "rubric": "观点完整、论证充分、结构清晰。",
                    "test_cases": [],
                }
            ],
        }

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        raw = (value or "").strip()
        if not raw:
            return None
        for candidate in (raw, raw.replace("Z", "+00:00")):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
        return None

    def _grade_with_llm(
        self,
        assignment: Dict[str, Any],
        submission: Dict[str, Any],
        teacher_username: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return None

        judge_report = self._build_code_judge_report(assignment, submission) if assignment.get("assignment_type") == "code" else None

        prompt = (
            "你是教师批改助手。根据作业要求和学生答案，给出0-100分和简短评语。严格输出 JSON：\n"
            "{\"score\": 85, \"feedback\": \"评语\", \"rationale\": \"评分理由\"}\n\n"
            f"【作业类型】{assignment.get('assignment_type', '')}\n"
            f"【标题】{assignment.get('title', '')}\n"
            f"【评分规则】{assignment.get('rubric', '')}\n"
            f"【题目】{json.dumps(assignment.get('questions', []), ensure_ascii=False)}\n"
            f"【学生答案】{json.dumps(submission.get('answers', []), ensure_ascii=False)}\n"
            f"【代码评测】{json.dumps(judge_report, ensure_ascii=False)}\n"
            "只输出 JSON 对象，不要解释。"
        )
        try:
            response = self.llm.invoke(prompt)
            raw_content = getattr(response, "content", "")
            parsed = self._extract_json_object(raw_content)
            if not parsed:
                logger.warning("LLM grading parse failed. Preview: %s", str(raw_content)[:200])
                return None
            score = float(parsed.get("score", 0))
            score = max(0.0, min(100.0, score))
            feedback = str(parsed.get("feedback", "")).strip() or "AI 未给出有效评语。"
            rationale = str(parsed.get("rationale", "")).strip()

            self.llm_logger.log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=response,
                model=self.model_name,
                module="HomeworkModule.ai_grading",
                metadata={
                    "action": "ai_grade_assist",
                    "assessment_type": assignment.get("assignment_type", "subjective"),
                    "assignment_id": assignment.get("id", ""),
                    "submission_id": submission.get("id", ""),
                },
                username=teacher_username,
            )
            return {
                "score": round(score, 2),
                "feedback": feedback,
                "rationale": rationale,
            }
        except Exception as exc:
            logger.exception("LLM grading failed: %s", exc)
            return None

    def _grade_with_heuristic(
        self,
        assignment: Dict[str, Any],
        submission: Dict[str, Any],
    ) -> Dict[str, Any]:
        assignment_type = assignment.get("assignment_type", "subjective")
        answers = submission.get("answers", []) or []
        answer_text = json.dumps(answers, ensure_ascii=False)
        length_score = min(len(answer_text) / 12.0, 60.0)

        if assignment_type == "code":
            judge_report = self._build_code_judge_report(assignment, submission)
            earned_score = float(judge_report.get("earned_score", 0.0) or 0.0)
            total_score = float(judge_report.get("total_score", 0.0) or 0.0)
            score = min(total_score, max(0.0, earned_score))
            feedback = (
                f"AI模型暂不可用，已回退规则评分：通过 {judge_report.get('passed', 0)}/"
                f"{judge_report.get('total', 0)}，得分 {round(score, 2)}/{round(total_score, 2)}，建议优先修复失败用例。"
            )
            rationale = json.dumps(judge_report, ensure_ascii=False)
        elif assignment_type in {"objective", "choice"}:
            score, feedback, rationale = self._grade_objective_like(assignment, submission)
        else:
            logic_tokens = ["因为", "所以", "例如", "首先", "其次", "最后"]
            hit = sum(1 for token in logic_tokens if token in answer_text)
            structure_score = min(hit * 5.0, 25.0)
            base = 35.0
            score = min(100.0, base + length_score + structure_score)
            feedback = "AI模型暂不可用，已给出启发式建议分。建议重点核对概念准确性与论证深度。"
            rationale = "基于文本长度和逻辑结构词覆盖的估计分数。"

        return {
            "score": round(score, 2),
            "feedback": feedback,
            "rationale": rationale,
        }

    def _build_code_judge_report(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
        questions = assignment.get("questions", []) if isinstance(assignment.get("questions"), list) else []
        answers = submission.get("answers", []) if isinstance(submission.get("answers"), list) else []

        answer_map: Dict[int, Dict[str, Any]] = {}
        for item in answers:
            if isinstance(item, dict):
                raw_idx = item.get("question_index", -1)
                idx = int(raw_idx if raw_idx is not None else -1)
                if idx >= 0:
                    answer_map[idx] = item

        total_score = 0.0
        earned_score = 0.0
        passed = 0
        total = 0
        details: List[Dict[str, Any]] = []
        case_no = 1

        if not questions:
            questions = [{"test_cases": [{"input": "1 2\\n", "expected": "3", "weight": 100, "is_file_io": False}]}]

        for q_idx, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            answer_item = answer_map.get(q_idx, {})
            code_text = str(answer_item.get("answer", ""))
            requested_lang = str(answer_item.get("language", "")).strip().lower()
            auto_lang = self._detect_language_from_code(code_text)
            language = auto_lang or requested_lang or "python"

            question_cases: List[Dict[str, Any]] = []
            raw_cases = q.get("test_cases") if isinstance(q.get("test_cases"), list) else []
            for case in raw_cases:
                if isinstance(case, dict):
                    normalized_case = {
                        "input": self._normalize_test_case_text(case.get("input", "")),
                        "expected": self._normalize_test_case_text(case.get("expected", case.get("output", ""))),
                        "weight": float(case.get("weight", 0) or 0),
                        "is_file_io": bool(case.get("is_file_io", False)),
                    }
                    if normalized_case["expected"]:
                        question_cases.append(normalized_case)

            if not question_cases:
                question_cases = [{"input": "1 2\\n", "expected": "3", "weight": 100, "is_file_io": False}]

            if sum(float(item.get("weight", 0) or 0) for item in question_cases) <= 0:
                uniform = round(100.0 / len(question_cases), 2)
                for item in question_cases:
                    item["weight"] = uniform

            if not code_text.strip():
                for case in question_cases:
                    weight = float(case.get("weight", 0) or 0)
                    total_score += weight
                    total += 1
                    details.append(
                        {
                            "case": case_no,
                            "question_index": q_idx,
                            "ok": False,
                            "status": "No Code",
                            "input": case.get("input", ""),
                            "expected": case.get("expected", ""),
                            "actual": "",
                            "stderr": "empty_code",
                            "weight": round(weight, 2),
                            "score": 0.0,
                            "is_file_io": bool(case.get("is_file_io", False)),
                            "exit_code": -2,
                            "time_ms": 0,
                            "memory_kb": 0,
                            "language": language,
                        }
                    )
                    case_no += 1
                continue

            report = self.sandbox_service.judge_code(code=code_text, language=language, test_cases=question_cases)
            total_score += float(report.get("total_score", 0.0) or 0.0)
            earned_score += float(report.get("earned_score", 0.0) or 0.0)
            total += int(report.get("total", 0) or 0)
            passed += int(report.get("passed", 0) or 0)

            for detail in report.get("details", []) or []:
                if isinstance(detail, dict):
                    details.append(
                        {
                            **detail,
                            "case": case_no,
                            "question_index": q_idx,
                            "language": report.get("language", language),
                        }
                    )
                    case_no += 1

        score_rate = (earned_score / total_score) if total_score > 0 else 0.0
        return {
            "language": "mixed",
            "passed": passed,
            "total": total,
            "earned_score": round(earned_score, 2),
            "total_score": round(total_score, 2),
            "score_rate": score_rate,
            "details": details,
        }

    def _detect_language_from_code(self, code_text: str) -> str:
        text = str(code_text or "")
        low = text.lower()
        if "public class" in text or "import java" in low or "system.out.println" in low:
            return "java"
        if "#include" in text or "using namespace std" in low or "int main(" in low:
            return "cpp"
        if "def " in low or "print(" in low or "input(" in low:
            return "python"
        return ""

    def _normalize_test_case_text(self, raw: Any) -> str:
        text = str(raw or "")
        return text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")

    def _extract_judge_report(self, raw: Any) -> Dict[str, Any]:
        text = str(raw or "").strip()
        if not text.startswith("{"):
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _build_code_question_results(self, judge_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        details = judge_report.get("details") if isinstance(judge_report.get("details"), list) else []
        grouped: Dict[int, Dict[str, Any]] = {}
        for item in details:
            if not isinstance(item, dict):
                continue
            q_idx = int(item.get("question_index", 0) or 0)
            bucket = grouped.setdefault(
                q_idx,
                {
                    "question_index": q_idx,
                    "type": "code",
                    "passed": 0,
                    "total": 0,
                    "earned_score": 0.0,
                    "total_score": 0.0,
                    "cases": [],
                },
            )
            ok = bool(item.get("ok", False))
            weight = float(item.get("weight", 0) or 0)
            score = float(item.get("score", 0) or 0)
            bucket["total"] += 1
            bucket["passed"] += 1 if ok else 0
            bucket["total_score"] += weight
            bucket["earned_score"] += score
            bucket["cases"].append(
                {
                    "case": item.get("case"),
                    "ok": ok,
                    "status": item.get("status", ""),
                    "score": score,
                    "weight": weight,
                    "language": item.get("language", ""),
                }
            )

        result: List[Dict[str, Any]] = []
        for q_idx in sorted(grouped.keys()):
            row = grouped[q_idx]
            row["earned_score"] = round(float(row["earned_score"]), 2)
            row["total_score"] = round(float(row["total_score"]), 2)
            result.append(row)
        return result

    def _build_objective_question_results(
        self,
        assignment: Dict[str, Any],
        submission: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        questions = assignment.get("questions", []) if isinstance(assignment.get("questions"), list) else []
        answers = submission.get("answers", []) if isinstance(submission.get("answers"), list) else []
        answer_map: Dict[int, str] = {}
        for item in answers:
            if isinstance(item, dict):
                raw_idx = item.get("question_index", -1)
                idx = int(raw_idx if raw_idx is not None else -1)
                if idx >= 0:
                    answer_map[idx] = str(item.get("answer", "")).strip()

        def normalize(raw: str) -> str:
            tokens = [x.strip().upper() for x in str(raw or "").split(",") if x.strip()]
            return ",".join(sorted(tokens))

        result: List[Dict[str, Any]] = []
        for idx, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            expected = normalize(str(q.get("correct_answer", "")))
            actual = normalize(answer_map.get(idx, ""))
            if not expected:
                ok = None
            else:
                ok = actual == expected
            result.append(
                {
                    "question_index": idx,
                    "type": str(assignment.get("assignment_type", "objective")),
                    "ok": ok,
                    "expected": expected,
                    "actual": actual,
                }
            )
        return result

    def _build_subjective_question_results(
        self,
        assignment: Dict[str, Any],
        submission: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        questions = assignment.get("questions", []) if isinstance(assignment.get("questions"), list) else []
        answers = submission.get("answers", []) if isinstance(submission.get("answers"), list) else []
        answer_map: Dict[int, str] = {}
        for item in answers:
            if isinstance(item, dict):
                raw_idx = item.get("question_index", -1)
                idx = int(raw_idx if raw_idx is not None else -1)
                if idx >= 0:
                    answer_map[idx] = str(item.get("answer", "")).strip()

        return [
            {
                "question_index": idx,
                "type": "subjective",
                "answered": bool(answer_map.get(idx, "")),
            }
            for idx, _ in enumerate(questions)
        ]

    def _grade_objective_like(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> tuple[float, str, str]:
        questions = assignment.get("questions", []) if isinstance(assignment.get("questions"), list) else []
        answers = submission.get("answers", []) if isinstance(submission.get("answers"), list) else []
        answer_map: Dict[int, str] = {}
        for item in answers:
            if isinstance(item, dict):
                raw_idx = item.get("question_index", -1)
                idx = int(raw_idx if raw_idx is not None else -1)
                if idx >= 0:
                    answer_map[idx] = str(item.get("answer", "")).strip()

        total = 0
        correct = 0
        details: List[str] = []

        def normalize_answer(raw: str) -> str:
            tokens = [x.strip().upper() for x in str(raw or "").split(",") if x.strip()]
            return ",".join(sorted(tokens))

        for idx, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            expected = normalize_answer(str(q.get("correct_answer", "")).strip())
            if not expected:
                continue
            total += 1
            actual = normalize_answer(answer_map.get(idx, ""))
            ok = actual == expected
            if ok:
                correct += 1
            details.append(f"Q{idx + 1}: {'√' if ok else '×'} (答:{actual or '-'} / 标准:{expected})")

        if total == 0:
            return 60.0, "未提供标准答案，已给默认建议分。", "missing_correct_answer"
        score = round((correct / total) * 100, 2)
        feedback = f"客观题自动核对：正确 {correct}/{total}。"
        rationale = "\n".join(details)
        return score, feedback, rationale

    def _extract_json_array(self, text: str) -> Optional[List[Dict[str, Any]]]:
        if not text:
            return None
        block = self._extract_json_block(text)
        if not block:
            return None
        try:
            data = json.loads(block)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except Exception:
            return None
        return None

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        normalized = self._normalize_llm_text(text)
        try:
            data = json.loads(normalized)
            if isinstance(data, dict):
                return data
            logger.warning(
                "_extract_json_object: JSON parsed from full text but got type=%s instead of dict, preview: %s",
                type(data).__name__, normalized[:200],
            )
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.warning("_extract_json_object: unexpected error in full-text parse: %s", exc)

        block = self._extract_json_block(normalized)
        if not block:
            logger.warning("_extract_json_object: no JSON block found in text (len=%d), text preview: %s", len(normalized), normalized[:200])
            return None
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
            logger.warning(
                "_extract_json_object: JSON parsed but got type=%s instead of dict, block preview: %s",
                type(data).__name__, block[:200],
            )
        except json.JSONDecodeError as exc:
            logger.warning(
                "_extract_json_object: JSON parse failed: %s at pos=%s, block preview: %s",
                exc, getattr(exc, "pos", -1), block[:200]
            )
            return None
        except Exception as exc:
            logger.warning("_extract_json_object: unexpected error: %s", exc)
            return None
        return None

    def _has_garbled_output(self, text: str) -> bool:
        """检测 LLM 输出是否包含大量重复模式（模型跑飞/幻觉特征）."""
        if len(text) < 100:
            return False
        # 检查是否有相同短模式重复多次（如 "D\"\nD\"\n"）
        patterns = [
            r'(\\?"?D\\?"?\s*\\n\s*){10,}',   # D"\nD"\n 重复
            r'([A-D]\\?"?\s*\\n\s*){20,}',     # A\nB\n 等重复
            r'(\b\w{1,3}\\n\s*){30,}',          # 短词+换行重复30次以上
        ]
        for pat in patterns:
            if re.search(pat, text):
                logger.warning("Garbled output detected: pattern=%s", pat)
                return True
        # 检查整体重复度：将文本分成两半，如果后半部分大量重复前半部分的短片段
        if len(text) > 400:
            half = len(text) // 2
            first = text[:half]
            second = text[half:]
            # 取第二半的前50个字符，看是否在第二半中重复出现
            sample = second[:30]
            if len(sample) > 5 and second.count(sample) > 5:
                return True
        return False

    def _extract_json_block(self, text: str) -> str:
        content = self._normalize_llm_text(text)
        fenced = re.search(r"```(?:json)?\\s*([\\s\\S]*?)\\s*```", content)
        if fenced:
            return fenced.group(1).strip()

        balanced_obj = self._extract_balanced_json_fragment(content, "{", "}")
        if balanced_obj:
            return balanced_obj

        balanced_arr = self._extract_balanced_json_fragment(content, "[", "]")
        if balanced_arr:
            return balanced_arr

        for start, end in [("[", "]"), ("{", "}")]:
            i = content.find(start)
            j = content.rfind(end)
            if i != -1 and j != -1 and j > i:
                return content[i : j + 1]
        return content

    def _extract_balanced_json_fragment(self, text: str, open_char: str, close_char: str) -> str:
        """从混杂文本中提取第一个括号平衡的 JSON 片段。"""
        start = text.find(open_char)
        if start == -1:
            return ""
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch == open_char:
                depth += 1
                continue
            if ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return ""

    def _normalize_llm_text(self, text: str) -> str:
        normalized = str(text or "").strip()
        if normalized.startswith("\ufeff"):
            normalized = normalized.lstrip("\ufeff")
        return normalized

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from HomeworkModule.code_judge import run_python_code_judge
from HomeworkModule.models import AssignmentQuestionGenerateRequest
from HomeworkModule.repository import HomeworkRepository
from tools.llm_logger import get_llm_logger


class HomeworkService:
    def __init__(self, repository: Optional[HomeworkRepository] = None) -> None:
        self.repository = repository or HomeworkRepository()
        self.model_name = os.environ.get("model_name", "")
        self.base_url = os.environ.get("base_url", "")
        self.api_key = os.environ.get("api_key", "")
        self.llm = self._build_llm()
        self.llm_logger = get_llm_logger()

    def _build_llm(self) -> Optional[ChatOpenAI]:
        if not (self.model_name and self.base_url and self.api_key):
            return None
        try:
            return ChatOpenAI(
                model=self.model_name,
                temperature=0.2,
                base_url=self.base_url,
                api_key=self.api_key,
            )
        except Exception:
            return None

    def _normalize_assignment_type(self, value: str) -> str:
        raw = str(value or "subjective").strip().lower()
        if raw == "code_practice":
            return "code"
        if raw not in {"subjective", "objective", "choice", "code"}:
            return "subjective"
        return raw

    def create_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        payload["status"] = "published" if payload.get("publish_now") else "draft"
        return self.repository.create_assignment(payload)

    def list_assignments(
        self,
        created_by: Optional[str] = None,
        status: Optional[str] = None,
        include_statuses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_assignments(
            created_by=created_by,
            status=status,
            include_statuses=include_statuses,
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
            return self._auto_grade_if_code(assignment, submitted)

        created = self.repository.create_submission(payload)
        return self._auto_grade_if_code(assignment, created)

    def _auto_grade_if_code(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> Dict[str, Any]:
        if assignment.get("assignment_type") != "code":
            return submission

        judge_report = self._build_code_judge_report(assignment, submission)
        passed = int(judge_report.get("passed", 0) or 0)
        total = int(judge_report.get("total", 0) or 0)
        pass_rate = float(judge_report.get("pass_rate", 0.0) or 0.0)
        score = round(min(100.0, max(0.0, pass_rate * 100.0)), 2)
        feedback = f"系统自动判题：通过 {passed}/{total}。"

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

    def list_submissions(
        self,
        assignment_id: Optional[str] = None,
        student_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_submissions(
            assignment_id=assignment_id,
            student_username=student_username,
        )

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
    ) -> Dict[str, Any]:
        normalized_assignment_type = self._normalize_assignment_type(assignment_type)
        draft = self._generate_assignment_draft_with_llm(
            assignment_type=normalized_assignment_type,
            topic=topic,
            difficulty=difficulty,
            class_name=class_name,
            teacher_username=teacher_username,
        )
        if draft:
            return {"ok": True, "draft": draft, "generated_at": datetime.now().isoformat()}

        return {
            "ok": False,
            "message": "ai_unavailable",
            "draft": self._fallback_assignment_draft(normalized_assignment_type, topic, difficulty, class_name),
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
            return None

        prompt = (
            "你是资深课程教师助教。请根据输入生成作业题目，严格输出 JSON 数组，不要输出其他内容。"
            "每个元素都包含 title, prompt, options, correct_answer, reference_answer, rubric, test_cases 字段。"
            f"题型: {request.assignment_type}; 主题: {request.topic}; 数量: {request.count}; "
            f"难度: {request.difficulty}; 语言: {request.language}; 额外要求: {request.extra_requirements}。"
        )
        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", "")
            parsed = self._extract_json_array(content)
            if not parsed:
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
        except Exception:
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
                            {"input": "示例输入1", "expected": "示例输出1"},
                            {"input": "边界输入", "expected": "边界输出"},
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

    def _generate_assignment_draft_with_llm(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        class_name: str,
        teacher_username: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.llm:
            return None

        prompt = (
            "你是高校课程助教。请生成可直接发布的作业草稿，严格输出JSON对象。"
            "字段必须包含：title, description, assignment_type, due_at, allow_late, total_score, rubric, questions。"
            "questions 是数组，每个元素包含 title, prompt, options, correct_answer, reference_answer, rubric, test_cases。"
            "assignment_type 支持 subjective/objective/choice/code。"
            "若 assignment_type=subjective，则 options 为空且 test_cases 为空。"
            "若 assignment_type=objective 或 choice，则必须提供 options 和 correct_answer。"
            "若为 code，则给至少3条 input/expected 用例。"
            f"题型: {assignment_type}; 主题: {topic}; 难度: {difficulty}; 班级: {class_name or '通用班级'}。"
        )
        try:
            response = self.llm.invoke(prompt)
            parsed = self._extract_json_object(getattr(response, "content", ""))
            if not parsed:
                return None
            questions = parsed.get("questions")
            if not isinstance(questions, list) or not questions:
                return None
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
                return None

            assignment_type_value = str(parsed.get("assignment_type", assignment_type)).strip().lower()
            if assignment_type_value not in {"subjective", "objective", "choice", "code"}:
                assignment_type_value = assignment_type
            draft = {
                "title": str(parsed.get("title", "")).strip() or f"{topic}作业（{difficulty}）",
                "description": str(parsed.get("description", "")).strip(),
                "assignment_type": assignment_type_value,
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
                },
                username=teacher_username,
            )
            return draft
        except Exception:
            return None

    def _fallback_assignment_draft(
        self,
        assignment_type: str,
        topic: str,
        difficulty: str,
        class_name: str,
    ) -> Dict[str, Any]:
        if assignment_type == "code":
            return {
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
                            {"input": "1 2\\n", "expected": "3"},
                            {"input": "10 20\\n", "expected": "30"},
                            {"input": "-5 3\\n", "expected": "-2"},
                        ],
                    }
                ],
            }
        if assignment_type == "choice":
            return {
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
            "你是教师的批改助手。请基于作业要求和学生答案，给出0到100分建议分与简洁评语。"
            "严格输出JSON对象，字段为 score, feedback, rationale。"
            f"作业类型: {assignment.get('assignment_type', '')}; 标题: {assignment.get('title', '')};"
            f"评分规则: {assignment.get('rubric', '')};"
            f"题目: {json.dumps(assignment.get('questions', []), ensure_ascii=False)};"
            f"学生答案: {json.dumps(submission.get('answers', []), ensure_ascii=False)};"
            f"代码题规则评测: {json.dumps(judge_report, ensure_ascii=False)}。"
        )
        try:
            response = self.llm.invoke(prompt)
            parsed = self._extract_json_object(getattr(response, "content", ""))
            if not parsed:
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
        except Exception:
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
            pass_rate = float(judge_report.get("pass_rate", 0.0) or 0.0)
            score = min(100.0, max(0.0, pass_rate * 100.0))
            feedback = (
                f"AI模型暂不可用，已回退规则评分：通过 {judge_report.get('passed', 0)}/"
                f"{judge_report.get('total', 0)}，建议优先修复失败用例。"
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
        code_answers: List[str] = []
        for item in submission.get("answers", []) or []:
            if isinstance(item, dict):
                code_answers.append(str(item.get("answer", "")))
        code_text = "\n\n".join([x for x in code_answers if x.strip()])

        test_cases: List[Dict[str, Any]] = []
        for q in questions:
            if isinstance(q, dict) and isinstance(q.get("test_cases"), list):
                for case in q.get("test_cases"):
                    if isinstance(case, dict):
                        test_cases.append(case)
        if not test_cases:
            test_cases = [
                {"input": "1 2\n", "expected": "3"},
                {"input": "5 7\n", "expected": "12"},
            ]
        return run_python_code_judge(code_text, test_cases)

    def _grade_objective_like(self, assignment: Dict[str, Any], submission: Dict[str, Any]) -> tuple[float, str, str]:
        questions = assignment.get("questions", []) if isinstance(assignment.get("questions"), list) else []
        answers = submission.get("answers", []) if isinstance(submission.get("answers"), list) else []
        answer_map: Dict[int, str] = {}
        for item in answers:
            if isinstance(item, dict):
                idx = int(item.get("question_index", -1) or -1)
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
        block = self._extract_json_block(text)
        if not block:
            return None
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
        return None

    def _extract_json_block(self, text: str) -> str:
        content = text.strip()
        fenced = re.search(r"```(?:json)?\\s*([\\s\\S]*?)\\s*```", content)
        if fenced:
            return fenced.group(1).strip()

        for start, end in [("[", "]"), ("{", "}")]:
            i = content.find(start)
            j = content.rfind(end)
            if i != -1 and j != -1 and j > i:
                return content[i : j + 1]
        return content

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_openai import ChatOpenAI

from DatabaseModule.database_factory import DatabaseFactory
from HomeworkModule.service import HomeworkService
from tools.llm_logger import get_llm_logger
from tools.session_manager import get_session_manager


NAMESPACE_KEY = "teacher_intervention_module_v1"


class TeacherInterventionService:
    def __init__(self) -> None:
        self.store = DatabaseFactory.get_store()
        self.session_manager = get_session_manager()
        self.homework_service = HomeworkService()
        self.llm_logger = get_llm_logger()
        self.model_name = str(os.environ.get("model_name") or "").strip()
        self.base_url = str(os.environ.get("base_url") or "").strip()
        self.api_key = str(os.environ.get("api_key") or "").strip()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _extract_json_object(self, raw_text: str) -> dict:
        text = str(raw_text or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            left = text.find("{")
            right = text.rfind("}")
            if left >= 0 and right > left:
                try:
                    return json.loads(text[left : right + 1])
                except json.JSONDecodeError:
                    return {}
        return {}

    def _get_user_module_state(self, username: str) -> Dict[str, Any]:
        state = self.session_manager.get_user_value(username, NAMESPACE_KEY, default={})
        if isinstance(state, dict):
            return state
        return {}

    def _set_user_module_state(self, username: str, module_state: Dict[str, Any]) -> None:
        payload = dict(module_state)
        payload["updated_at"] = self._now()
        self.session_manager.set_user_value(username, NAMESPACE_KEY, payload)

    def _normalize_question_type(self, value: str) -> str:
        raw = str(value or "subjective").strip().lower()
        alias_map = {
            "blank": "fill_blank",
            "fillblank": "fill_blank",
            "single": "single_choice",
            "choice": "single_choice",
            "multiple": "multiple_choice",
            "multi_choice": "multiple_choice",
            "programming": "code",
        }
        normalized = alias_map.get(raw, raw)
        if normalized not in {"fill_blank", "single_choice", "multiple_choice", "code", "subjective"}:
            return "subjective"
        return normalized

    def _normalize_question(self, raw: Dict[str, Any], index: int, default_difficulty: str) -> Dict[str, Any]:
        question_type = self._normalize_question_type(str(raw.get("question_type") or "subjective"))
        options = raw.get("options")
        if not isinstance(options, list):
            options = []
        safe_options = [str(item).strip() for item in options if str(item).strip()]
        test_cases = raw.get("test_cases")
        if not isinstance(test_cases, list):
            test_cases = []
        safe_cases = []
        for case in test_cases:
            if not isinstance(case, dict):
                continue
            input_text = str(case.get("input") or "").strip()
            expected_text = str(case.get("expected") or "").strip()
            if not input_text and not expected_text:
                continue
            safe_cases.append({"input": input_text, "expected": expected_text})

        return {
            "id": str(raw.get("id") or f"q-{index + 1}"),
            "title": str(raw.get("title") or f"题目 {index + 1}"),
            "prompt": str(raw.get("prompt") or ""),
            "question_type": question_type,
            "options": safe_options,
            "correct_answer": str(raw.get("correct_answer") or ""),
            "reference_answer": str(raw.get("reference_answer") or ""),
            "rubric": str(raw.get("rubric") or ""),
            "test_cases": safe_cases,
            "difficulty": str(raw.get("difficulty") or default_difficulty or "中等"),
        }

    def _build_student_answer_entries(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = self._now()
        entries = []
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            entries.append(
                {
                    "question_id": qid,
                    "question_title": str(question.get("title") or f"题目 {index + 1}"),
                    "question_type": self._normalize_question_type(str(question.get("question_type") or "subjective")),
                    "answer": "",
                    "note": "",
                    "status": "pending",
                    "updated_at": now,
                }
            )
        return entries

    def _build_grade_entries(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = self._now()
        grades = []
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            grades.append(
                {
                    "question_id": qid,
                    "question_title": str(question.get("title") or f"题目 {index + 1}"),
                    "question_type": self._normalize_question_type(str(question.get("question_type") or "subjective")),
                    "ai_score": None,
                    "ai_feedback": "",
                    "ai_detail": {},
                    "teacher_score": None,
                    "teacher_comment": "",
                    "final_score": None,
                    "status": "pending",
                    "ai_graded_at": None,
                    "teacher_graded_at": None,
                    "updated_at": now,
                }
            )
        return grades

    def _split_tokens(self, text: str) -> List[str]:
        raw = re.split(r"[\s,，。；;、:：\n\r\t]+", str(text or ""))
        return [token.strip() for token in raw if token.strip()]

    def _normalize_choice_answer(self, answer: str) -> str:
        items = [token.upper() for token in self._split_tokens(answer)]
        return ",".join(sorted(set(items)))

    def _grade_textual(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        clean_answer = str(answer or "").strip()
        reference = str(question.get("reference_answer") or "").strip()
        rubric = str(question.get("rubric") or "").strip()

        length_part = min(len(clean_answer) / 220.0, 1.0)
        structure_part = 1.0 if any(flag in clean_answer for flag in ["步骤", "思路", "首先", "然后", "最后", "总结"]) else 0.0
        ref_tokens = [token for token in self._split_tokens(reference) if len(token) >= 2][:12]
        hit_count = 0
        if ref_tokens:
            hit_count = sum(1 for token in ref_tokens if token in clean_answer)
        keyword_part = (hit_count / len(ref_tokens)) if ref_tokens else 0.0

        criteria = [
            {
                "name": "内容完整性",
                "score": round(length_part * 40, 2),
                "full_score": 40,
                "reason": f"答案长度与内容展开程度评估（长度={len(clean_answer)}）。",
            },
            {
                "name": "关键要点命中",
                "score": round(keyword_part * 40, 2),
                "full_score": 40,
                "reason": f"命中参考要点 {hit_count}/{len(ref_tokens) if ref_tokens else 0}。",
            },
            {
                "name": "表达与结构",
                "score": 20.0 if structure_part > 0 else 8.0,
                "full_score": 20,
                "reason": "检测到分步表达结构。" if structure_part > 0 else "缺少明显分步结构。",
            },
        ]
        total = round(sum(item["score"] for item in criteria), 2)
        feedback = f"文本题自动评分 {total}/100。"
        if rubric:
            feedback += " 已参考教师评分细则。"
        return {"score": total, "feedback": feedback, "detail": {"total_score": total, "criteria": criteria}}

    def _grade_fill_blank(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        expected = str(question.get("correct_answer") or question.get("reference_answer") or "").strip()
        normalized_expected = " ".join(expected.lower().split())
        normalized_answer = " ".join(str(answer or "").lower().split())
        is_correct = normalized_expected != "" and normalized_answer == normalized_expected
        score = 100.0 if is_correct else 0.0
        criteria = [
            {
                "name": "答案匹配",
                "score": score,
                "full_score": 100,
                "reason": "与标准答案完全一致。" if is_correct else "与标准答案不一致。",
            }
        ]
        feedback = "填空题判定正确。" if is_correct else f"填空题答案不匹配，期望：{expected or '-'}。"
        return {
            "score": score,
            "feedback": feedback,
            "detail": {
                "total_score": score,
                "criteria": criteria,
                "match": {
                    "normalized_answer": normalized_answer,
                    "expected": normalized_expected,
                    "is_correct": is_correct,
                },
            },
        }

    def _grade_choice(self, question: Dict[str, Any], answer: str, multiple: bool) -> Dict[str, Any]:
        expected = str(question.get("correct_answer") or "").strip()
        normalized_expected = self._normalize_choice_answer(expected)
        normalized_answer = self._normalize_choice_answer(answer)
        if not normalized_expected:
            return self._grade_textual(question, answer)

        if multiple:
            expected_set = set(normalized_expected.split(",")) if normalized_expected else set()
            answer_set = set(normalized_answer.split(",")) if normalized_answer else set()
            hit = len(expected_set & answer_set)
            wrong = len(answer_set - expected_set)
            miss = len(expected_set - answer_set)
            raw = 0.0
            if expected_set:
                raw = max(0.0, (hit / len(expected_set)) - (wrong * 0.25))
            score = round(min(100.0, raw * 100.0), 2)
            reason = f"命中 {hit} 项，漏选 {miss} 项，错选 {wrong} 项。"
            is_correct = miss == 0 and wrong == 0 and len(expected_set) > 0
        else:
            is_correct = normalized_expected == normalized_answer and normalized_expected != ""
            score = 100.0 if is_correct else 0.0
            reason = "单选答案匹配。" if is_correct else f"标准答案 {normalized_expected}，提交 {normalized_answer or '-'}。"

        criteria = [
            {
                "name": "选项匹配度",
                "score": score,
                "full_score": 100,
                "reason": reason,
            }
        ]
        feedback = "选择题判定正确。" if is_correct else "选择题未完全匹配标准答案。"
        return {
            "score": score,
            "feedback": feedback,
            "detail": {
                "total_score": score,
                "criteria": criteria,
                "match": {
                    "normalized_answer": normalized_answer,
                    "expected": normalized_expected,
                    "is_correct": is_correct,
                },
            },
        }

    def _grade_code(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        test_cases = question.get("test_cases")
        if not isinstance(test_cases, list) or not test_cases:
            return self._grade_textual(question, answer)

        code_text = str(answer or "").strip()
        case_details: List[Dict[str, Any]] = []
        passed = 0
        for index, case in enumerate(test_cases):
            if not isinstance(case, dict):
                continue
            expected = str(case.get("expected") or "").strip()
            actual = code_text
            ok = expected != "" and expected in code_text
            if ok:
                passed += 1
            case_details.append(
                {
                    "index": index + 1,
                    "ok": ok,
                    "input": str(case.get("input") or ""),
                    "expected": expected,
                    "actual": actual[:120],
                    "reason": "答案中包含期望输出片段。" if ok else "未命中期望输出片段。",
                }
            )
        total_cases = len(case_details)
        score = round((passed / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
        criteria = [
            {
                "name": "测试点通过率",
                "score": score,
                "full_score": 100,
                "reason": f"通过 {passed}/{total_cases} 个测试点（轻量规则）。",
            }
        ]
        feedback = f"代码题自动评分 {score}/100，通过 {passed}/{total_cases}。"
        return {
            "score": score,
            "feedback": feedback,
            "detail": {
                "total_score": score,
                "criteria": criteria,
                "code": {
                    "case_passed": passed,
                    "case_total": total_cases,
                    "case_details": case_details,
                },
            },
        }

    def _compute_ai_score_feedback(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        clean_answer = str(answer or "").strip()
        if not clean_answer:
            return {
                "score": 0.0,
                "feedback": "未作答。",
                "detail": {
                    "total_score": 0.0,
                    "criteria": [
                        {"name": "作答状态", "score": 0.0, "full_score": 100, "reason": "当前题目未提交答案。"}
                    ],
                },
            }

        question_type = self._normalize_question_type(str(question.get("question_type") or "subjective"))
        if question_type == "fill_blank":
            return self._grade_fill_blank(question, clean_answer)
        if question_type == "single_choice":
            return self._grade_choice(question, clean_answer, multiple=False)
        if question_type == "multiple_choice":
            return self._grade_choice(question, clean_answer, multiple=True)
        if question_type == "code":
            return self._grade_code(question, clean_answer)
        return self._grade_textual(question, clean_answer)

    def _ensure_package_struct(self, package: Dict[str, Any]) -> None:
        questions = package.get("questions") if isinstance(package.get("questions"), list) else []
        answers = package.get("answers")
        grades = package.get("grades")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(questions)
            package["answers"] = answers
        if not isinstance(grades, list):
            grades = self._build_grade_entries(questions)
            package["grades"] = grades

        answer_map = {str(item.get("question_id") or ""): item for item in answers if isinstance(item, dict)}
        grade_map = {str(item.get("question_id") or ""): item for item in grades if isinstance(item, dict)}
        now = self._now()
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            normalized_type = self._normalize_question_type(str(question.get("question_type") or "subjective"))
            if qid not in answer_map:
                answers.append(
                    {
                        "question_id": qid,
                        "question_title": str(question.get("title") or f"题目 {index + 1}"),
                        "question_type": normalized_type,
                        "answer": "",
                        "note": "",
                        "status": "pending",
                        "updated_at": now,
                    }
                )
            else:
                answer_map[qid]["question_title"] = str(question.get("title") or answer_map[qid].get("question_title") or f"题目 {index + 1}")
                answer_map[qid]["question_type"] = normalized_type
            if qid not in grade_map:
                grades.append(
                    {
                        "question_id": qid,
                        "question_title": str(question.get("title") or f"题目 {index + 1}"),
                        "question_type": normalized_type,
                        "ai_score": None,
                        "ai_feedback": "",
                        "ai_detail": {},
                        "teacher_score": None,
                        "teacher_comment": "",
                        "final_score": None,
                        "status": "pending",
                        "ai_graded_at": None,
                        "teacher_graded_at": None,
                        "updated_at": now,
                    }
                )
            else:
                grade_map[qid]["question_title"] = str(question.get("title") or grade_map[qid].get("question_title") or f"题目 {index + 1}")
                grade_map[qid]["question_type"] = normalized_type
                if not isinstance(grade_map[qid].get("ai_detail"), dict):
                    grade_map[qid]["ai_detail"] = {}
        package["answers"] = answers
        package["grades"] = grades

    def _auto_grade_single_question(self, package: Dict[str, Any], question_id: str, *, now: Optional[str] = None) -> None:
        self._ensure_package_struct(package)
        now_text = now or self._now()
        question_map = {
            str(item.get("id") or ""): item
            for item in (package.get("questions") if isinstance(package.get("questions"), list) else [])
            if isinstance(item, dict)
        }
        answer_rows = package.get("answers") if isinstance(package.get("answers"), list) else []
        grade_rows = package.get("grades") if isinstance(package.get("grades"), list) else []
        answer_row = next((item for item in answer_rows if isinstance(item, dict) and str(item.get("question_id") or "") == question_id), None)
        grade_row = next((item for item in grade_rows if isinstance(item, dict) and str(item.get("question_id") or "") == question_id), None)
        question = question_map.get(question_id)
        if not isinstance(answer_row, dict) or not isinstance(grade_row, dict) or not isinstance(question, dict):
            return

        answer_text = str(answer_row.get("answer") or "").strip()
        if not answer_text:
            grade_row["ai_score"] = None
            grade_row["ai_feedback"] = ""
            grade_row["ai_detail"] = {}
            grade_row["status"] = "pending"
            grade_row["final_score"] = grade_row.get("teacher_score")
            grade_row["updated_at"] = now_text
            return

        judged = self._compute_ai_score_feedback(question, answer_text)
        grade_row["question_type"] = self._normalize_question_type(str(question.get("question_type") or "subjective"))
        grade_row["ai_score"] = judged["score"]
        grade_row["ai_feedback"] = judged["feedback"]
        grade_row["ai_detail"] = judged.get("detail") or {}
        grade_row["ai_graded_at"] = now_text
        grade_row["status"] = "ai_graded" if grade_row.get("teacher_score") is None else "teacher_graded"
        grade_row["final_score"] = grade_row.get("teacher_score")
        if grade_row.get("final_score") is None:
            grade_row["final_score"] = grade_row.get("ai_score")
        grade_row["updated_at"] = now_text

    def _recompute_score_summary(self, package: Dict[str, Any], *, now: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_package_struct(package)
        now_text = now or self._now()
        grade_rows = package.get("grades") if isinstance(package.get("grades"), list) else []
        final_scores: List[float] = []
        ai_scores: List[float] = []
        teacher_scores: List[float] = []
        graded_questions = 0
        for row in grade_rows:
            if not isinstance(row, dict):
                continue
            ai_score = row.get("ai_score")
            teacher_score = row.get("teacher_score")
            final_score = row.get("final_score")
            if isinstance(ai_score, (int, float)):
                ai_scores.append(float(ai_score))
            if isinstance(teacher_score, (int, float)):
                teacher_scores.append(float(teacher_score))
            if isinstance(final_score, (int, float)):
                final_scores.append(float(final_score))
                graded_questions += 1
        question_count = len([x for x in grade_rows if isinstance(x, dict)])
        summary = {
            "question_count": question_count,
            "graded_questions": graded_questions,
            "average_final_score": round(sum(final_scores) / len(final_scores), 2) if final_scores else None,
            "average_ai_score": round(sum(ai_scores) / len(ai_scores), 2) if ai_scores else None,
            "average_teacher_score": round(sum(teacher_scores) / len(teacher_scores), 2) if teacher_scores else None,
            "updated_at": now_text,
        }
        package["score_summary"] = summary
        return summary

    def _recompute_progress(self, package: Dict[str, Any], *, now: Optional[str] = None) -> Dict[str, Any]:
        now_text = now or self._now()
        self._ensure_package_struct(package)
        answers = package.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(
                package.get("questions") if isinstance(package.get("questions"), list) else []
            )
            package["answers"] = answers

        normalized_answers = []
        for item in answers:
            if not isinstance(item, dict):
                continue
            answer_text = str(item.get("answer") or "").strip()
            normalized_answers.append(
                {
                    "question_id": str(item.get("question_id") or ""),
                    "question_title": str(item.get("question_title") or ""),
                    "question_type": self._normalize_question_type(str(item.get("question_type") or "subjective")),
                    "answer": answer_text,
                    "note": str(item.get("note") or ""),
                    "status": "completed" if answer_text else "pending",
                    "updated_at": str(item.get("updated_at") or now_text),
                }
            )
        package["answers"] = normalized_answers

        total_questions = len(normalized_answers)
        answered_questions = sum(1 for item in normalized_answers if str(item.get("answer") or "").strip())
        completion_rate = round((answered_questions / total_questions), 4) if total_questions > 0 else 0.0

        current_status = str(package.get("student_status") or "pending")
        if current_status == "declined":
            derived_status = "declined"
        elif completion_rate >= 1 and total_questions > 0:
            derived_status = "completed"
        elif completion_rate > 0:
            derived_status = "in_progress"
        elif current_status in {"accepted", "in_progress", "completed"}:
            derived_status = "accepted"
        else:
            derived_status = current_status

        package["student_status"] = derived_status
        progress = {
            "completion_rate": completion_rate,
            "answered_questions": answered_questions,
            "total_questions": total_questions,
            "status": derived_status,
            "updated_at": now_text,
        }
        package["progress"] = progress
        self._recompute_score_summary(package, now=now_text)
        return progress

    def _resolve_teacher_students(self, teacher_session: Dict[str, Any]) -> List[Dict[str, Any]]:
        teacher_identifier = (
            str(teacher_session.get("user_id") or "").strip()
            or str(teacher_session.get("login_id") or "").strip()
            or str(teacher_session.get("username") or "").strip()
        )
        linked = self.store.list_teacher_students(teacher_identifier)
        if linked:
            return linked
        teacher_username = str(teacher_session.get("username") or "").strip()
        fallback = []
        for student in self.store.list_users("student"):
            if str(student.get("teacher") or "").strip() == teacher_username:
                fallback.append(
                    {
                        "student_username": str(student.get("username") or ""),
                        "student_user_id": student.get("user_id"),
                        "student_payload": student,
                    }
                )
        return fallback

    def _calc_weak_nodes(self, twin_profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not twin_profile:
            return []
        weak_nodes: List[Dict[str, Any]] = []
        nodes = twin_profile.get("knowledge_nodes") if isinstance(twin_profile, dict) else []
        if not isinstance(nodes, list):
            nodes = []
        for item in nodes:
            if not isinstance(item, dict):
                continue
            mastery = float(item.get("mastery_score") or 0)
            progress = float(item.get("progress") or 0)
            quiz_score_raw = item.get("quiz_score")
            quiz_score = float(quiz_score_raw) if isinstance(quiz_score_raw, (int, float)) else None
            weak_reason: List[str] = []
            if mastery < 60:
                weak_reason.append("掌握度偏低")
            if progress < 60:
                weak_reason.append("学习进度偏慢")
            if quiz_score is not None and quiz_score < 60:
                weak_reason.append("测验得分偏低")
            if not weak_reason:
                continue
            weak_nodes.append(
                {
                    "node_id": str(item.get("node_id") or ""),
                    "mastery_score": round(mastery, 2),
                    "progress": round(progress, 2),
                    "quiz_score": round(quiz_score, 2) if quiz_score is not None else None,
                    "reason": "、".join(weak_reason),
                }
            )
        weak_nodes.sort(key=lambda x: (x.get("mastery_score", 0), x.get("progress", 0)))
        return weak_nodes[:6]

    def get_students_overview(self, teacher_session: Dict[str, Any]) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "")
        linked = self._resolve_teacher_students(teacher_session)
        items: List[Dict[str, Any]] = []
        for row in linked:
            student_username = str(row.get("student_username") or "").strip()
            if not student_username:
                continue
            twin = self.store.get_twin_profile(student_username)
            weak_nodes = self._calc_weak_nodes(twin)
            homework = self.homework_service.get_student_twin_homework_snapshot(
                student_username=student_username,
                assignment_id=None,
                teacher_owner=teacher_username,
            )
            items.append(
                {
                    "student_username": student_username,
                    "student_user_id": row.get("student_user_id"),
                    "overall_mastery": round(float((twin or {}).get("overall_mastery") or 0), 2),
                    "weak_node_count": len(weak_nodes),
                    "weak_nodes_preview": weak_nodes[:3],
                    "homework_submission_count": int(homework.get("submission_count") or 0),
                    "homework_average_score": homework.get("average_score"),
                }
            )
        return {
            "teacher_username": teacher_username,
            "students": items,
        }

    def diagnose_students(self, teacher_session: Dict[str, Any], student_usernames: Optional[List[str]] = None) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "")
        linked = self._resolve_teacher_students(teacher_session)
        allowed = {str(item.get("student_username") or "").strip() for item in linked}
        requested = [str(item or "").strip() for item in (student_usernames or []) if str(item or "").strip()]
        target_students = requested if requested else sorted([name for name in allowed if name])

        diagnosis: List[Dict[str, Any]] = []
        for student_username in target_students:
            if student_username not in allowed:
                continue
            twin = self.store.get_twin_profile(student_username)
            weak_nodes = self._calc_weak_nodes(twin)
            homework = self.homework_service.get_student_twin_homework_snapshot(
                student_username=student_username,
                assignment_id=None,
                teacher_owner=teacher_username,
            )
            diagnosis.append(
                {
                    "student_username": student_username,
                    "overall_mastery": round(float((twin or {}).get("overall_mastery") or 0), 2),
                    "weak_nodes": weak_nodes,
                    "homework_snapshot": {
                        "submission_count": int(homework.get("submission_count") or 0),
                        "graded_count": int(homework.get("graded_count") or 0),
                        "average_score": homework.get("average_score"),
                    },
                }
            )
        return {"teacher_username": teacher_username, "diagnosis": diagnosis}

    def _generate_with_ai(
        self,
        *,
        teacher_username: str,
        student_username: str,
        diagnosis: Dict[str, Any],
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        if not (self.model_name and self.api_key):
            return {}
        llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.2,
            base_url=self.base_url,
            api_key=self.api_key,
        )
        prompt = (
            "你是教学干预设计助手。基于学生画像输出严格 JSON。\n"
            "要求：\n"
            "1) strategy_summary: 1 段中文，明确先补什么、再练什么。\n"
            "2) recommended_concepts: 2-5 条基础概念。\n"
            "3) recommended_videos: 2-4 条建议视频主题（仅标题描述）。\n"
            f"4) questions: {question_count} 道题，字段必须包含 "
            "[title,prompt,question_type,options,correct_answer,reference_answer,rubric,test_cases,difficulty]。\n"
            "5) question_type 仅可为 fill_blank/single_choice/multiple_choice/code/subjective。\n"
            "6) single_choice/multiple_choice 必须提供 options 和 correct_answer；code 题尽量提供 test_cases。\n"
            "7) fill_blank 提供 correct_answer。\n"
            "5) 输出格式只能是 JSON 对象，不要 markdown。\n"
            f"教师：{teacher_username}\n"
            f"学生：{student_username}\n"
            f"难度：{difficulty}\n"
            f"诊断数据：{json.dumps(diagnosis, ensure_ascii=False)}"
        )
        response = llm.invoke(prompt)
        payload = self._extract_json_object(getattr(response, "content", ""))
        try:
            self.llm_logger.log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=response,
                model=self.model_name,
                module="TeacherInterventionModule.service",
                metadata={"function": "generate_intervention_draft"},
                username=teacher_username,
            )
        except Exception:
            pass
        return payload if isinstance(payload, dict) else {}

    def _build_heuristic_draft(
        self,
        *,
        diagnosis: Dict[str, Any],
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        weak_nodes = diagnosis.get("weak_nodes") if isinstance(diagnosis, dict) else []
        if not isinstance(weak_nodes, list):
            weak_nodes = []
        weak_node_ids = [str(item.get("node_id") or "") for item in weak_nodes if isinstance(item, dict) and item.get("node_id")]
        concepts = weak_node_ids[:4] or ["核心概念回顾", "关键题型拆解"]
        videos = [f"{name}：10-15分钟基础讲解" for name in concepts[:3]]
        questions = []
        type_cycle = ["fill_blank", "single_choice", "code", "subjective"]
        for idx in range(question_count):
            focus = concepts[idx % len(concepts)] if concepts else "基础巩固"
            q_type = type_cycle[idx % len(type_cycle)]
            base_question = {
                "title": f"{focus} 训练题 {idx + 1}",
                "difficulty": difficulty,
                "reference_answer": f"参考答案应包含：{focus} 的定义、关键步骤、易错点。",
                "rubric": "按正确性、完整性、步骤表达评分。",
                "options": [],
                "correct_answer": "",
                "test_cases": [],
            }
            if q_type == "fill_blank":
                base_question.update(
                    {
                        "question_type": "fill_blank",
                        "prompt": f"填空：{focus} 中最核心的定义是 ______ 。",
                        "correct_answer": f"{focus} 的核心定义",
                    }
                )
            elif q_type == "single_choice":
                base_question.update(
                    {
                        "question_type": "single_choice",
                        "prompt": f"单选：关于 {focus}，以下哪项最准确？",
                        "options": ["A. 概念定义", "B. 常见误解", "C. 应用场景", "D. 全都不对"],
                        "correct_answer": "A",
                    }
                )
            elif q_type == "code":
                base_question.update(
                    {
                        "question_type": "code",
                        "prompt": f"编程：实现一个函数处理“{focus}”的基础逻辑，并输出关键结果。",
                        "test_cases": [{"input": "sample", "expected": "ok"}],
                        "correct_answer": "函数可正确处理输入并输出预期结果",
                    }
                )
            else:
                base_question.update(
                    {
                        "question_type": "subjective",
                        "prompt": f"围绕“{focus}”完成分步作答：先写思路，再给最终答案，并说明易错点。",
                    }
                )
            questions.append(
                base_question
            )
        return {
            "strategy_summary": "先做薄弱知识点的概念补齐，再做分层习题训练，最后进行一次综合复盘。",
            "recommended_concepts": concepts,
            "recommended_videos": videos,
            "questions": questions,
        }

    def generate_intervention_draft(
        self,
        *,
        teacher_session: Dict[str, Any],
        student_username: str,
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "").strip()
        allowed_students = {
            str(item.get("student_username") or "").strip()
            for item in self._resolve_teacher_students(teacher_session)
        }
        if student_username not in allowed_students:
            raise PermissionError("该学生不在当前教师管理范围内")

        diagnosis_result = self.diagnose_students(teacher_session, [student_username])
        diagnosis = (diagnosis_result.get("diagnosis") or [{}])[0]
        ai_payload = self._generate_with_ai(
            teacher_username=teacher_username,
            student_username=student_username,
            diagnosis=diagnosis,
            question_count=question_count,
            difficulty=difficulty,
        )
        if not ai_payload:
            ai_payload = self._build_heuristic_draft(
                diagnosis=diagnosis,
                question_count=question_count,
                difficulty=difficulty,
            )

        questions = ai_payload.get("questions")
        if not isinstance(questions, list):
            questions = []
        safe_questions = []
        for index, item in enumerate(questions):
            if not isinstance(item, dict):
                continue
            safe_questions.append(self._normalize_question(item, index, difficulty))

        package_id = uuid4().hex
        now = self._now()
        package = {
            "id": package_id,
            "teacher_username": teacher_username,
            "student_username": student_username,
            "stage": "draft",
            "strategy_summary": str(ai_payload.get("strategy_summary") or ""),
            "recommended_concepts": [str(x) for x in ai_payload.get("recommended_concepts", []) if str(x).strip()],
            "recommended_videos": [str(x) for x in ai_payload.get("recommended_videos", []) if str(x).strip()],
            "questions": safe_questions,
            "answers": self._build_student_answer_entries(safe_questions),
            "grades": self._build_grade_entries(safe_questions),
            "diagnosis": diagnosis,
            "student_status": "pending",
            "student_note": "",
            "progress": {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(safe_questions),
                "status": "pending",
                "updated_at": now,
            },
            "created_at": now,
            "updated_at": now,
            "pushed_at": None,
        }
        self._recompute_score_summary(package, now=now)
        teacher_state = self._get_user_module_state(teacher_username)
        packages = teacher_state.get("packages")
        if not isinstance(packages, list):
            packages = []
        packages.insert(0, package)
        teacher_state["packages"] = packages
        self._set_user_module_state(teacher_username, teacher_state)
        return package

    def list_teacher_packages(self, teacher_username: str) -> List[Dict[str, Any]]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            return []
        rows = sorted(
            [item for item in packages if isinstance(item, dict)],
            key=lambda x: str(x.get("updated_at") or ""),
            reverse=True,
        )
        for item in rows:
            self._recompute_progress(item)
        return rows

    def get_teacher_package(self, teacher_username: str, package_id: str) -> Dict[str, Any]:
        packages = self.list_teacher_packages(teacher_username)
        for item in packages:
            if str(item.get("id")) == package_id:
                return item
        raise ValueError("任务包不存在")

    def update_teacher_package(
        self,
        *,
        teacher_username: str,
        package_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")
        if str(target.get("stage") or "") != "draft":
            raise ValueError("仅草稿状态可编辑")

        target["strategy_summary"] = str(updates.get("strategy_summary") or "")
        target["recommended_concepts"] = [str(x) for x in updates.get("recommended_concepts", []) if str(x).strip()]
        target["recommended_videos"] = [str(x) for x in updates.get("recommended_videos", []) if str(x).strip()]
        target["questions"] = [
            self._normalize_question(q, idx, str(q.get("difficulty") or "中等"))
            for idx, q in enumerate(updates.get("questions", []))
            if isinstance(q, dict)
        ]
        target["answers"] = self._build_student_answer_entries(target["questions"])
        target["grades"] = self._build_grade_entries(target["questions"])
        self._recompute_progress(target)
        target["updated_at"] = self._now()
        self._set_user_module_state(teacher_username, state)
        return target

    def push_package_to_student(self, *, teacher_username: str, package_id: str) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        student_username = str(target.get("student_username") or "").strip()
        if not student_username:
            raise ValueError("任务包缺少学生信息")

        now = self._now()
        target["stage"] = "pushed"
        target["student_status"] = "pending"
        target["answers"] = self._build_student_answer_entries(target.get("questions", []))
        target["grades"] = self._build_grade_entries(target.get("questions", []))
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        target["pushed_at"] = now
        self._set_user_module_state(teacher_username, state)

        student_state = self._get_user_module_state(student_username)
        student_packages = student_state.get("packages")
        if not isinstance(student_packages, list):
            student_packages = []
        student_copy = {
            "id": target.get("id"),
            "teacher_username": target.get("teacher_username"),
            "student_username": student_username,
            "strategy_summary": target.get("strategy_summary", ""),
            "recommended_concepts": target.get("recommended_concepts", []),
            "recommended_videos": target.get("recommended_videos", []),
            "questions": target.get("questions", []),
            "answers": target.get("answers", []),
            "grades": target.get("grades", []),
            "diagnosis": target.get("diagnosis", {}),
            "student_status": "pending",
            "student_note": "",
            "progress": {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(target.get("questions", []) if isinstance(target.get("questions"), list) else []),
                "status": "pending",
                "updated_at": now,
            },
            "created_at": target.get("created_at"),
            "updated_at": now,
            "pushed_at": now,
        }
        self._recompute_progress(student_copy, now=now)
        replaced = False
        for idx, item in enumerate(student_packages):
            if isinstance(item, dict) and str(item.get("id")) == str(target.get("id")):
                student_packages[idx] = student_copy
                replaced = True
                break
        if not replaced:
            student_packages.insert(0, student_copy)
        student_state["packages"] = student_packages
        self._set_user_module_state(student_username, student_state)
        return target

    def get_teacher_progress(self, teacher_username: str) -> List[Dict[str, Any]]:
        packages = self.list_teacher_packages(teacher_username)
        rows = []
        for item in packages:
            if str(item.get("stage") or "") != "pushed":
                continue
            rows.append(
                {
                    "package_id": item.get("id"),
                    "student_username": item.get("student_username"),
                    "student_status": item.get("student_status", "pending"),
                    "completion_rate": float(((item.get("progress") or {}).get("completion_rate") or 0)),
                    "answered_questions": int(((item.get("progress") or {}).get("answered_questions") or 0)),
                    "total_questions": int(((item.get("progress") or {}).get("total_questions") or 0)),
                    "student_note": item.get("student_note", ""),
                    "average_final_score": ((item.get("score_summary") or {}).get("average_final_score")),
                    "average_ai_score": ((item.get("score_summary") or {}).get("average_ai_score")),
                    "average_teacher_score": ((item.get("score_summary") or {}).get("average_teacher_score")),
                    "updated_at": ((item.get("progress") or {}).get("updated_at") or item.get("updated_at")),
                    "pushed_at": item.get("pushed_at"),
                }
            )
        return rows

    def grade_teacher_question(
        self,
        *,
        teacher_username: str,
        package_id: str,
        question_id: str,
        teacher_score: float,
        teacher_comment: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            raise ValueError("任务包不存在")
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        self._ensure_package_struct(target)
        grades = target.get("grades")
        grade_row = None
        if isinstance(grades, list):
            for item in grades:
                if isinstance(item, dict) and str(item.get("question_id") or "") == question_id:
                    grade_row = item
                    break
        if grade_row is None:
            raise ValueError("题目不存在")

        now = self._now()
        clamped_score = round(max(0.0, min(100.0, float(teacher_score))), 2)
        grade_row["teacher_score"] = clamped_score
        grade_row["teacher_comment"] = str(teacher_comment or "").strip()
        grade_row["teacher_graded_at"] = now
        grade_row["final_score"] = clamped_score
        grade_row["status"] = "teacher_graded"
        grade_row["updated_at"] = now
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(teacher_username, state)

        student_username = str(target.get("student_username") or "").strip()
        if student_username:
            student_state = self._get_user_module_state(student_username)
            student_packages = student_state.get("packages")
            if isinstance(student_packages, list):
                for package in student_packages:
                    if not isinstance(package, dict):
                        continue
                    if str(package.get("id")) != package_id:
                        continue
                    package["grades"] = target.get("grades", [])
                    package["score_summary"] = target.get("score_summary", {})
                    package["updated_at"] = now
                    self._set_user_module_state(student_username, student_state)
                    break
        return target

    def list_student_packages(self, student_username: str) -> List[Dict[str, Any]]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            return []
        rows = sorted(
            [item for item in packages if isinstance(item, dict)],
            key=lambda x: str(x.get("updated_at") or ""),
            reverse=True,
        )
        for item in rows:
            self._recompute_progress(item)
        return rows

    def get_student_package(self, student_username: str, package_id: str) -> Dict[str, Any]:
        packages = self.list_student_packages(student_username)
        for item in packages:
            if str(item.get("id")) == package_id:
                return item
        raise ValueError("任务包不存在")

    def _sync_back_to_teacher(self, package: Dict[str, Any]) -> None:
        teacher_username = str(package.get("teacher_username") or "").strip()
        package_id = str(package.get("id") or "").strip()
        if not teacher_username or not package_id:
            return
        teacher_state = self._get_user_module_state(teacher_username)
        teacher_packages = teacher_state.get("packages")
        if not isinstance(teacher_packages, list):
            return
        for item in teacher_packages:
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) != package_id:
                continue
            item["student_status"] = package.get("student_status", item.get("student_status"))
            item["student_note"] = package.get("student_note", item.get("student_note"))
            item["progress"] = package.get("progress", item.get("progress"))
            item["answers"] = package.get("answers", item.get("answers", []))
            item["grades"] = package.get("grades", item.get("grades", []))
            item["score_summary"] = package.get("score_summary", item.get("score_summary", {}))
            item["updated_at"] = self._now()
            self._set_user_module_state(teacher_username, teacher_state)
            return

    def student_decide_package(
        self,
        *,
        student_username: str,
        package_id: str,
        decision: str,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        now = self._now()
        target["student_status"] = decision
        target["student_note"] = note
        target["updated_at"] = now
        if decision == "declined":
            target["progress"] = {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(target.get("questions", []) if isinstance(target.get("questions"), list) else []),
                "status": "declined",
                "updated_at": now,
            }
        elif decision == "accepted":
            self._recompute_progress(target, now=now)
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        return target

    def student_save_answer(
        self,
        *,
        student_username: str,
        package_id: str,
        question_id: str,
        answer: str,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        current_status = str(target.get("student_status") or "pending")
        if current_status == "declined":
            raise ValueError("该任务包已被标记为暂不执行")
        if current_status == "pending":
            raise ValueError("请先点击“接受并开始”后再作答")

        answers = target.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(target.get("questions", []))
        found = False
        now = self._now()
        normalized_question_id = str(question_id).strip()
        if not normalized_question_id:
            raise ValueError("题目ID不能为空")

        for item in answers:
            if not isinstance(item, dict):
                continue
            if str(item.get("question_id") or "") != normalized_question_id:
                continue
            clean_answer = str(answer or "").strip()
            item["answer"] = clean_answer
            item["note"] = str(note or "").strip()
            item["status"] = "completed" if clean_answer else "pending"
            item["updated_at"] = now
            found = True
            break
        if not found:
            raise ValueError("题目不存在")

        target["answers"] = answers
        self._auto_grade_single_question(target, normalized_question_id, now=now)
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        return target

    def student_update_progress(
        self,
        *,
        student_username: str,
        package_id: str,
        status: str,
        completion_rate: float,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        now = self._now()
        if str(target.get("student_status") or "") == "declined":
            raise ValueError("该任务包已被标记为暂不执行")
        if note.strip():
            target["student_note"] = note.strip()
        answers = target.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(target.get("questions", []))
            target["answers"] = answers
        if status == "completed":
            for item in answers:
                if not isinstance(item, dict):
                    continue
                if str(item.get("answer") or "").strip():
                    item["status"] = "completed"
                    continue
                item["status"] = "completed"
                item["answer"] = "已完成（未填写详细答案）"
                item["updated_at"] = now
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        return target


from pathlib import Path

from HomeworkModule.models import AssignmentQuestionGenerateRequest
from HomeworkModule.repository import HomeworkRepository
from HomeworkModule.service import HomeworkService


def test_homework_publish_submit_and_grade(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    assignment = service.create_assignment(
        {
            "title": "Python 主观作业",
            "description": "解释装饰器与闭包",
            "assignment_type": "subjective",
            "class_name": "Class-1",
            "due_at": None,
            "rubric": "概念准确，结构完整",
            "questions": [
                {
                    "title": "题目1",
                    "prompt": "什么是装饰器？",
                    "reference_answer": "",
                    "rubric": "",
                    "test_cases": [],
                }
            ],
            "created_by": "teacher_a",
            "publish_now": True,
        }
    )
    assert assignment["id"]

    submission = service.submit_assignment(
        {
            "assignment_id": assignment["id"],
            "student_username": "student_a",
            "answers": [{"question_index": 0, "answer": "首先...其次...例如..."}],
        }
    )
    assert submission["id"]

    graded = service.grade_with_ai(assignment, submission, teacher_username="teacher_a")
    assert graded["ai_score"] is not None
    assert graded["ai_feedback"]

    finaled = service.finalize_grade(
        submission_id=submission["id"],
        teacher_score=88,
        teacher_comment="思路清晰",
        grader_username="teacher_a",
    )
    assert finaled is not None
    assert finaled["teacher_score"] == 88
    assert finaled["grader_username"] == "teacher_a"


def test_generate_questions_fallback(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    request = AssignmentQuestionGenerateRequest(
        topic="排序算法",
        assignment_type="code_practice",
        count=2,
        difficulty="medium",
        language="zh",
    )
    questions = service.generate_questions(request, teacher_username="teacher_a")

    assert len(questions) == 2
    assert all("title" in item for item in questions)
    assert all("prompt" in item for item in questions)


def test_code_submission_auto_graded_by_sandbox(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    assignment = service.create_assignment(
        {
            "title": "代码自动判题作业",
            "description": "输入两个整数输出和",
            "assignment_type": "code",
            "class_name": "Class-1",
            "due_at": None,
            "rubric": "以测试用例通过率计分",
            "questions": [
                {
                    "title": "求和",
                    "prompt": "读取一行两个整数并输出和",
                    "reference_answer": "",
                    "rubric": "",
                    "test_cases": [
                        {"input": "1 2\n", "expected": "3"},
                        {"input": "10 20\n", "expected": "30"},
                    ],
                }
            ],
            "created_by": "teacher_a",
            "publish_now": True,
        }
    )

    submission = service.submit_assignment(
        {
            "assignment_id": assignment["id"],
            "student_username": "student_a",
            "answers": [
                {
                    "question_index": 0,
                    "answer": "a, b = map(int, input().split())\nprint(a + b)",
                }
            ],
        }
    )

    assert submission["status"] == "graded"
    assert submission["ai_score"] == 100
    assert submission["teacher_score"] == 100
    assert submission["grader_username"] == "sandbox"
    assert "系统自动判题" in submission.get("ai_feedback", "")

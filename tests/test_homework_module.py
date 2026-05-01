from pathlib import Path

from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
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
            "course_id": "course_big_data",
            "node_id": "node-chapter-1",
            "node_name": "第一章 导论",
            "node_path": ["第一章 导论", "1.1 基本概念"],
            "chapter_context": "围绕导论中的核心概念进行阐述",
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
    assert assignment["course_id"] == "course_big_data"
    assert assignment["node_id"] == "node-chapter-1"
    assert assignment["node_name"] == "第一章 导论"
    assert assignment["node_path"] == ["第一章 导论", "1.1 基本概念"]
    assert "导论" in assignment["chapter_context"]

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

    events = get_teacher_event_repository().list_grading_events("teacher_a")
    event_types = {item.get("event_type") for item in events}
    assert "ai_recommendation_generated" in event_types
    assert "teacher_final_grade" in event_types


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


def test_list_assignments_support_course_node_filters(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    service.create_assignment(
        {
            "title": "章节A作业",
            "description": "",
            "assignment_type": "subjective",
            "class_name": "Class-1",
            "course_id": "course_big_data",
            "node_id": "node-a",
            "node_name": "章节A",
            "node_path": ["章节A"],
            "chapter_context": "",
            "due_at": None,
            "rubric": "",
            "questions": [{"title": "Q1", "prompt": "P1"}],
            "created_by": "teacher_a",
            "publish_now": True,
        }
    )
    service.create_assignment(
        {
            "title": "章节B作业",
            "description": "",
            "assignment_type": "subjective",
            "class_name": "Class-1",
            "course_id": "course_big_data",
            "node_id": "node-b",
            "node_name": "章节B",
            "node_path": ["章节B"],
            "chapter_context": "",
            "due_at": None,
            "rubric": "",
            "questions": [{"title": "Q1", "prompt": "P1"}],
            "created_by": "teacher_a",
            "publish_now": True,
        }
    )

    filtered = service.list_assignments(status="published", course_id="course_big_data", node_name="章节A")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "章节A作业"


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


def test_draft_prompt_distinguishes_objective_and_choice(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)

    objective_prompt = service._build_draft_prompt(
        assignment_type="objective",
        topic="大数据生命周期",
        difficulty="中等",
        chapter_ctx="章节路径：A > B > C",
    )
    choice_prompt = service._build_draft_prompt(
        assignment_type="choice",
        topic="大数据生命周期",
        difficulty="中等",
        chapter_ctx="章节路径：A > B > C",
    )

    assert 'options": ["A. 正确", "B. 错误"]' in objective_prompt
    assert "correct_answer 只能是 A 或 B" in objective_prompt
    assert 'options": ["A. 选项一", "B. 选项二", "C. 选项三", "D. 选项四"]' in choice_prompt
    assert "单选如 A，多选如 A,C" in choice_prompt


def test_assignment_type_choice_should_not_be_normalized_to_subjective(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    assignment = service.create_assignment(
        {
            "title": "大数据生命周期选择题",
            "description": "用于验证题型存储",
            "assignment_type": "choice",
            "class_name": "Class-1",
            "questions": [{"title": "Q1", "prompt": "P1", "options": ["A. x", "B. y"], "correct_answer": "A"}],
            "created_by": "teacher_a",
            "publish_now": True,
        }
    )
    loaded = service.get_assignment(assignment["id"])
    assert loaded is not None
    assert loaded["assignment_type"] == "choice"


def test_objective_should_auto_grade_immediately_by_default(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    assignment = service.create_assignment(
        {
            "title": "判断题自动判题",
            "description": "",
            "assignment_type": "objective",
            "questions": [
                {
                    "title": "Q1",
                    "prompt": "这是判断题",
                    "options": ["A. 正确", "B. 错误"],
                    "correct_answer": "B",
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
            "answers": [{"question_index": 0, "answer": "B"}],
        }
    )
    assert submission["status"] == "graded"
    assert submission["ai_score"] == 100
    assert "客观题自动核对" in submission.get("ai_feedback", "")


def test_objective_manual_review_should_not_auto_grade_on_submit(tmp_path: Path):
    repo = HomeworkRepository(db_path=tmp_path / "app.db")
    service = HomeworkService(repository=repo)
    service.llm = None

    assignment = service.create_assignment(
        {
            "title": "判断题人工批改",
            "description": "",
            "assignment_type": "objective",
            "objective_result_mode": "manual_review",
            "questions": [
                {
                    "title": "Q1",
                    "prompt": "这是判断题",
                    "options": ["A. 正确", "B. 错误"],
                    "correct_answer": "B",
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
            "answers": [{"question_index": 0, "answer": "B"}],
        }
    )
    assert submission["status"] == "submitted"
    assert submission["ai_score"] is None

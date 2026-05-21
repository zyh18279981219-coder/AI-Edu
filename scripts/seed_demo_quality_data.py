from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from DatabaseModule.database_factory import DatabaseFactory
from HomeworkModule.repository import HomeworkRepository
from TeachingInteractionModule.service import TeachingInteractionService
from TeachingResearchModule.service import TeachingResearchService
from tools.session_manager import get_session_manager


COURSE_ID = "course_big_data"
CLASS_NAME = "大数据 1 班"
TEACHER_USERNAME = "teacher"
ADMIN_USERNAME = "admin"


def now_iso(offset_days: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset_days)).isoformat(timespec="seconds")


def ensure_admin_and_teacher_links() -> dict[str, int]:
    store = DatabaseFactory.get_store()
    admin_users = store.list_users("admin")
    if not any(user.get("username") == ADMIN_USERNAME or user.get("login_id") == ADMIN_USERNAME for user in admin_users):
        admin_users.append(
            {
                "username": ADMIN_USERNAME,
                "login_id": ADMIN_USERNAME,
                "password": "123456",
                "user_type": "admin",
                "display_name": "系统管理员",
                "name": "系统管理员",
                "email": "admin@example.com",
                "role": "admin",
            }
        )
        store.replace_users("admin", admin_users)

    students = store.list_users("student")
    demo_student_names = [
        str(user.get("username") or "").strip()
        for user in students
        if str(user.get("username") or "").strip()
    ]
    teachers = store.list_users("teacher")
    for teacher in teachers:
        if str(teacher.get("username") or "") != TEACHER_USERNAME:
            continue
        existing = list(teacher.get("students") or [])
        merged = list(dict.fromkeys([*existing, *demo_student_names]))
        teacher["students"] = merged
        break
    if teachers:
        store.replace_users("teacher", teachers)

    return {
        "admins": len(store.list_users("admin")),
        "students_linked": len(demo_student_names),
    }


def question(title: str, prompt: str, answer: str, options: list[str] | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "prompt": prompt,
        "options": options or [],
        "correct_answer": answer,
        "reference_answer": answer,
        "rubric": "答案需要覆盖核心概念、关键步骤和应用场景，表达清晰可得满分。",
        "test_cases": [],
    }


def ensure_homework_demo_data() -> dict[str, int]:
    repo = HomeworkRepository()
    existing_titles = {item["title"]: item for item in repo.list_assignments(include_statuses=["draft", "published", "closed"])}
    assignments = [
        {
            "title": "大数据生命周期课前诊断",
            "description": "面向课程第一章的课前诊断，帮助教师识别学生对采集、存储、处理、分析、可视化链路的理解差异。",
            "assignment_type": "objective",
            "node_id": "big_data_lifecycle",
            "node_name": "大数据生命周期",
            "node_path": ["大数据基础", "大数据生命周期"],
            "chapter_context": "大数据基础概念与生命周期",
            "objective_result_mode": "immediate",
            "due_at": now_iso(5),
            "questions": [
                question(
                    "生命周期排序",
                    "请写出大数据项目从数据产生到业务应用的一般流程。",
                    "数据采集、数据存储、数据处理、数据分析、数据可视化与业务决策。",
                    ["采集-存储-处理-分析-可视化", "分析-采集-存储-可视化", "存储-可视化-采集-分析"],
                ),
                question("关键风险", "数据生命周期中为什么要关注数据质量？", "数据质量会影响分析结论、模型效果和业务决策可信度。"),
            ],
        },
        {
            "title": "数据质量问题分类案例分析",
            "description": "基于业务日志样例识别缺失、重复、异常和不一致问题，并给出处理策略。",
            "assignment_type": "subjective",
            "node_id": "data_quality",
            "node_name": "数据质量问题分类",
            "node_path": ["数据预处理", "数据质量问题分类"],
            "chapter_context": "数据清洗与质量评估",
            "objective_result_mode": "manual_review",
            "due_at": now_iso(7),
            "questions": [
                question("质量问题识别", "某电商订单表存在空手机号、重复订单号和负数金额，请分别说明属于哪类质量问题。", "空手机号属于缺失值，重复订单号属于重复数据，负数金额属于异常值。"),
                question("治理方案", "请给出一套可落地的数据清洗流程。", "先做字段规则校验，再处理缺失和重复，随后做异常检测，最后形成质量报告和追踪机制。"),
            ],
        },
        {
            "title": "MapReduce 词频统计实践",
            "description": "用 Map 和 Reduce 思想拆解词频统计任务，理解分布式计算的分治流程。",
            "assignment_type": "code",
            "node_id": "mapreduce",
            "node_name": "MapReduce计算模型",
            "node_path": ["分布式计算", "MapReduce计算模型"],
            "chapter_context": "Hadoop 与分布式计算模型",
            "objective_result_mode": "immediate",
            "due_at": now_iso(10),
            "questions": [
                {
                    "title": "词频统计",
                    "prompt": "输入若干行英文单词，输出每个单词出现次数。要求先说明 Map 阶段和 Reduce 阶段各做什么，再提交代码。",
                    "options": [],
                    "correct_answer": "",
                    "reference_answer": "Map 输出 (word, 1)，Shuffle 按 word 分组，Reduce 对每组计数求和。",
                    "rubric": "能说明 Map、Shuffle、Reduce 的职责并给出可运行代码。",
                    "test_cases": [
                        {"input": "big data big\n", "expected": "big 2\ndata 1", "weight": 50, "is_file_io": False},
                        {"input": "hadoop spark hadoop\n", "expected": "hadoop 2\nspark 1", "weight": 50, "is_file_io": False},
                    ],
                }
            ],
        },
    ]

    created = 0
    for payload in assignments:
        if payload["title"] in existing_titles:
            continue
        created += 1
        repo.create_assignment(
            {
                **payload,
                "class_name": CLASS_NAME,
                "course_id": COURSE_ID,
                "allow_late": True,
                "total_score": 100,
                "rubric": "按知识点理解、案例分析、表达完整度和可操作性综合评分。",
                "publish_now": True,
                "status": "published",
                "created_by": TEACHER_USERNAME,
            }
        )

    student_answers = {
        "zyh": ["采集、存储、处理、分析和可视化。", "质量问题会导致分析结论不可靠。"],
        "stucaihaozhan": ["采集、清洗、存储、分析、展示。", "会影响后续建模和业务决策。"],
        "stuliuyiming": ["数据采集到业务使用。", "因为脏数据会让结果有偏差。"],
    }
    graded = 0
    for assignment in repo.list_assignments(status="published"):
        if assignment["created_by"] != TEACHER_USERNAME:
            continue
        for username, answers in student_answers.items():
            existing = repo.list_submissions(assignment_id=assignment["id"], student_username=username)
            if existing:
                continue
            submission = repo.create_submission(
                {
                    "assignment_id": assignment["id"],
                    "student_username": username,
                    "answers": [
                        {"question_index": index, "answer": answer}
                        for index, answer in enumerate(answers[: len(assignment.get("questions") or [])])
                    ],
                }
            )
            score = {"zyh": 92, "stucaihaozhan": 86, "stuliuyiming": 78}.get(username, 80)
            repo.update_submission(
                submission["id"],
                {
                    "status": "graded",
                    "ai_score": score,
                    "ai_feedback": "演示数据：答案覆盖主要知识点，建议继续结合课程案例完善细节。",
                    "ai_rationale": "根据关键词覆盖度、结构完整性和应用解释进行评分。",
                    "teacher_score": score,
                    "teacher_comment": "思路清楚，后续补充更多业务场景会更完整。",
                    "graded_at": now_iso(),
                    "grader_username": TEACHER_USERNAME,
                },
            )
            graded += 1

    return {
        "assignments": len(repo.list_assignments(include_statuses=["draft", "published", "closed"])),
        "created_assignments": created,
        "created_submissions": graded,
    }


def ensure_interaction_demo_data() -> dict[str, int]:
    service = TeachingInteractionService()
    announcements = service.list_announcements(TEACHER_USERNAME)
    if not any(item.get("title") == "本周学习安排：数据质量与 MapReduce" for item in announcements):
        service.create_announcement(
            {
                "teacher_username": TEACHER_USERNAME,
                "title": "本周学习安排：数据质量与 MapReduce",
                "content": "请同学们完成课前诊断，重点复习数据质量问题分类，并在周五前提交 MapReduce 词频统计实践。",
                "class_name": CLASS_NAME,
                "course_id": COURSE_ID,
            }
        )
    if not any(item.get("title") == "课堂提醒：行业岗位技能分析已开放" for item in announcements):
        service.create_announcement(
            {
                "teacher_username": TEACHER_USERNAME,
                "title": "课堂提醒：行业岗位技能分析已开放",
                "content": "行业资讯模块已补充大数据分析岗位样例，同学们可以对照岗位技能要求调整自己的学习计划。",
                "class_name": CLASS_NAME,
                "course_id": COURSE_ID,
            }
        )

    topics = service.list_topics(TEACHER_USERNAME)
    topic = next((item for item in topics if item.get("title") == "讨论：数据质量问题如何影响推荐结果？"), None)
    if not topic:
        topic = service.create_topic(
            {
                "teacher_username": TEACHER_USERNAME,
                "title": "讨论：数据质量问题如何影响推荐结果？",
                "content": "请结合课程案例说明缺失、重复、异常数据会怎样影响学习资源推荐或行业岗位分析。",
                "class_name": CLASS_NAME,
                "course_id": COURSE_ID,
            }
        )
        first = service.add_post(
            teacher_username=TEACHER_USERNAME,
            topic_id=topic["id"],
            author_username="zyh",
            author_role="student",
            content="如果学生测验记录缺失，系统会不会低估学生对某个知识点的掌握度？",
        )
        service.add_post(
            teacher_username=TEACHER_USERNAME,
            topic_id=topic["id"],
            author_username=TEACHER_USERNAME,
            author_role="teacher",
            content="会的，所以数字孪生画像需要同时看测验、作业、学习时长和互动记录，不能只看单一指标。",
            replied_to_post_id=first["id"],
            replied_to_created_at=first["created_at"],
        )
        service.add_post(
            teacher_username=TEACHER_USERNAME,
            topic_id=topic["id"],
            author_username="stucaihaozhan",
            author_role="student",
            content="重复日志会让某些资源被误判为更热门，推荐结果可能偏向同一类内容。",
        )

    return {
        "announcements": len(service.list_announcements(TEACHER_USERNAME)),
        "topics": len(service.list_topics(TEACHER_USERNAME)),
    }


def ensure_research_demo_data() -> dict[str, int]:
    service = TeachingResearchService()
    records = service.list_records(TEACHER_USERNAME)
    payloads = [
        {
            "activity_type": "co_preparation",
            "title": "集体备课：数据质量问题分类与课堂案例",
            "description": "围绕订单数据、学习行为日志和行业岗位数据设计三组课堂案例，用于支撑学生理解数据质量治理。",
            "resource_link": "https://example.com/big-data-quality-cases",
            "class_name": CLASS_NAME,
            "course_id": COURSE_ID,
            "happened_at": now_iso(-3),
        },
        {
            "activity_type": "shared_courseware",
            "title": "共享课件：MapReduce 词频统计实践",
            "description": "补充 Map、Shuffle、Reduce 三阶段流程图、伪代码和课堂练习数据。",
            "resource_link": "https://example.com/mapreduce-wordcount",
            "class_name": CLASS_NAME,
            "course_id": COURSE_ID,
            "happened_at": now_iso(-2),
        },
        {
            "activity_type": "research_post",
            "title": "教研记录：学习反馈闭环与资源推荐优化",
            "description": "基于学生作业表现、讨论问题和行业岗位技能热度，调整下一轮推荐资源排序。",
            "resource_link": "https://example.com/learning-feedback-loop",
            "class_name": CLASS_NAME,
            "course_id": COURSE_ID,
            "happened_at": now_iso(-1),
        },
    ]
    titles = {item.get("title") for item in records}
    created = 0
    for payload in payloads:
        if payload["title"] in titles:
            continue
        service.create_record({"teacher_username": TEACHER_USERNAME, **payload})
        created += 1
    return {
        "records": len(service.list_records(TEACHER_USERNAME)),
        "created_records": created,
    }


def build_industry_result() -> dict[str, Any]:
    jobs = [
        {
            "title": "大数据分析师",
            "company": "云启数据科技",
            "salary": "15-25K",
            "experience": "1-3年",
            "education": "本科",
            "location": "北京",
            "source": "Boss直聘",
            "description": "负责业务数据指标体系建设、用户行为分析、可视化看板和专题分析报告。",
            "requirements": "熟悉 SQL、Python、Hive/Spark，理解数据质量治理和指标口径管理。",
            "relevance_score": 11,
            "relevance_reasons": ["与课程中的数据采集、数据清洗、可视化分析高度相关", "岗位强调 SQL、Python 和 Spark 实践能力"],
            "skills": ["SQL", "Python", "数据清洗", "可视化", "Spark"],
            "skill_evidence": [
                {"name": "SQL", "evidence": "负责指标体系和专题分析，需要熟练编写查询。"},
                {"name": "Spark", "evidence": "岗位要求 Hive/Spark 数据处理能力。"},
            ],
            "market_country": "中国",
        },
        {
            "title": "数据仓库工程师",
            "company": "数智云仓",
            "salary": "18-30K",
            "experience": "3-5年",
            "education": "本科",
            "location": "上海",
            "source": "猎聘网",
            "description": "建设离线数仓模型，维护数据质量规则，支持 BI 与推荐业务数据需求。",
            "requirements": "掌握 Hive、Spark、ETL 调度、维度建模和数据质量监控。",
            "relevance_score": 10,
            "relevance_reasons": ["对应课程中的数据存储、ETL 和质量评估知识点", "能作为学习路径中工程实践方向的目标岗位"],
            "skills": ["Hive", "Spark", "ETL", "维度建模", "数据质量"],
            "skill_evidence": [{"name": "数据质量", "evidence": "岗位明确要求维护数据质量规则。"}],
            "market_country": "中国",
        },
        {
            "title": "机器学习数据工程师",
            "company": "慧学智能",
            "salary": "20-35K",
            "experience": "3-5年",
            "education": "硕士",
            "location": "杭州",
            "source": "拉勾网",
            "description": "负责特征工程、训练数据集构建、模型评估数据分析和线上效果监控。",
            "requirements": "熟悉 Python、特征工程、统计分析、数据处理流水线和 A/B 实验。",
            "relevance_score": 9,
            "relevance_reasons": ["与数据预处理、分析建模、反馈闭环相关", "适合高阶学习路径延伸"],
            "skills": ["Python", "特征工程", "统计分析", "A/B实验", "数据处理"],
            "skill_evidence": [{"name": "特征工程", "evidence": "岗位职责包含训练数据集构建。"}],
            "market_country": "中国",
        },
        {
            "title": "BI 数据分析实习生",
            "company": "智联教育",
            "salary": "150-220/天",
            "experience": "应届生",
            "education": "本科",
            "location": "广州",
            "source": "前程无忧",
            "description": "协助完成教学业务数据清洗、报表维护、课堂互动指标分析。",
            "requirements": "掌握 Excel、SQL、基础 Python 和可视化工具，有学习数据分析经验优先。",
            "relevance_score": 8,
            "relevance_reasons": ["适合课程初学者对照能力缺口", "与当前系统学习行为分析场景一致"],
            "skills": ["Excel", "SQL", "Python", "可视化", "学习分析"],
            "skill_evidence": [{"name": "学习分析", "evidence": "岗位涉及课堂互动指标分析。"}],
            "market_country": "中国",
        },
    ]
    skills = Counter(skill for job in jobs for skill in job["skills"])
    source_counts = Counter(job["source"] for job in jobs)
    experience_counts = Counter(job["experience"] for job in jobs)
    education_counts = Counter(job["education"] for job in jobs)
    return {
        "jobs": jobs,
        "metrics": {
            "jobs_total": len(jobs),
            "jobs_analyzed": len(jobs),
            "skills_total": len(skills),
            "sources_total": len(source_counts),
        },
        "summary": {
            "核心结论": "大数据岗位集中要求 SQL、Python、Spark、数据质量和可视化能力。",
            "学习建议": "优先补齐数据清洗和 SQL 分析，再通过 MapReduce/Spark 实践提升工程能力。",
        },
        "raw_count": len(jobs),
        "source_counts": dict(source_counts),
        "relevance_summary": {
            "input_count": len(jobs),
            "requested_count": 20,
            "threshold": 5,
            "threshold_kept_count": len(jobs),
            "selected_count": len(jobs),
            "dropped_count": 0,
            "backfilled_count": 0,
            "strict_threshold": True,
            "fetch_rounds": 1,
            "final_fetch_limit": 20,
            "max_fetch_limit": 50,
            "completed_target": True,
            "country": "中国",
            "city": "全国",
            "search_terms": ["大数据分析", "数据质量", "Spark", "SQL", "Python"],
            "parallel": False,
            "included_countries": ["中国"],
        },
        "relevance_message": "已加载演示行业数据：职位与当前大数据课程知识点高度相关，可用于课堂展示。",
        "warnings": [],
        "charts": {
            "skill_ranking": [{"name": name, "value": value} for name, value in skills.most_common()],
            "job_distribution": [{"name": name, "value": value} for name, value in source_counts.items()],
            "experience_distribution": [{"name": name, "value": value} for name, value in experience_counts.items()],
            "education_distribution": [{"name": name, "value": value} for name, value in education_counts.items()],
            "skill_heatmap": {},
        },
    }


def ensure_industry_demo_data() -> dict[str, int]:
    store = DatabaseFactory.get_store()
    session_manager = get_session_manager()
    snapshot = {
        "task_id": "demo-industry-big-data",
        "task_type": "analyze",
        "status": "completed",
        "message": "演示行业数据已生成。",
        "meta": {"step": 5, "title": "大数据分析岗位演示"},
        "result": build_industry_result(),
        "error": None,
        "cancel_requested": False,
    }
    count = 0
    for user in store.list_users("student"):
        username = str(user.get("username") or "").strip()
        if not username:
            continue
        session_manager.set_user_value(username, "industry_latest_task_id", snapshot["task_id"])
        session_manager.set_user_value(username, "industry_latest_task_snapshot", snapshot)
        count += 1
    return {"industry_student_snapshots": count}


def main() -> None:
    summary = {}
    summary.update(ensure_admin_and_teacher_links())
    summary.update(ensure_homework_demo_data())
    summary.update(ensure_interaction_demo_data())
    summary.update(ensure_research_demo_data())
    summary.update(ensure_industry_demo_data())
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

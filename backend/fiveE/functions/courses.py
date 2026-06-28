import json
from typing import List

from sqlalchemy import select

from ..models import Course, CourseNode
from ..session import SessionLocal1, check_session_exists


async def get_course_detail(course_id: str) -> tuple[str, str]:
    # return "大数据分析", "本课程聚焦大数据时代下的数据价值挖掘与决策支撑，系统讲解大数据分析的核心理论、技术方法与实战应用。课程从数据采集、预处理、存储管理入手，覆盖数据分析基础、统计建模、数据挖掘、可视化呈现等关键模块，结合主流工具与实战案例，引导学习者完成从原始数据到有效信息、再到科学决策的全流程实践。通过理论学习与项目实操相结合，学员将掌握数据清洗、特征工程、分析建模、结果解读等核心能力，能够运用大数据思维解决商业分析、运营优化、趋势预测等实际问题，为从事数据分析师、数据运营、商业分析等相关岗位奠定坚实基础。"
    async with SessionLocal1() as db:
        stmt = select(Course.course_name, Course.description).where(Course.course_id == course_id)
        result = await db.execute(stmt)
        row = result.first()
        if row:
            return str(row.course_name or ""), str(row.description or "")
        return "", ""


async def _get_course_name_by_id(course_id: str) -> str:
    async with SessionLocal1() as db:
        stmt = select(Course.course_name).where(Course.course_id == course_id)
        result = await db.execute(stmt)
        row = result.first()
        if row:
            return str(row.cours_name)
        return ""


async def _get_course_id_by_name(course_name: str) -> str:
    async with SessionLocal1() as db:
        stmt = select(Course.course_id).where(Course.course_name == course_name)
        result = await db.execute(stmt)
        row = result.first()
        if row:
            return row.course_id
        return ""


async def get_related_course(course_id: str) -> List[str]:
    course_name = await _get_course_name_by_id(course_id)
    course_id_list = []
    async with SessionLocal1() as db:
        stmt = select(CourseNode.node_path_json).where(Course.course_id == course_name)
        result = await db.execute(stmt)
        row = result.first()
        if row:
            row_json = json.loads(row.node_path_json)
            for item in row_json:
                course_id = _get_course_id_by_name(item)
                course_id_list.append(course_id)

    return course_id_list

async def is_first_learn(user_id: str, course_id: str):
    return await check_session_exists(user_id, course_id)

from sqlalchemy import select
from ..models import User, TwinProfile, ChatSession
from ..session import get_db, get_agent_db

async def get_student_mastery(student_id: str) -> float:
    async with get_db() as db:
        stmt = select(TwinProfile.overall_mastery).where(TwinProfile.username == student_id)
        result = await db.execute(stmt)
        values = result.scalars().all()
        mastery = sum(float(v or 0) for v in values) / len(values) if values else None
        return float(mastery) if mastery is not None else 0.0

async def get_student_info(student_id: str) -> User:
    async with get_db() as db:
        stmt = select(User).where(User.username == student_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

def get_learning_detail(student_id: str,course_id: str) :
    pass

async def get_learned_courses(student_id: str) -> list:
    from ..session import session_service
    await session_service._prepare_tables()
    async with get_agent_db() as db:
        stmt = select(ChatSession.id).where(ChatSession.user_id==student_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

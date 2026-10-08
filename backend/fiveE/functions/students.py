from sqlalchemy import select
from ..models.user import User
from ..models.twin_profile import TwinProfile
from ..session import SessionLocal1

async def get_student_mastery(student_id: str) -> float:
    async with SessionLocal1() as db:
        stmt = select(TwinProfile.overall_mastery).where(TwinProfile.user_id == student_id)
        result = await db.execute(stmt)
        mastery = result.scalar_one_or_none()
        return float(mastery) if mastery is not None else 0.0

async def get_student_info(student_id: str) -> User:
    async with SessionLocal1() as db:
        stmt = select(User).where(User.user_id == student_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

def get_learning_detail(student_id: str,course_id: str) :
    pass

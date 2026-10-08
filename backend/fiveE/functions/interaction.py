from sqlalchemy import insert

from ..models.user_interaction import UserInteraction
from ..session import SessionLocal1

async def collect_student_interaction(user_id: str, course_id: str, stage:str, question_type: str, question_count: int, error: str):
    async with SessionLocal1() as db:
        async with db.begin():
            stmt = insert(UserInteraction).values(user_id,course_id,stage,question_type,question_count,error)
            await db.execute(stmt)

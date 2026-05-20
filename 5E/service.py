import json
from typing import List, Optional

from google.adk import Runner
from google.genai import types
from sqlalchemy import select

from agents import *
from agents.entrance import EntranceAgent
from models.chat_event_data import ChatEventData
from models.chat_history import ChatHistory
from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from models.course import Course
from session import SessionLocal1, SessionLocal2, session_service

agent_runner = Runner(
    agent=EntranceAgent(
        name="orchestrator",
        engagement_agent=engagement_agent,
        exploration_agent=exploration_agent,
        explanation_agent=explanation_agent,
        elaboration_agent=elaboration_agent,
        evaluation_agent=evaluation_agent,
        orchestrator_agent=orchestrator_agent
    ),
    app_name="5E",
    session_service=session_service,
    auto_create_session=True
)


async def get_history_by_student_and_course(student_id: str, course_id: str) -> List[ChatResponse]:
    async with SessionLocal2() as db:
        stmt = select(ChatHistory).filter(
            ChatHistory.user_id == student_id,
            ChatHistory.session_id == course_id
        ).order_by(ChatHistory.timestamp.asc())

        result = await db.execute(stmt)
        rows = result.scalars().all()

        results = []
        for row in rows:
            if row.event_data:
                data = json.loads(row.event_data)
                event_data = ChatEventData(**data)

                part=event_data.content.parts[0]
                part_data=json.loads(part.text)
                # Map ChatEventData to ChatResponse with flattened content and action items
                results.append(ChatResponse(
                    role=part_data.get('role'),
                    content=part_data.get('content'),
                    buttonList=part_data.get('buttons', []),
                    resourceList=part_data.get('resources', []),
                    testList=part_data.get('tests', []),
                    timestamp=event_data.timestamp
                ))
        return results




async def chat_message_stream(request: ChatRequest):
    user_id = request.user_id
    course_id = request.course_id
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=request.content)
        ]
    )

    events = agent_runner.run_async(user_id=user_id, session_id=course_id, new_message=content)
    async for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text
        elif event.actions and event.actions.escalate:
            yield f"Agent escalated: {event.error_message or 'No specific message'}"


async def get_course_id_by_name(course_name: str) -> Optional[str]:
    async with SessionLocal1() as db:
        stmt = select(Course.course_id).where(Course.course_name == course_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

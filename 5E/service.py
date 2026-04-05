import json
from typing import List

from google.adk import Runner
from google.genai import types
from sqlalchemy import select

import session
from agents import *
from agents.entrance import EntranceAgent

from models.chat_history import ChatHistory
from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from session import SessionLocal

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
    session_service=session.session_service,
    auto_create_session=True
)


async def get_history_by_user_and_lesson(user_id: str, lesson_id: str) -> List[ChatResponse]:
    async with SessionLocal() as db:
        stmt = select(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == lesson_id
        ).order_by(ChatHistory.timestamp.asc())

        result = await db.execute(stmt)
        rows = result.scalars().all()

        results = []
        for row in rows:
            if row.event_data:
                # Parse JSON string from database into Pydantic model
                results.append(ChatResponse(**json.loads(row.event_data)))
        return results


async def check_session_exists(user_id: str, lesson_id: str) -> bool:
    async with SessionLocal() as db:
        stmt = select(ChatHistory.id).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.session_id == lesson_id
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar() is not None


async def chat_message_stream(request: ChatRequest):
    user_id = request.user_id
    lesson_id = request.lesson_id
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=request.content)
        ]
    )

    events = agent_runner.run_async(user_id=user_id, session_id=lesson_id, new_message=content)
    async for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text
        elif event.actions and event.actions.escalate:
            yield f"Agent escalated: {event.error_message or 'No specific message'}"

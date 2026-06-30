import json
import logging
import time
from typing import Any, AsyncGenerator, List, Optional

from .models.chat_request import ChatRequest
from .models.chat_response import ChatResponse
from .effectiveness_service import record_chat_effectiveness

logger = logging.getLogger(__name__)
_runtime: Optional[dict[str, Any]] = None


def _unavailable_response(message: str) -> ChatResponse:
    return ChatResponse(
        role="assistant",
        content=message,
        buttons=[],
        resources=[],
        tests=[],
        timestamp=time.time(),
    )


def _load_runtime() -> dict[str, Any]:
    """Load the Google ADK based 5E runtime only when it is first used."""
    global _runtime
    if _runtime is not None:
        return _runtime

    try:
        from google.adk import Runner
        from google.genai import types
        from sqlalchemy import select

        from .agents import (
            elaboration_agent,
            engagement_agent,
            evaluation_agent,
            explanation_agent,
            exploration_agent,
            orchestrator_agent,
        )
        from .agents.entrance import EntranceAgent
        from .models.chat_event_data import ChatEventData
        from .models.chat_history import ChatHistory
        from .models.course import Course
        from .session import SessionLocal1, SessionLocal2, session_service

        agent_runner = Runner(
            agent=EntranceAgent(
                name="orchestrator",
                engagement_agent=engagement_agent,
                exploration_agent=exploration_agent,
                explanation_agent=explanation_agent,
                elaboration_agent=elaboration_agent,
                evaluation_agent=evaluation_agent,
                orchestrator_agent=orchestrator_agent,
            ),
            app_name="agents",
            session_service=session_service,
            auto_create_session=True,
        )
        _runtime = {
            "types": types,
            "select": select,
            "ChatEventData": ChatEventData,
            "ChatHistory": ChatHistory,
            "Course": Course,
            "SessionLocal1": SessionLocal1,
            "SessionLocal2": SessionLocal2,
            "agent_runner": agent_runner,
        }
        return _runtime
    except Exception as exc:
        logger.exception("Failed to initialize 5E runtime")
        raise RuntimeError("5E assistant runtime is unavailable. Check dependencies and .env configuration.") from exc


async def get_history_by_student_and_course(student_id: str, course_id: str) -> List[ChatResponse]:
    try:
        runtime = _load_runtime()
    except RuntimeError:
        return []

    SessionLocal2 = runtime["SessionLocal2"]
    ChatHistory = runtime["ChatHistory"]
    ChatEventData = runtime["ChatEventData"]
    select = runtime["select"]

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

                if event_data.author=='user':
                    results.append(ChatResponse(
                        role='user',
                        content=event_data.content.parts[0].text,
                        buttons=[],
                        resources=[],
                        tests=[],
                        timestamp=event_data.timestamp
                    ))
                else:
                    part = event_data.content.parts[0]
                    part_data = json.loads(part.text)
                    # Map ChatEventData to ChatResponse with flattened content and action items
                    results.append(ChatResponse(
                        role=event_data.author,
                        content=part_data.get('content'),
                        buttons=part_data.get('buttons', []),
                        resources=part_data.get('resources', []),
                        tests=part_data.get('tests', []),
                        timestamp=event_data.timestamp
                    ))

        return results




async def chat_message_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    try:
        runtime = _load_runtime()
    except RuntimeError as exc:
        yield _unavailable_response(str(exc)).model_dump_json()
        return

    types = runtime["types"]
    agent_runner = runtime["agent_runner"]
    user_id = request.user_id
    course_id = request.course_id
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=request.content)
        ]
    )

    try:
        events = agent_runner.run_async(user_id=user_id, session_id=course_id, new_message=content)
        emitted_parts: list[str] = []
        async for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        emitted_parts.append(part.text)
                        yield part.text
            elif event.actions and event.actions.escalate:
                fallback = _unavailable_response(event.error_message or "Agent escalated without a message")
                fallback_text = fallback.model_dump_json()
                emitted_parts.append(fallback_text)
                yield fallback_text
        _record_effectiveness_from_stream(request, emitted_parts)
    except Exception as exc:
        logger.exception("5E chat stream failed")
        yield _unavailable_response("5E 智能体响应失败，请稍后再试。").model_dump_json()


def _response_from_stream_parts(parts: list[str]) -> ChatResponse | None:
    raw = "".join(parts).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return ChatResponse(**data)
    except Exception:
        pass
    return ChatResponse(
        role="assistant",
        content=raw,
        buttons=[],
        resources=[],
        tests=[],
        timestamp=time.time(),
    )


def _record_effectiveness_from_stream(request: ChatRequest, parts: list[str]) -> None:
    response = _response_from_stream_parts(parts)
    if response is None:
        return
    try:
        record_chat_effectiveness(
            user_identifier=request.user_id,
            course_id=request.course_id,
            node_id=request.node_id,
            session_id=request.course_id,
            response=response,
            prompt=request.content,
        )
    except Exception:
        logger.exception("Failed to record 5E effectiveness for %s/%s", request.user_id, request.course_id)


async def get_course_id_by_name(course_name: str) -> Optional[str]:
    runtime = _load_runtime()
    SessionLocal1 = runtime["SessionLocal1"]
    Course = runtime["Course"]
    select = runtime["select"]

    async with SessionLocal1() as db:
        stmt = select(Course.course_id).where(Course.course_name == course_name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

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
        from .agents import (
            elaboration_agent,
            engagement_agent,
            evaluation_agent,
            explanation_agent,
            exploration_agent,
            orchestrator_agent,
        )
        from .agents.entrance import EntranceAgent
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
            "Course": Course,
            "SessionLocal1": SessionLocal1,
            "SessionLocal2": SessionLocal2,
            "session_service": session_service,
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

    session_service = runtime["session_service"]
    session = await session_service.get_session(
        app_name="agents",
        user_id=student_id,
        session_id=course_id,
    )
    if session is None:
        return []

    results: list[ChatResponse] = []
    for event in session.events:
        content = getattr(event, "content", None)
        parts = getattr(content, "parts", None) or []
        text = "".join(
            str(getattr(part, "text", "") or "")
            for part in parts
            if getattr(part, "text", None)
        ).strip()
        if not text:
            continue

        timestamp = float(getattr(event, "timestamp", time.time()) or time.time())
        if getattr(event, "author", "") == "user":
            results.append(ChatResponse(
                role="user",
                content=text,
                buttons=[],
                resources=[],
                tests=[],
                timestamp=timestamp,
            ))
            continue

        try:
            payload = json.loads(text)
            if not isinstance(payload, dict) or "content" not in payload:
                continue
            results.append(ChatResponse(
                role="assistant",
                content=str(payload.get("content") or ""),
                buttons=payload.get("buttons") or [],
                resources=payload.get("resources") or [],
                tests=payload.get("tests") or [],
                timestamp=timestamp,
            ))
        except (TypeError, ValueError):
            results.append(ChatResponse(
                role="assistant",
                content=text,
                buttons=[],
                resources=[],
                tests=[],
                timestamp=timestamp,
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
        final_parts: list[str] = []
        fallback_response: ChatResponse | None = None
        async for event in events:
            # ADK emits intermediate tool/function events (often JSON such as
            # {"status":"success"}).  They are internal state, not a user
            # response, and must not be sent to the chat client.
            if event.actions and event.actions.escalate:
                fallback_response = _unavailable_response(
                    event.error_message or "Agent escalated without a message"
                )
                continue

            if not event.content or not event.content.parts:
                continue
            if not event.is_final_response():
                continue
            for part in event.content.parts:
                if part.text:
                    final_parts.append(part.text)

        response = fallback_response or _response_from_stream_parts(final_parts)
        if response is None:
            response = _unavailable_response("5E 助教暂时没有返回内容，请稍后再试。")
        response_text = response.model_dump_json()
        yield response_text
        _record_effectiveness_from_stream(request, [response_text])
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
            # Agent prompts historically returned the response payload without
            # the transport-only role/timestamp fields.  Normalize both forms
            # here instead of exposing the raw JSON as chat text.
            nested = data.get("content")
            if isinstance(nested, str) and nested.lstrip().startswith("{"):
                try:
                    nested_data = json.loads(nested)
                    if isinstance(nested_data, dict) and "content" in nested_data:
                        data = {**nested_data, **{
                            key: value for key, value in data.items()
                            if key not in {"content", "buttons", "resources", "tests"}
                        }}
                except (TypeError, ValueError):
                    pass
            if isinstance(data.get("content"), str):
                return ChatResponse(
                    role=str(data.get("role") or "assistant"),
                    content=data["content"],
                    buttons=data.get("buttons") or [],
                    resources=data.get("resources") or [],
                    tests=data.get("tests") or [],
                    timestamp=float(data.get("timestamp") or time.time()),
                )
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

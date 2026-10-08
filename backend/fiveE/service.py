import json
import logging
import time
from typing import Any, AsyncGenerator, List, Optional

from google.adk import Runner
from google.genai import types

from .models import ChatRequest, ChatResponse, Course, ChatHistory, ChatEventData, CourseNode, CourseResponse, Resource
from . import rag
from .session import get_db, get_agent_db, session_service
from .model import CHROMA_PERSIST_DIRECTORY,DEFAULT_RESOURCE_DIRECTORY
from .agents import engagement_agent, exploration_agent, explanation_agent, elaboration_agent, evaluation_agent, orchestrator_agent, EntranceAgent

from sqlalchemy import select

logger = logging.getLogger(__name__)

agent_runner = Runner(
    agent = EntranceAgent(
        name="agents",
        engagement_agent=engagement_agent,
        exploration_agent=exploration_agent,
        explanation_agent=explanation_agent,
        elaboration_agent=elaboration_agent,
        evaluation_agent=evaluation_agent,
        orchestrator_agent=orchestrator_agent
    ),
    app_name="agents",
    session_service=session_service,
    auto_create_session=True
)

async def get_history_by_student_and_course(student_id: str, course_id: int) -> List[ChatResponse]:
    await session_service._prepare_tables()
    async with get_agent_db() as db:
        stmt = select(ChatHistory).filter(
            ChatHistory.user_id == student_id,
            ChatHistory.session_id == course_id
        ).order_by(ChatHistory.timestamp.asc())

        result = await db.execute(stmt)
        rows = result.scalars().all()

        results = []
        for row in rows:
            if row.event_data:
                try:
                    data = row.event_data if isinstance(row.event_data, dict) else json.loads(row.event_data)
                    event_data = ChatEventData(**data)
                except Exception as e:
                    print(f"[service.py] json.loads(row.event_data) 解析失败: {e}")
                    print(f"[service.py] event_data 内容: {row.event_data}")
                    continue

                if not event_data.content.parts or not event_data.content.parts[0].text:
                    continue
                if event_data.content.parts[0].function_call:
                    continue

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
                    try:
                        part_data = json.loads(part.text)
                    except Exception as e:
                        print(f"[service.py] json.loads(part.text) 解析失败: {e}")
                        print(f"[service.py] part.text 内容: {part.text}")
                        continue
                    # Map ChatEventData to ChatResponse with flattened content and action items
                    results.append(ChatResponse(
                        role=event_data.author,
                        content=part_data.get('content') or "",
                        stage=part_data.get('stage'),
                        buttons=part_data.get('buttons', []),
                        resources=part_data.get('resources', []),
                        tests=part_data.get('tests', []),
                        timestamp=event_data.timestamp
                    ))

        return results


async def get_raw_history_by_student_and_course(student_id: str, course_id: int) -> List[dict]:
    """返回未经反序列化的原始对话历史（纯 JSON）。

    直接读取 events 表并返回 event_data 的原始结构，
    不做 ChatEventData 反序列化，也不过滤 function_call / 映射 ChatResponse。
    """
    await session_service._prepare_tables()
    async with get_agent_db() as db:
        stmt = select(ChatHistory).filter(
            ChatHistory.user_id == student_id,
            ChatHistory.session_id == course_id
        ).order_by(ChatHistory.timestamp.asc())

        result = await db.execute(stmt)
        rows = result.scalars().all()

        results: List[dict] = []
        for row in rows:
            if not row.event_data:
                continue
            try:
                results.append((row.event_data if isinstance(row.event_data, dict) else json.loads(row.event_data)))
            except Exception as e:
                print(f"[service.py] json.loads(row.event_data) 解析失败: {e}")
                print(f"[service.py] event_data 内容: {row.event_data}")
                continue

        return results


async def chat_message_stream(request: ChatRequest) -> AsyncGenerator[str, None]:
    user_id = request.user_id
    course_id = int(request.course_id)
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=request.content)
        ]
    )

    events = agent_runner.run_async(user_id=user_id, session_id=str(course_id), new_message=content)
    async for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    yield part.text
        elif event.actions and event.actions.escalate:
            yield f"Agent escalated: {event.error_message or 'No specific message'}"


async def get_course_id_by_name(course_name: str, course_id: str | None = None) -> Optional[int]:
    async with get_db() as db:
        stmt = select(CourseNode.node_detail_id).where(CourseNode.node_name == course_name)
        if course_id:
            stmt = stmt.where(CourseNode.course_id == course_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


async def get_all_courses() -> List[CourseResponse]:
    """查询 CourseNode 表，返回所有课程的 node_name 和 node_detail_id。"""
    async with get_db() as db:
        stmt = select(CourseNode.node_detail_id, CourseNode.node_name).order_by(
            CourseNode.node_detail_id.asc()
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            CourseResponse(
                id=row.node_detail_id,
                name=row.node_name
            )
            for row in rows
        ]


async def resolve_resource_path(resource_id: int, node_detail_id: int) -> Optional[str]:
    async with get_db() as db:
        node = await db.get(CourseNode, node_detail_id)
        if not node:
            return None
        result = await db.execute(select(Resource.resource_path).where(
            Resource.resource_id == resource_id, Resource.course_id == node.course_id,
            Resource.node_id == node.node_id, Resource.is_deleted == 0,
        ))
        return result.scalar_one_or_none()


async def init_rag() -> None:
    rag.prepare_chroma_db_from_directory(
        directory_path=DEFAULT_RESOURCE_DIRECTORY,
        persist_directory=CHROMA_PERSIST_DIRECTORY
    )

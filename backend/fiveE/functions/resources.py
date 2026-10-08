from typing import List
import asyncio
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy import select

from ..models import Resource, CourseNode
from ..session import SessionLocal1
from ..model import CHROMA_PERSIST_DIRECTORY, DEFAULT_RAG_MODEL


async def get_course_resources(course_id:str) -> List[dict]:
    async with SessionLocal1() as db:
        node = await db.get(CourseNode, int(course_id)) if str(course_id).isdigit() else None
        stmt = select(Resource).where(Resource.course_id == (node.course_id if node else course_id), Resource.is_deleted == 0)
        if node:
            stmt = stmt.where(Resource.node_id == node.node_id)
        result = await db.execute(stmt)
        return [dict(id=str(r.resource_id), title=r.title or '', type=r.resource_type,
                     path=r.resource_path) for r in result.scalars().all()]

@lru_cache(maxsize=1)
def _cached_embedding():
    return HuggingFaceEmbeddings(model_name=DEFAULT_RAG_MODEL,
                                model_kwargs={'local_files_only': True})


def _query_prepared_content(query: str) -> dict:
    directory = Path(CHROMA_PERSIST_DIRECTORY)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    if not (directory / 'chroma.sqlite3').is_file():
        return {'status': 'unavailable', 'reason': 'Course document index has not been prepared', 'documents': []}
    try:
        store = Chroma(collection_name='course_materials', persist_directory=str(directory))
        if not store._collection.count():
            return {'status': 'unavailable', 'reason': 'Course document index is empty', 'documents': []}
        store = Chroma(collection_name='course_materials', persist_directory=str(directory),
                       embedding_function=_cached_embedding())
        docs = store.similarity_search(query=query, k=4)
        return {'status': 'ok', 'documents': [dict(content=d.page_content, metadata=d.metadata) for d in docs]}
    except Exception:
        return {'status': 'unavailable', 'reason': 'Prepared local embedding model or document index is unavailable', 'documents': []}


async def query_resources_content(query: str) -> dict:
    """Search prepared course documents without downloading models during a chat."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(_query_prepared_content, query), timeout=10)
    except asyncio.TimeoutError:
        return {'status': 'unavailable', 'reason': 'Course document search timed out', 'documents': []}

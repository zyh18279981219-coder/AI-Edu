from typing import List

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy import select

from ..models import Resource, CourseNode
from ..session import SessionLocal1


async def get_course_resources(course_id:str) -> List[dict]:
    async with SessionLocal1() as db:
        node = await db.get(CourseNode, int(course_id)) if str(course_id).isdigit() else None
        stmt = select(Resource).where(Resource.course_id == (node.course_id if node else course_id), Resource.is_deleted == 0)
        if node:
            stmt = stmt.where(Resource.node_id == node.node_id)
        result = await db.execute(stmt)
        return [dict(id=str(r.resource_id), title=r.title or '', type=r.resource_type,
                     path=r.resource_path) for r in result.scalars().all()]

async def query_resources_content(query: str):
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )
    vector_store = Chroma(
        persist_directory="chroma_db",
        embedding_function=embedding,
    )

    docs = await vector_store.asimilarity_search(query=query)

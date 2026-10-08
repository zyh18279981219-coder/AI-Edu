from typing import List

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy import select

from ..models import Resource
from ..session import SessionLocal1


async def get_course_resources(course_id:str) -> List[str]:
    async with SessionLocal1() as db:
        stmt= select(Resource).where(Resource.course_id == course_id, Resource.is_deleted == 0)
        result = await db.execute(stmt)
        return list(result.scalars().all())

async def query_resources_detail(query: str):
    embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )
    vector_store = Chroma(
        persist_directory="chroma_db",
        embedding_function=embedding,
    )

    docs = await vector_store.asimilarity_search(query=query)

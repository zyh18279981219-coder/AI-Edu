import os

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .models import CourseNode,Course
from .model import MODEL, ENDPOINT, API_KEY, CHROMA_PERSIST_DIRECTORY
from .session import SessionLocal1

from sqlalchemy import select, insert
import asyncio

def get_embedding():
    model=os.getenv("RAG_MODEL") or "huggingface"
    if(model=="deepseek"):
        return OpenAIEmbeddings(
                model = MODEL,
                base_url = ENDPOINT,
                api_key = API_KEY,
                check_embedding_ctx_length = False
            )
    else:
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")



def prepare_chroma_db(pdf_path: str, persist_directory: str):
    print(f"Loading document from {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    print("Splitting document into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    print("Initializing embeddings model...")
    embeddings = get_embedding()

    print(f"Creating and persisting ChromaDB to {persist_directory}...")
    vector_store = Chroma(
        collection_name="course_materials",
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )

    vector_store.add_documents(texts)
    print(f"ChromaDB created and persisted to {persist_directory}")

def prepare_chroma_db_from_directory(directory_path: str, persist_directory: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    embeddings = get_embedding()

    loader = DirectoryLoader(directory_path)
    documents=loader.load()

    print("Splitting all documents into chunks...")
    texts = text_splitter.split_documents(documents)

    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        print(f"ChromaDB already exists in {persist_directory}. Removing the old one...")
        os.removedirs(persist_directory)

    print(f"Creating and persisting new ChromaDB to {persist_directory}...")
    vectordb = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)
    print(f"ChromaDB created and persisted to {persist_directory}")


def query_chroma_db(persist_directory: str, query_text: str) -> []:
    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"ChromaDB not found in {persist_directory}. Please run prepare_db.py first.")
        return

    print(f"Loading ChromaDB from {persist_directory}...")
    embeddings = get_embedding()
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

    docs = vectordb.similarity_search(query_text)

    result = []
    for i, doc in enumerate(docs):
        content = doc.page_content
        source = doc.metadata.get('source','N/A')
        result.append({'content':content,'source':source})

    return result

def _query_chroma_db(persist_directory: str, query_text: str):
    query_result = query_chroma_db(persist_directory=persist_directory,query_text=query_text)

    print(f"\nPerforming similarity search for query: '{query_text}'")
    if len(query_result) <= 0:
        print("No relevant documents found.")
    for i in range(len(query_result)):
        query = query_result[i]
        # print(query)
        print(f"Document {i + 1}:")
        print(f"Content: {query['content']}")
        print(f"Source: {query['source']}")
        print("-" * 30)

if __name__ == '__main__':
    pdf_file_path = "data/Book/1.pdf"
    chroma_persist_directory = CHROMA_PERSIST_DIRECTORY

    # prepare_chroma_db_from_directory(
        # directory_path="data/Book",
        # persist_directory=chroma_persist_directory,
    # )

    _query_chroma_db(
        persist_directory=chroma_persist_directory,
        query_text="什么是大数据基础概念",
    )

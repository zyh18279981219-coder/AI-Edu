import os

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def prepare_chroma_db(pdf_path: str, persist_directory: str):
    print(f"Loading document from {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    print("Splitting document into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    print("Initializing embeddings model...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print(f"Creating and persisting ChromaDB to {persist_directory}...")
    vector_store = Chroma(
        collection_name="foo",
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )

    vector_store.add_documents(texts)
    print(f"ChromaDB created and persisted to {persist_directory}")


def prepare_chroma_db_from_directory(directory_path: str, persist_directory: str):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    loader = DirectoryLoader(directory_path)
    documents=loader.load()

    print("Splitting all documents into chunks...")
    texts = text_splitter.split_documents(documents)

    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        print(f"ChromaDB already exists in {persist_directory}. Attempting to add new documents.")
        # Load existing database and add new documents
        vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
        vectordb.add_documents(texts)
        print(f"Added new documents to existing ChromaDB in {persist_directory}")
    else:
        print(f"Creating and persisting new ChromaDB to {persist_directory}...")
        vectordb = Chroma.from_documents(documents=texts,
                                         embedding=embeddings,
                                         persist_directory=persist_directory)
        print(f"ChromaDB created and persisted to {persist_directory}")


def query_chroma_db(persist_directory: str, query_text: str):
    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"ChromaDB not found in {persist_directory}. Please run prepare_db.py first.")
        return

    print(f"Loading ChromaDB from {persist_directory}...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

    print(f"\nPerforming similarity search for query: '{query_text}'")
    docs = vectordb.similarity_search(query_text)

    print("\nTest Query Results:")
    if not docs:
        print("No relevant documents found.")
    for i, doc in enumerate(docs):
        print(f"Document {i + 1}:")
        print(f"Content: {doc.page_content[:200]}...")  # Print first 200 characters
        print(f"Source: {doc.metadata.get('source', 'N/A')}")
        print("-" * 30)


if __name__ == '__main__':
    pdf_file_path = "data/Book/1.pdf"
    chroma_persist_directory = "chroma_db"

    # prepare_chroma_db_from_directory(
    #     directory_path="data/Book",
    #     persist_directory=chroma_persist_directory,
    # )

    query_chroma_db(
        persist_directory=chroma_persist_directory,
        query_text="What is big data?",
    )

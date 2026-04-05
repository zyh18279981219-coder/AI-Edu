from __future__ import annotations

from typing import Iterable, Optional, Tuple, Union

import logging
import os
import shutil
from hashlib import sha256

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import (
    UnstructuredFileLoader,
    Docx2txtLoader,
)

# 尝试导入 MultiQueryRetriever（可选功能）
MultiQueryRetriever = None
try:
    from langchain.retrievers.multi_query import MultiQueryRetriever
except ImportError:
    try:
        from langchain_community.retrievers.multi_query import MultiQueryRetriever
    except ImportError:
        import logging
        logging.getLogger(__name__).warning(
            "MultiQueryRetriever not available, will use basic retriever"
        )
from tools.pdf_ocr_loader import PDFOCRLoader

logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from dotenv import load_dotenv
import os

load_dotenv()

# 从环境变量中获取配置
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")
embedding_model = os.environ.get("embedding_model")
logger = logging.getLogger(__name__)


class RAGService:
    """Lazy wrapper around a Chroma vector store."""

    def __init__(
        self,
        embeddings: Optional[Embeddings] = None,
        persist_directory: str = "data/chroma_db",
        retriever_k: Optional[int] = None,
        use_mmr: Optional[bool] = None,
        use_multiquery: Optional[bool] = None,
        mq_llm_model: Optional[str] = None,
        mq_num_queries: Optional[int] = None,
        mq_include_original: Optional[bool] = None,
    ) -> None:
        # 初始化 OpenAI 嵌入模型
        self._embeddings = OpenAIEmbeddings(
            openai_api_base=base_url + "/v1",
            model=embedding_model,
            openai_api_key=api_key,
        )
        self._persist_directory = persist_directory
        self._vectorstore: Optional[Chroma] = None
        self._retriever = None
        self._retriever_params: Optional[Tuple[int, bool]] = None

        # 默认检索参数
        self._default_k = retriever_k or int(os.getenv("RAG_K", 4))
        env_mmr = os.getenv("RAG_USE_MMR")
        self._default_mmr = (
            use_mmr
            if use_mmr is not None
            else (env_mmr is None or env_mmr.lower() in {"1", "true", "yes"})
        )
        env_multi = os.getenv("RAG_USE_MULTIQUERY")
        self._use_multiquery = (
            use_multiquery
            if use_multiquery is not None
            else (env_multi is None or env_multi.lower() in {"1", "true", "yes"})
        )
        self._mq_llm_model = mq_llm_model or os.getenv("RAG_MQ_MODEL")
        self._mq_num_queries = mq_num_queries or int(os.getenv("RAG_MQ_NUM_QUERIES", 3))
        env_inc = os.getenv("RAG_MQ_INCLUDE_ORIGINAL", "false")
        self._mq_include_original = (
            mq_include_original
            if mq_include_original is not None
            else env_inc.lower() in {"1", "true", "yes"}
        )

    def _get_vectorstore(self) -> Chroma:
        if self._vectorstore is None:
            try:
                self._vectorstore = Chroma(
                    embedding_function=self._embeddings,
                    persist_directory=self._persist_directory,
                )
            except Exception:
                logger.warning("Chroma persistence appears corrupted; rebuilding store")
                shutil.rmtree(self._persist_directory, ignore_errors=True)
                try:
                    self._vectorstore = Chroma(
                        embedding_function=self._embeddings,
                        persist_directory=self._persist_directory,
                    )
                except Exception:
                    logger.warning(
                        "Persistent Chroma store unavailable, falling back to in-memory store",
                    )
                    self._vectorstore = Chroma(
                        embedding_function=self._embeddings,
                    )
        return self._vectorstore

    def get_retriever(self, k: Optional[int] = None, mmr: Optional[bool] = None):
        """Return a cached retriever from the vector store."""
        k = k or self._default_k
        mmr = self._default_mmr if mmr is None else mmr
        params = (k, mmr)

        if self._retriever is None or self._retriever_params != params:
            search_type = "mmr" if mmr else "similarity"
            base = self._get_vectorstore().as_retriever(
                search_type=search_type, search_kwargs={"k": k}
            )
            self._retriever_params = params

            if self._use_multiquery and MultiQueryRetriever is not None:
                try:
                    llm = ChatOpenAI(
                        model=model_name,
                        temperature=0,
                        base_url=base_url,
                        api_key=api_key,
                    )

                    # 🎉 关键修改：使用中文的 PromptTemplate 🎉
                    prompt = PromptTemplate.from_template(
                        "你是一个AI语言模型助手。你的任务是\n    为给定的用户问题生成{n}个不同版本，\n    以便从向量数据库中检索相关文档。\n    通过为用户问题生成多种视角，\n    你的目标是帮助用户克服基于距离的相似性搜索的某些局限性。\n    请将这些替代问题用换行符分隔。原始问题：{question}".replace(
                            "{n}", str(self._mq_num_queries)
                        )
                    )

                    self._retriever = MultiQueryRetriever.from_llm(
                        retriever=base,
                        llm=llm,
                        prompt=prompt,
                        include_original=self._mq_include_original,
                    )
                    logger.info(
                        "Initialized MultiQueryRetriever with model %s",
                        self._mq_llm_model,
                    )
                except Exception as exc:  # pragma: no cover - network issues
                    logger.warning("MultiQueryRetriever unavailable: %s", exc)
                    self._retriever = base
            else:
                if self._use_multiquery and MultiQueryRetriever is None:
                    logger.debug("MultiQueryRetriever requested but not available, using basic retriever")
                self._retriever = base
        return self._retriever

    def ingest_paths(self, items: Iterable[Union[str, Document]]) -> Optional[str]:
        """Embed documents from ``items`` into the vector store and persist.

        ``items`` may be file paths or :class:`~langchain_core.documents.Document`
        instances. Chunks are deduplicated using a ``doc_hash`` metadata field to
        avoid embedding the same content multiple times.

        Returns an error string if ingestion fails so callers can surface
        actionable feedback to users.
        """
        store = self._get_vectorstore()
        documents: list[Document] = []
        for item in items:
            if isinstance(item, str):
                # 根据文件扩展名选择合适的加载器
                if item.lower().endswith(".pdf"):
                    loader = PDFOCRLoader(item)
                elif item.lower().endswith(".docx"):
                    loader = Docx2txtLoader(item)
                else:
                    loader = UnstructuredFileLoader(item)
                try:
                    documents.extend(loader.load())
                except LookupError:
                    msg = (
                        "Missing NLTK data. Run nltk.download('punkt'); "
                        "nltk.download('averaged_perceptron_tagger')"
                    )
                    logger.error("Failed to load %s: %s", item, msg)
                    return msg
                except ImportError:
                    # 提示用户安装所需的依赖
                    if item.lower().endswith(".docx"):
                        msg = "Missing docx2txt dependency. Install with pip install docx2txt"
                    else:
                        msg = (
                            "Missing optional PDF dependencies. Install with "
                            "pip install 'unstructured[pdf]'"
                        )
                    logger.error("Failed to load %s: %s", item, msg)
                    return msg
            else:
                documents.append(item)

        to_add: list[Document] = []
        seen_hashes: set[str] = set()
        for doc in documents:
            # 使用内容哈希值进行去重
            doc_hash = (
                doc.metadata.get("doc_hash")
                or sha256(doc.page_content.encode("utf-8")).hexdigest()
            )
            doc.metadata["doc_hash"] = doc_hash
            if doc_hash in seen_hashes:
                continue
            seen_hashes.add(doc_hash)

            # 检查 Chroma 中是否已存在此哈希值的文档
            if not store.get(where={"doc_hash": doc_hash}, limit=1)["ids"]:
                to_add.append(doc)

        if to_add:
            store.add_documents(to_add)
            if hasattr(store, "persist"):
                store.persist()
            logger.info("Ingested %d new document(s)", len(to_add))
        else:
            logger.info("No new documents to ingest")

        return None


_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Return a module-level singleton instance of :class:`RAGService`."""
    global _instance
    if _instance is None:
        _instance = RAGService()
    return _instance

import logging
import os

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI

from tools.edu_tools import (
    calculator,
    current_date,
    current_weekday,
    define_word,
    detect_language,
    wikipedia_search,
)
from tools.language_handler import LanguageHandler
from tools.llm_logger import get_llm_logger
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")


@tool
def rag_search(query: str) -> str:
    """Search course knowledge from the RAG store."""
    try:
        retriever = RAGService().get_retriever()
        return get_context_or_empty(query, retriever)
    except Exception as exc:
        logging.getLogger(__name__).warning("RAG search error: %s", exc)
        return ""


class QA_Agent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            base_url=base_url,
            api_key=api_key,
        )
        self.tools = [
            wikipedia_search,
            define_word,
            calculator,
            current_date,
            current_weekday,
            detect_language,
            rag_search,
        ]

    def chat(
        self,
        question: str,
        retriever=None,
        return_details: bool = False,
        username: str = "anonymous",
    ) -> str | tuple[str, bool, bool]:
        self.logger.info("QA chat request: %s", question[:200])

        used_retriever = False
        context = ""
        if retriever:
            context = get_context_or_empty(question, retriever)
            if context:
                used_retriever = True
                self.logger.info("QA retrieved context length: %s", len(context))
            else:
                self.logger.info("QA retrieved no context")

        lang = LanguageHandler.choose_or_detect(question)
        self.logger.info("QA detected language: %s", lang)

        try:
            if context:
                prompt = (
                    "你是一名课程学习助手。请严格依据给定上下文回答；"
                    "如果上下文不足以支持结论，就明确说明未在材料中找到。\n\n"
                    f"上下文：\n{context}\n\n"
                    f"问题：{question}\n\n"
                    f"请使用 {lang} 回答。"
                )
            else:
                prompt = (
                    "你是一名课程学习助手，请直接、清晰地回答用户问题。"
                    f"\n\n问题：{question}\n\n请使用 {lang} 回答。"
                )

            msg = self.llm.invoke(prompt)
            output = getattr(msg, "content", str(msg))

            get_llm_logger().log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=msg,
                model=model_name,
                module="AgentModule.qa_agent",
                metadata={
                    "function": "chat",
                    "language": lang,
                    "used_retriever": used_retriever,
                },
                username=username,
            )
            self.logger.info("QA chat completed")
        except Exception as exc:
            error_text = str(exc)
            if "Connection error" in error_text or "WinError 10013" in error_text:
                output = (
                    "AI 服务当前连接失败。"
                    "这通常不是 API Key 失效，而是本机网络、代理、防火墙或安全软件"
                    "阻止了到模型服务的连接，请检查对 api.siliconflow.cn 的访问。"
                )
            else:
                output = f"AI 服务调用失败：{error_text}"
            self.logger.exception("QA chat failed")

        used_fallback = False
        output = LanguageHandler.ensure_language(output, lang)

        if return_details:
            return output, used_fallback, used_retriever
        return output

import logging
import os

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from tools.language_handler import LanguageHandler
from tools.llm_logger import get_llm_logger
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")


class Summary_Agent:
    def __init__(self, retriever=None):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            base_url=base_url,
            api_key=api_key,
            streaming=True,
        )
        self.retriever = retriever or RAGService().get_retriever()
        self.base_prompt = PromptTemplate.from_template(
            """
你是一名专业课程讲师，请为学生生成结构清晰、适合复习的学习总结。

主题：{input}

要求：
- 给出核心概念定义
- 梳理关键知识点和方法
- 补充必要的公式、步骤或示例
- 用清晰的小标题和要点组织内容
- 如果材料不足，不要编造，直接说明

请使用 {language} 输出。
"""
        )

    def generate_summary(
        self,
        input_text: str,
        language: str = "en",
        retriever=None,
        username: str = "anonymous",
    ) -> tuple[str, bool]:
        lang = (
            LanguageHandler.choose_or_detect(input_text)
            if language == "auto"
            else language
        )

        retriever = retriever or self.retriever or RAGService().get_retriever()
        ctx = get_context_or_empty(input_text, retriever)
        used_retriever = bool(ctx)
        if ctx:
            input_text = f"{ctx}\n\n主题：\n{input_text}"
        self.logger.info("Summary generated with RAG: %s", used_retriever)

        chain = self.base_prompt | self.llm
        response = chain.invoke({"input": input_text, "language": lang})

        get_llm_logger().log_llm_call(
            messages=[
                {
                    "role": "user",
                    "content": f"Generate summary for: {input_text[:200]}...",
                }
            ],
            response=response,
            model=model_name,
            module="SummaryModule.summary_agent",
            metadata={
                "function": "generate_summary",
                "language": lang,
                "used_retriever": used_retriever,
            },
            username=username,
        )

        return response.content, used_retriever

    async def generate_summary_stream(
        self,
        input_text: str,
        language: str = "en",
        retriever=None,
        username: str = "anonymous",
    ):
        lang = (
            LanguageHandler.choose_or_detect(input_text)
            if language == "auto"
            else language
        )

        retriever = retriever or self.retriever or RAGService().get_retriever()
        ctx = get_context_or_empty(input_text, retriever)
        if ctx:
            input_text = f"{ctx}\n\n主题：\n{input_text}"
        self.logger.info("Streaming summary generated with RAG: %s", bool(ctx))

        prompt = self.base_prompt.format(input=input_text, language=lang)
        async for chunk in self.llm.astream(prompt):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

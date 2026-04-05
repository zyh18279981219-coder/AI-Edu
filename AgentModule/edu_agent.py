import logging
import os

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_core.prompts import PromptTemplate
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


def rag_search(query: str) -> str:
    """Search course knowledge from the RAG store."""
    try:
        retriever = RAGService().get_retriever()
        return get_context_or_empty(query, retriever)
    except Exception as exc:
        logging.getLogger(__name__).warning("RAG search error: %s", exc)
        return ""


DEFAULT_PROMPT = PromptTemplate.from_template(
    """Answer the user's question as accurately as possible.

You can use these tools if needed:
{tools}

Rules:
1. For greetings or simple questions, answer directly.
2. If the user asks about course files, PDF content, uploaded documents, or learning material, prefer rag_search.
3. Do not invent tool names.
4. When you use a tool, choose from [{tool_names}].
5. Always answer in {language}.

Question: {input}
Thought:{agent_scratchpad}"""
)


def create_agent() -> AgentExecutor:
    rag_search_tool = tool("rag_search")(rag_search)
    tools = [
        wikipedia_search,
        define_word,
        calculator,
        current_date,
        current_weekday,
        detect_language,
        rag_search_tool,
    ]

    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        base_url=base_url,
        api_key=api_key,
    )
    agent = create_react_agent(llm, tools, DEFAULT_PROMPT)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=3,
        handle_parsing_errors=True,
        early_stopping_method="force",
    )


def run_agent(
    question: str,
    executor: AgentExecutor | None = None,
    retriever=None,
    return_details: bool = False,
) -> str | tuple[str, bool, bool]:
    executor = executor or create_agent()
    logger = logging.getLogger(__name__)
    logger.info("edu_agent received question: %s", question[:200])

    used_retriever = False
    if retriever:
        context = get_context_or_empty(question, retriever)
        if context:
            logger.info("edu_agent retrieved context length: %s", len(context))
            question = f"{question}\n\nContext:\n{context}"
            used_retriever = True
        else:
            logger.info("edu_agent retrieved no context")

    lang = LanguageHandler.choose_or_detect(question)
    logger.info("edu_agent detected language: %s", lang)

    try:
        result = executor.invoke({"input": question, "language": lang})
        output = result["output"]

        get_llm_logger().log_llm_call(
            messages=[{"role": "user", "content": question}],
            response=type(
                "Response", (), {"content": output, "response_metadata": {}}
            )(),
            model=model_name,
            module="AgentModule.edu_agent",
            metadata={
                "function": "run_agent",
                "language": lang,
                "used_retriever": used_retriever,
            },
        )
        logger.info("edu_agent completed")
    except Exception as exc:
        output = f"Agent error: {exc}"
        logger.exception("edu_agent failed")

    used_fallback = False

    def _needs_fallback(text: str) -> bool:
        text_stripped = text.strip()
        if not text_stripped:
            return True

        error_markers = [
            "agent error",
            "agent stopped",
            "i don't know",
            "i cannot",
            "i'm unable",
            "我不知道",
            "我无法",
            "抱歉，我无法",
            "无法回答",
        ]
        text_lower = text_stripped.lower()
        return any(marker in text_lower for marker in error_markers)

    if _needs_fallback(output):
        logger.info("edu_agent fallback triggered")
        llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            base_url=base_url,
            api_key=api_key,
        )
        try:
            msg = llm.invoke(question)
            output = getattr(msg, "content", str(msg))

            get_llm_logger().log_llm_call(
                messages=[{"role": "user", "content": question}],
                response=msg,
                model=model_name,
                module="AgentModule.edu_agent",
                metadata={"function": "run_agent_fallback", "language": lang},
            )
            logger.info("edu_agent fallback completed")
        except Exception as exc:
            output = f"LLM error: {exc}"
            logger.exception("edu_agent fallback failed")
        finally:
            used_fallback = True

    output = LanguageHandler.ensure_language(output, lang)

    if return_details:
        return output, used_fallback, used_retriever
    return output

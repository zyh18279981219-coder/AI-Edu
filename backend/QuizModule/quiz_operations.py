from tools.quiz_prompts import (
    generate_topic_list_prompt,
    generate_questions_prompt,
    parse_quiz_questions_response,
)
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableParallel
from LearningPlanModule.learning_plan import LearningPlan
from tools.rag_service import RAGService
from tools.rag_utils import get_context_or_empty
from tools.llm_logger import get_llm_logger
import logging
from tools.env_loader import load_project_env
import os

load_project_env()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")
logger = logging.getLogger(__name__)


def prepare_quiz_questions(
    subject: str, language: str = "en", retriever=None
) -> tuple[list[dict], bool]:
    import httpx
    http_client = httpx.Client(verify=False)
    llm = ChatOpenAI(
        model=model_name, temperature=0, base_url=base_url, api_key=api_key,
        http_client=http_client,
    )

    if retriever is None:
        retriever = RAGService().get_retriever()

    context = get_context_or_empty(subject, retriever)
    used_retriever = bool(context)
    logger.info("Quiz generation used RAG: %s", used_retriever)

    prompt_subject = subject
    if context:
        prompt_subject = f"{subject}\n\nContext:\n{context}"

    # Generate topics
    topic_prompt = generate_topic_list_prompt(prompt_subject, language)
    topic_result = llm.invoke(topic_prompt.format_prompt(subject=prompt_subject))
    
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        messages=[{"role": "user", "content": topic_prompt.format_prompt(subject=prompt_subject).to_string()}],
        response=topic_result,
        model=model_name,
        module="QuizModule.quiz_operations",
        metadata={"function": "prepare_quiz_questions", "step": "generate_topics", "subject": subject, "language": language}
    )
    
    topics = [t.strip() for t in topic_result.content.split("\n") if t.strip()]
    if not topics:
        return [], used_retriever

    max_questions = 20
    max_topics = min(len(topics), 5)
    topics = topics[:max_topics]
    if max_topics == 0:
        return [], used_retriever

    questions_per_topic = max_questions // max_topics

    if retriever:

        def _topic_ctx(inputs):
            return get_context_or_empty(inputs["topic"], retriever)

        context_chain = RunnableLambda(_topic_ctx)
        prompt_chain = RunnableLambda(
            lambda inputs: generate_questions_prompt(
                inputs["topic"], language=language
            ).format_prompt(topic=inputs["topic"])
        )
        question_chain = (
            RunnableParallel({"ctx": context_chain, "prompt": prompt_chain})
            | RunnableLambda(
                lambda d: (d["ctx"] + "\n\n" if d["ctx"] else "")
                + d["prompt"].to_string()
            )
            | llm
        )
    else:
        question_chain = (
            RunnableLambda(
                lambda inputs: generate_questions_prompt(
                    inputs["topic"], language=language
                ).format_prompt(topic=inputs["topic"])
            )
            | llm
        )

    question_sets = question_chain.batch([{"topic": t} for t in topics])

    llm_logger = get_llm_logger()
    for topic, qset in zip(topics, question_sets):
        llm_logger.log_llm_call(
            messages=[{"role": "user", "content": f"Generate questions for topic: {topic}"}],
            response=qset,
            model=model_name,
            module="QuizModule.quiz_operations",
            metadata={"function": "prepare_quiz_questions", "step": "generate_questions", "topic": topic, "language": language}
        )

    questions_list = []
    for topic, qset in zip(topics, question_sets):
        parsed_questions = parse_quiz_questions_response(qset.content, topic)
        if not parsed_questions:
            logger.warning("No valid quiz questions parsed for topic: %s", topic)
            continue
        questions_list.extend(parsed_questions[:questions_per_topic])

    return questions_list, used_retriever


def generate_quiz(subject: str, language: str = "en", retriever=None):
    if retriever is None:
        retriever = RAGService().get_retriever()

    try:
        questions, used_retriever = prepare_quiz_questions(
            subject, language=language, retriever=retriever
        )
        if not questions:
            logger.warning("No quiz topics generated.")
            return {"questions": [], "used_retriever": used_retriever}
            
        logger.info("小测基于 RAG 生成: %s", used_retriever)
        return {"questions": questions, "used_retriever": used_retriever}
    except Exception as e:
        logger.error(f"在生成测试时发生错误： {e}")
        return {"questions": [], "used_retriever": False}

def generate_learning_plan_from_quiz(user_name, quiz_results, language="en"):
    plan = LearningPlan(
        user_name=user_name, quiz_results=quiz_results, user_language=language
    )
    learning_plan = plan.generate_plan()
    return learning_plan

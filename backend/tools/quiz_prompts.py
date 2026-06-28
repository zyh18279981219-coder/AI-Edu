import json
import re
from typing import Dict, List

from langchain_core.prompts import ChatPromptTemplate


def generate_topic_list_prompt(subject: str, language: str = "zh") -> ChatPromptTemplate:
    system_message = (
        "你是一名课程测验设计专家。"
        "请根据给定主题，拆分出适合出题的 3 到 5 个子主题。"
        "只输出子主题列表，每行一个，不要附加解释。"
        f"请使用 {language} 输出。"
    )

    human_message = (
        f"主题：{subject}\n\n"
        "请给出 3 到 5 个适合生成测验题目的子主题。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def generate_questions_prompt(topic: str, language: str = "zh") -> ChatPromptTemplate:
    system_message = (
        "你是一名严谨的课程测验命题专家。"
        "请围绕给定主题生成高质量单选题。"
        "必须只返回一个 JSON 对象，不要输出解释、标题或 Markdown 代码块。"
        'JSON 结构必须是：{{"title":"主题","single-choice":[{{"question":"题干","options":["A. ...","B. ...","C. ...","D. ..."],"right-answer":"A"}}]}}。'
        "single-choice 中必须有 4 道题。"
        "right-answer 只能是 A、B、C、D 之一。"
        f"请使用 {language} 输出题目内容。"
    )

    human_message = (
        f"主题：{topic}\n\n"
        "请生成 4 道高质量单选题，覆盖核心概念、关键方法与实际应用。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def assess_knowledge_level_prompt(
    topic: str, score_percentage: float, language: str = "zh"
) -> ChatPromptTemplate:
    system_message = (
        "你是一名学习反馈导师。"
        "请根据学生测验结果给出简短、具体、可执行的学习建议。"
        f"请使用 {language} 输出。"
    )

    human_message = (
        f"主题：{topic}\n"
        f"得分百分比：{score_percentage}\n\n"
        "请评估学生当前掌握情况，并给出下一步学习建议。"
    )

    return ChatPromptTemplate.from_messages(
        [("system", system_message), ("human", human_message)]
    )


def generate_QUESTION_TEMPLATE(core_topic: str) -> str:
    return (
        "你是一名严谨的课程测验命题专家。\n"
        f"当前主题：{core_topic}\n"
        "请只输出一个 JSON 对象，结构如下：\n"
        '{{"title":"主题","single-choice":[{{"question":"题干","options":["A. ...","B. ...","C. ...","D. ..."],"right-answer":"A"}}]}}\n'
        "必须生成 8 道单选题，right-answer 只能是 A/B/C/D。"
    )


def parse_quiz_questions_response(content: str, topic: str) -> List[Dict[str, str]]:
    questions = _parse_json_questions(content)
    if questions:
        return [_normalize_question(item, topic) for item in questions]

    return _parse_legacy_questions(content, topic)


def _parse_json_questions(content: str) -> List[Dict[str, str]]:
    raw = content.strip()
    if not raw:
        return []

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return []

    try:
        data = json.loads(match.group(0))
    except Exception:
        return []

    items = data.get("single-choice")
    if not isinstance(items, list):
        return []

    valid_items: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options") or []
        answer = str(item.get("right-answer", "")).strip().upper()
        if not question or len(options) < 2:
            continue
        if answer not in {"A", "B", "C", "D"}:
            continue
        valid_items.append(
            {
                "question": question,
                "options": [str(option).strip() for option in options if str(option).strip()],
                "right-answer": answer,
            }
        )
    return valid_items


def _normalize_question(item: Dict[str, str], topic: str) -> Dict[str, str]:
    options = item.get("options") or []
    lines = [item.get("question", "").strip(), *options]
    return {
        "topic": topic,
        "question": "\n".join(line for line in lines if line),
        "correct": str(item.get("right-answer", "")).strip().lower(),
    }


def _parse_legacy_questions(content: str, topic: str) -> List[Dict[str, str]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
    parsed: List[Dict[str, str]] = []
    for block in blocks:
        answer_match = re.search(r"Correct Answer\s*:\s*([A-Da-d])", block)
        correct = answer_match.group(1).lower() if answer_match else "?"
        question_text = re.sub(r"Correct Answer\s*:\s*[A-Da-d]\s*$", "", block).strip()
        if not question_text:
            continue
        parsed.append({"topic": topic, "question": question_text, "correct": correct})
    return parsed

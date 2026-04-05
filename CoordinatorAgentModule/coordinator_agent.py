import json
import logging
import os

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_classic.agents import create_react_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from tools.language_handler import LanguageHandler
from tools.llm_logger import get_llm_logger

load_dotenv()
model_name = os.environ.get("model_name")
base_url = os.environ.get("base_url")
api_key = os.environ.get("api_key")


@tool
def intent_classifier(user_input: str) -> str:
    """Classify user intent from input text."""
    intents = {
        "qa": ["问", "什么", "如何", "为什么", "哪里", "谁", "question", "what", "how", "why", "who"],
        "quiz": ["测试", "测验", "考试", "题目", "quiz", "test", "exam"],
        "summary": ["总结", "归纳", "概括", "summary", "summarize"],
        "plan": ["计划", "学习计划", "规划", "plan", "schedule"],
        "greeting": ["你好", "hello", "hi"],
        "feedback": ["反馈", "建议", "feedback", "suggestion"],
    }

    user_lower = user_input.lower()
    detected = [intent for intent, keywords in intents.items() if any(keyword in user_lower for keyword in keywords)]
    if not detected:
        detected = ["qa"]
    return json.dumps({"intents": detected, "primary": detected[0]}, ensure_ascii=False)


@tool
def task_decomposer(user_input: str) -> str:
    """Decompose a complex user request into subtasks."""
    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        base_url=base_url,
        api_key=api_key,
    )

    prompt = f"""Decompose the following user request into subtasks. Return JSON only.

User request: {user_input}

Output format:
{{
  "is_complex": true,
  "subtasks": [
    {{"step": 1, "action": "action description", "target": "target agent"}}
  ]
}}

Possible target agents: qa_agent, quiz_agent, summary_agent, plan_agent
"""

    try:
        response = llm.invoke(prompt)
        content = response.content
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        return content
    except Exception as exc:
        return json.dumps(
            {
                "is_complex": False,
                "subtasks": [{"step": 1, "action": user_input, "target": "qa_agent"}],
                "error": str(exc),
            },
            ensure_ascii=False,
        )


@tool
def priority_analyzer(tasks: str) -> str:
    """Analyze priority levels for subtasks."""
    try:
        tasks_data = json.loads(tasks)
        subtasks = tasks_data.get("subtasks", [])
        priorities = []
        for task in subtasks:
            action = task.get("action", "").lower()
            if any(keyword in action for keyword in ["urgent", "立刻", "马上", "紧急"]):
                priority = "high"
            elif any(keyword in action for keyword in ["later", "稍后", "以后"]):
                priority = "low"
            else:
                priority = "medium"
            priorities.append(
                {
                    "step": task.get("step"),
                    "priority": priority,
                    "action": task.get("action"),
                }
            )
        return json.dumps({"priorities": priorities}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


COORDINATOR_PROMPT = PromptTemplate.from_template(
    """You are a coordinator agent responsible for intent recognition and task decomposition.

Available tools:
{tools}

When using a tool, choose from [{tool_names}].

Responsibilities:
1. Identify user intent with intent_classifier.
2. If the request is complex, use task_decomposer.
3. If subtasks exist, use priority_analyzer.
4. Return a concise coordination result in {language}.

Question: {input}
Thought:{agent_scratchpad}"""
)


class Coordinator_Agent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            base_url=base_url,
            api_key=api_key,
        )
        self.tools = [intent_classifier, task_decomposer, priority_analyzer]
        agent = create_react_agent(self.llm, self.tools, COORDINATOR_PROMPT)
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True,
            early_stopping_method="force",
        )

    def coordinate(self, user_input: str, return_details: bool = False):
        self.logger.info("Coordinator processing: %s", user_input)
        lang = LanguageHandler.choose_or_detect(user_input)

        try:
            result = self.executor.invoke({"input": user_input, "language": lang})
            output = result["output"]

            get_llm_logger().log_llm_call(
                messages=[{"role": "user", "content": user_input}],
                response=type(
                    "Response", (), {"content": output, "response_metadata": {}}
                )(),
                model=model_name,
                module="AgentModule.coordinator_agent",
                metadata={"function": "coordinate", "language": lang},
            )
            coordination_plan = self._parse_coordination_output(output)
        except Exception as exc:
            output = f"Coordination error: {exc}"
            coordination_plan = {
                "intent": "unknown",
                "is_complex": False,
                "subtasks": [],
                "error": str(exc),
            }
            self.logger.exception("Coordinator error")

        if return_details:
            return output, coordination_plan
        return output

    def _parse_coordination_output(self, output: str):
        coordination = {
            "intent": "unknown",
            "is_complex": False,
            "subtasks": [],
            "routing": "qa_agent",
        }
        try:
            output_lower = output.lower()
            if "intent:" in output_lower:
                intent_part = output.split("intent:", 1)[1].split(".", 1)[0].strip()
                coordination["intent"] = intent_part
            if "subtasks" in output_lower or "decomposed" in output_lower:
                coordination["is_complex"] = True
                import re

                matches = re.findall(r"(\d+)\)\s*(.+?)\s*\((.+?)\)", output)
                if matches:
                    coordination["subtasks"] = [
                        {"step": int(step), "action": action.strip(), "target": target.strip()}
                        for step, action, target in matches
                    ]
            if "route to" in output_lower:
                route_part = output.split("route to", 1)[1].split(".", 1)[0].strip()
                coordination["routing"] = route_part
        except Exception:
            self.logger.exception("Parse coordination output error")
        return coordination

    def analyze_intent(self, user_input: str):
        lang = LanguageHandler.choose_or_detect(user_input)
        prompt = f"""Analyze the user's intent and return JSON only.

Categories: qa, quiz, summary, plan, greeting, feedback
User input: {user_input}

Output format:
{{
  "primary_intent": "...",
  "secondary_intents": [],
  "confidence": 0.0
}}

Answer in {lang}.
"""
        try:
            response = self.llm.invoke(prompt)
            content = response.content
            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(content)
        except Exception as exc:
            return {
                "primary_intent": "qa",
                "secondary_intents": [],
                "confidence": 0.5,
                "error": str(exc),
            }

    def decompose_task(self, user_input: str):
        lang = LanguageHandler.choose_or_detect(user_input)
        prompt = f"""Decompose the following task into sequential subtasks if needed. Return JSON only.

User task: {user_input}

Output format:
{{
  "is_complex": true,
  "subtasks": [
    {{
      "step": 1,
      "description": "...",
      "target_agent": "...",
      "dependencies": []
    }}
  ]
}}

Possible agents: qa_agent, quiz_agent, summary_agent, plan_agent
Answer in {lang}.
"""
        try:
            response = self.llm.invoke(prompt)
            content = response.content
            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(content)
        except Exception as exc:
            return {
                "is_complex": False,
                "subtasks": [
                    {
                        "step": 1,
                        "description": user_input,
                        "target_agent": "qa_agent",
                        "dependencies": [],
                    }
                ],
                "error": str(exc),
            }

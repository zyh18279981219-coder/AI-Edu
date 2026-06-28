from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from ..functions import get_course_detail, get_course_resources
from ..model import deepseek
from ..prompts import explanation
from ..session import session_service

explanation_agent = Agent(
    model=deepseek,
    name='explanation_agent',
    description='5E 教学模型 Explanation 阶段智能体',
    instruction=explanation,
    tools=[get_course_detail,get_course_resources]
)

runner = Runner(
    agent=explanation_agent,
    app_name='explanation',
    session_service=session_service,
    auto_create_session=True
)

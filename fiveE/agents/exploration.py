from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from ..model import deepseek
from ..prompts import exploration
from ..session import session_service

exploration_agent = Agent(
    model=deepseek,
    name='exploration_agent',
    description='5E 教学模型 Exploration 阶段智能体',
    instruction=exploration,
)

runner = Runner(
    agent=exploration_agent,
    app_name='exploration',
    session_service=session_service,
    auto_create_session=True
)

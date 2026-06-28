from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from ..model import deepseek
from ..prompts import elaboration
from ..session import session_service

elaboration_agent = Agent(
    model=deepseek,
    name='elaboration_agent',
    description='5E 教学模型 Elaboration',
    instruction=elaboration
)

runner=Runner(
    agent=elaboration_agent,
    app_name='elaborate',
    session_service=session_service,
    auto_create_session=True
)

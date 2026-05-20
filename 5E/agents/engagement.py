from google.adk.agents.llm_agent import Agent

from functions.courses import is_first_learn
from model import deepseek
from models import ChatResponse
from prompts import engagement
from functions import get_course_detail

engagement_agent = Agent(
    model=deepseek,
    name="engagement",
    description='5E教学模型 Engagement 阶段智能体',
    instruction=engagement,
    tools=[is_first_learn]
)
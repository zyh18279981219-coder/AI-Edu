from google.adk.agents.llm_agent import Agent

from model import deepseek
from prompts import engagement
from functions import get_course_detail

engagement_agent = Agent(
    model=deepseek,
    name="engagement",
    description='5E教学模型 Engagement 阶段智能体',
    instruction=engagement,
    output_key='engagement',
    tools=[get_course_detail]
)

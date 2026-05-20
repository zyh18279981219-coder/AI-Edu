from google.adk.agents.llm_agent import Agent

from functions import get_course_detail
from functions import is_first_learn
from functions import collect_student_interaction
from model import deepseek
from prompts import engagement

engagement_agent = Agent(
    model=deepseek,
    name="engagement",
    description='5E教学模型 Engagement 阶段智能体',
    instruction=engagement,
    tools=[
        collect_student_interaction,
        is_first_learn,
        get_course_detail
    ]
)
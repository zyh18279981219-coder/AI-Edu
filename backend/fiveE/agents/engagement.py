from google.adk.agents.llm_agent import Agent

from ..functions import collect_student_interaction, get_course_detail, is_first_learn
from ..functions.courses import get_related_course
from ..model import deepseek
from ..prompts import engagement

engagement_agent = Agent(
    model=deepseek,
    name="engagement",
    description='5E教学模型 Engagement 阶段智能体',
    instruction=engagement,
    tools=[
        collect_student_interaction,
        is_first_learn,
        get_course_detail,
        get_related_course,
    ]
)

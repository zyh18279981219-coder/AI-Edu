from google.adk.agents.llm_agent import Agent

from ..functions import get_course_detail, is_first_learn, get_related_course, get_learned_courses, get_course_resources, query_resources_content
from ..model import deepseek
from ..prompts import engagement

engagement_agent = Agent(
    model=deepseek,
    name="engagement",
    description='5E教学模型 Engagement 阶段智能体',
    instruction=engagement,
    tools=[
        is_first_learn,
        get_course_detail,
        get_related_course,
        get_learned_courses,
        get_course_resources,
        query_resources_content
    ]
)

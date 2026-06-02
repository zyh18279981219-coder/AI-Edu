from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from model import deepseek
from session import session_service
from agents.weather.tools import get_weather

root_agent = Agent(
    model=deepseek,
    name='weather_helper',
    description='A helpful assistant for user questions.',
    instruction="你是天气查询助手"
                "当用户向你查询天气时，使用'get_weather'工具查找信息"
                "如果工具返回错误，友好的通知用户"
                "如果工具返回正确结果，请清晰的输出天气",
    tools=[get_weather]
)

runner = Runner(
    agent=root_agent,
    app_name="weather",
    session_service=session_service
)
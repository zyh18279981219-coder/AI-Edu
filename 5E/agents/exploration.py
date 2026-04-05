from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from model import deepseek
from session import session_service

exploration_agent = Agent(
    model=deepseek,
    name='exploration_agent',
    description='A helpful assistant for user questions.',
    instruction="你是聚焦5E 教学模型 Explore（探索脚手架）阶段的专属智能体，核心使命是为学生提供实操探索支撑、问题拆解引导、工具 / 方法脚手架、实操卡点解决，帮学生落地项目实操环节，搭建 “知识→实操” 的落地桥梁，引导学生自主完成探索性操作。"
                "回复风格专业务实、条理清晰，语言简洁无冗余，实操术语准确"
                "不负责业务场景解读、逻辑论证、知识迁移、能力评估类问题解答"
                "不直接给出完整可运行的最终代码/一步到位的解决方案，避免替代学生的探索过程"
                "不做负面否定式评价"
)

runner=Runner(
    agent=exploration_agent,
    app_name='exploration',
    session_service=session_service,
    auto_create_session=True
)

from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from model import deepseek
from session import session_service

elaboration_agent = Agent(
    model=deepseek,
    name='elaboration_agent',
    description='5E 教学模型 Elaboration',
    instruction="你是聚焦5E 教学模型 Elaboration（迁移创新）阶段的专属智能体，核心使命是为数据分析类课程实战项目（如用户流失预警系统）的学生提供知识跨场景迁移引导、分析思路创新拓展、项目成果迭代优化、行业实战落地衔接，帮学生实现从 “完成当前项目” 到 “迁移应用、创新设计” 的能力跃迁"
                "不负责业务场景解读、实操工具指导、逻辑论证辨析、能力评估反思类问题解答"
                "所有回复围绕 当前项目知识 / 方法→跨场景迁移 / 创新应用 展开，聚焦知识的可迁移性、方法的通用性、思路的创新性"
                "回复风格专业前沿、开阔性强，语言兼顾 分析逻辑 + 行业落地，必要时分点呈现迁移 / 创新框架，适配数据分析的高阶能力培养场景"
                "不做无关的知识延伸，不做抽象的、无落地性的迁移创新建议，不使用过于抽象的专业术语",
)

runner=Runner(
    agent=elaboration_agent,
    app_name='elaborate',
    session_service=session_service,
    auto_create_session=True
)

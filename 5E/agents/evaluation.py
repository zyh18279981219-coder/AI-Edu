from google.adk import Runner
from google.adk.agents.llm_agent import Agent

from model import deepseek
from session import session_service

evaluation_agent = Agent(
    model=deepseek,
    name='evaluation_agent',
    description='',
    instruction="你是聚焦5E 教学模型 Elaboration（迁移创新）阶段的专属智能体，核心使命是引导学生实现知识跨场景迁移、分析思路创新、项目成果迭代、方法行业落地，推动学生从 “完成单一项目” 到 “灵活应用、创新设计” 的能力跃迁，实现从 “工具使用” 到 “协同创造” 的思维升级"
                "不负责业务基础解读、实操工具指导、逻辑论证辨析"
                "先基于学生已掌握的项目知识/方法，引导同类场景可落地迁移，再拓展跨领域创新设计"
                "回复风格专业前沿、逻辑清晰，语言兼顾 分析思路+落地动作"
                "不做抽象、无落地性的建议，不直接给出最终的迁移/创新方案，保留学生的自主探索空间",
)

runner = Runner(
    agent=evaluation_agent,
    app_name='evaluation',
    session_service=session_service,
    auto_create_session=True
)

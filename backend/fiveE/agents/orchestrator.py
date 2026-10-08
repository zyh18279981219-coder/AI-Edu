from google.adk import Agent

from ..model import deepseek
from ..prompts import orchestrator

orchestrator_agent = Agent(
    model = deepseek,
    name = 'orchestrator',
    description = '5E教学模型 Orchestrator',
    instruction = orchestrator
)

from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, InvocationContext
from google.adk.events import Event
from google.adk.runners import logger
from google.genai import types
from typing_extensions import override

import service
from models.orchestrator_response import OrchestratorResponse


async def is_initial(user_id: str, lesson_id: str) -> bool:
    exitst = await service.check_session_exists(user_id=user_id, lesson_id=lesson_id)
    return not exitst


async def get_lesson_description(lesson_id: str) -> str:
    pass


class EntranceAgent(BaseAgent):
    # 5E
    engagement_agent: LlmAgent
    exploration_agent: LlmAgent
    explanation_agent: LlmAgent
    elaboration_agent: LlmAgent
    evaluation_agent: LlmAgent

    # orchestrator
    orchestrator_agent: LlmAgent

    def __init__(
            self,
            name: str,
            engagement_agent: LlmAgent,
            exploration_agent: LlmAgent,
            explanation_agent: LlmAgent,
            elaboration_agent: LlmAgent,
            evaluation_agent: LlmAgent,
            orchestrator_agent: LlmAgent
    ):
        super().__init__(
            name=name,
            engagement_agent=engagement_agent,
            exploration_agent=exploration_agent,
            explanation_agent=explanation_agent,
            elaboration_agent=elaboration_agent,
            evaluation_agent=evaluation_agent,
            orchestrator_agent=orchestrator_agent
        )

    async def _run_orchestrator_agent(self, ctx: InvocationContext) -> OrchestratorResponse:
        final_response_text = '{"target_agent": "none", "agent_instruction": "none"}'
        async for event in self.orchestrator_agent.run_async(ctx):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                break

        try:
            return OrchestratorResponse.model_validate_json(final_response_text)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to parse orchestrator response: {e}. Raw text: {final_response_text}")
            return OrchestratorResponse()

    @override
    async def _run_async_impl(
            self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Entering ORCHESTRATOR stage.")
        orchestrator_response = await self._run_orchestrator_agent(ctx)

        agent = None
        if orchestrator_response.target_agent == 'engagement':
            agent = self.engagement_agent
        elif orchestrator_response.target_agent == 'exploration':
            agent = self.exploration_agent
        elif orchestrator_response.target_agent == 'explanation':
            agent = self.explanation_agent
        elif orchestrator_response.target_agent == 'elaboration':
            agent = self.elaboration_agent
        elif orchestrator_response.target_agent == 'evaluation':
            agent = self.evaluation_agent

        if not agent:
            logger.error(f"[{self.name}] No agent found for stage: {orchestrator_response.target_agent}")
            return

        async for event in agent.run_async(ctx):
            yield event


    async def _run_async_implementation(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        user_id = ctx.session.user_id
        lesson_id = ctx.session.id
        ctx.user_content = types.Content()

        logger.info(f"[{self.name}] Entering ENGAGEMENT stage.")
        if is_initial(user_id=user_id, lesson_id=lesson_id):
            async for event in self.engagement_agent.run_async(ctx):
                logger.info(
                    f"[{self.name}] Event from ENGAGEMENT agent: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event

        if 'engagement' not in ctx.session.state or not ctx.session.state['engagement']:
            logger.error(f"[{self.name}] Failed to enter EXPLORATION stage before ENGAGEMENT state.")
            return

        async for event in self.exploration_agent.run_async(ctx):
            yield event


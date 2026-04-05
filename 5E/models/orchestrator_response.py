from pydantic import BaseModel


class OrchestratorResponse(BaseModel):
    target_agent: str = "none"

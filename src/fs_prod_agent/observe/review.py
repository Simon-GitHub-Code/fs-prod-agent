"""Human review is a queued state. The agent cannot mark it approved."""

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ReviewItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    resume_token: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    actor_id: str
    tool_name: str
    status: str = "pending"

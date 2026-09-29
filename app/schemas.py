import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreate(BaseModel):
    """Fields accepted when starting a conversation."""

    user_id: uuid.UUID | None = None


class ConversationRead(BaseModel):
    """Public conversation fields returned by the API."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    status: str
    human_required: bool
    escalation_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """Validated input for a customer message sent to the assistant."""

    conversation_id: uuid.UUID
    message: str = Field(min_length=1, max_length=10_000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        """Trim input before length checks so whitespace-only messages are rejected."""
        return value.strip() if isinstance(value, str) else value


class MessageRead(BaseModel):
    """Public representation of a stored conversation message."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    intent_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    """Assistant reply and classification/escalation metadata returned to clients."""

    conversation_id: uuid.UUID
    message: str
    intent: str
    human_required: bool
    escalation_reason: str | None


class HealthResponse(BaseModel):
    """Minimal liveness response for the health endpoint."""

    status: str
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Conversation, Intent, KnowledgeBaseEntry, Message
from app.schemas import ChatResponse
from app.services.llm import LLMService


class ConversationNotFoundError(Exception):
    """Raised when a chat request references a conversation that does not exist."""

    pass


class ChatService:
    """Coordinate conversation context, LLM generation, and message persistence."""

    def __init__(self, database: Session, settings: Settings):
        self.database = database
        self.settings = settings
        self.llm = LLMService(settings)

    async def reply(self, conversation_id: uuid.UUID, content: str) -> ChatResponse:
        """Generate and store one assistant response together with the user message."""
        conversation = self.database.get(Conversation, conversation_id)
        if conversation is None:
            raise ConversationNotFoundError

        # Fetch the most recent messages, then restore chronological order for the model.
        history = list(
            self.database.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(self.settings.conversation_history_limit)
            )
        )
        history.reverse()

        # Add only the best lexical knowledge-base match to the model context.
        knowledge = self._find_knowledge(content)
        result = await self.llm.generate(content, history, knowledge)
        intent = self.database.scalar(select(Intent).where(Intent.name == result.intent))

        # Escalation remains active until a separate human workflow resolves it.
        conversation.human_required = conversation.human_required or result.human_required
        if result.escalation_reason:
            conversation.escalation_reason = result.escalation_reason
        # Distinct timestamps keep the user message before the assistant reply in history.
        timestamp = datetime.now(timezone.utc)
        self.database.add_all(
            [
                Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=content,
                    created_at=timestamp,
                ),
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=result.response,
                    intent_id=intent.id if intent else None,
                    created_at=timestamp + timedelta(microseconds=1),
                ),
            ]
        )
        self.database.commit()
        self.database.refresh(conversation)
        return ChatResponse(
            conversation_id=conversation.id,
            message=result.response,
            intent=result.intent,
            human_required=conversation.human_required,
            escalation_reason=conversation.escalation_reason,
        )

    def _find_knowledge(self, content: str) -> list[KnowledgeBaseEntry]:
        """Rank active knowledge entries by the number of matching message terms."""
        entries = list(
            self.database.scalars(
                select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.is_active.is_(True)).limit(100)
            )
        )
        terms = {term for term in content.casefold().split() if len(term) > 2}
        ranked = sorted(
            entries,
            key=lambda entry: sum(
                term in f"{entry.question} {entry.answer}".casefold() for term in terms
            ),
            reverse=True,
        )
        return [ranked[0]] if ranked and any(
            term in f"{ranked[0].question} {ranked[0].answer}".casefold() for term in terms
        ) else []
import uuid
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Conversation, Message, User
from app.schemas import (
    ChatResponse,
    ConversationCreate,
    ConversationRead,
    HealthResponse,
    MessageCreate,
    MessageRead,
)
from app.services.chat import ChatService, ConversationNotFoundError

router = APIRouter()


def get_chat_service(
    database: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> Generator[ChatService, None, None]:
    """Build the chat orchestration service from request-scoped dependencies."""
    yield ChatService(database, settings)


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Report that the API process is responding to requests."""
    return HealthResponse(status="ok")


@router.post("/conversations", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate, database: Session = Depends(get_db)
) -> Conversation:
    """Create a conversation and optionally associate it with an existing user."""
    if payload.user_id and database.get(User, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    conversation = Conversation(user_id=payload.user_id)
    database.add(conversation)
    database.commit()
    database.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: uuid.UUID, database: Session = Depends(get_db)) -> Conversation:
    """Return one conversation or a not-found response."""
    conversation = database.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
def get_messages(conversation_id: uuid.UUID, database: Session = Depends(get_db)) -> list[Message]:
    """Return all messages for a conversation in chronological order."""
    if database.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return list(
        database.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
        )
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: MessageCreate,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Generate a reply and translate known service errors into HTTP responses."""
    try:
        return await service.reply(payload.conversation_id, payload.message)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.") from error
    except Exception as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        raise HTTPException(status_code=502, detail="Não foi possível gerar uma resposta agora.") from error
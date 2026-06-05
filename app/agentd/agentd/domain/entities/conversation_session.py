from dataclasses import dataclass, replace
from datetime import datetime

from agentd.domain.entities.conversation_message import ConversationMessage


@dataclass(frozen=True, slots=True)
class ConversationSession:
    conversation_id: str
    user_id: str
    messages: tuple[ConversationMessage, ...]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


def create_conversation_session(
    conversation_id: str,
    user_id: str,
    created_at: datetime,
    expires_at: datetime,
) -> ConversationSession:
    return ConversationSession(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=(),
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
    )


def append_conversation_message(
    session: ConversationSession,
    message: ConversationMessage,
    updated_at: datetime,
    expires_at: datetime,
    max_messages: int,
) -> ConversationSession:
    next_messages: tuple[ConversationMessage, ...] = session.messages + (message,)
    limited_messages: tuple[ConversationMessage, ...] = next_messages[-max_messages:]
    return replace(
        session,
        messages=limited_messages,
        updated_at=updated_at,
        expires_at=expires_at,
    )


def touch_conversation_session(
    session: ConversationSession,
    updated_at: datetime,
    expires_at: datetime,
) -> ConversationSession:
    return replace(session, updated_at=updated_at, expires_at=expires_at)


def is_conversation_session_expired(
    session: ConversationSession,
    current_time: datetime,
) -> bool:
    return current_time >= session.expires_at
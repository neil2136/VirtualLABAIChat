from datetime import datetime, timedelta, timezone
from uuid import uuid4

from agentd.domain.entities.conversation_message import ConversationMessage, MessageRole
from agentd.domain.entities.conversation_session import (
    ConversationSession,
    append_conversation_message,
    create_conversation_session,
    is_conversation_session_expired,
    touch_conversation_session,
)
from agentd.domain.errors.conversation_errors import (
    ConversationAccessDeniedError,
    ConversationExpiredError,
    ConversationNotFoundError,
)
from agentd.infrastructure.repositories.in_memory_conversation_repository import (
    InMemoryConversationRepository,
    cleanup_expired_conversation_sessions,
    delete_conversation_session,
    get_conversation_session,
    save_conversation_session,
)


def get_current_time() -> datetime:
    return datetime.now(timezone.utc)


def build_expiration_time(current_time: datetime, session_ttl_seconds: int) -> datetime:
    return current_time + timedelta(seconds=session_ttl_seconds)


def create_conversation(
    repository: InMemoryConversationRepository,
    user_id: str,
    session_ttl_seconds: int,
) -> ConversationSession:
    current_time: datetime = get_current_time()
    expires_at: datetime = build_expiration_time(current_time, session_ttl_seconds)
    session: ConversationSession = create_conversation_session(
        conversation_id=str(uuid4()),
        user_id=user_id,
        created_at=current_time,
        expires_at=expires_at,
    )
    save_conversation_session(repository, session)
    return session


def get_conversation_for_user(
    repository: InMemoryConversationRepository,
    conversation_id: str,
    user_id: str,
    session_ttl_seconds: int,
) -> ConversationSession:
    cleanup_expired_sessions(repository)
    session: ConversationSession | None = get_conversation_session(repository, conversation_id)

    if session is None:
        raise ConversationNotFoundError(conversation_id)

    if session.user_id != user_id:
        raise ConversationAccessDeniedError(conversation_id)

    current_time: datetime = get_current_time()
    if is_conversation_session_expired(session, current_time):
        delete_conversation_session(repository, conversation_id)
        raise ConversationExpiredError(conversation_id)

    refreshed_session: ConversationSession = touch_conversation_session(
        session=session,
        updated_at=current_time,
        expires_at=build_expiration_time(current_time, session_ttl_seconds),
    )
    save_conversation_session(repository, refreshed_session)
    return refreshed_session


def append_message_to_conversation(
    repository: InMemoryConversationRepository,
    conversation_id: str,
    user_id: str,
    role: MessageRole,
    content: str,
    session_ttl_seconds: int,
    max_conversation_messages: int,
) -> ConversationSession:
    session: ConversationSession = get_conversation_for_user(
        repository=repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )
    current_time: datetime = get_current_time()
    message: ConversationMessage = ConversationMessage(role=role, content=content, created_at=current_time)
    updated_session: ConversationSession = append_conversation_message(
        session=session,
        message=message,
        updated_at=current_time,
        expires_at=build_expiration_time(current_time, session_ttl_seconds),
        max_messages=max_conversation_messages,
    )
    save_conversation_session(repository, updated_session)
    return updated_session


def delete_conversation_for_user(
    repository: InMemoryConversationRepository,
    conversation_id: str,
    user_id: str,
    session_ttl_seconds: int,
) -> None:
    get_conversation_for_user(
        repository=repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )
    delete_conversation_session(repository, conversation_id)


def cleanup_expired_sessions(repository: InMemoryConversationRepository) -> tuple[str, ...]:
    return cleanup_expired_conversation_sessions(repository, get_current_time())
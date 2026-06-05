from dataclasses import dataclass, field
from datetime import datetime

from agentd.domain.entities.conversation_session import ConversationSession, is_conversation_session_expired


@dataclass(slots=True)
class InMemoryConversationRepository:
    sessions: dict[str, ConversationSession] = field(default_factory=dict)


def create_in_memory_conversation_repository() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


def save_conversation_session(
    repository: InMemoryConversationRepository,
    session: ConversationSession,
) -> None:
    repository.sessions[session.conversation_id] = session


def get_conversation_session(
    repository: InMemoryConversationRepository,
    conversation_id: str,
) -> ConversationSession | None:
    return repository.sessions.get(conversation_id)


def delete_conversation_session(
    repository: InMemoryConversationRepository,
    conversation_id: str,
) -> bool:
    session_exists: bool = conversation_id in repository.sessions
    if session_exists:
        del repository.sessions[conversation_id]
    return session_exists


def cleanup_expired_conversation_sessions(
    repository: InMemoryConversationRepository,
    current_time: datetime,
) -> tuple[str, ...]:
    expired_conversation_ids: tuple[str, ...] = tuple(
        conversation_id
        for conversation_id, session in repository.sessions.items()
        if is_conversation_session_expired(session, current_time)
    )

    for conversation_id in expired_conversation_ids:
        del repository.sessions[conversation_id]

    return expired_conversation_ids
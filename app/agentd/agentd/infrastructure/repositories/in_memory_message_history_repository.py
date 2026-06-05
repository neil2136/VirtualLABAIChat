from dataclasses import dataclass, field


@dataclass(slots=True)
class InMemoryMessageHistoryRepository:
    message_histories: dict[str, bytes] = field(default_factory=dict)


def create_in_memory_message_history_repository() -> InMemoryMessageHistoryRepository:
    return InMemoryMessageHistoryRepository()


def save_message_history(
    repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
    message_history_json: bytes,
) -> None:
    repository.message_histories[conversation_id] = message_history_json


def get_message_history(
    repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
) -> bytes | None:
    return repository.message_histories.get(conversation_id)


def delete_message_history(
    repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
) -> bool:
    history_exists: bool = conversation_id in repository.message_histories
    if history_exists:
        del repository.message_histories[conversation_id]
    return history_exists


def delete_message_histories(
    repository: InMemoryMessageHistoryRepository,
    conversation_ids: tuple[str, ...],
) -> None:
    for conversation_id in conversation_ids:
        delete_message_history(repository, conversation_id)
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import TypeAlias, TypeGuard

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ToolReturnPart,
)

from agentd.application.services.conversation_service import (
    append_message_to_conversation,
)
from agentd.application.services.conversation_service import cleanup_expired_sessions
from agentd.application.services.conversation_service import create_conversation
from agentd.application.services.conversation_service import (
    delete_conversation_for_user,
)
from agentd.application.services.conversation_service import get_conversation_for_user
from agentd.core.debug import emit_debug_log
from agentd.domain.entities.conversation_session import ConversationSession
from agentd.domain.types.chat_types import (
    BORROW_DEVICE_STRUCTURED_DATA_TYPE,
    BORROW_DEVICE_TOOL_NAME,
    DUT_SEARCH_STRUCTURED_DATA_TYPE,
    DUT_SEARCH_TOOL_NAME,
    RETURN_DEVICE_STRUCTURED_DATA_TYPE,
    RETURN_DEVICE_TOOL_NAME,
    ChatAgentDeps,
)
from agentd.infrastructure.repositories.in_memory_conversation_repository import (
    InMemoryConversationRepository,
)
from agentd.infrastructure.repositories.in_memory_message_history_repository import (
    InMemoryMessageHistoryRepository,
    delete_message_histories,
    delete_message_history,
    get_message_history,
    save_message_history,
)

StructuredDataPayload: TypeAlias = dict[str, object]
GENERAL_DUT_SEARCH_RESULT_FIELD_NAMES: tuple[str, ...] = (
    "id",
    "sn",
    "owner_raw",
    "owner_account",
    "owner_display_name",
    "owner_label",
)
IDLE_DUT_STRUCTURED_DATA_TYPE: str = "idle_dut_device_list"
IDLE_DUT_SEARCH_TOOL_NAME: str = "search_idle_dut_devices_by_model"


@dataclass(frozen=True, slots=True)
class ChatTurnResult:
    conversation_id: str
    assistant_message: str
    conversation: ConversationSession


@dataclass(frozen=True, slots=True)
class MessageStartStreamEvent:
    conversation_id: str


@dataclass(frozen=True, slots=True)
class TokenStreamEvent:
    conversation_id: str
    token: str


@dataclass(frozen=True, slots=True)
class ToolCallStreamEvent:
    conversation_id: str
    tool_name: str
    arguments_json: str


@dataclass(frozen=True, slots=True)
class ToolResultStreamEvent:
    conversation_id: str
    tool_name: str
    result_json: str


@dataclass(frozen=True, slots=True)
class MessageEndStreamEvent:
    conversation_id: str
    message: str
    structured_data: tuple[StructuredDataPayload, ...] | None = None


@dataclass(frozen=True, slots=True)
class ErrorStreamEvent:
    conversation_id: str
    code: str
    message: str


ChatStreamEvent = (
    MessageStartStreamEvent
    | TokenStreamEvent
    | ToolCallStreamEvent
    | ToolResultStreamEvent
    | MessageEndStreamEvent
    | ErrorStreamEvent
)


def is_idle_dut_structured_data_payload(
    payload: object,
) -> TypeGuard[StructuredDataPayload]:
    if not isinstance(payload, dict):
        return False

    payload_type: object = payload.get("type")
    tool_name: object = payload.get("tool_name")
    query: object = payload.get("query")
    items: object = payload.get("items")
    count: object = payload.get("count")
    return (
        payload_type == IDLE_DUT_STRUCTURED_DATA_TYPE
        and tool_name == IDLE_DUT_SEARCH_TOOL_NAME
        and isinstance(query, dict)
        and isinstance(items, list)
        and isinstance(count, int)
    )


def is_general_dut_structured_data_payload(
    payload: object,
) -> TypeGuard[StructuredDataPayload]:
    if not isinstance(payload, dict):
        return False

    payload_type: object = payload.get("type")
    tool_name: object = payload.get("tool_name")
    query: object = payload.get("query")
    items: object = payload.get("items")
    count: object = payload.get("count")
    if (
        payload_type != DUT_SEARCH_STRUCTURED_DATA_TYPE
        or tool_name != DUT_SEARCH_TOOL_NAME
        or not isinstance(query, dict)
        or not isinstance(items, list)
        or not isinstance(count, int)
    ):
        return False

    return all(
        isinstance(item, dict)
        and all(
            field_name in item
            for field_name in GENERAL_DUT_SEARCH_RESULT_FIELD_NAMES
        )
        for item in items
    )


def is_device_action_structured_data_payload(
    payload: object,
    payload_type: str,
    tool_name: str,
    result_field_names: tuple[str, ...],
) -> TypeGuard[StructuredDataPayload]:
    if not isinstance(payload, dict):
        return False

    payload_type_value: object = payload.get("type")
    tool_name_value: object = payload.get("tool_name")
    result: object = payload.get("result")
    return (
        payload_type_value == payload_type
        and tool_name_value == tool_name
        and isinstance(result, dict)
        and all(
            isinstance(result.get(field_name), str) for field_name in result_field_names
        )
    )


def is_borrow_device_structured_data_payload(
    payload: object,
) -> TypeGuard[StructuredDataPayload]:
    return is_device_action_structured_data_payload(
        payload=payload,
        payload_type=BORROW_DEVICE_STRUCTURED_DATA_TYPE,
        tool_name=BORROW_DEVICE_TOOL_NAME,
        result_field_names=("device_id", "message", "requester", "status", "type"),
    )


def is_return_device_structured_data_payload(
    payload: object,
) -> TypeGuard[StructuredDataPayload]:
    return is_device_action_structured_data_payload(
        payload=payload,
        payload_type=RETURN_DEVICE_STRUCTURED_DATA_TYPE,
        tool_name=RETURN_DEVICE_TOOL_NAME,
        result_field_names=("device_id", "message", "owner", "status", "type"),
    )


def extract_tool_return_structured_data(
    part: ToolReturnPart,
) -> StructuredDataPayload | None:
    payload: dict[str, object] = part.model_response_object()
    if part.tool_name == DUT_SEARCH_TOOL_NAME:
        if not is_general_dut_structured_data_payload(payload):
            emit_debug_log(
                "chat_service.structured_data.invalid",
                tool_name=part.tool_name,
                payload=payload,
            )
            return None
        emit_debug_log(
            "chat_service.structured_data.extracted",
            tool_name=part.tool_name,
            payload_type=payload.get("type"),
        )
        return payload

    if part.tool_name == IDLE_DUT_SEARCH_TOOL_NAME:
        if not is_idle_dut_structured_data_payload(payload):
            emit_debug_log(
                "chat_service.structured_data.invalid",
                tool_name=part.tool_name,
                payload=payload,
            )
            return None
        emit_debug_log(
            "chat_service.structured_data.extracted",
            tool_name=part.tool_name,
            payload_type=payload.get("type"),
        )
        return payload

    if part.tool_name == BORROW_DEVICE_TOOL_NAME:
        if not is_borrow_device_structured_data_payload(payload):
            emit_debug_log(
                "chat_service.structured_data.invalid",
                tool_name=part.tool_name,
                payload=payload,
            )
            return None
        emit_debug_log(
            "chat_service.structured_data.extracted",
            tool_name=part.tool_name,
            payload_type=payload.get("type"),
        )
        return payload

    if part.tool_name == RETURN_DEVICE_TOOL_NAME:
        if not is_return_device_structured_data_payload(payload):
            emit_debug_log(
                "chat_service.structured_data.invalid",
                tool_name=part.tool_name,
                payload=payload,
            )
            return None
        emit_debug_log(
            "chat_service.structured_data.extracted",
            tool_name=part.tool_name,
            payload_type=payload.get("type"),
        )
        return payload

    emit_debug_log(
        "chat_service.structured_data.skipped",
        tool_name=part.tool_name,
    )
    return None


def extract_message_end_structured_data(
    messages: Sequence[ModelMessage],
) -> tuple[StructuredDataPayload, ...]:
    structured_data: list[StructuredDataPayload] = []
    for message in messages:
        if not isinstance(message, ModelRequest):
            continue

        for part in message.parts:
            if not isinstance(part, ToolReturnPart):
                continue

            payload: StructuredDataPayload | None = extract_tool_return_structured_data(
                part
            )
            if payload is not None:
                structured_data.append(payload)

    emit_debug_log(
        "chat_service.structured_data.collected",
        structured_data_count=len(structured_data),
        structured_data_types=tuple(
            str(payload.get("type")) for payload in structured_data
        ),
    )
    return tuple(structured_data)


def load_message_history(
    repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
) -> list[ModelMessage]:
    message_history_json: bytes | None = get_message_history(
        repository, conversation_id
    )
    if message_history_json is None:
        return []

    return list(ModelMessagesTypeAdapter.validate_json(message_history_json))


def cleanup_expired_chat_histories(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
) -> tuple[str, ...]:
    expired_conversation_ids: tuple[str, ...] = cleanup_expired_sessions(
        conversation_repository
    )
    delete_message_histories(message_history_repository, expired_conversation_ids)
    return expired_conversation_ids


def create_chat_conversation(
    conversation_repository: InMemoryConversationRepository,
    user_id: str,
    session_ttl_seconds: int,
) -> ConversationSession:
    return create_conversation(
        repository=conversation_repository,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )


def prepare_chat_turn(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
    user_id: str,
    session_ttl_seconds: int,
) -> list[ModelMessage]:
    cleanup_expired_chat_histories(conversation_repository, message_history_repository)
    get_conversation_for_user(
        repository=conversation_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )
    return load_message_history(message_history_repository, conversation_id)


def persist_chat_turn(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
    user_id: str,
    user_prompt: str,
    assistant_message: str,
    message_history_json: bytes,
    session_ttl_seconds: int,
    max_conversation_messages: int,
) -> ConversationSession:
    save_message_history(
        message_history_repository, conversation_id, message_history_json
    )
    append_message_to_conversation(
        repository=conversation_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=user_prompt,
        session_ttl_seconds=session_ttl_seconds,
        max_conversation_messages=max_conversation_messages,
    )
    return append_message_to_conversation(
        repository=conversation_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content=assistant_message,
        session_ttl_seconds=session_ttl_seconds,
        max_conversation_messages=max_conversation_messages,
    )


async def run_chat_turn(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
    agent: Agent[ChatAgentDeps, str],
    conversation_id: str,
    user_id: str,
    user_prompt: str,
    session_ttl_seconds: int,
    max_conversation_messages: int,
) -> ChatTurnResult:
    message_history: list[ModelMessage] = prepare_chat_turn(
        conversation_repository=conversation_repository,
        message_history_repository=message_history_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )
    emit_debug_log(
        "chat_service.run.start",
        conversation_id=conversation_id,
        user_id=user_id,
        user_prompt=user_prompt,
        history_length=len(message_history),
    )
    result = await agent.run(
        user_prompt=user_prompt,
        message_history=list(message_history),
        deps=ChatAgentDeps(user_id=user_id, user_prompt=user_prompt),
    )
    conversation: ConversationSession = persist_chat_turn(
        conversation_repository=conversation_repository,
        message_history_repository=message_history_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        user_prompt=user_prompt,
        assistant_message=result.output,
        message_history_json=result.all_messages_json(),
        session_ttl_seconds=session_ttl_seconds,
        max_conversation_messages=max_conversation_messages,
    )
    return ChatTurnResult(
        conversation_id=conversation.conversation_id,
        assistant_message=result.output,
        conversation=conversation,
    )


async def stream_chat_turn(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
    agent: Agent[ChatAgentDeps, str],
    conversation_id: str,
    user_id: str,
    user_prompt: str,
    message_history: Sequence[ModelMessage],
    session_ttl_seconds: int,
    max_conversation_messages: int,
) -> AsyncIterator[ChatStreamEvent]:
    emit_debug_log(
        "chat_service.stream.start",
        conversation_id=conversation_id,
        user_id=user_id,
        user_prompt=user_prompt,
        history_length=len(message_history),
    )
    yield MessageStartStreamEvent(conversation_id=conversation_id)

    try:
        token_count: int = 0
        token_characters: int = 0
        assistant_message: str = ""
        structured_data: tuple[StructuredDataPayload, ...] = ()
        async with agent.run_stream(
            user_prompt=user_prompt,
            message_history=list(message_history),
            deps=ChatAgentDeps(user_id=user_id, user_prompt=user_prompt),
        ) as response:
            async for token in response.stream_text(delta=True, debounce_by=None):
                if token != "":
                    token_count += 1
                    token_characters += len(token)
                    emit_debug_log(
                        "chat_service.stream.token",
                        conversation_id=conversation_id,
                        token_count=token_count,
                        token_length=len(token),
                        token_preview=token[:200],
                    )
                    yield TokenStreamEvent(conversation_id=conversation_id, token=token)

            assistant_message = await response.get_output()
            structured_data = extract_message_end_structured_data(
                response.new_messages()
            )
            emit_debug_log(
                "chat_service.stream.output",
                conversation_id=conversation_id,
                token_count=token_count,
                token_characters=token_characters,
                structured_data_count=len(structured_data),
                assistant_message_length=len(assistant_message),
                assistant_message_preview=assistant_message[:500],
            )
            conversation: ConversationSession = persist_chat_turn(
                conversation_repository=conversation_repository,
                message_history_repository=message_history_repository,
                conversation_id=conversation_id,
                user_id=user_id,
                user_prompt=user_prompt,
                assistant_message=assistant_message,
                message_history_json=response.all_messages_json(),
                session_ttl_seconds=session_ttl_seconds,
                max_conversation_messages=max_conversation_messages,
            )

        emit_debug_log(
            "chat_service.stream.completed",
            conversation_id=conversation.conversation_id,
            user_id=user_id,
            structured_data_count=len(structured_data),
            assistant_message_preview=assistant_message[:500],
        )
        yield MessageEndStreamEvent(
            conversation_id=conversation.conversation_id,
            message=assistant_message,
            structured_data=structured_data if structured_data else None,
        )
    except Exception as exc:
        emit_debug_log(
            "chat_service.stream.error",
            conversation_id=conversation_id,
            user_id=user_id,
            error=repr(exc),
        )
        yield ErrorStreamEvent(
            conversation_id=conversation_id,
            code="stream_error",
            message=str(exc),
        )


def delete_chat_conversation(
    conversation_repository: InMemoryConversationRepository,
    message_history_repository: InMemoryMessageHistoryRepository,
    conversation_id: str,
    user_id: str,
    session_ttl_seconds: int,
) -> None:
    delete_conversation_for_user(
        repository=conversation_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=session_ttl_seconds,
    )
    delete_message_history(message_history_repository, conversation_id)

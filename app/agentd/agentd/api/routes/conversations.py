from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from agentd.agents.chat_agent import get_chat_agent
from agentd.api.dependencies.settings import get_app_settings
from agentd.api.dependencies.user import get_current_user_id
from agentd.api.schemas.conversations import (
    BorrowDeviceStructuredData,
    CreateConversationResponse,
    DeleteConversationResponse,
    DutDeviceListData,
    ErrorEventData,
    IdleDutDeviceListData,
    MessageEndEventData,
    MessageEndStructuredDataItem,
    MessageStartEventData,
    ReturnDeviceStructuredData,
    StreamMessageRequest,
    TokenEventData,
    ToolCallEventData,
    ToolResultEventData,
)
from agentd.application.services.chat_service import (
    ChatStreamEvent,
    ErrorStreamEvent,
    MessageEndStreamEvent,
    MessageStartStreamEvent,
    TokenStreamEvent,
    ToolCallStreamEvent,
    ToolResultStreamEvent,
    create_chat_conversation,
    delete_chat_conversation,
    prepare_chat_turn,
    stream_chat_turn,
)
from agentd.core.debug import emit_debug_log
from agentd.infrastructure.config import Settings
from agentd.infrastructure.repositories.in_memory_conversation_repository import (
    InMemoryConversationRepository,
)
from agentd.infrastructure.repositories.in_memory_message_history_repository import (
    InMemoryMessageHistoryRepository,
)
from agentd.infrastructure.streaming.sse import format_sse_event

router: APIRouter = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_repository(request: Request) -> InMemoryConversationRepository:
    return request.app.state.conversation_repository


def get_message_history_repository(
    request: Request,
) -> InMemoryMessageHistoryRepository:
    return request.app.state.message_history_repository


def encode_message_end_structured_data_item(
    item: dict[str, object],
) -> MessageEndStructuredDataItem:
    payload_type: object = item.get("type")
    emit_debug_log(
        "api.conversation.structured_data.encode",
        payload_type=payload_type,
    )
    if payload_type == "dut_device_list":
        return DutDeviceListData.model_validate(item)
    if payload_type == "idle_dut_device_list":
        return IdleDutDeviceListData.model_validate(item)
    if payload_type == "borrow_device_result":
        return BorrowDeviceStructuredData.model_validate(item)
    if payload_type == "return_device_result":
        return ReturnDeviceStructuredData.model_validate(item)
    raise ValueError(f"Unsupported structured_data payload type: {payload_type!r}")


def encode_chat_stream_event(event: ChatStreamEvent) -> str:
    if isinstance(event, MessageStartStreamEvent):
        return format_sse_event(
            event="message_start",
            data=MessageStartEventData(conversation_id=event.conversation_id),
        )

    if isinstance(event, TokenStreamEvent):
        return format_sse_event(
            event="token",
            data=TokenEventData(
                conversation_id=event.conversation_id, token=event.token
            ),
        )

    if isinstance(event, ToolCallStreamEvent):
        return format_sse_event(
            event="tool_call",
            data=ToolCallEventData(
                conversation_id=event.conversation_id,
                tool_name=event.tool_name,
                arguments_json=event.arguments_json,
            ),
        )

    if isinstance(event, ToolResultStreamEvent):
        return format_sse_event(
            event="tool_result",
            data=ToolResultEventData(
                conversation_id=event.conversation_id,
                tool_name=event.tool_name,
                result_json=event.result_json,
            ),
        )

    if isinstance(event, MessageEndStreamEvent):
        structured_data: list[MessageEndStructuredDataItem] | None = None
        if event.structured_data is not None:
            structured_data = [
                encode_message_end_structured_data_item(item)
                for item in event.structured_data
            ]
        emit_debug_log(
            "api.conversation.message_end.encode",
            conversation_id=event.conversation_id,
            structured_data_count=0
            if structured_data is None
            else len(structured_data),
            structured_data_types=()
            if structured_data is None
            else tuple(item.type for item in structured_data),
        )
        return format_sse_event(
            event="message_end",
            data=MessageEndEventData(
                conversation_id=event.conversation_id,
                message=event.message,
                structured_data=structured_data,
            ),
        )

    if isinstance(event, ErrorStreamEvent):
        return format_sse_event(
            event="error",
            data=ErrorEventData(
                conversation_id=event.conversation_id,
                code=event.code,
                message=event.message,
            ),
        )

    raise TypeError(f"Unsupported chat stream event: {type(event)!r}")


@router.post(
    "", response_model=CreateConversationResponse, status_code=status.HTTP_201_CREATED
)
def create_conversation_route(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
) -> CreateConversationResponse:
    conversation_repository: InMemoryConversationRepository = (
        get_conversation_repository(request)
    )
    conversation = create_chat_conversation(
        conversation_repository=conversation_repository,
        user_id=user_id,
        session_ttl_seconds=settings.session_ttl_seconds,
    )
    return CreateConversationResponse(
        conversation_id=conversation.conversation_id,
        created_at=conversation.created_at,
        expires_at=conversation.expires_at,
    )


@router.post("/{conversation_id}/messages/stream")
def stream_conversation_message_route(
    conversation_id: str,
    payload: StreamMessageRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    conversation_repository: InMemoryConversationRepository = (
        get_conversation_repository(request)
    )
    message_history_repository: InMemoryMessageHistoryRepository = (
        get_message_history_repository(request)
    )
    emit_debug_log(
        "api.conversation.stream.start",
        conversation_id=conversation_id,
        user_id=user_id,
        message=payload.message,
        trusted_user_header=settings.trusted_user_header,
    )
    agent = get_chat_agent(settings)
    message_history = prepare_chat_turn(
        conversation_repository=conversation_repository,
        message_history_repository=message_history_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=settings.session_ttl_seconds,
    )
    emit_debug_log(
        "api.conversation.stream.prepared",
        conversation_id=conversation_id,
        user_id=user_id,
        history_length=len(message_history),
    )

    async def event_stream() -> AsyncIterator[str]:
        async for event in stream_chat_turn(
            conversation_repository=conversation_repository,
            message_history_repository=message_history_repository,
            agent=agent,
            conversation_id=conversation_id,
            user_id=user_id,
            user_prompt=payload.message,
            message_history=message_history,
            session_ttl_seconds=settings.session_ttl_seconds,
            max_conversation_messages=settings.max_conversation_messages,
        ):
            emit_debug_log(
                "api.conversation.stream.event",
                conversation_id=conversation_id,
                user_id=user_id,
                event_type=type(event).__name__,
            )
            yield encode_chat_stream_event(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation_route(
    conversation_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_app_settings),
) -> DeleteConversationResponse:
    conversation_repository: InMemoryConversationRepository = (
        get_conversation_repository(request)
    )
    message_history_repository: InMemoryMessageHistoryRepository = (
        get_message_history_repository(request)
    )
    delete_chat_conversation(
        conversation_repository=conversation_repository,
        message_history_repository=message_history_repository,
        conversation_id=conversation_id,
        user_id=user_id,
        session_ttl_seconds=settings.session_ttl_seconds,
    )
    return DeleteConversationResponse(conversation_id=conversation_id, deleted=True)

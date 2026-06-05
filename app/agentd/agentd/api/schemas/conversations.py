from datetime import datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, field_validator


class CreateConversationResponse(BaseModel):
    conversation_id: str
    created_at: datetime
    expires_at: datetime


class DeleteConversationResponse(BaseModel):
    conversation_id: str
    deleted: Literal[True]


class StreamMessageRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned_value: str = value.strip()
        if cleaned_value == "":
            raise ValueError("message must not be blank.")
        return cleaned_value


class MessageStartEventData(BaseModel):
    conversation_id: str


class TokenEventData(BaseModel):
    conversation_id: str
    token: str


class ToolCallEventData(BaseModel):
    conversation_id: str
    tool_name: str
    arguments_json: str


class ToolResultEventData(BaseModel):
    conversation_id: str
    tool_name: str
    result_json: str


class DutDeviceListQueryFilterData(BaseModel):
    field_name: str
    value: str | int | float | bool


class DutDeviceListQueryData(BaseModel):
    keyword: str
    limit: int
    filters: list[DutDeviceListQueryFilterData]


class DutDeviceListItemData(BaseModel):
    id: str | None
    sn: str | None
    owner_raw: str | None
    owner_account: str | None
    owner_display_name: str | None
    owner_label: str | None


class DutDeviceListData(BaseModel):
    type: Literal["dut_device_list"]
    tool_name: Literal["search_dut_devices"]
    query: DutDeviceListQueryData
    count: int
    items: list[DutDeviceListItemData]


class IdleDutDeviceListQueryData(BaseModel):
    model: str
    limit: int


class IdleDutDeviceListItemData(BaseModel):
    id: str | None
    sn: str | None
    product: str | None
    product_type: str | None
    owner_raw: str | None
    owner_account: str | None
    owner_display_name: str | None
    owner_label: str | None
    user: str | None


class IdleDutDeviceListData(BaseModel):
    type: Literal["idle_dut_device_list"]
    tool_name: Literal["search_idle_dut_devices_by_model"]
    query: IdleDutDeviceListQueryData
    count: int
    items: list[IdleDutDeviceListItemData]


class BorrowDeviceResultData(BaseModel):
    device_id: str
    message: str
    requester: str
    status: str
    type: str


class BorrowDeviceStructuredData(BaseModel):
    type: Literal["borrow_device_result"]
    tool_name: Literal["borrow_device"]
    result: BorrowDeviceResultData


class ReturnDeviceResultData(BaseModel):
    device_id: str
    message: str
    owner: str
    status: str
    type: str


class ReturnDeviceStructuredData(BaseModel):
    type: Literal["return_device_result"]
    tool_name: Literal["return_device"]
    result: ReturnDeviceResultData


MessageEndStructuredDataItem: TypeAlias = (
    DutDeviceListData
    | IdleDutDeviceListData
    | BorrowDeviceStructuredData
    | ReturnDeviceStructuredData
)


class MessageEndEventData(BaseModel):
    conversation_id: str
    message: str
    structured_data: list[MessageEndStructuredDataItem] | None = None


class ErrorEventData(BaseModel):
    conversation_id: str
    code: str
    message: str

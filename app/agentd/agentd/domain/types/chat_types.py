from dataclasses import dataclass

DUT_SEARCH_STRUCTURED_DATA_TYPE: str = "dut_device_list"
DUT_SEARCH_TOOL_NAME: str = "search_dut_devices"
BORROW_DEVICE_STRUCTURED_DATA_TYPE: str = "borrow_device_result"
BORROW_DEVICE_TOOL_NAME: str = "borrow_device"
RETURN_DEVICE_STRUCTURED_DATA_TYPE: str = "return_device_result"
RETURN_DEVICE_TOOL_NAME: str = "return_device"


@dataclass(frozen=True, slots=True)
class DutDeviceListQueryFilter:
    field_name: str
    value: str | int | float | bool


@dataclass(frozen=True, slots=True)
class DutDeviceListQuery:
    keyword: str
    limit: int
    filters: tuple[DutDeviceListQueryFilter, ...]


@dataclass(frozen=True, slots=True)
class DutDeviceListItem:
    id: str | None
    sn: str | None
    owner_raw: str | None
    owner_account: str | None
    owner_display_name: str | None
    owner_label: str | None


@dataclass(frozen=True, slots=True)
class DutDeviceListPayload:
    type: str
    tool_name: str
    query: DutDeviceListQuery
    count: int
    items: tuple[DutDeviceListItem, ...]


@dataclass(frozen=True, slots=True)
class IdleDutDeviceListQuery:
    model: str
    limit: int


@dataclass(frozen=True, slots=True)
class IdleDutDeviceListItem:
    id: str | None
    sn: str | None
    product: str | None
    product_type: str | None
    owner_raw: str | None
    owner_account: str | None
    owner_display_name: str | None
    owner_label: str | None
    user: str | None


@dataclass(frozen=True, slots=True)
class IdleDutDeviceListPayload:
    type: str
    tool_name: str
    query: IdleDutDeviceListQuery
    count: int
    items: tuple[IdleDutDeviceListItem, ...]


@dataclass(frozen=True, slots=True)
class ChatAgentDeps:
    user_id: str
    user_prompt: str


@dataclass(frozen=True, slots=True)
class BorrowDeviceResult:
    device_id: str
    message: str
    requester: str
    status: str
    type: str


@dataclass(frozen=True, slots=True)
class BorrowDevicePayload:
    type: str
    tool_name: str
    result: BorrowDeviceResult


@dataclass(frozen=True, slots=True)
class ReturnDeviceResult:
    device_id: str
    message: str
    owner: str
    status: str
    type: str


@dataclass(frozen=True, slots=True)
class ReturnDevicePayload:
    type: str
    tool_name: str
    result: ReturnDeviceResult

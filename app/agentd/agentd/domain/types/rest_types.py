from dataclasses import dataclass
from typing import Literal, TypeAlias

RestAuthType = Literal[
    "none",
    "bearer_token",
    "basic_auth",
    "api_key_header",
    "api_key_query",
    "custom_headers",
]
RestMethod = Literal["GET", "HEAD", "POST"]
RestQueryParamValue: TypeAlias = str | int | float | bool
RestQueryParams: TypeAlias = dict[str, RestQueryParamValue]
RestPathParamValue: TypeAlias = str | int
RestPathParams: TypeAlias = dict[str, RestPathParamValue]
RestHeaderMap: TypeAlias = dict[str, str]
RestJsonValue: TypeAlias = str | int | float | bool | None
RestJsonBody: TypeAlias = dict[str, RestJsonValue]


@dataclass(frozen=True, slots=True)
class RestAuthConfig:
    token: str | None
    username: str | None
    password: str | None
    key_name: str | None
    key_value: str | None
    headers: RestHeaderMap


@dataclass(frozen=True, slots=True)
class RestResourceConfig:
    resource_name: str
    method: RestMethod
    path: str
    path_parameter_names: tuple[str, ...]
    description: str | None


@dataclass(frozen=True, slots=True)
class RestServiceConfig:
    service_name: str
    base_url: str
    auth_type: RestAuthType
    auth_config: RestAuthConfig
    timeout_seconds: float
    retry_count: int
    resources: dict[str, RestResourceConfig]
    resource_aliases: dict[str, str]


@dataclass(frozen=True, slots=True)
class RestRequestSpec:
    service_name: str
    resource_name: str
    method: RestMethod
    path: str
    url: str
    path_params: RestPathParams
    query_params: RestQueryParams
    json_body: RestJsonBody | None = None


@dataclass(frozen=True, slots=True)
class RestResponseData:
    service_name: str
    resource_name: str
    status_code: int
    url: str
    content_type: str | None
    body_text: str

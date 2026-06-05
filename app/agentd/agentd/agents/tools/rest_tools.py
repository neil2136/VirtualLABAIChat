from dataclasses import asdict
import json
from typing import Any

from pydantic_ai import Agent, RunContext

from agentd.core.debug import emit_debug_log
from agentd.domain.errors.rest_errors import (
    RestResourceNotFoundError,
    RestServiceNotFoundError,
)
from agentd.domain.types.chat_types import (
    BORROW_DEVICE_STRUCTURED_DATA_TYPE,
    BORROW_DEVICE_TOOL_NAME,
    RETURN_DEVICE_STRUCTURED_DATA_TYPE,
    RETURN_DEVICE_TOOL_NAME,
    BorrowDevicePayload,
    BorrowDeviceResult,
    ChatAgentDeps,
    ReturnDevicePayload,
    ReturnDeviceResult,
)
from agentd.domain.types.rest_types import (
    RestJsonBody,
    RestPathParams,
    RestQueryParams,
    RestResponseData,
    RestResourceConfig,
    RestServiceConfig,
)
from agentd.infrastructure.connectors.rest.connector import RestConnector
from agentd.infrastructure.connectors.rest.service_registry import (
    RestServiceRegistry,
    build_rest_service_registry,
    describe_rest_resource_catalog,
    get_rest_resource_config,
    get_rest_service_config,
)

DEVICE_ACTION_SERVICE_NAME: str = "device_action_api"


def build_rest_tool_docstring(registry: RestServiceRegistry) -> str:
    catalog_description: str = describe_rest_resource_catalog(registry)
    return (
        "Call a configured REST resource.\n\n"
        "Use this tool when the user asks for information or actions "
        "that must be executed against a configured REST service.\n"
        "Only use the listed service_name and resource_name pairs.\n"
        "Pass service_name as the service part, for example devh.\n"
        "Pass resource_name as the short resource part, for example version. "
        "If resource_name is provided as service.resource, it will be normalized.\n"
        "Pass path_params, query_params and request_body as objects. "
        "Use an empty object when a field is not needed.\n\n"
        "Available resources:\n"
        f"{catalog_description}"
    )


def build_device_action_tool_docstring(tool_name: str) -> str:
    if tool_name == BORROW_DEVICE_TOOL_NAME:
        return (
            "Borrow a device by device id.\n\n"
            "Use this tool when the user asks to borrow a device, "
            "for example 借用设备83.\n"
            "Extract only the device id from the user request.\n"
            "The requester_name is read from the trusted user header automatically.\n"
            "Pass device_id as a string."
        )

    return (
        "Return a device by device id.\n\n"
        "Use this tool when the user asks to return a device, "
        "for example 归还设备83.\n"
        "Extract only the device id from the user request.\n"
        "The requester_name is read from the trusted user header automatically.\n"
        "Pass device_id as a string."
    )


def format_rest_response_for_agent(response: RestResponseData) -> str:
    if response.body_text == "":
        return (
            f"service={response.service_name}\n"
            f"resource={response.resource_name}\n"
            f"status_code={response.status_code}\n"
            "body=<empty>"
        )

    return (
        f"service={response.service_name}\n"
        f"resource={response.resource_name}\n"
        f"status_code={response.status_code}\n"
        f"body:\n{response.body_text}"
    )


def build_registered_resource_names(registry: RestServiceRegistry) -> tuple[str, ...]:
    resource_names: list[str] = []
    for service_name in sorted(registry.services):
        service_config: RestServiceConfig = registry.services[service_name]
        for resource_name in sorted(service_config.resources):
            resource_names.append(f"{service_name}.{resource_name}")
    return tuple(resource_names)


def normalize_requested_resource_name(service_name: str, resource_name: str) -> str:
    service_prefix: str = f"{service_name.strip()}."
    if resource_name.casefold().startswith(service_prefix.casefold()):
        return resource_name[len(service_prefix) :]
    return resource_name


def parse_device_action_response_body(body_text: str) -> dict[str, object]:
    payload: object = json.loads(body_text)
    if not isinstance(payload, dict):
        raise ValueError(f"Device action response body must be an object: {body_text}")
    return payload


def require_string_field(payload: dict[str, object], field_name: str) -> str:
    value: object = payload.get(field_name)
    if not isinstance(value, str):
        raise ValueError(
            "Device action response field must be string: "
            f"field={field_name}, value={value!r}"
        )
    return value


def build_borrow_device_payload(response: RestResponseData) -> dict[str, object]:
    parsed_body: dict[str, object] = parse_device_action_response_body(
        response.body_text
    )
    payload = BorrowDevicePayload(
        type=BORROW_DEVICE_STRUCTURED_DATA_TYPE,
        tool_name=BORROW_DEVICE_TOOL_NAME,
        result=BorrowDeviceResult(
            device_id=require_string_field(parsed_body, "device_id"),
            message=require_string_field(parsed_body, "message"),
            requester=require_string_field(parsed_body, "requester"),
            status=require_string_field(parsed_body, "status"),
            type=require_string_field(parsed_body, "type"),
        ),
    )
    return asdict(payload)


def build_return_device_payload(response: RestResponseData) -> dict[str, object]:
    parsed_body: dict[str, object] = parse_device_action_response_body(
        response.body_text
    )
    payload = ReturnDevicePayload(
        type=RETURN_DEVICE_STRUCTURED_DATA_TYPE,
        tool_name=RETURN_DEVICE_TOOL_NAME,
        result=ReturnDeviceResult(
            device_id=require_string_field(parsed_body, "device_id"),
            message=require_string_field(parsed_body, "message"),
            owner=require_string_field(parsed_body, "owner"),
            status=require_string_field(parsed_body, "status"),
            type=require_string_field(parsed_body, "type"),
        ),
    )
    return asdict(payload)


def build_device_action_request_body(user_id: str) -> RestJsonBody:
    return {"requester_name": user_id}


def resolve_optional_rest_resource(
    registry: RestServiceRegistry,
    service_name: str,
    resource_name: str,
) -> tuple[RestServiceConfig, RestResourceConfig] | None:
    try:
        service_config: RestServiceConfig = get_rest_service_config(
            registry, service_name
        )
        resource_config: RestResourceConfig = get_rest_resource_config(
            service_config, resource_name
        )
        return service_config, resource_config
    except (RestServiceNotFoundError, RestResourceNotFoundError):
        return None


async def execute_rest_resource(
    connector: RestConnector,
    service_config: RestServiceConfig,
    resource_config: RestResourceConfig,
    path_params: RestPathParams,
    query_params: RestQueryParams,
    request_body: RestJsonBody | None,
) -> RestResponseData:
    emit_debug_log(
        "rest_tools.resource.execute",
        service_name=service_config.service_name,
        resource_name=resource_config.resource_name,
        method=resource_config.method,
        path_template=resource_config.path,
        path_params=path_params,
        query_params=query_params,
        request_body=request_body,
    )
    response: RestResponseData = await connector.request_resource(
        service_config=service_config,
        resource_config=resource_config,
        path_params=path_params,
        query_params=query_params,
        json_body=request_body,
    )
    emit_debug_log(
        "rest_tools.resource.executed",
        service_name=response.service_name,
        resource_name=response.resource_name,
        status_code=response.status_code,
        body_preview=response.body_text[:200],
    )
    return response


def register_rest_tools(
    agent: Agent[Any, str], rest_api_services_json: str | None
) -> tuple[str, ...]:
    registry: RestServiceRegistry = build_rest_service_registry(rest_api_services_json)
    registered_resources: tuple[str, ...] = build_registered_resource_names(registry)
    emit_debug_log(
        "rest_tools.registry.loaded",
        service_count=len(registry.services),
        registered_resources=registered_resources,
    )

    if not registry.services:
        emit_debug_log("rest_tools.registry.empty")
        return ()

    connector = RestConnector()
    query_tool_docstring: str = build_rest_tool_docstring(registry)

    async def query_rest_resource(
        service_name: str,
        resource_name: str,
        path_params: RestPathParams,
        query_params: RestQueryParams,
        request_body: RestJsonBody,
    ) -> str:
        normalized_resource_name: str = normalize_requested_resource_name(
            service_name=service_name,
            resource_name=resource_name,
        )
        emit_debug_log(
            "rest_tools.query.start",
            service_name=service_name,
            resource_name=resource_name,
            normalized_resource_name=normalized_resource_name,
            path_params=path_params,
            query_params=query_params,
            request_body=request_body,
        )
        try:
            service_config: RestServiceConfig = get_rest_service_config(
                registry, service_name
            )
            resource_config: RestResourceConfig = get_rest_resource_config(
                service_config, normalized_resource_name
            )
            emit_debug_log(
                "rest_tools.query.resolved",
                requested_service_name=service_name,
                requested_resource_name=resource_name,
                normalized_resource_name=normalized_resource_name,
                resolved_service_name=service_config.service_name,
                resolved_resource_name=resource_config.resource_name,
                base_url=service_config.base_url,
                method=resource_config.method,
                path=resource_config.path,
            )
            response: RestResponseData = await execute_rest_resource(
                connector=connector,
                service_config=service_config,
                resource_config=resource_config,
                path_params=path_params,
                query_params=query_params,
                request_body=request_body if request_body != {} else None,
            )
            emit_debug_log(
                "rest_tools.query.success",
                service_name=service_config.service_name,
                resource_name=resource_config.resource_name,
                status_code=response.status_code,
                content_type=response.content_type,
                body_preview=response.body_text[:200],
            )
            return format_rest_response_for_agent(response)
        except Exception as exc:
            emit_debug_log(
                "rest_tools.query.error",
                service_name=service_name,
                resource_name=resource_name,
                normalized_resource_name=normalized_resource_name,
                path_params=path_params,
                query_params=query_params,
                request_body=request_body,
                error=repr(exc),
            )
            raise

    query_rest_resource.__doc__ = query_tool_docstring
    agent.tool_plain(query_rest_resource)
    emit_debug_log(
        "rest_tools.query.registered",
        tool_name="query_rest_resource",
        registered_resources=registered_resources,
    )

    borrow_resource = resolve_optional_rest_resource(
        registry=registry,
        service_name=DEVICE_ACTION_SERVICE_NAME,
        resource_name=BORROW_DEVICE_TOOL_NAME,
    )
    if borrow_resource is not None:
        borrow_tool_docstring: str = build_device_action_tool_docstring(
            BORROW_DEVICE_TOOL_NAME
        )
        borrow_service_config, borrow_resource_config = borrow_resource

        async def borrow_device(
            ctx: RunContext[ChatAgentDeps],
            device_id: str,
        ) -> dict[str, object]:
            user_id: str = ctx.deps.user_id
            request_body: RestJsonBody = build_device_action_request_body(user_id)
            emit_debug_log(
                "rest_tools.borrow.start",
                device_id=device_id,
                user_id=user_id,
                request_body=request_body,
            )
            try:
                response: RestResponseData = await execute_rest_resource(
                    connector=connector,
                    service_config=borrow_service_config,
                    resource_config=borrow_resource_config,
                    path_params={"device_id": device_id},
                    query_params={},
                    request_body=request_body,
                )
                payload: dict[str, object] = build_borrow_device_payload(response)
                emit_debug_log(
                    "rest_tools.borrow.success",
                    device_id=device_id,
                    user_id=user_id,
                    status_code=response.status_code,
                    payload=payload,
                )
                return payload
            except Exception as exc:
                emit_debug_log(
                    "rest_tools.borrow.error",
                    device_id=device_id,
                    user_id=user_id,
                    error=repr(exc),
                )
                raise

        borrow_device.__doc__ = borrow_tool_docstring
        agent.tool(borrow_device)
        emit_debug_log(
            "rest_tools.borrow.registered",
            tool_name=BORROW_DEVICE_TOOL_NAME,
            service_name=borrow_service_config.service_name,
            resource_name=borrow_resource_config.resource_name,
        )
    else:
        emit_debug_log("rest_tools.borrow.unconfigured")

    return_resource = resolve_optional_rest_resource(
        registry=registry,
        service_name=DEVICE_ACTION_SERVICE_NAME,
        resource_name=RETURN_DEVICE_TOOL_NAME,
    )
    if return_resource is not None:
        return_tool_docstring: str = build_device_action_tool_docstring(
            RETURN_DEVICE_TOOL_NAME
        )
        return_service_config, return_resource_config = return_resource

        async def return_device(
            ctx: RunContext[ChatAgentDeps],
            device_id: str,
        ) -> dict[str, object]:
            user_id: str = ctx.deps.user_id
            request_body: RestJsonBody = build_device_action_request_body(user_id)
            emit_debug_log(
                "rest_tools.return.start",
                device_id=device_id,
                user_id=user_id,
                request_body=request_body,
            )
            try:
                response: RestResponseData = await execute_rest_resource(
                    connector=connector,
                    service_config=return_service_config,
                    resource_config=return_resource_config,
                    path_params={"device_id": device_id},
                    query_params={},
                    request_body=request_body,
                )
                payload: dict[str, object] = build_return_device_payload(response)
                emit_debug_log(
                    "rest_tools.return.success",
                    device_id=device_id,
                    user_id=user_id,
                    status_code=response.status_code,
                    payload=payload,
                )
                return payload
            except Exception as exc:
                emit_debug_log(
                    "rest_tools.return.error",
                    device_id=device_id,
                    user_id=user_id,
                    error=repr(exc),
                )
                raise

        return_device.__doc__ = return_tool_docstring
        agent.tool(return_device)
        emit_debug_log(
            "rest_tools.return.registered",
            tool_name=RETURN_DEVICE_TOOL_NAME,
            service_name=return_service_config.service_name,
            resource_name=return_resource_config.resource_name,
        )
    else:
        emit_debug_log("rest_tools.return.unconfigured")

    return registered_resources

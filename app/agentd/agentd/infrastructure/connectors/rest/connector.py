import logging

import httpx

from agentd.core.debug import emit_debug_log
from agentd.domain.errors.rest_errors import (
    RestMethodNotAllowedError,
    RestRequestExecutionError,
    RestRequestInputError,
)
from agentd.domain.types.rest_types import (
    RestMethod,
    RestPathParamValue,
    RestPathParams,
    RestQueryParamValue,
    RestQueryParams,
    RestRequestSpec,
    RestResourceConfig,
    RestResponseData,
    RestServiceConfig,
)
from agentd.infrastructure.connectors.rest.auth import (
    PreparedRestAuth,
    prepare_rest_auth,
)

logger = logging.getLogger(__name__)
ALLOWED_REST_METHODS: tuple[RestMethod, ...] = ("GET", "HEAD", "POST")


class RestConnector:
    async def request_resource(
        self,
        service_config: RestServiceConfig,
        resource_config: RestResourceConfig,
        path_params: RestPathParams,
        query_params: RestQueryParams,
        json_body: dict[str, object] | None,
    ) -> RestResponseData:
        request_spec: RestRequestSpec = build_rest_request_spec(
            service_config=service_config,
            resource_config=resource_config,
            path_params=path_params,
            query_params=query_params,
            json_body=json_body,
        )
        prepared_auth: PreparedRestAuth = prepare_rest_auth(service_config)
        merged_query_params: dict[str, str] = normalize_rest_query_params(query_params)
        merged_query_params.update(prepared_auth.query_params)
        max_attempts: int = service_config.retry_count + 1

        emit_debug_log(
            "rest_connector.request.start",
            service_name=service_config.service_name,
            resource_name=resource_config.resource_name,
            method=request_spec.method,
            path=request_spec.path,
            url=request_spec.url,
            auth_type=service_config.auth_type,
            timeout_seconds=service_config.timeout_seconds,
            retry_count=service_config.retry_count,
            path_params=request_spec.path_params,
            query_params=merged_query_params,
            request_body=request_spec.json_body,
        )

        for attempt in range(1, max_attempts + 1):
            emit_debug_log(
                "rest_connector.request.attempt",
                service_name=service_config.service_name,
                resource_name=resource_config.resource_name,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            try:
                response = await execute_rest_request(
                    request_spec=request_spec,
                    timeout_seconds=service_config.timeout_seconds,
                    headers=prepared_auth.headers,
                    query_params=merged_query_params,
                    basic_auth=prepared_auth.basic_auth,
                )
            except httpx.HTTPError as exc:
                emit_debug_log(
                    "rest_connector.request.http_error",
                    service_name=service_config.service_name,
                    resource_name=resource_config.resource_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=repr(exc),
                )
                if attempt < max_attempts:
                    logger.warning(
                        "REST request retry",
                        extra={
                            "service_name": service_config.service_name,
                            "resource_name": resource_config.resource_name,
                            "method": request_spec.method,
                            "path": request_spec.path,
                            "path_params": request_spec.path_params,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "query_params": merged_query_params,
                            "request_body": request_spec.json_body,
                            "error": repr(exc),
                        },
                    )
                    continue
                raise RestRequestExecutionError(
                    service_name=service_config.service_name,
                    resource_name=resource_config.resource_name,
                    method=request_spec.method,
                    path=request_spec.path,
                    path_params=request_spec.path_params,
                    query_params=request_spec.query_params,
                    request_body=request_spec.json_body,
                    status_code=None,
                    response_body=None,
                    original_error=exc,
                ) from exc

            emit_debug_log(
                "rest_connector.request.response",
                service_name=service_config.service_name,
                resource_name=resource_config.resource_name,
                attempt=attempt,
                status_code=response.status_code,
                url=str(response.request.url),
                content_type=response.headers.get("Content-Type"),
                body_preview=response.text[:200],
            )

            if 200 <= response.status_code < 300:
                return RestResponseData(
                    service_name=service_config.service_name,
                    resource_name=resource_config.resource_name,
                    status_code=response.status_code,
                    url=str(response.request.url),
                    content_type=response.headers.get("Content-Type"),
                    body_text=response.text,
                )

            if 500 <= response.status_code < 600 and attempt < max_attempts:
                logger.warning(
                    "REST request retry",
                    extra={
                        "service_name": service_config.service_name,
                        "resource_name": resource_config.resource_name,
                        "method": request_spec.method,
                        "path": request_spec.path,
                        "path_params": request_spec.path_params,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "query_params": merged_query_params,
                        "request_body": request_spec.json_body,
                        "status_code": response.status_code,
                        "response_body": response.text[:500],
                    },
                )
                continue

            raise RestRequestExecutionError(
                service_name=service_config.service_name,
                resource_name=resource_config.resource_name,
                method=request_spec.method,
                path=request_spec.path,
                path_params=request_spec.path_params,
                query_params=request_spec.query_params,
                request_body=request_spec.json_body,
                status_code=response.status_code,
                response_body=response.text,
                original_error=None,
            )

        raise RestRequestExecutionError(
            service_name=service_config.service_name,
            resource_name=resource_config.resource_name,
            method=request_spec.method,
            path=request_spec.path,
            path_params=request_spec.path_params,
            query_params=request_spec.query_params,
            request_body=request_spec.json_body,
            status_code=None,
            response_body=None,
            original_error=None,
        )


def build_rest_request_spec(
    service_config: RestServiceConfig,
    resource_config: RestResourceConfig,
    path_params: RestPathParams,
    query_params: RestQueryParams,
    json_body: dict[str, object] | None,
) -> RestRequestSpec:
    if resource_config.method not in ALLOWED_REST_METHODS:
        raise RestMethodNotAllowedError(
            service_name=service_config.service_name,
            resource_name=resource_config.resource_name,
            method=resource_config.method,
        )

    normalized_path_params: RestPathParams = normalize_rest_path_params(path_params)
    formatted_path: str = format_rest_path(
        path_template=resource_config.path,
        path_params=normalized_path_params,
        expected_parameter_names=resource_config.path_parameter_names,
    )
    normalized_json_body: dict[str, object] | None = normalize_rest_json_body(
        method=resource_config.method,
        json_body=json_body,
    )
    return RestRequestSpec(
        service_name=service_config.service_name,
        resource_name=resource_config.resource_name,
        method=resource_config.method,
        path=formatted_path,
        url=f"{service_config.base_url}{formatted_path}",
        path_params=normalized_path_params,
        query_params=dict(query_params),
        json_body=normalized_json_body,
    )


def normalize_rest_path_param_value(value: RestPathParamValue) -> str:
    return str(value)


def normalize_rest_path_params(path_params: RestPathParams) -> RestPathParams:
    normalized_path_params: RestPathParams = {}
    for key, value in path_params.items():
        normalized_path_params[key] = normalize_rest_path_param_value(value)
    return normalized_path_params


def format_rest_path(
    path_template: str,
    path_params: RestPathParams,
    expected_parameter_names: tuple[str, ...],
) -> str:
    provided_parameter_names: tuple[str, ...] = tuple(sorted(path_params))
    expected_parameter_names_sorted: tuple[str, ...] = tuple(
        sorted(expected_parameter_names)
    )
    if provided_parameter_names != expected_parameter_names_sorted:
        raise RestRequestInputError(
            "path params do not match resource path template: "
            f"path={path_template}, "
            f"expected={expected_parameter_names_sorted}, "
            f"provided={provided_parameter_names}"
        )

    formatted_path: str = path_template
    for parameter_name in expected_parameter_names:
        parameter_value: str = str(path_params[parameter_name])
        formatted_path = formatted_path.replace(
            f"{{{parameter_name}}}", parameter_value
        )
    return formatted_path


def normalize_rest_json_body(
    method: RestMethod,
    json_body: dict[str, object] | None,
) -> dict[str, object] | None:
    if method == "POST":
        if json_body is None:
            return None
        return dict(json_body)

    if json_body is None or json_body == {}:
        return None

    raise RestRequestInputError(
        f"request body is only supported for POST resources: method={method}"
    )


def normalize_rest_query_param_value(value: RestQueryParamValue) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def normalize_rest_query_params(query_params: RestQueryParams) -> dict[str, str]:
    normalized_query_params: dict[str, str] = {}
    for key, value in query_params.items():
        normalized_query_params[key] = normalize_rest_query_param_value(value)
    return normalized_query_params


async def execute_rest_request(
    request_spec: RestRequestSpec,
    timeout_seconds: float,
    headers: dict[str, str],
    query_params: dict[str, str],
    basic_auth: tuple[str, str] | None,
) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        verify=False,
    ) as client:
        auth = httpx.BasicAuth(*basic_auth) if basic_auth is not None else None
        return await client.request(
            method=request_spec.method,
            url=request_spec.url,
            headers=headers,
            params=query_params,
            auth=auth,
            json=request_spec.json_body,
        )

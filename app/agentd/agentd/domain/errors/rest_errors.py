import json

from agentd.domain.types.rest_types import (
    RestJsonBody,
    RestMethod,
    RestPathParams,
    RestQueryParams,
)


class RestError(Exception):
    pass


class RestConfigurationError(RestError):
    pass


class RestServiceNotFoundError(RestError):
    def __init__(self, service_name: str) -> None:
        super().__init__(f"Rest service not found: {service_name}")


class RestResourceNotFoundError(RestError):
    def __init__(self, service_name: str, resource_name: str) -> None:
        super().__init__(
            f"Rest resource not found: service={service_name}, resource={resource_name}"
        )


class RestAuthenticationError(RestError):
    def __init__(self, service_name: str, auth_type: str, message: str) -> None:
        super().__init__(
            "Rest authentication error: "
            f"service={service_name}, auth_type={auth_type}, "
            f"message={message}"
        )


class RestMethodNotAllowedError(RestError):
    def __init__(
        self, service_name: str, resource_name: str, method: RestMethod
    ) -> None:
        super().__init__(
            "Rest method not allowed: "
            f"service={service_name}, resource={resource_name}, "
            f"method={method}"
        )


class RestRequestInputError(RestError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Rest request input error: {message}")


class RestRequestExecutionError(RestError):
    def __init__(
        self,
        service_name: str,
        resource_name: str,
        method: RestMethod,
        path: str,
        path_params: RestPathParams,
        query_params: RestQueryParams,
        request_body: RestJsonBody | None,
        status_code: int | None,
        response_body: str | None,
        original_error: Exception | None,
    ) -> None:
        serialized_path_params: str = json.dumps(
            path_params, ensure_ascii=True, sort_keys=True
        )
        serialized_query_params: str = json.dumps(
            query_params, ensure_ascii=True, sort_keys=True
        )
        message_parts: list[str] = [
            "Rest request failed",
            f"service={service_name}",
            f"resource={resource_name}",
            f"method={method}",
            f"path={path}",
            f"path_params={serialized_path_params}",
            f"query_params={serialized_query_params}",
        ]
        if request_body is not None:
            serialized_request_body: str = json.dumps(
                request_body, ensure_ascii=True, sort_keys=True
            )
            message_parts.append(f"request_body={serialized_request_body}")
        if status_code is not None:
            message_parts.append(f"status_code={status_code}")
        if response_body is not None:
            message_parts.append(f"response_body={response_body[:500]}")
        if original_error is not None:
            message_parts.append(f"original_error={original_error!r}")
        super().__init__("; ".join(message_parts))

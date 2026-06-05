from collections.abc import Mapping, Sequence

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from agentd.api.schemas.common import ErrorDetail, ErrorResponse
from agentd.domain.errors.agent_errors import AgentConfigurationError
from agentd.domain.errors.conversation_errors import (
    ConversationAccessDeniedError,
    ConversationExpiredError,
    ConversationNotFoundError,
)
from agentd.domain.errors.mongo_errors import (
    MongoAggregationExecutionError,
    MongoConfigurationError,
    MongoFilterFieldNotAllowedError,
    MongoFilterValueError,
    MongoLimitValueError,
    MongoQueryExecutionError,
    MongoResourceNotFoundError,
)
from agentd.domain.errors.rest_errors import (
    RestAuthenticationError,
    RestConfigurationError,
    RestRequestInputError,
    RestRequestExecutionError,
    RestResourceNotFoundError,
    RestServiceNotFoundError,
)


def build_error_response(
    status_code: int, error_code: str, message: str
) -> JSONResponse:
    payload: ErrorResponse = ErrorResponse(
        error=ErrorDetail(code=error_code, message=message)
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def get_http_exception_message(detail: object) -> str:
    if isinstance(detail, str):
        return detail

    if isinstance(detail, Mapping):
        return str(dict(detail))

    if isinstance(detail, Sequence):
        return str(list(detail))

    return str(detail)


async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    message: str = get_http_exception_message(exc.detail)
    return build_error_response(exc.status_code, "http_error", message)


async def handle_conversation_not_found(
    _: Request, exc: ConversationNotFoundError
) -> JSONResponse:
    return build_error_response(
        404, "conversation_not_found", f"Conversation not found: {exc}"
    )


async def handle_conversation_expired(
    _: Request, exc: ConversationExpiredError
) -> JSONResponse:
    return build_error_response(
        410, "conversation_expired", f"Conversation expired: {exc}"
    )


async def handle_conversation_access_denied(
    _: Request, exc: ConversationAccessDeniedError
) -> JSONResponse:
    return build_error_response(
        403, "conversation_access_denied", f"Conversation access denied: {exc}"
    )


async def handle_agent_configuration_error(
    _: Request, exc: AgentConfigurationError
) -> JSONResponse:
    return build_error_response(500, "agent_configuration_error", str(exc))


async def handle_mongo_configuration_error(
    _: Request, exc: MongoConfigurationError
) -> JSONResponse:
    return build_error_response(500, "mongo_configuration_error", str(exc))


async def handle_mongo_resource_not_found(
    _: Request, exc: MongoResourceNotFoundError
) -> JSONResponse:
    return build_error_response(404, "mongo_resource_not_found", str(exc))


async def handle_mongo_filter_field_not_allowed(
    _: Request, exc: MongoFilterFieldNotAllowedError
) -> JSONResponse:
    return build_error_response(400, "mongo_filter_field_not_allowed", str(exc))


async def handle_mongo_filter_value_error(
    _: Request, exc: MongoFilterValueError
) -> JSONResponse:
    return build_error_response(400, "mongo_filter_value_error", str(exc))


async def handle_mongo_limit_value_error(
    _: Request, exc: MongoLimitValueError
) -> JSONResponse:
    return build_error_response(400, "mongo_limit_value_error", str(exc))


async def handle_mongo_query_execution_error(
    _: Request, exc: MongoQueryExecutionError
) -> JSONResponse:
    return build_error_response(502, "mongo_query_execution_error", str(exc))


async def handle_mongo_aggregation_execution_error(
    _: Request, exc: MongoAggregationExecutionError
) -> JSONResponse:
    return build_error_response(502, "mongo_aggregation_execution_error", str(exc))


async def handle_rest_configuration_error(
    _: Request, exc: RestConfigurationError
) -> JSONResponse:
    return build_error_response(500, "rest_configuration_error", str(exc))


async def handle_rest_service_not_found(
    _: Request, exc: RestServiceNotFoundError
) -> JSONResponse:
    return build_error_response(404, "rest_service_not_found", str(exc))


async def handle_rest_resource_not_found(
    _: Request, exc: RestResourceNotFoundError
) -> JSONResponse:
    return build_error_response(404, "rest_resource_not_found", str(exc))


async def handle_rest_authentication_error(
    _: Request, exc: RestAuthenticationError
) -> JSONResponse:
    return build_error_response(500, "rest_authentication_error", str(exc))


async def handle_rest_request_input_error(
    _: Request, exc: RestRequestInputError
) -> JSONResponse:
    return build_error_response(400, "rest_request_input_error", str(exc))


async def handle_rest_request_execution_error(
    _: Request, exc: RestRequestExecutionError
) -> JSONResponse:
    return build_error_response(502, "rest_request_execution_error", str(exc))


async def handle_unexpected_exception(_: Request, exc: Exception) -> JSONResponse:
    return build_error_response(500, "internal_server_error", str(exc))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(ConversationNotFoundError, handle_conversation_not_found)
    app.add_exception_handler(ConversationExpiredError, handle_conversation_expired)
    app.add_exception_handler(
        ConversationAccessDeniedError, handle_conversation_access_denied
    )
    app.add_exception_handler(AgentConfigurationError, handle_agent_configuration_error)
    app.add_exception_handler(MongoConfigurationError, handle_mongo_configuration_error)
    app.add_exception_handler(
        MongoResourceNotFoundError, handle_mongo_resource_not_found
    )
    app.add_exception_handler(
        MongoFilterFieldNotAllowedError, handle_mongo_filter_field_not_allowed
    )
    app.add_exception_handler(MongoFilterValueError, handle_mongo_filter_value_error)
    app.add_exception_handler(MongoLimitValueError, handle_mongo_limit_value_error)
    app.add_exception_handler(
        MongoQueryExecutionError, handle_mongo_query_execution_error
    )
    app.add_exception_handler(
        MongoAggregationExecutionError, handle_mongo_aggregation_execution_error
    )
    app.add_exception_handler(RestConfigurationError, handle_rest_configuration_error)
    app.add_exception_handler(RestServiceNotFoundError, handle_rest_service_not_found)
    app.add_exception_handler(RestResourceNotFoundError, handle_rest_resource_not_found)
    app.add_exception_handler(RestAuthenticationError, handle_rest_authentication_error)
    app.add_exception_handler(RestRequestInputError, handle_rest_request_input_error)
    app.add_exception_handler(
        RestRequestExecutionError, handle_rest_request_execution_error
    )
    app.add_exception_handler(Exception, handle_unexpected_exception)

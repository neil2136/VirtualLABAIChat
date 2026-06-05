from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentd.infrastructure.config import get_settings
from agentd.infrastructure.connectors.mongodb import get_optional_mongo_connector
from agentd.infrastructure.repositories.in_memory_conversation_repository import create_in_memory_conversation_repository
from agentd.infrastructure.repositories.in_memory_message_history_repository import create_in_memory_message_history_repository


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.conversation_repository = create_in_memory_conversation_repository()
    app.state.message_history_repository = create_in_memory_message_history_repository()
    app.state.mongo_connector = get_optional_mongo_connector(
        mongodb_uri=settings.mongodb_uri,
        mongodb_database=settings.mongodb_database,
        mongodb_resources_json=settings.mongodb_resources_json,
    )
    try:
        yield
    finally:
        mongo_connector = app.state.mongo_connector
        if mongo_connector is not None:
            mongo_connector.close()


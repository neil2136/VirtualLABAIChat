from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentd.api.router import api_router
from agentd.core.exceptions import register_exception_handlers
from agentd.core.lifespan import app_lifespan
from agentd.infrastructure.config import Settings
from agentd.infrastructure.config import get_settings


def configure_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    app: FastAPI = FastAPI(title="agentd", version="0.1.0", lifespan=app_lifespan)
    configure_cors(app, settings)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app

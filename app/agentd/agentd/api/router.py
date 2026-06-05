from fastapi import APIRouter

from agentd.api.routes.conversations import router as conversations_router
from agentd.api.routes.health import router as health_router

api_router: APIRouter = APIRouter()
api_router.include_router(health_router)
api_router.include_router(conversations_router)
from typing import Annotated

from fastapi import APIRouter, Depends

from agentd.api.dependencies.settings import get_app_settings
from agentd.api.schemas.common import HealthResponse
from agentd.infrastructure.config import Settings

router: APIRouter = APIRouter(tags=["health"])
SettingsDependency = Annotated[Settings, Depends(get_app_settings)]


@router.get("/health", response_model=HealthResponse)
def get_health(_settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(status="ok", service="agentd", version="0.1.0")
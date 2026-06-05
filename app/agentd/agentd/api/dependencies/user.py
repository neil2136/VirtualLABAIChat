from fastapi import Depends, HTTPException, Request, status

from agentd.api.dependencies.settings import get_app_settings
from agentd.infrastructure.config import Settings


def get_current_user_id(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> str:
    header_name: str = settings.trusted_user_header
    user_id: str | None = request.headers.get(header_name)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Missing trusted user header: {header_name}',
        )

    cleaned_user_id: str = user_id.strip()
    if cleaned_user_id == '':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Empty trusted user header: {header_name}',
        )

    return cleaned_user_id
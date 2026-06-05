import uvicorn
from fastapi import FastAPI

from agentd.api.app_factory import create_app
from agentd.infrastructure.config import (
    APP_HOST,
    Settings,
    get_settings,
    get_tls_file_paths,
)

app: FastAPI = create_app()


def main() -> None:
    settings: Settings = get_settings()
    tls_cert_file, tls_key_file = get_tls_file_paths(settings)
    uvicorn.run(
        app,
        host=APP_HOST,
        port=settings.app_port,
        ssl_certfile=str(tls_cert_file),
        ssl_keyfile=str(tls_key_file),
    )


if __name__ == "__main__":
    main()

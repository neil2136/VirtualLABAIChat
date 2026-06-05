from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_HOST: str = "0.0.0.0"
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def parse_string_collection(value: object, env_name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        items: tuple[str, ...] = tuple(
            item.strip() for item in value.split(",") if item.strip() != ""
        )
        if len(items) == 0:
            raise ValueError(f"{env_name} must contain at least one item.")
        return items

    if isinstance(value, list | tuple):
        normalized_items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{env_name} items must all be strings.")

            normalized_item: str = item.strip()
            if normalized_item == "":
                continue
            normalized_items.append(normalized_item)

        if len(normalized_items) == 0:
            raise ValueError(f"{env_name} must contain at least one item.")
        return tuple(normalized_items)

    return value  # type: ignore[return-value]


def normalize_cors_origin(origin: str) -> str:
    parsed_origin = urlparse(origin)
    normalized_scheme: str = parsed_origin.scheme.lower()
    normalized_netloc: str = parsed_origin.netloc

    if normalized_scheme not in {"http", "https"}:
        raise ValueError(
            "CORS origins must include an http or https scheme. "
            f"Invalid origin: {origin!r}"
        )
    if normalized_netloc == "":
        raise ValueError(
            "CORS origins must include a host or host:port value. "
            f"Invalid origin: {origin!r}"
        )
    if parsed_origin.path not in {"", "/"}:
        raise ValueError(
            "CORS origins must not include a path. "
            f"Invalid origin: {origin!r}"
        )
    if parsed_origin.params != "" or parsed_origin.query != "":
        raise ValueError(
            "CORS origins must not include params or query strings. "
            f"Invalid origin: {origin!r}"
        )
    if parsed_origin.fragment != "":
        raise ValueError(
            "CORS origins must not include fragments. "
            f"Invalid origin: {origin!r}"
        )

    return f"{normalized_scheme}://{normalized_netloc}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_port: int = Field(default=10443, alias="APP_PORT")
    log_level: LogLevel = Field(default="INFO", alias="LOG_LEVEL")
    tls_cert_file: Path | None = Field(default=None, alias="TLS_CERT_FILE")
    tls_key_file: Path | None = Field(default=None, alias="TLS_KEY_FILE")
    trusted_user_header: str = Field(alias="TRUSTED_USER_HEADER", min_length=1)
    session_ttl_seconds: int = Field(default=1800, alias="SESSION_TTL_SECONDS", gt=0)
    max_conversation_messages: int = Field(
        default=100, alias="MAX_CONVERSATION_MESSAGES", gt=0
    )
    model_name: str | None = Field(default=None, alias="MODEL_NAME")
    model_base_url: str | None = Field(default=None, alias="MODEL_BASE_URL")
    model_api_key: str | None = Field(default=None, alias="MODEL_API_KEY")
    mongodb_uri: str | None = Field(default=None, alias="MONGODB_URI")
    mongodb_database: str | None = Field(default=None, alias="MONGODB_DATABASE")
    mongodb_resources_json: str | None = Field(
        default=None, alias="MONGODB_RESOURCES_JSON"
    )
    rest_api_services_json: str | None = Field(
        default=None, alias="REST_API_SERVICES_JSON"
    )
    cors_allow_origins: tuple[str, ...] = Field(
        default=("http://10.103.2.128", "https://10.103.2.128"),
        alias="CORS_ALLOW_ORIGINS",
    )

    @field_validator(
        "model_name",
        "model_base_url",
        "model_api_key",
        "tls_cert_file",
        "tls_key_file",
        "mongodb_uri",
        "mongodb_database",
        "mongodb_resources_json",
        "rest_api_services_json",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object) -> object:
        return parse_string_collection(value, "CORS_ALLOW_ORIGINS")

    @field_validator("cors_allow_origins")
    @classmethod
    def normalize_cors_allow_origins(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized_origins: list[str] = []
        for origin in value:
            normalized_origin: str = normalize_cors_origin(origin)
            if normalized_origin in normalized_origins:
                continue
            normalized_origins.append(normalized_origin)
        return tuple(normalized_origins)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().upper()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_required_tls_file(path: Path | None, env_name: str) -> Path:
    if path is None:
        raise ValueError(f"{env_name} is required when starting the HTTPS server.")

    normalized_path: Path = path.expanduser()
    if not normalized_path.is_absolute():
        normalized_path = Path.cwd() / normalized_path

    resolved_path: Path = normalized_path.resolve()
    if not resolved_path.exists():
        raise ValueError(f"{env_name} file not found: {resolved_path}")
    if not resolved_path.is_file():
        raise ValueError(f"{env_name} must point to a file: {resolved_path}")

    return resolved_path


def get_tls_file_paths(settings: Settings) -> tuple[Path, Path]:
    tls_cert_file: Path = resolve_required_tls_file(
        settings.tls_cert_file, "TLS_CERT_FILE"
    )
    tls_key_file: Path = resolve_required_tls_file(
        settings.tls_key_file, "TLS_KEY_FILE"
    )
    return tls_cert_file, tls_key_file

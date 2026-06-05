from pydantic import BaseModel, Field, field_validator

from agentd.domain.types.rest_types import RestAuthType, RestMethod


class RestAuthConfigSettingsModel(BaseModel):
    token: str | None = None
    username: str | None = None
    password: str | None = None
    key_name: str | None = None
    key_value: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "token", "username", "password", "key_name", "key_value", mode="before"
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


class RestResourceSettingsModel(BaseModel):
    method: RestMethod
    path: str = Field(min_length=1)
    description: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        normalized_value: str = value.strip()
        if not normalized_value.startswith("/"):
            raise ValueError("path must start with /.")
        return normalized_value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value: str = value.strip()
        if normalized_value == "":
            return None
        return normalized_value


class RestServiceSettingsModel(BaseModel):
    base_url: str = Field(min_length=1)
    auth_type: RestAuthType
    auth_config: RestAuthConfigSettingsModel = Field(
        default_factory=RestAuthConfigSettingsModel
    )
    timeout_seconds: float = Field(gt=0)
    retry_count: int = Field(ge=0)
    resources: dict[str, RestResourceSettingsModel] = Field(min_length=1)

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        normalized_value: str = value.strip().rstrip("/")
        if normalized_value == "":
            raise ValueError("base_url must not be blank.")
        return normalized_value

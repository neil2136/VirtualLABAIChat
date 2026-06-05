from pydantic import BaseModel, Field, field_validator

from agentd.domain.types.mongo_types import MongoFieldType, MongoSortSpec, MongoStringMatchMode


class MongoFilterFieldSettingsModel(BaseModel):
    document_path: str = Field(min_length=1)
    field_type: MongoFieldType
    string_match_mode: MongoStringMatchMode = 'exact'

    @field_validator('document_path', mode='before')
    @classmethod
    def normalize_document_path(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized_value: str = value.strip()
        if normalized_value == '':
            raise ValueError('Mongo document path must not be blank.')
        return normalized_value


class MongoResourceSettingsModel(BaseModel):
    collection: str = Field(min_length=1)
    description: str = Field(min_length=1)
    filter_fields: dict[str, MongoFilterFieldSettingsModel]
    projection_fields: tuple[str, ...]
    keyword_paths: tuple[str, ...]
    sort: MongoSortSpec
    limit: int = Field(gt=0)
    retry_count: int = Field(ge=0)

    @field_validator('collection', 'description', mode='before')
    @classmethod
    def normalize_non_blank_string(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized_value: str = value.strip()
        if normalized_value == '':
            raise ValueError('Value must not be blank.')
        return normalized_value

    @field_validator('filter_fields')
    @classmethod
    def validate_filter_fields(
        cls,
        value: dict[str, MongoFilterFieldSettingsModel],
    ) -> dict[str, MongoFilterFieldSettingsModel]:
        normalized_fields: dict[str, MongoFilterFieldSettingsModel] = {}
        for field_name, field_config in value.items():
            normalized_name: str = field_name.strip()
            if normalized_name == '':
                raise ValueError('Mongo filter field name must not be blank.')
            normalized_fields[normalized_name] = field_config
        return normalized_fields

    @field_validator('projection_fields')
    @classmethod
    def validate_projection_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized_fields: list[str] = []
        for field_name in value:
            normalized_name: str = field_name.strip()
            if normalized_name == '':
                raise ValueError('Mongo projection field name must not be blank.')
            normalized_fields.append(normalized_name)
        if not normalized_fields:
            raise ValueError('Mongo projection_fields must not be empty.')
        return tuple(normalized_fields)

    @field_validator('keyword_paths')
    @classmethod
    def validate_keyword_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized_paths: list[str] = []
        for path in value:
            normalized_path: str = path.strip()
            if normalized_path == '':
                raise ValueError('Mongo keyword path must not be blank.')
            normalized_paths.append(normalized_path)
        return tuple(normalized_paths)

    @field_validator('sort')
    @classmethod
    def validate_sort(cls, value: MongoSortSpec) -> MongoSortSpec:
        normalized_entries: list[tuple[str, int]] = []
        for field_name, direction in value:
            normalized_name: str = field_name.strip()
            if normalized_name == '':
                raise ValueError('Mongo sort field name must not be blank.')
            if direction not in (-1, 1):
                raise ValueError('Mongo sort direction must be 1 or -1.')
            normalized_entries.append((normalized_name, direction))
        return tuple(normalized_entries)

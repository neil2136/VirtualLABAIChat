from dataclasses import dataclass

from pydantic import TypeAdapter, ValidationError

from agentd.domain.errors.mongo_errors import MongoConfigurationError, MongoResourceNotFoundError
from agentd.domain.types.mongo_types import MongoFilterFieldConfig, MongoResourceConfig
from agentd.infrastructure.connectors.mongodb.settings_models import MongoResourceSettingsModel


@dataclass(frozen=True, slots=True)
class MongoResourceRegistry:
    resources: dict[str, MongoResourceConfig]


MongoResourceSettingsAdapter = TypeAdapter(dict[str, MongoResourceSettingsModel])


def normalize_mongo_resource_name(resource_name: str) -> str:
    normalized_name: str = resource_name.strip()
    if normalized_name == '':
        raise MongoConfigurationError('Mongo resource name must not be blank.')
    return normalized_name


def normalize_mongo_filter_alias(field_name: str) -> str:
    normalized_name: str = field_name.strip().lower()
    if normalized_name == '':
        raise MongoConfigurationError('Mongo filter field alias must not be blank.')
    return normalized_name


def build_mongo_resource_registry(mongodb_resources_json: str | None) -> MongoResourceRegistry:
    if mongodb_resources_json is None:
        return MongoResourceRegistry(resources={})

    try:
        raw_resources: dict[str, MongoResourceSettingsModel] = MongoResourceSettingsAdapter.validate_json(
            mongodb_resources_json
        )
    except ValidationError as exc:
        raise MongoConfigurationError(f'Invalid Mongo resource configuration: {exc}') from exc

    resources: dict[str, MongoResourceConfig] = {}
    for raw_resource_name, raw_resource_config in raw_resources.items():
        resource_name: str = normalize_mongo_resource_name(raw_resource_name)
        if resource_name in resources:
            raise MongoConfigurationError(f'Duplicate Mongo resource name: {resource_name}')

        filter_fields: dict[str, MongoFilterFieldConfig] = {}
        filter_field_aliases: dict[str, str] = {}
        for field_name, field_config in raw_resource_config.filter_fields.items():
            normalized_field_name: str = field_name.strip()
            filter_fields[normalized_field_name] = MongoFilterFieldConfig(
                field_name=normalized_field_name,
                document_path=field_config.document_path,
                field_type=field_config.field_type,
                string_match_mode=field_config.string_match_mode,
            )
            field_alias: str = normalize_mongo_filter_alias(normalized_field_name)
            if field_alias in filter_field_aliases:
                raise MongoConfigurationError(
                    f'Duplicate Mongo filter field alias: resource={resource_name}, field={normalized_field_name}'
                )
            filter_field_aliases[field_alias] = normalized_field_name

        resources[resource_name] = MongoResourceConfig(
            resource_name=resource_name,
            collection=raw_resource_config.collection,
            description=raw_resource_config.description,
            filter_fields=filter_fields,
            filter_field_aliases=filter_field_aliases,
            projection_fields=tuple(raw_resource_config.projection_fields),
            keyword_paths=tuple(raw_resource_config.keyword_paths),
            sort=tuple(raw_resource_config.sort),
            limit=raw_resource_config.limit,
            retry_count=raw_resource_config.retry_count,
        )

    return MongoResourceRegistry(resources=resources)


def get_mongo_resource_config(registry: MongoResourceRegistry, resource_name: str) -> MongoResourceConfig:
    resource_config: MongoResourceConfig | None = registry.resources.get(resource_name)
    if resource_config is None:
        raise MongoResourceNotFoundError(resource_name)
    return resource_config


def describe_mongo_resource_catalog(registry: MongoResourceRegistry) -> str:
    if not registry.resources:
        return '- No Mongo resources are configured.'

    lines: list[str] = []
    for resource_name in sorted(registry.resources):
        resource_config: MongoResourceConfig = registry.resources[resource_name]
        filter_fields: str = ', '.join(sorted(resource_config.filter_fields))
        keyword_paths: str = ', '.join(resource_config.keyword_paths)
        lines.append(
            f'- {resource_name}: {resource_config.description} '
            f'(collection={resource_config.collection}, filter_fields=[{filter_fields}], keyword_paths=[{keyword_paths}])'
        )
    return '\n'.join(lines)

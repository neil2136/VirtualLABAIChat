from dataclasses import dataclass
import re

from pydantic import TypeAdapter, ValidationError

from agentd.domain.errors.rest_errors import (
    RestConfigurationError,
    RestResourceNotFoundError,
    RestServiceNotFoundError,
)
from agentd.domain.types.rest_types import (
    RestAuthConfig,
    RestResourceConfig,
    RestServiceConfig,
)
from agentd.infrastructure.connectors.rest.settings_models import (
    RestServiceSettingsModel,
)


@dataclass(frozen=True, slots=True)
class RestServiceRegistry:
    services: dict[str, RestServiceConfig]
    service_aliases: dict[str, str]


RestServiceSettingsAdapter = TypeAdapter(dict[str, RestServiceSettingsModel])
PATH_PARAMETER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def normalize_registry_name(name: str, name_type: str) -> str:
    normalized_name: str = name.strip()
    if normalized_name == "":
        raise RestConfigurationError(f"Rest {name_type} name must not be blank.")
    return normalized_name


def normalize_lookup_name(name: str, name_type: str) -> str:
    normalized_name: str = normalize_registry_name(name, name_type)
    return normalized_name.casefold()


def extract_path_parameter_names(path: str) -> tuple[str, ...]:
    path_parameter_names: list[str] = PATH_PARAMETER_PATTERN.findall(path)
    if len(path_parameter_names) != len(set(path_parameter_names)):
        raise RestConfigurationError(
            f"Duplicate REST path parameter name detected: path={path}"
        )
    return tuple(path_parameter_names)


def build_rest_service_registry(
    rest_api_services_json: str | None,
) -> RestServiceRegistry:
    if rest_api_services_json is None:
        return RestServiceRegistry(services={}, service_aliases={})

    try:
        raw_services: dict[str, RestServiceSettingsModel] = (
            RestServiceSettingsAdapter.validate_json(rest_api_services_json)
        )
    except ValidationError as exc:
        raise RestConfigurationError(
            f"Invalid REST service configuration: {exc}"
        ) from exc

    services: dict[str, RestServiceConfig] = {}
    service_aliases: dict[str, str] = {}
    for raw_service_name, raw_service_config in raw_services.items():
        service_name: str = normalize_registry_name(raw_service_name, "service")
        service_lookup_name: str = normalize_lookup_name(service_name, "service")
        if service_lookup_name in service_aliases:
            raise RestConfigurationError(f"Duplicate REST service name: {service_name}")

        resources: dict[str, RestResourceConfig] = {}
        resource_aliases: dict[str, str] = {}
        for (
            raw_resource_name,
            raw_resource_config,
        ) in raw_service_config.resources.items():
            resource_name: str = normalize_registry_name(raw_resource_name, "resource")
            resource_lookup_name: str = normalize_lookup_name(resource_name, "resource")
            if resource_lookup_name in resource_aliases:
                raise RestConfigurationError(
                    "Duplicate REST resource name: "
                    f"service={service_name}, "
                    f"resource={resource_name}"
                )
            resources[resource_name] = RestResourceConfig(
                resource_name=resource_name,
                method=raw_resource_config.method,
                path=raw_resource_config.path,
                path_parameter_names=extract_path_parameter_names(
                    raw_resource_config.path
                ),
                description=raw_resource_config.description,
            )
            resource_aliases[resource_lookup_name] = resource_name

        services[service_name] = RestServiceConfig(
            service_name=service_name,
            base_url=raw_service_config.base_url,
            auth_type=raw_service_config.auth_type,
            auth_config=RestAuthConfig(
                token=raw_service_config.auth_config.token,
                username=raw_service_config.auth_config.username,
                password=raw_service_config.auth_config.password,
                key_name=raw_service_config.auth_config.key_name,
                key_value=raw_service_config.auth_config.key_value,
                headers=dict(raw_service_config.auth_config.headers),
            ),
            timeout_seconds=raw_service_config.timeout_seconds,
            retry_count=raw_service_config.retry_count,
            resources=resources,
            resource_aliases=resource_aliases,
        )
        service_aliases[service_lookup_name] = service_name

    return RestServiceRegistry(services=services, service_aliases=service_aliases)


def get_rest_service_config(
    registry: RestServiceRegistry, service_name: str
) -> RestServiceConfig:
    service_lookup_name: str = normalize_lookup_name(service_name, "service")
    canonical_service_name: str | None = registry.service_aliases.get(
        service_lookup_name
    )
    if canonical_service_name is None:
        raise RestServiceNotFoundError(service_name)
    service_config: RestServiceConfig | None = registry.services.get(
        canonical_service_name
    )
    if service_config is None:
        raise RestServiceNotFoundError(service_name)
    return service_config


def get_rest_resource_config(
    service_config: RestServiceConfig, resource_name: str
) -> RestResourceConfig:
    resource_lookup_name: str = normalize_lookup_name(resource_name, "resource")
    canonical_resource_name: str | None = service_config.resource_aliases.get(
        resource_lookup_name
    )
    if canonical_resource_name is None:
        raise RestResourceNotFoundError(service_config.service_name, resource_name)
    resource_config: RestResourceConfig | None = service_config.resources.get(
        canonical_resource_name
    )
    if resource_config is None:
        raise RestResourceNotFoundError(service_config.service_name, resource_name)
    return resource_config


def describe_rest_resource_catalog(registry: RestServiceRegistry) -> str:
    if not registry.services:
        return "- No REST resources are configured."

    lines: list[str] = []
    for service_name in sorted(registry.services):
        service_config: RestServiceConfig = registry.services[service_name]
        for resource_name in sorted(service_config.resources):
            resource_config: RestResourceConfig = service_config.resources[
                resource_name
            ]
            description: str = resource_config.description or "No description provided."
            lines.append(
                f"- {service_name}.{resource_name} [{resource_config.method}]: "
                f"{description}"
            )
    return "\n".join(lines)

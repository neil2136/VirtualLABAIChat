from dataclasses import dataclass

from agentd.domain.errors.rest_errors import RestAuthenticationError
from agentd.domain.types.rest_types import RestAuthConfig, RestHeaderMap, RestServiceConfig


@dataclass(frozen=True, slots=True)
class PreparedRestAuth:
    headers: RestHeaderMap
    query_params: dict[str, str]
    basic_auth: tuple[str, str] | None



def prepare_rest_auth(service_config: RestServiceConfig) -> PreparedRestAuth:
    auth_type = service_config.auth_type
    auth_config: RestAuthConfig = service_config.auth_config

    if auth_type == 'none':
        return PreparedRestAuth(headers={}, query_params={}, basic_auth=None)

    if auth_type == 'bearer_token':
        if auth_config.token is None:
            raise RestAuthenticationError(service_config.service_name, auth_type, 'token is required.')
        return PreparedRestAuth(
            headers={'Authorization': f'Bearer {auth_config.token}'},
            query_params={},
            basic_auth=None,
        )

    if auth_type == 'basic_auth':
        if auth_config.username is None or auth_config.password is None:
            raise RestAuthenticationError(service_config.service_name, auth_type, 'username and password are required.')
        return PreparedRestAuth(
            headers={},
            query_params={},
            basic_auth=(auth_config.username, auth_config.password),
        )

    if auth_type == 'api_key_header':
        if auth_config.key_name is None or auth_config.key_value is None:
            raise RestAuthenticationError(service_config.service_name, auth_type, 'key_name and key_value are required.')
        return PreparedRestAuth(
            headers={auth_config.key_name: auth_config.key_value},
            query_params={},
            basic_auth=None,
        )

    if auth_type == 'api_key_query':
        if auth_config.key_name is None or auth_config.key_value is None:
            raise RestAuthenticationError(service_config.service_name, auth_type, 'key_name and key_value are required.')
        return PreparedRestAuth(
            headers={},
            query_params={auth_config.key_name: auth_config.key_value},
            basic_auth=None,
        )

    if auth_type == 'custom_headers':
        return PreparedRestAuth(
            headers=dict(auth_config.headers),
            query_params={},
            basic_auth=None,
        )

    raise RestAuthenticationError(service_config.service_name, auth_type, 'unsupported auth type.')
from functools import lru_cache

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from agentd.agents.tools import (
    register_mongo_tools,
    register_rest_tools,
)
from agentd.core.debug import emit_debug_log
from agentd.domain.errors.agent_errors import AgentConfigurationError
from agentd.domain.types.chat_types import ChatAgentDeps
from agentd.infrastructure.config import Settings


def build_instructions(ctx: RunContext[ChatAgentDeps]) -> str:
    """Build dynamic instructions that include user-specific information."""
    user_id = ctx.deps.user_id
    return (
        f"You are an AI assistant helping the user with device management. "
        f"The current user's ID is '{user_id}'. "
        f"Always address the user by their ID '{user_id}' when greeting. "
        f"For example, when the user says 'hello', respond with "
        f"'Hello, {user_id}, I'm your AI assistant...' "
        f"Use the registered tools when the user asks for current data "
        f"from configured external services or configured databases. "
        f"When the user wants to search DUT devices, use only the "
        f"dedicated DUT device search tools. Words like 设备, 型号, "
        f"盒子, 防火墙 and DUT all refer to DUT devices. Use "
        f"search_dut_devices by default for DUT searches. "
        f"When the user asks about their own devices using phrases like "
        f"'我的设备', 'my devices', '我拥有的', '我的tz570p', "
        f"call search_dut_devices with owner_filter='me'. "
        f"Use search_idle_dut_devices_by_model only when the user "
        f"explicitly asks for idle or available devices, asks to "
        f"find idle devices by model, or says Owner and User should "
        f"refer to the same user. For a request like 搜索tz570p设备, "
        f"do not call search_idle_dut_devices_by_model. Terms like "
        f"unlock, TZ270W_Unlock and g7unlock can be passed directly "
        f"to the DUT search "
        f"tools because the backend normalizes them. Use "
        f"borrow_device when the user asks to borrow a device such "
        f"as 借用设备83. Use return_device when the user asks to "
        f"return a device such as 归还设备83. Do not ask the user for "
        f"requester_name or user_id because those are provided by "
        f"the trusted request header. Do not invent service names, "
        f"resource names or device data. Only call tools that are "
        f"available to you."
    )


@lru_cache
def create_chat_agent(
    model_name: str,
    model_base_url: str | None,
    model_api_key: str | None,
    mongodb_uri: str | None,
    mongodb_database: str | None,
    mongodb_resources_json: str | None,
    rest_api_services_json: str | None,
) -> Agent[ChatAgentDeps, str]:
    emit_debug_log(
        "chat_agent.create.start",
        model_name=model_name,
        model_base_url=model_base_url,
        has_model_api_key=model_api_key is not None,
        has_mongodb_uri=mongodb_uri is not None,
        has_mongodb_database=mongodb_database is not None,
        has_mongodb_resources_json=mongodb_resources_json is not None,
        has_rest_api_services_json=rest_api_services_json is not None,
    )
    provider: OpenAIProvider = OpenAIProvider(
        base_url=model_base_url, api_key=model_api_key
    )
    model: OpenAIChatModel = OpenAIChatModel(model_name, provider=provider)
    agent: Agent[ChatAgentDeps, str] = Agent(
        model=model,
        deps_type=ChatAgentDeps,
        output_type=str,
        instructions=build_instructions,
    )
    registered_mongo_resources: tuple[str, ...] = register_mongo_tools(
        agent=agent,
        mongodb_uri=mongodb_uri,
        mongodb_database=mongodb_database,
        mongodb_resources_json=mongodb_resources_json,
    )
    registered_rest_resources: tuple[str, ...] = register_rest_tools(
        agent, rest_api_services_json
    )
    emit_debug_log(
        "chat_agent.create.completed",
        model_name=model_name,
        registered_mongo_resources=registered_mongo_resources,
        registered_rest_resources=registered_rest_resources,
    )
    return agent


def get_chat_agent(settings: Settings) -> Agent[ChatAgentDeps, str]:
    if settings.model_name is None:
        raise AgentConfigurationError(
            "MODEL_NAME is required to initialize the chat agent."
        )

    return create_chat_agent(
        model_name=settings.model_name,
        model_base_url=settings.model_base_url,
        model_api_key=settings.model_api_key,
        mongodb_uri=settings.mongodb_uri,
        mongodb_database=settings.mongodb_database,
        mongodb_resources_json=settings.mongodb_resources_json,
        rest_api_services_json=settings.rest_api_services_json,
    )

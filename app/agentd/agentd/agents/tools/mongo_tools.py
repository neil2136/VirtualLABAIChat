from dataclasses import asdict, dataclass
import re

from pydantic_ai import Agent, ModelRetry, RunContext

from agentd.core.debug import emit_debug_log
from agentd.domain.types.chat_types import (
    ChatAgentDeps,
    DUT_SEARCH_STRUCTURED_DATA_TYPE,
    DUT_SEARCH_TOOL_NAME,
    DutDeviceListItem,
    DutDeviceListPayload,
    DutDeviceListQuery,
    DutDeviceListQueryFilter,
    IdleDutDeviceListItem,
    IdleDutDeviceListPayload,
    IdleDutDeviceListQuery,
)
from agentd.domain.types.mongo_types import (
    MongoDocument,
    MongoQueryParams,
    MongoQueryResult,
    MongoResourceConfig,
)
from agentd.infrastructure.connectors.mongodb import (
    MongoResourceRegistry,
    build_mongo_resource_registry,
    get_mongo_resource_config,
    get_optional_mongo_connector,
)

DUT_SEARCH_RESOURCE_NAME: str = "dut_search"
IDLE_DUT_SEARCH_TOOL_NAME: str = "search_idle_dut_devices_by_model"
IDLE_DUT_STRUCTURED_DATA_TYPE: str = "idle_dut_device_list"
DUT_SEARCH_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile("设备"),
    re.compile("型号"),
    re.compile("盒子"),
    re.compile("防火墙"),
    re.compile(r"\bdut\b", re.IGNORECASE),
    re.compile(r"\bdevice(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bmodel(?:s)?\b", re.IGNORECASE),
    re.compile(r"\bbox(?:es)?\b", re.IGNORECASE),
    re.compile(r"\bfirewall(?:s)?\b", re.IGNORECASE),
)
DUT_SEARCH_TOKEN_PATTERN: re.Pattern[str] = re.compile(r"[A-Za-z0-9]+")
DUT_SEARCH_UNLOCK_PATTERN: re.Pattern[str] = re.compile(r"unlock", re.IGNORECASE)
DUT_SEARCH_PRODUCT_TYPE_PATTERN: re.Pattern[str] = re.compile(r"^g\d+$", re.IGNORECASE)
DUT_SEARCH_PRODUCT_ALIASES: tuple[tuple[str, str], ...] = (("tz270w", "TZ270W"),)
IDLE_DUT_PROMPT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile("空闲"),
    re.compile("闲置"),
    re.compile("可用"),
    re.compile(r"\bidle\b", re.IGNORECASE),
    re.compile(r"\bavailable\b", re.IGNORECASE),
)
IDLE_DUT_OWNER_USER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"owner\s*(and|&)?\s*user", re.IGNORECASE),
    re.compile(r"user\s*(and|&)?\s*owner", re.IGNORECASE),
    re.compile(r"owner\s*和\s*user", re.IGNORECASE),
    re.compile(r"user\s*和\s*owner", re.IGNORECASE),
    re.compile("owner和user"),
    re.compile("user和owner"),
)
IDLE_DUT_SAME_USER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile("同一个人"),
    re.compile("同一用户"),
    re.compile("同人"),
    re.compile("相同用户"),
    re.compile(r"\bsame\b", re.IGNORECASE),
    re.compile(r"\bequal\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class DutSearchNormalizationResult:
    filters: MongoQueryParams
    keyword: str


def build_dut_search_tool_docstring(resource_config: MongoResourceConfig) -> str:
    filter_names: str = ", ".join(sorted(resource_config.filter_fields))
    keyword_paths: str = ", ".join(resource_config.keyword_paths)
    return (
        "Search DUT devices by natural-language keyword and structured filters.\n\n"
        "Use this tool when the user wants a general DUT device search.\n"
        "When the user asks about their own devices using phrases like "
        "'我的设备', 'my devices', '我拥有的设备', or '我的tz570p', "
        "set owner_filter to 'me' to search for devices owned by the current user.\n"
        "Return results only from the configured DUT collection.\n"
        "Filter names are case-insensitive.\n"
        "String filter values are case-insensitive.\n"
        "The current user's own Owner or User records are excluded automatically.\n"
        "Use this tool by default for DUT searches.\n"
        "Use the idle-device tool only when the user explicitly asks for idle "
        "or available devices.\n"
        "Natural-language terms like unlock, TZ270W_Unlock and g7unlock are "
        "normalized automatically.\n"
        "Set keyword to an empty string when only structured filters are needed.\n"
        "Set filters to an empty object when only keyword search is needed.\n"
        "Set limit to a positive integer.\n"
        "The owner_filter parameter accepts 'me', 'my', '我的' to search current user's devices.\n"
        "The tool returns structured list data with id, sn, owner_raw, "
        "owner_account, owner_display_name and owner_label.\n\n"
        f"Available filter names: {filter_names}\n"
        f"Keyword search paths: {keyword_paths}"
    )


def build_idle_dut_search_tool_docstring() -> str:
    return (
        "Search idle DUT devices by model.\n\n"
        "Use this tool only when the user explicitly asks for idle or available "
        "devices, even if the user does not say DUT, or says Owner and User "
        "must refer to the same person.\n"
        "The current user's own Owner or User records are excluded automatically.\n"
        "The model value is case-insensitive and matches Product or ProductType.\n"
        "Natural-language terms like unlock, TZ270W_Unlock and g7unlock are "
        "normalized automatically.\n"
        "A device is idle only when Owner and User normalize to the "
        "same non-empty user name.\n"
        "Owner normalization uses the text before the first opening parenthesis.\n"
        "Set limit to a positive integer.\n"
        "The tool returns structured list data with id, sn, product, "
        "product_type, owner_raw, owner_account, "
        "owner_display_name, owner_label and user fields."
    )


def build_dut_device_list_query_filters(
    filters: MongoQueryParams,
) -> tuple[DutDeviceListQueryFilter, ...]:
    query_filters: list[DutDeviceListQueryFilter] = []
    for field_name, value in filters.items():
        # Skip MongoDB operators (e.g., $or) as they have complex values
        # that cannot be serialized as simple filter items
        if field_name.startswith("$"):
            continue
        query_filters.append(
            DutDeviceListQueryFilter(field_name=field_name, value=value)
        )
    return tuple(query_filters)


def build_dut_device_list_item(document: MongoDocument) -> DutDeviceListItem:
    owner_raw: str | None = stringify_document_value(document.get("Owner"))
    return DutDeviceListItem(
        id=stringify_document_value(document.get("id")),
        sn=stringify_document_value(document.get("SN")),
        owner_raw=owner_raw,
        owner_account=extract_owner_account(owner_raw),
        owner_display_name=extract_owner_display_name(owner_raw),
        owner_label=build_owner_label(owner_raw),
    )


def build_dut_search_result_payload(
    result: MongoQueryResult,
    keyword: str,
    filters: MongoQueryParams,
    limit: int,
) -> dict[str, object]:
    items: tuple[DutDeviceListItem, ...] = tuple(
        build_dut_device_list_item(document) for document in result.documents
    )
    payload = DutDeviceListPayload(
        type=DUT_SEARCH_STRUCTURED_DATA_TYPE,
        tool_name=DUT_SEARCH_TOOL_NAME,
        query=DutDeviceListQuery(
            keyword=keyword,
            limit=limit,
            filters=build_dut_device_list_query_filters(filters),
        ),
        count=result.count,
        items=items,
    )
    return asdict(payload)


def expand_dut_search_text(text: str) -> str:
    expanded_text: str = DUT_SEARCH_UNLOCK_PATTERN.sub(" unlock ", text.strip())
    normalized_text: str = expanded_text
    for pattern in DUT_SEARCH_NOISE_PATTERNS:
        normalized_text = pattern.sub(" ", normalized_text)
    return normalized_text


def split_dut_search_tokens(text: str) -> tuple[str, ...]:
    expanded_text: str = expand_dut_search_text(text)
    if expanded_text == "":
        return ()
    return tuple(DUT_SEARCH_TOKEN_PATTERN.findall(expanded_text))


def resolve_dut_search_alias(token: str) -> tuple[str, str] | None:
    normalized_token: str = token.strip().lower()
    if normalized_token == "":
        return None

    if normalized_token == "unlock":
        return ("classify", "Unlock")

    if DUT_SEARCH_PRODUCT_TYPE_PATTERN.fullmatch(normalized_token) is not None:
        return ("ProductType", normalized_token.upper())

    for alias, product_name in DUT_SEARCH_PRODUCT_ALIASES:
        if normalized_token == alias:
            return ("Product", product_name)
    return None


def build_dut_search_filters_and_keyword(text: str) -> DutSearchNormalizationResult:
    tokens: tuple[str, ...] = split_dut_search_tokens(text)
    derived_filters: MongoQueryParams = {}
    residual_tokens: list[str] = []

    for raw_token in tokens:
        alias: tuple[str, str] | None = resolve_dut_search_alias(raw_token)
        if alias is None:
            residual_tokens.append(raw_token)
            continue

        field_name, field_value = alias
        current_value: object | None = derived_filters.get(field_name)
        if current_value is None:
            derived_filters[field_name] = field_value
            continue

        if str(current_value).casefold() != field_value.casefold():
            residual_tokens.append(raw_token)

    return DutSearchNormalizationResult(
        filters=derived_filters,
        keyword=" ".join(residual_tokens).strip(),
    )


def merge_dut_search_filters(
    explicit_filters: MongoQueryParams,
    derived_filters: MongoQueryParams,
) -> MongoQueryParams:
    merged_filters: MongoQueryParams = dict(derived_filters)
    for field_name, value in explicit_filters.items():
        merged_filters[field_name] = value
    return merged_filters


def normalize_dut_search_request(
    text: str,
    explicit_filters: MongoQueryParams,
) -> DutSearchNormalizationResult:
    normalized_result: DutSearchNormalizationResult = (
        build_dut_search_filters_and_keyword(text)
    )
    return DutSearchNormalizationResult(
        filters=merge_dut_search_filters(
            explicit_filters=explicit_filters,
            derived_filters=normalized_result.filters,
        ),
        keyword=normalized_result.keyword,
    )


def has_idle_dut_prompt_pattern(
    user_prompt: str,
    patterns: tuple[re.Pattern[str], ...],
) -> bool:
    return any(pattern.search(user_prompt) is not None for pattern in patterns)


def is_explicit_idle_dut_request(user_prompt: str) -> bool:
    normalized_prompt: str = user_prompt.strip()
    if normalized_prompt == "":
        return False
    if has_idle_dut_prompt_pattern(normalized_prompt, IDLE_DUT_PROMPT_PATTERNS):
        return True
    has_owner_user_reference: bool = has_idle_dut_prompt_pattern(
        normalized_prompt, IDLE_DUT_OWNER_USER_PATTERNS
    )
    has_same_user_reference: bool = has_idle_dut_prompt_pattern(
        normalized_prompt, IDLE_DUT_SAME_USER_PATTERNS
    )
    return has_owner_user_reference and has_same_user_reference


def require_explicit_idle_dut_request(user_prompt: str, model: str) -> None:
    if is_explicit_idle_dut_request(user_prompt):
        return
    raise ModelRetry(
        "Only call search_idle_dut_devices_by_model when the current user "
        "message explicitly asks for idle or available devices, or says "
        "Owner and User should refer to the same user. "
        f"The current message does not contain that intent for model={model!r}. "
        "Use search_dut_devices instead."
    )


def stringify_document_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return None


def extract_owner_account(owner_raw: str | None) -> str | None:
    if owner_raw is None:
        return None
    owner_account: str = owner_raw.split("(", 1)[0].strip()
    if owner_account == "":
        return None
    return owner_account


def extract_owner_display_name(owner_raw: str | None) -> str | None:
    if owner_raw is None:
        return None
    left_index: int = owner_raw.find("(")
    right_index: int = owner_raw.find(")", left_index + 1)
    if left_index == -1 or right_index == -1:
        return None
    owner_display_name: str = owner_raw[left_index + 1 : right_index].strip()
    if owner_display_name == "":
        return None
    return owner_display_name


def build_owner_label(owner_raw: str | None) -> str | None:
    owner_account: str | None = extract_owner_account(owner_raw)
    if owner_account is None:
        return None
    owner_display_name: str | None = extract_owner_display_name(owner_raw)
    if owner_display_name is None:
        return f"owner: {owner_account}"
    return f"owner: {owner_account} ({owner_display_name})"


def build_idle_dut_device_list_item(document: MongoDocument) -> IdleDutDeviceListItem:
    owner_raw: str | None = stringify_document_value(document.get("Owner"))
    return IdleDutDeviceListItem(
        id=stringify_document_value(document.get("id")),
        sn=stringify_document_value(document.get("SN")),
        product=stringify_document_value(document.get("Product")),
        product_type=stringify_document_value(document.get("ProductType")),
        owner_raw=owner_raw,
        owner_account=extract_owner_account(owner_raw),
        owner_display_name=extract_owner_display_name(owner_raw),
        owner_label=build_owner_label(owner_raw),
        user=stringify_document_value(document.get("User")),
    )


def build_idle_dut_search_result_for_agent(
    result: MongoQueryResult,
    model: str,
    limit: int,
) -> dict[str, object]:
    items: tuple[IdleDutDeviceListItem, ...] = tuple(
        build_idle_dut_device_list_item(document) for document in result.documents
    )
    payload = IdleDutDeviceListPayload(
        type=IDLE_DUT_STRUCTURED_DATA_TYPE,
        tool_name=IDLE_DUT_SEARCH_TOOL_NAME,
        query=IdleDutDeviceListQuery(model=model, limit=limit),
        count=result.count,
        items=items,
    )
    return asdict(payload)


def build_registered_mongo_resource_names(
    registry: MongoResourceRegistry,
) -> tuple[str, ...]:
    return tuple(sorted(registry.resources))


def register_mongo_tools(
    agent: Agent[ChatAgentDeps, str],
    mongodb_uri: str | None,
    mongodb_database: str | None,
    mongodb_resources_json: str | None,
) -> tuple[str, ...]:
    registry: MongoResourceRegistry = build_mongo_resource_registry(
        mongodb_resources_json
    )
    registered_resources: tuple[str, ...] = build_registered_mongo_resource_names(
        registry
    )
    emit_debug_log(
        "mongo_tools.registry.loaded",
        resource_count=len(registry.resources),
        registered_resources=registered_resources,
    )

    if mongodb_resources_json is None or not registry.resources:
        emit_debug_log("mongo_tools.registry.empty")
        return ()

    connector = get_optional_mongo_connector(
        mongodb_uri=mongodb_uri,
        mongodb_database=mongodb_database,
        mongodb_resources_json=mongodb_resources_json,
    )
    if connector is None:
        emit_debug_log("mongo_tools.registry.empty")
        return ()

    if DUT_SEARCH_RESOURCE_NAME not in registry.resources:
        emit_debug_log("dut_tools.registry.empty")
        return registered_resources

    dut_resource_config: MongoResourceConfig = get_mongo_resource_config(
        registry, DUT_SEARCH_RESOURCE_NAME
    )
    dut_tool_docstring: str = build_dut_search_tool_docstring(dut_resource_config)
    idle_dut_tool_docstring: str = build_idle_dut_search_tool_docstring()

    async def search_dut_devices(
        ctx: RunContext[ChatAgentDeps],
        keyword: str,
        filters: MongoQueryParams,
        limit: int,
        owner_filter: str | None = None,
    ) -> dict[str, object]:
        user_id: str = ctx.deps.user_id
        
        # Handle owner_filter for "my devices" queries
        effective_filters: MongoQueryParams = dict(filters)
        is_my_devices_query: bool = False
        if owner_filter is not None:
            normalized_owner: str = owner_filter.strip().lower()
            if normalized_owner in ("me", "my", "我的", "mine", "我"):
                # Mark as my devices query - will use $or for Owner OR User
                is_my_devices_query = True
            else:
                # Use the specified owner value
                effective_filters["Owner"] = owner_filter
        
        # For "my devices" query, add $or condition to match Owner OR User
        if is_my_devices_query:
            effective_filters["$or"] = [
                {"Owner": user_id},
                {"User": user_id},
            ]
        
        normalized_request: DutSearchNormalizationResult = normalize_dut_search_request(
            text=keyword,
            explicit_filters=effective_filters,
        )
        emit_debug_log(
            "dut_tools.search.start",
            user_id=user_id,
            raw_keyword=keyword,
            raw_filters=filters,
            owner_filter=owner_filter,
            effective_filters=effective_filters,
            normalized_keyword=normalized_request.keyword,
            normalized_filters=normalized_request.filters,
            limit=limit,
        )
        try:
            # When owner_filter targets current user, don't exclude current user
            # to allow searching for own devices
            should_exclude_current_user: bool = not (
                owner_filter is not None and 
                owner_filter.strip().lower() in ("me", "my", "我的", "mine", "我")
            )
            excluded_user_id: str | None = user_id if should_exclude_current_user else None
            
            result: MongoQueryResult = await connector.query_resource(
                resource_name=DUT_SEARCH_RESOURCE_NAME,
                query_params=normalized_request.filters,
                keyword=normalized_request.keyword,
                limit_override=limit,
                excluded_user_id=excluded_user_id,
            )
            payload: dict[str, object] = build_dut_search_result_payload(
                result=result,
                keyword=normalized_request.keyword,
                filters=normalized_request.filters,
                limit=limit,
            )
            emit_debug_log(
                "dut_tools.search.success",
                user_id=user_id,
                raw_keyword=keyword,
                raw_filters=filters,
                normalized_keyword=normalized_request.keyword,
                normalized_filters=normalized_request.filters,
                limit=limit,
                count=result.count,
                first_document=result.documents[0] if result.documents else None,
                payload=payload,
            )
            return payload
        except Exception as exc:
            emit_debug_log(
                "dut_tools.search.error",
                user_id=user_id,
                raw_keyword=keyword,
                raw_filters=filters,
                normalized_keyword=normalized_request.keyword,
                normalized_filters=normalized_request.filters,
                limit=limit,
                error=repr(exc),
            )
            raise

    async def search_idle_dut_devices_by_model(
        ctx: RunContext[ChatAgentDeps],
        model: str,
        limit: int,
    ) -> dict[str, object]:
        user_id: str = ctx.deps.user_id
        user_prompt: str = ctx.deps.user_prompt
        normalized_request: DutSearchNormalizationResult = normalize_dut_search_request(
            text=model,
            explicit_filters={},
        )
        print(f"[DEBUG search_idle_dut] user_id={user_id}, model={model!r}")
        print(f"[DEBUG search_idle_dut] normalized_keyword={normalized_request.keyword!r}")
        print(f"[DEBUG search_idle_dut] normalized_filters={normalized_request.filters}")
        emit_debug_log(
            "dut_tools.idle_search.start",
            user_id=user_id,
            user_prompt=user_prompt,
            model=model,
            normalized_keyword=normalized_request.keyword,
            normalized_filters=normalized_request.filters,
            limit=limit,
        )
        try:
            require_explicit_idle_dut_request(user_prompt=user_prompt, model=model)
            print(f"[DEBUG search_idle_dut] Calling connector.search_idle_dut_devices_by_model...")
            result: MongoQueryResult = await connector.search_idle_dut_devices_by_model(
                resource_name=DUT_SEARCH_RESOURCE_NAME,
                model=model,
                query_params=normalized_request.filters,
                keyword=normalized_request.keyword,
                limit_override=limit,
                excluded_user_id=user_id,
            )
            print(f"[DEBUG search_idle_dut] Query result count={result.count}")
            payload: dict[str, object] = build_idle_dut_search_result_for_agent(
                result=result,
                model=model,
                limit=limit,
            )
            emit_debug_log(
                "dut_tools.idle_search.success",
                user_id=user_id,
                user_prompt=user_prompt,
                model=model,
                normalized_keyword=normalized_request.keyword,
                normalized_filters=normalized_request.filters,
                limit=limit,
                count=result.count,
                first_document=result.documents[0] if result.documents else None,
            )
            return payload
        except Exception as exc:
            emit_debug_log(
                "dut_tools.idle_search.error",
                user_id=user_id,
                user_prompt=user_prompt,
                model=model,
                normalized_keyword=normalized_request.keyword,
                normalized_filters=normalized_request.filters,
                limit=limit,
                error=repr(exc),
            )
            raise

    search_dut_devices.__doc__ = dut_tool_docstring
    search_idle_dut_devices_by_model.__doc__ = idle_dut_tool_docstring
    agent.tool(search_dut_devices)
    agent.tool(search_idle_dut_devices_by_model)
    emit_debug_log(
        "dut_tools.search.registered",
        tool_name="search_dut_devices",
        filter_names=tuple(sorted(dut_resource_config.filter_fields)),
        keyword_paths=dut_resource_config.keyword_paths,
    )
    emit_debug_log(
        "dut_tools.idle_search.registered",
        tool_name=IDLE_DUT_SEARCH_TOOL_NAME,
        model_fields=("Product", "ProductType"),
    )
    emit_debug_log(
        "mongo_tools.exposure.restricted",
        exposed_tools=("search_dut_devices", IDLE_DUT_SEARCH_TOOL_NAME),
        configured_resources=registered_resources,
    )
    return registered_resources

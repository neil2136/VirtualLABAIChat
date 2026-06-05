import re

from collections.abc import Mapping, Sequence

from agentd.domain.errors.mongo_errors import (
    MongoFilterFieldNotAllowedError,
    MongoFilterValueError,
    MongoLimitValueError,
)
from agentd.domain.types.mongo_types import (
    MongoAggregationSpec,
    MongoAggregationStage,
    MongoAggregationValue,
    MongoDocument,
    MongoFilterFieldConfig,
    MongoQueryFilter,
    MongoQueryFilterValue,
    MongoQueryParamValue,
    MongoQueryParams,
    MongoQuerySpec,
    MongoResourceConfig,
    MongoSortSpec,
    MongoStringMatchMode,
    MongoValue,
)
from agentd.infrastructure.connectors.mongodb.resource_registry import (
    normalize_mongo_filter_alias,
)

IDLE_DUT_MODEL_SEARCH_FIELDS: tuple[str, ...] = ("Product", "ProductType")
IDLE_DUT_RESULT_FIELDS: tuple[str, ...] = (
    "id",
    "SN",
    "Product",
    "ProductType",
    "Owner",
    "User",
)
IDLE_DUT_NORMALIZED_OWNER_FIELD: str = "_normalized_owner"
IDLE_DUT_NORMALIZED_USER_FIELD: str = "_normalized_user"


def build_mongo_query_spec(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
    keyword: str,
    limit_override: int | None,
    excluded_user_id: str | None,
) -> MongoQuerySpec:
    normalized_query_filter: MongoQueryFilter = build_mongo_query_filter(
        resource_config=resource_config,
        query_params=query_params,
        keyword=keyword,
        excluded_user_id=excluded_user_id,
    )
    normalized_limit: int = normalize_mongo_query_limit(resource_config, limit_override)
    return MongoQuerySpec(
        resource_name=resource_config.resource_name,
        collection=resource_config.collection,
        query_filter=normalized_query_filter,
        projection_fields=resource_config.projection_fields,
        sort=resource_config.sort,
        limit=normalized_limit,
    )


def build_idle_dut_search_aggregation_spec(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
    keyword: str,
    limit_override: int | None,
    excluded_user_id: str | None,
) -> MongoAggregationSpec:
    normalized_limit: int = normalize_mongo_query_limit(resource_config, limit_override)
    pipeline = build_idle_dut_search_pipeline(
        resource_config=resource_config,
        query_params=query_params,
        keyword=keyword,
        limit=normalized_limit,
        excluded_user_id=excluded_user_id,
    )
    return MongoAggregationSpec(
        resource_name=resource_config.resource_name,
        collection=resource_config.collection,
        pipeline=pipeline,
        limit=normalized_limit,
    )


def build_idle_dut_search_pipeline(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
    keyword: str,
    limit: int,
    excluded_user_id: str | None,
) -> tuple[MongoAggregationStage, ...]:
    stages: list[MongoAggregationStage] = [
        build_idle_dut_normalization_stage(),
        build_idle_dut_match_stage(
            resource_config=resource_config,
            query_params=query_params,
            keyword=keyword,
            excluded_user_id=excluded_user_id,
        ),
        build_idle_dut_projection_stage(),
    ]
    if resource_config.sort:
        stages.append(build_mongo_sort_stage(resource_config.sort))
    stages.append({"$limit": limit})
    return tuple(stages)


def build_idle_dut_normalization_stage() -> MongoAggregationStage:
    owner_expression: MongoAggregationValue = (
        build_mongo_owner_normalization_expression()
    )
    user_expression: MongoAggregationValue = build_mongo_field_normalization_expression(
        "User"
    )
    return {
        "$addFields": {
            IDLE_DUT_NORMALIZED_OWNER_FIELD: owner_expression,
            IDLE_DUT_NORMALIZED_USER_FIELD: user_expression,
        }
    }


def build_idle_dut_match_stage(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
    keyword: str,
    excluded_user_id: str | None,
) -> MongoAggregationStage:
    conditions: list[MongoAggregationValue] = [
        {"$expr": build_idle_dut_same_user_expression()},
    ]
    model_filter: MongoQueryFilter | None = build_idle_dut_model_filter(
        resource_name=resource_config.resource_name,
        keyword=keyword,
    )
    if model_filter is not None:
        conditions.append(model_filter)

    exact_filter: MongoQueryFilter = normalize_mongo_exact_filter(
        resource_config=resource_config,
        query_params=query_params,
    )
    if exact_filter:
        conditions.append(exact_filter)

    excluded_user_filter: MongoQueryFilter | None = build_mongo_excluded_user_filter(
        resource_name=resource_config.resource_name,
        excluded_user_id=excluded_user_id,
        owner_expression={"$ifNull": (f"${IDLE_DUT_NORMALIZED_OWNER_FIELD}", "")},
        user_expression={"$ifNull": (f"${IDLE_DUT_NORMALIZED_USER_FIELD}", "")},
    )
    if excluded_user_filter is not None:
        conditions.append(excluded_user_filter)

    return {"$match": {"$and": tuple(conditions)}}


def build_idle_dut_model_filter(
    resource_name: str,
    keyword: str,
) -> MongoQueryFilter | None:
    normalized_keyword: str = keyword.strip()
    if normalized_keyword == "":
        return None
    normalized_model: str = normalize_mongo_text_value(
        resource_name, "model", normalized_keyword
    )
    return {
        "$or": tuple(
            build_case_insensitive_contains_entry(field_name, normalized_model)
            for field_name in IDLE_DUT_MODEL_SEARCH_FIELDS
        )
    }


def build_idle_dut_projection_stage() -> MongoAggregationStage:
    projection: dict[str, MongoAggregationValue] = {"_id": 0}
    for field_name in IDLE_DUT_RESULT_FIELDS:
        projection[field_name] = 1
    return {"$project": projection}


def build_mongo_sort_stage(sort: MongoSortSpec) -> MongoAggregationStage:
    return {"$sort": {field_name: direction for field_name, direction in sort}}


def build_case_insensitive_contains_entry(
    field_name: str,
    normalized_model: str,
) -> dict[str, MongoAggregationValue]:
    return {
        field_name: build_case_insensitive_mongo_string_filter(
            normalized_model, "contains"
        )
    }


def build_idle_dut_same_user_expression() -> MongoAggregationValue:
    normalized_owner_field_reference: str = f"${IDLE_DUT_NORMALIZED_OWNER_FIELD}"
    normalized_user_field_reference: str = f"${IDLE_DUT_NORMALIZED_USER_FIELD}"
    return {
        "$and": (
            {"$ne": (normalized_owner_field_reference, "")},
            {"$ne": (normalized_user_field_reference, "")},
            {
                "$eq": (
                    normalized_owner_field_reference,
                    normalized_user_field_reference,
                )
            },
        )
    }


def build_mongo_excluded_user_filter(
    resource_name: str,
    excluded_user_id: str | None,
    owner_expression: MongoAggregationValue,
    user_expression: MongoAggregationValue,
) -> MongoQueryFilter | None:
    normalized_user_id: str | None = normalize_mongo_excluded_user_id(
        resource_name=resource_name,
        excluded_user_id=excluded_user_id,
    )
    if normalized_user_id is None:
        return None
    return {
        "$expr": build_mongo_excluded_user_expression(
            normalized_user_id=normalized_user_id,
            owner_expression=owner_expression,
            user_expression=user_expression,
        )
    }


def normalize_mongo_excluded_user_id(
    resource_name: str,
    excluded_user_id: str | None,
) -> str | None:
    if excluded_user_id is None:
        return None
    return normalize_mongo_text_value(
        resource_name, "excluded_user_id", excluded_user_id
    ).lower()


def build_mongo_excluded_user_expression(
    normalized_user_id: str,
    owner_expression: MongoAggregationValue,
    user_expression: MongoAggregationValue,
) -> MongoAggregationValue:
    return {
        "$and": (
            {"$ne": (owner_expression, normalized_user_id)},
            {"$ne": (user_expression, normalized_user_id)},
        )
    }


def build_mongo_owner_normalization_expression() -> MongoAggregationValue:
    return build_mongo_lowercase_trimmed_expression(
        {
            "$arrayElemAt": (
                {
                    "$split": (
                        {"$ifNull": ("$Owner", "")},
                        "(",
                    )
                },
                0,
            )
        }
    )


def build_mongo_field_normalization_expression(
    field_name: str,
) -> MongoAggregationValue:
    return build_mongo_lowercase_trimmed_expression({"$ifNull": (f"${field_name}", "")})


def build_mongo_lowercase_trimmed_expression(
    input_expression: MongoAggregationValue,
) -> MongoAggregationValue:
    return {
        "$toLower": {
            "$trim": {
                "input": input_expression,
            }
        }
    }


def build_mongo_query_filter(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
    keyword: str,
    excluded_user_id: str | None,
) -> MongoQueryFilter:
    exact_filter: MongoQueryFilter = normalize_mongo_exact_filter(
        resource_config, query_params
    )
    keyword_filter: MongoQueryFilter | None = build_mongo_keyword_filter(
        resource_config.keyword_paths, keyword
    )
    excluded_user_filter: MongoQueryFilter | None = build_mongo_excluded_user_filter(
        resource_name=resource_config.resource_name,
        excluded_user_id=excluded_user_id,
        owner_expression=build_mongo_owner_normalization_expression(),
        user_expression=build_mongo_field_normalization_expression("User"),
    )
    return combine_mongo_query_filters(
        (exact_filter, keyword_filter, excluded_user_filter)
    )


def combine_mongo_query_filters(
    query_filters: tuple[MongoQueryFilter | None, ...],
) -> MongoQueryFilter:
    active_filters: list[MongoQueryFilter] = []
    for query_filter in query_filters:
        if query_filter is None or query_filter == {}:
            continue
        active_filters.append(query_filter)
    if not active_filters:
        return {}
    if len(active_filters) == 1:
        return active_filters[0]
    return {"$and": tuple(active_filters)}


def normalize_mongo_exact_filter(
    resource_config: MongoResourceConfig,
    query_params: MongoQueryParams,
) -> MongoQueryFilter:
    normalized_query_filter: MongoQueryFilter = {}
    for raw_field_name, raw_value in query_params.items():
        # Pass through MongoDB operators (starting with $) directly
        if raw_field_name.startswith("$"):
            normalized_query_filter[raw_field_name] = raw_value
            continue
        
        field_name: str = normalize_mongo_filter_field_name(
            resource_config, raw_field_name
        )
        field_config: MongoFilterFieldConfig = resource_config.filter_fields[field_name]
        normalized_query_filter[field_config.document_path] = (
            normalize_mongo_field_value(
                resource_name=resource_config.resource_name,
                field_config=field_config,
                value=raw_value,
            )
        )
    return normalized_query_filter


def normalize_mongo_filter_field_name(
    resource_config: MongoResourceConfig, field_name: str
) -> str:
    field_alias: str = normalize_mongo_filter_alias(field_name)
    normalized_field_name: str | None = resource_config.filter_field_aliases.get(
        field_alias
    )
    if normalized_field_name is None:
        raise MongoFilterFieldNotAllowedError(resource_config.resource_name, field_name)
    return normalized_field_name


def build_mongo_keyword_filter(
    keyword_paths: tuple[str, ...], keyword: str
) -> MongoQueryFilter | None:
    normalized_keyword: str = keyword.strip()
    if normalized_keyword == "" or not keyword_paths:
        return None
    escaped_keyword: str = re.escape(normalized_keyword)
    or_entries: list[MongoQueryFilterValue] = []
    for keyword_path in keyword_paths:
        or_entries.append({keyword_path: {"$regex": escaped_keyword, "$options": "i"}})
    return {"$or": tuple(or_entries)}


def normalize_mongo_query_limit(
    resource_config: MongoResourceConfig, limit_override: int | None
) -> int:
    if limit_override is None:
        return resource_config.limit
    if limit_override <= 0:
        raise MongoLimitValueError(resource_config.resource_name, limit_override)
    return min(limit_override, resource_config.limit)


def normalize_mongo_field_value(
    resource_name: str,
    field_config: MongoFilterFieldConfig,
    value: MongoQueryParamValue,
) -> MongoQueryFilterValue:
    if field_config.field_type == "string":
        return normalize_mongo_string_value(
            resource_name=resource_name,
            field_name=field_config.field_name,
            value=value,
            string_match_mode=field_config.string_match_mode,
        )
    if field_config.field_type == "int":
        return normalize_mongo_int_value(resource_name, field_config.field_name, value)
    if field_config.field_type == "float":
        return normalize_mongo_float_value(
            resource_name, field_config.field_name, value
        )
    if field_config.field_type == "bool":
        return normalize_mongo_bool_value(resource_name, field_config.field_name, value)
    raise MongoFilterValueError(
        resource_name, field_config.field_name, field_config.field_type, value
    )


def normalize_mongo_string_value(
    resource_name: str,
    field_name: str,
    value: MongoQueryParamValue,
    string_match_mode: MongoStringMatchMode,
) -> MongoQueryFilterValue:
    normalized_value: str = normalize_mongo_text_value(resource_name, field_name, value)
    return build_case_insensitive_mongo_string_filter(
        normalized_value, string_match_mode
    )


def normalize_mongo_text_value(
    resource_name: str,
    field_name: str,
    value: MongoQueryParamValue,
) -> str:
    normalized_value: str = str(value).strip()
    if normalized_value == "":
        raise MongoFilterValueError(resource_name, field_name, "string", value)
    return normalized_value


def build_case_insensitive_mongo_string_filter(
    normalized_value: str,
    string_match_mode: MongoStringMatchMode,
) -> MongoQueryFilterValue:
    escaped_value: str = re.escape(normalized_value)
    if string_match_mode == "contains":
        return {"$regex": escaped_value, "$options": "i"}
    return {"$regex": f"^{escaped_value}$", "$options": "i"}


def normalize_mongo_int_value(
    resource_name: str, field_name: str, value: MongoQueryParamValue
) -> int:
    if isinstance(value, bool):
        raise MongoFilterValueError(resource_name, field_name, "int", value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        normalized_value: str = value.strip()
        if normalized_value != "":
            try:
                return int(normalized_value)
            except ValueError as exc:
                raise MongoFilterValueError(
                    resource_name, field_name, "int", value
                ) from exc
    raise MongoFilterValueError(resource_name, field_name, "int", value)


def normalize_mongo_float_value(
    resource_name: str, field_name: str, value: MongoQueryParamValue
) -> float:
    if isinstance(value, bool):
        raise MongoFilterValueError(resource_name, field_name, "float", value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized_value: str = value.strip()
        if normalized_value != "":
            try:
                return float(normalized_value)
            except ValueError as exc:
                raise MongoFilterValueError(
                    resource_name, field_name, "float", value
                ) from exc
    raise MongoFilterValueError(resource_name, field_name, "float", value)


def normalize_mongo_bool_value(
    resource_name: str, field_name: str, value: MongoQueryParamValue
) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized_value: str = value.strip().lower()
        if normalized_value in ("true", "1", "yes", "y"):
            return True
        if normalized_value in ("false", "0", "no", "n"):
            return False
    raise MongoFilterValueError(resource_name, field_name, "bool", value)


def build_mongo_projection(projection_fields: tuple[str, ...]) -> dict[str, int]:
    return {field_name: 1 for field_name in projection_fields}


def serialize_mongo_document(document: dict[str, object]) -> MongoDocument:
    serialized_document: MongoDocument = {}
    for key, value in document.items():
        serialized_document[key] = serialize_mongo_value(value)
    return serialized_document


def serialize_mongo_value(value: object) -> MongoValue:
    from datetime import date, datetime

    from bson import ObjectId

    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Mapping):
        serialized_mapping: dict[str, MongoValue] = {}
        for key, nested_value in value.items():
            serialized_mapping[str(key)] = serialize_mongo_value(nested_value)
        return serialized_mapping
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(serialize_mongo_value(item) for item in value)
    return str(value)

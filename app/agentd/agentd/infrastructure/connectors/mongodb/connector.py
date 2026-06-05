import asyncio
import logging
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from agentd.core.debug import emit_debug_log
from agentd.domain.errors.mongo_errors import (
    MongoAggregationExecutionError,
    MongoConfigurationError,
    MongoQueryExecutionError,
)
from agentd.domain.types.mongo_types import (
    MongoAggregationSpec,
    MongoDocument,
    MongoQueryParams,
    MongoQueryResult,
    MongoQuerySpec,
)
from agentd.infrastructure.connectors.mongodb.query_builder import (
    build_idle_dut_search_aggregation_spec,
    build_mongo_projection,
    build_mongo_query_spec,
    serialize_mongo_document,
)
from agentd.infrastructure.connectors.mongodb.resource_registry import (
    MongoResourceRegistry,
    build_mongo_resource_registry,
    get_mongo_resource_config,
)

logger = logging.getLogger(__name__)


class MongoConnector:
    def __init__(
        self,
        mongodb_uri: str,
        mongodb_database: str,
        registry: MongoResourceRegistry,
    ) -> None:
        self._registry = registry
        self._client = MongoClient(mongodb_uri)
        self._database = self._client[mongodb_database]

    async def query_resource(
        self,
        resource_name: str,
        query_params: MongoQueryParams,
        keyword: str,
        limit_override: int | None,
        excluded_user_id: str | None,
    ) -> MongoQueryResult:
        resource_config = get_mongo_resource_config(self._registry, resource_name)
        query_spec: MongoQuerySpec = build_mongo_query_spec(
            resource_config=resource_config,
            query_params=query_params,
            keyword=keyword,
            limit_override=limit_override,
            excluded_user_id=excluded_user_id,
        )
        max_attempts: int = resource_config.retry_count + 1

        emit_debug_log(
            "mongo_connector.query.start",
            resource_name=resource_name,
            collection=query_spec.collection,
            query_filter=query_spec.query_filter,
            projection_fields=query_spec.projection_fields,
            sort=query_spec.sort,
            limit=query_spec.limit,
            excluded_user_id=excluded_user_id,
            retry_count=resource_config.retry_count,
        )

        for attempt in range(1, max_attempts + 1):
            emit_debug_log(
                "mongo_connector.query.attempt",
                resource_name=resource_name,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            try:
                documents: tuple[MongoDocument, ...] = await asyncio.to_thread(
                    execute_mongo_query,
                    database=self._database,
                    query_spec=query_spec,
                )
            except Exception as exc:
                emit_debug_log(
                    "mongo_connector.query.error",
                    resource_name=resource_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=repr(exc),
                )
                if attempt < max_attempts:
                    logger.warning(
                        "Mongo query retry",
                        extra={
                            "resource_name": resource_name,
                            "collection": query_spec.collection,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "query_filter": query_spec.query_filter,
                            "projection_fields": query_spec.projection_fields,
                            "sort": query_spec.sort,
                            "limit": query_spec.limit,
                            "error": repr(exc),
                        },
                    )
                    continue
                raise MongoQueryExecutionError(
                    resource_name=resource_name,
                    collection=query_spec.collection,
                    query_filter=query_spec.query_filter,
                    projection_fields=query_spec.projection_fields,
                    sort=query_spec.sort,
                    limit=query_spec.limit,
                    original_error=exc,
                ) from exc

            emit_debug_log(
                "mongo_connector.query.result",
                resource_name=resource_name,
                count=len(documents),
                first_document=documents[0] if documents else None,
            )
            return MongoQueryResult(
                resource_name=resource_name,
                documents=documents,
                count=len(documents),
            )

        raise MongoQueryExecutionError(
            resource_name=resource_name,
            collection=query_spec.collection,
            query_filter=query_spec.query_filter,
            projection_fields=query_spec.projection_fields,
            sort=query_spec.sort,
            limit=query_spec.limit,
            original_error=None,
        )

    async def search_idle_dut_devices_by_model(
        self,
        resource_name: str,
        model: str,
        query_params: MongoQueryParams,
        keyword: str,
        limit_override: int | None,
        excluded_user_id: str | None,
    ) -> MongoQueryResult:
        resource_config = get_mongo_resource_config(self._registry, resource_name)
        aggregation_spec: MongoAggregationSpec = build_idle_dut_search_aggregation_spec(
            resource_config=resource_config,
            query_params=query_params,
            keyword=keyword,
            limit_override=limit_override,
            excluded_user_id=excluded_user_id,
        )
        max_attempts: int = resource_config.retry_count + 1

        print(f"[DEBUG mongo_connector] search_idle_dut_devices_by_model: model={model!r}, keyword={keyword!r}")
        print(f"[DEBUG mongo_connector] excluded_user_id={excluded_user_id!r}")
        print(f"[DEBUG mongo_connector] aggregation_pipeline={aggregation_spec.pipeline}")
        emit_debug_log(
            "mongo_connector.aggregate.start",
            resource_name=resource_name,
            collection=aggregation_spec.collection,
            model=model,
            query_params=query_params,
            keyword=keyword,
            excluded_user_id=excluded_user_id,
            pipeline=aggregation_spec.pipeline,
            limit=aggregation_spec.limit,
            retry_count=resource_config.retry_count,
        )

        for attempt in range(1, max_attempts + 1):
            emit_debug_log(
                "mongo_connector.aggregate.attempt",
                resource_name=resource_name,
                model=model,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            try:
                documents: tuple[MongoDocument, ...] = await asyncio.to_thread(
                    execute_mongo_aggregation,
                    database=self._database,
                    aggregation_spec=aggregation_spec,
                )
            except Exception as exc:
                emit_debug_log(
                    "mongo_connector.aggregate.error",
                    resource_name=resource_name,
                    model=model,
                    query_params=query_params,
                    keyword=keyword,
                    excluded_user_id=excluded_user_id,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=repr(exc),
                )
                if attempt < max_attempts:
                    logger.warning(
                        "Mongo aggregation retry",
                        extra={
                            "resource_name": resource_name,
                            "collection": aggregation_spec.collection,
                            "model": model,
                            "query_params": query_params,
                            "keyword": keyword,
                            "excluded_user_id": excluded_user_id,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "pipeline": aggregation_spec.pipeline,
                            "limit": aggregation_spec.limit,
                            "error": repr(exc),
                        },
                    )
                    continue
                raise MongoAggregationExecutionError(
                    resource_name=resource_name,
                    collection=aggregation_spec.collection,
                    model=model,
                    limit=aggregation_spec.limit,
                    pipeline=aggregation_spec.pipeline,
                    original_error=exc,
                ) from exc

            print(f"[DEBUG mongo_connector] aggregation returned {len(documents)} documents")
            if documents:
                print(f"[DEBUG mongo_connector] first_document={documents[0]}")
            emit_debug_log(
                "mongo_connector.aggregate.result",
                resource_name=resource_name,
                model=model,
                count=len(documents),
                first_document=documents[0] if documents else None,
            )
            return MongoQueryResult(
                resource_name=resource_name,
                documents=documents,
                count=len(documents),
            )

        raise MongoAggregationExecutionError(
            resource_name=resource_name,
            collection=aggregation_spec.collection,
            model=model,
            limit=aggregation_spec.limit,
            pipeline=aggregation_spec.pipeline,
            original_error=None,
        )

    def close(self) -> None:
        self._client.close()


def validate_mongo_connector_configuration(
    mongodb_uri: str | None,
    mongodb_database: str | None,
    mongodb_resources_json: str | None,
) -> tuple[str, str, str] | None:
    if (
        mongodb_uri is None
        and mongodb_database is None
        and mongodb_resources_json is None
    ):
        return None
    if (
        mongodb_uri is None
        or mongodb_database is None
        or mongodb_resources_json is None
    ):
        raise MongoConfigurationError(
            "Mongo configuration is incomplete. "
            "MONGODB_URI, MONGODB_DATABASE and "
            "MONGODB_RESOURCES_JSON "
            "must be set together."
        )
    return mongodb_uri, mongodb_database, mongodb_resources_json


@lru_cache
def get_mongo_connector(
    mongodb_uri: str,
    mongodb_database: str,
    mongodb_resources_json: str,
) -> MongoConnector:
    registry: MongoResourceRegistry = build_mongo_resource_registry(
        mongodb_resources_json
    )
    return MongoConnector(
        mongodb_uri=mongodb_uri,
        mongodb_database=mongodb_database,
        registry=registry,
    )


def get_optional_mongo_connector(
    mongodb_uri: str | None,
    mongodb_database: str | None,
    mongodb_resources_json: str | None,
) -> MongoConnector | None:
    connector_configuration: tuple[str, str, str] | None = (
        validate_mongo_connector_configuration(
            mongodb_uri=mongodb_uri,
            mongodb_database=mongodb_database,
            mongodb_resources_json=mongodb_resources_json,
        )
    )
    if connector_configuration is None:
        return None

    (
        validated_mongodb_uri,
        validated_mongodb_database,
        validated_mongodb_resources_json,
    ) = connector_configuration
    return get_mongo_connector(
        mongodb_uri=validated_mongodb_uri,
        mongodb_database=validated_mongodb_database,
        mongodb_resources_json=validated_mongodb_resources_json,
    )


def execute_mongo_query(
    database: Database,
    query_spec: MongoQuerySpec,
) -> tuple[MongoDocument, ...]:
    collection: Collection = database[query_spec.collection]
    projection: dict[str, int] = build_mongo_projection(query_spec.projection_fields)
    cursor = collection.find(query_spec.query_filter, projection)
    if query_spec.sort:
        cursor = cursor.sort(list(query_spec.sort))
    cursor = cursor.limit(query_spec.limit)
    documents: list[MongoDocument] = []
    for document in cursor:
        documents.append(serialize_mongo_document(document))
    return tuple(documents)


def execute_mongo_aggregation(
    database: Database,
    aggregation_spec: MongoAggregationSpec,
) -> tuple[MongoDocument, ...]:
    collection: Collection = database[aggregation_spec.collection]
    cursor = collection.aggregate(list(aggregation_spec.pipeline))
    documents: list[MongoDocument] = []
    for document in cursor:
        documents.append(serialize_mongo_document(document))
    return tuple(documents)

from agentd.domain.types.mongo_types import MongoAggregationPipeline, MongoQueryFilter, MongoSortSpec


class MongoError(Exception):
    pass


class MongoConfigurationError(MongoError):
    pass


class MongoResourceNotFoundError(MongoError):
    def __init__(self, resource_name: str) -> None:
        super().__init__(f'Mongo resource not found: {resource_name}')


class MongoFilterFieldNotAllowedError(MongoError):
    def __init__(self, resource_name: str, field_name: str) -> None:
        super().__init__(
            f'Mongo filter field is not allowed: resource={resource_name}, field={field_name}'
        )


class MongoFilterValueError(MongoError):
    def __init__(self, resource_name: str, field_name: str, field_type: str, value: object) -> None:
        super().__init__(
            'Invalid Mongo filter value: '
            f'resource={resource_name}, field={field_name}, expected_type={field_type}, value={value!r}'
        )


class MongoLimitValueError(MongoError):
    def __init__(self, resource_name: str, limit: int) -> None:
        super().__init__(f'Invalid Mongo query limit: resource={resource_name}, limit={limit}')


class MongoQueryExecutionError(MongoError):
    def __init__(
        self,
        resource_name: str,
        collection: str,
        query_filter: MongoQueryFilter,
        projection_fields: tuple[str, ...],
        sort: MongoSortSpec,
        limit: int,
        original_error: Exception | None,
    ) -> None:
        original_error_message: str = repr(original_error) if original_error is not None else 'None'
        super().__init__(
            'Mongo query execution failed: '
            f'resource={resource_name}, '
            f'collection={collection}, '
            f'query_filter={query_filter}, '
            f'projection_fields={projection_fields}, '
            f'sort={sort}, '
            f'limit={limit}, '
            f'error={original_error_message}'
        )


class MongoAggregationExecutionError(MongoError):
    def __init__(
        self,
        resource_name: str,
        collection: str,
        model: str,
        limit: int,
        pipeline: MongoAggregationPipeline,
        original_error: Exception | None,
    ) -> None:
        original_error_message: str = repr(original_error) if original_error is not None else 'None'
        super().__init__(
            'Mongo aggregation execution failed: '
            f'resource={resource_name}, '
            f'collection={collection}, '
            f'model={model!r}, '
            f'limit={limit}, '
            f'pipeline={pipeline}, '
            f'error={original_error_message}'
        )

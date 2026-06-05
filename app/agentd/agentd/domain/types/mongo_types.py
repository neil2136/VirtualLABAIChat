from dataclasses import dataclass
from typing import Literal, TypeAlias

MongoFieldType: TypeAlias = Literal['string', 'int', 'float', 'bool']
MongoStringMatchMode: TypeAlias = Literal['exact', 'contains']
MongoQueryParamValue: TypeAlias = str | int | float | bool
MongoQueryParams: TypeAlias = dict[str, MongoQueryParamValue]
MongoPrimitiveValue: TypeAlias = str | int | float | bool | None
MongoQueryFilterValue: TypeAlias = MongoPrimitiveValue | dict[str, 'MongoQueryFilterValue'] | tuple['MongoQueryFilterValue', ...]
MongoQueryFilter: TypeAlias = dict[str, MongoQueryFilterValue]
MongoAggregationValue: TypeAlias = (
    MongoPrimitiveValue | dict[str, 'MongoAggregationValue'] | tuple['MongoAggregationValue', ...]
)
MongoAggregationStage: TypeAlias = dict[str, MongoAggregationValue]
MongoAggregationPipeline: TypeAlias = tuple[MongoAggregationStage, ...]
MongoValue: TypeAlias = MongoPrimitiveValue | tuple['MongoValue', ...] | dict[str, 'MongoValue']
MongoDocument: TypeAlias = dict[str, MongoValue]
MongoSortSpec: TypeAlias = tuple[tuple[str, Literal[-1, 1]], ...]


@dataclass(frozen=True, slots=True)
class MongoFilterFieldConfig:
    field_name: str
    document_path: str
    field_type: MongoFieldType
    string_match_mode: MongoStringMatchMode


@dataclass(frozen=True, slots=True)
class MongoResourceConfig:
    resource_name: str
    collection: str
    description: str
    filter_fields: dict[str, MongoFilterFieldConfig]
    filter_field_aliases: dict[str, str]
    projection_fields: tuple[str, ...]
    keyword_paths: tuple[str, ...]
    sort: MongoSortSpec
    limit: int
    retry_count: int


@dataclass(frozen=True, slots=True)
class MongoQuerySpec:
    resource_name: str
    collection: str
    query_filter: MongoQueryFilter
    projection_fields: tuple[str, ...]
    sort: MongoSortSpec
    limit: int


@dataclass(frozen=True, slots=True)
class MongoAggregationSpec:
    resource_name: str
    collection: str
    pipeline: MongoAggregationPipeline
    limit: int


@dataclass(frozen=True, slots=True)
class MongoQueryResult:
    resource_name: str
    documents: tuple[MongoDocument, ...]
    count: int

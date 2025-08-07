import operator
import warnings
from functools import cache, partial
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Union
from django.utils.module_loading import import_string
from returns.result import Result, Success, Failure
from rest_framework import pagination
from . import transactions
from .exceptions import Error
from .events import DomainEventBroker
from .models import AbstractRoot
from .filters import Criteria, Filters


TCriteria = TypeVar("TCriteria", bound=Criteria, covariant=True)
TAbstractRoot = TypeVar("TAbstractRoot", bound=AbstractRoot, covariant=True)


@dataclass
class NotFoundError(Error):
    code: str = "not_found"


class Pagination:
    """
    Adapts django pagination to reduce interface complexity.
    """
    
    def __init__(self, request = None):
        self._request = request
    
    def paginate_queryset(self, queryset) -> list:
        return super().paginate_queryset(queryset, self._request)


class CursorPagination(Pagination, pagination.CursorPagination):
    ordering: tuple[str] = None # No ordering by default, you can set it to any field names tuple


class PageNumberPagination(Pagination, pagination.PageNumberPagination): ...


class Repository(ABC, Generic[TAbstractRoot, TCriteria]):
    
    domain_events_broker: DomainEventBroker = DomainEventBroker.resolve()
    
    @classmethod
    @cache
    def resolve(cls, python_path: str) -> "Repository[TAbstractRoot, TCriteria]":
        repo_cls = import_string(python_path)
        if not issubclass(repo_cls, Repository):
            raise RuntimeError(f"Class {repo_cls} is not an implementation of Repository")
        return repo_cls
    
    @abstractmethod
    def get(self, criteria: TCriteria, for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]: ...
    
    @abstractmethod
    def get_by_id(self, id: str, for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]: ...
    
    @abstractmethod
    def find(self, criteria: TCriteria, pagination: Union[CursorPagination, PageNumberPagination]) -> Result[list[TAbstractRoot], NotFoundError | Error]: ...
    
    @abstractmethod
    def store(self, instance: TAbstractRoot) -> Result[TAbstractRoot, Error]: ...


class DjangoRepository(Repository[TAbstractRoot, Filters[TCriteria]]):
    """
    Baseclass with utils to implement django orm (querysets) based repositories
    """
    
    model: type[TAbstractRoot] = None
    
    def _get_queryset(self):
        return self.model.objects.all()
    
    def _load_instance(self, instance: TAbstractRoot) -> TAbstractRoot:
        return instance
    
    def _store_instance(self, instance: TAbstractRoot):
        instance.save()
    
    def get(self, criteria: Filters[TCriteria], for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]:
        
        if not criteria.data:
            return Failure(NotFoundError())
        
        queryset = self._get_queryset()
        
        if for_update:
            queryset = queryset.select_for_update()
            
        queryset = criteria.filter_queryset(queryset)
        instance = queryset.first()
        
        if instance is None:
            return Failure(NotFoundError(details=criteria.to_dict()))
        
        instance = self._load_instance(instance)
        
        return Success(instance)
    
    def get_by_id(self, id: str, for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]:
        try:
            queryset = self._get_queryset()
            
            if for_update:
                queryset = queryset.select_for_update()
            
            instance = queryset.get(id=id)
            instance = self._load_instance(instance)
            return Success(instance)
        except self.model.DoesNotExist:
            return Failure(NotFoundError())
    
    def find(self, criteria: Filters[TCriteria], pagination: Union[CursorPagination, PageNumberPagination]) -> Result[list[TAbstractRoot], NotFoundError | Error]:
        
        queryset = self._get_queryset()
        
        if isinstance(pagination, CursorPagination):
            pagination.ordering = criteria.values.order or pagination.ordering
        
        if criteria.data:
            queryset = criteria.filter_queryset(queryset)
        
        paginated_queryset = pagination.paginate_queryset(queryset)
        
        paginated_queryset = list(map(self._load_instance, paginated_queryset))
        
        return Success(paginated_queryset)
    
    @transactions.atomic
    def store(self, instance: TAbstractRoot) -> Result[TAbstractRoot, Error]:
        self._store_instance(instance)
        events = instance.pull_events()
        dispatch_events = partial(self.domain_events_broker.dispatch, events)
        transactions.transaction.on_commit(dispatch_events, robust=True)
        return Success(instance)


class InMemoryRepository(Repository[TAbstractRoot, Filters[TCriteria]]):
    """
    Works as an in-memory collection adapted to work with django pagination.
    Useful for testing purposes.
    """
    
    def __init__(self, instances: list[TAbstractRoot] = None):
        self._instances = list(instances or [])
    
    def __getitem__(self, item):
        return self._instances[item]
    
    def __len__(self):
        return len(self._instances)
    
    def _matches(self, instance: TAbstractRoot, filter_expr, filter_value) -> bool:
        try:
            suffix_based_filters = {
                '__lt': operator.lt,
                '__gt': operator.gt,
                '__lte': operator.le,
                '__gte': operator.ge,
                '__eq': operator.eq,
                '__exact': operator.eq,
                '__in': operator.contains
            }
            
            for suffix, op in suffix_based_filters.items():
                if filter_expr.endswith(suffix):
                    filter_expr = filter_expr.replace(suffix, '')
                    field_value = instance.get_field_value(filter_expr)
                    filter_value = instance.parse_field_value(filter_expr, filter_value)
                    return op(field_value, filter_value)
            
            field_value = instance.get_field_value(filter_expr)
            filter_value = instance.parse_field_value(filter_expr, filter_value)
            
            return operator.eq(field_value, filter_value)
        except ValueError:
            warnings.warn(
                f"Filters like '{filter_expr}' are not supported by default, maybe you would like to override '._matches(...)' "
                f"method at '{self.__class__.__name__}' to implement custom complex filters."
            )
            return False
    
    def filter(self, **filter_values):
        filters = lambda instance: all(
            self._matches(instance, filter_name, filter_value) for filter_name, filter_value in filter_values.items()
        )
        results = filter(filters, self._instances)
        return InMemoryRepository(results)
    
    def order_by(self, *ordering_fields):
        result = self._instances
        # Stable sort like python's "sorted(...)" is required to avoid changing the order of the same elements
        for ordering_field in reversed(ordering_fields):
            reverse = ordering_field.startswith("-")
            ordering_field = ordering_field.lstrip("-+")
            ordering_field_value = lambda instance: instance.get_field_value(ordering_field)
            result = sorted(result, key=ordering_field_value, reverse=reverse)
        return InMemoryRepository(result)
    
    def get(self, criteria: Filters[TCriteria], for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]:
        
        if not criteria.data:
            return Failure(NotFoundError())
        
        instances = self.filter(**criteria.expressions_values)
        
        if not instances:
            return Failure(NotFoundError())
        
        return Success(instances[0])
    
    def get_by_id(self, id: str, for_update: bool = False) -> Result[TAbstractRoot, NotFoundError]:
        try:
            instance = next(filter(lambda instance: instance.id == id, self._instances))
            return Success(instance)
        except StopIteration:
            return Failure(NotFoundError())
    
    def find(self, criteria: Filters[TCriteria], pagination: Pagination) -> Result[list[TAbstractRoot], NotFoundError | Error]:
        
        filtered = self.filter(**criteria.expressions_values)
        
        if isinstance(pagination, CursorPagination):
            pagination.ordering = criteria.values.order or pagination.ordering
        else:
            filtered = filtered.order_by(*criteria.values.order)
        
        paginated = pagination.paginate_queryset(filtered)
        
        return Success(paginated)
    
    def store(self, instance: TAbstractRoot) -> Result[TAbstractRoot, Error]:
        self._instances.append(instance)
        events = instance.pull_events()
        self.domain_events_broker.dispatch(events)
        return Success(instance)

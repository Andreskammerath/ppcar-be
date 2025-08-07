from uuid import UUID
from functools import cached_property
from typing import Generic, Union, TypeVar, Iterator, Optional, Any, get_origin, get_args
from decimal import Decimal
from datetime import datetime, date
from dataclasses import dataclass, is_dataclass
from django_filters import FilterSet, filters


TCriteria = TypeVar('TCriteria', bound="Criteria", covariant=True)


def is_optional_type(given_type: type) -> bool:
    origin = get_origin(given_type)
    if origin is Union:
        args = get_args(given_type)
        return type(None) in args
    return False


def get_all_annotations(cls):
    annotations = {}
    for base in reversed(cls.__mro__):
        annotations.update(getattr(base, '__annotations__', {}))
    return annotations


class Ordering(tuple[str, ...]): ...


@dataclass(frozen=True)
class Criteria:
    """ Filtering and ordering criteria supported by the repository. """
    
    order: Optional[Ordering] = None
    
    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class Filters(Generic[TCriteria], FilterSet, Criteria):
    """ Builds valid django-filters from a given criteria dynamically. """
    
    _model = None
    _criteria_type: type[TCriteria] = None
    
    class UUIDListFilter(filters.BaseInFilter, filters.UUIDFilter): ...
    class CharListFilter(filters.BaseInFilter, filters.CharFilter): ...
    class NumericListFilter(filters.BaseInFilter, filters.NumberFilter): ...
    class DateListFilter(filters.BaseInFilter, filters.DateFilter): ...
    class DateTimeListFilter(filters.BaseInFilter, filters.IsoDateTimeFilter): ...
    class BooleanListFilter(filters.BaseInFilter, filters.BooleanFilter): ...
    
    def __init__(self, *args, **kwargs):
        self._model = kwargs.pop('_model', self._model)
        self._criteria_type = kwargs.pop('_criteria_type', self._criteria_type)
        
        if self._model:
            kwargs.setdefault('queryset', self._model.objects.none())
        
        super().__init__(*args, **kwargs)
    
    def _create_criteria(self, dataclass_type, filters_dict, prefix='') -> TCriteria:
        """
        Create an instance of dataclass_type using values from filters_dict.
        Handles nested dataclasses recursively.
        """
        
        kwargs = {}
        
        for field_name, field_type in get_all_annotations(dataclass_type).items():
            
            key = f"{prefix}{field_name}"
            
            if is_optional_type(field_type):
                field_type = get_args(field_type)[0]
            
            if is_dataclass(field_type):
                value = self._create_criteria(field_type, filters_dict, prefix=f"{key}_")
                kwargs[field_name] = value
            elif key in filters_dict:
                kwargs[field_name] = field_type(filters_dict[key])
        
        if not kwargs:
            return None
        
        return dataclass_type(**kwargs)
    
    @classmethod
    def numeric_filter(cls, field_name: str) -> filters.Filter:
        
        suffixes = {
            "_min": "gte",
            "_max": "lte",
            "_emin": "gt",
            "_emax": "lt",
        }
        
        for suffix, lookup_expr in suffixes.items():
            if field_name.endswith(suffix):
                field_name = field_name.replace(suffix, '')
                return filters.NumberFilter(field_name=field_name, lookup_expr=lookup_expr)
        
        return filters.NumberFilter(field_name=field_name)
    
    @classmethod
    def datetime_filter(cls, field_name: str) -> filters.IsoDateTimeFilter:
        
        suffixes = {
            "_after": "gt",
            "_before": "lt",
            "_iafter": "gte",
            "_ibefore": "lte",
        }
        
        for suffix, lookup_expr in suffixes.items():
            if field_name.endswith(suffix):
                field_name = field_name.replace(suffix, '')
                return filters.IsoDateTimeFilter(field_name=field_name, lookup_expr=lookup_expr)
        
        return filters.IsoDateTimeFilter(field_name=field_name)
    
    @classmethod
    def date_filter(cls, field_name: str) -> filters.DateFilter:
        
        suffixes = {
            "_after": "gt",
            "_before": "lt",
            "_iafter": "gte",
            "_ibefore": "lte",
        }
        
        for suffix, lookup_expr in suffixes.items():
            if field_name.endswith(suffix):
                field_name = field_name.replace(suffix, '')
                return filters.DateFilter(field_name=field_name, lookup_expr=lookup_expr)
        
        return filters.DateFilter(field_name=field_name)
    
    @classmethod
    def ordering_filter(cls, ordering_fields: set[str]) -> filters.OrderingFilter:
        return filters.OrderingFilter(fields=ordering_fields)
    
    @staticmethod
    def filterset_to_dict(filterset: FilterSet) -> dict[str, Any]:
        return { name: value for name, value in filterset.form.cleaned_data.items() if value is not None }
    
    @classmethod
    def expand_fields(cls, fields_types: dict[str, type], prefix: str = '') -> Iterator[tuple[str, Any]]:
        
        for field, field_type in fields_types.items():
            
            if field.startswith('_'):
                continue
            
            if field.startswith(prefix):
                field = field.replace(prefix, '', 1)
            
            if is_optional_type(field_type):
                field_type = get_args(field_type)[0]
            
            if is_dataclass(field_type):
                annotations = get_all_annotations(field_type)
                yield from cls.expand_fields(annotations, prefix=f'{prefix}{field}_')
            else:
                yield f'{prefix}{field}', field_type
    
    @classmethod
    def from_criteria(cls, criteria: type[TCriteria], filters_kwargs: dict[str, Any] = {}, _model = None) -> type["Filters[TCriteria]"]:
        
        filter_mappings = {
            str: filters.CharFilter,
            UUID: filters.UUIDFilter,
            bool: filters.BooleanFilter,
            date: cls.date_filter,
            datetime: cls.datetime_filter,
            int: cls.numeric_filter,
            float: cls.numeric_filter,
            Decimal: cls.numeric_filter,
            list[str]: cls.CharListFilter,
            list[int]: cls.NumericListFilter,
            list[float]: cls.NumericListFilter,
            list[Decimal]: cls.NumericListFilter,
            list[UUID]: cls.UUIDListFilter,
            list[date]: cls.DateListFilter,
            list[datetime]: cls.DateTimeListFilter,
            list[bool]: cls.BooleanListFilter,
        }
        
        filterset = {}
        all_fields = get_all_annotations(criteria)
        filtering_fields = { field: field_type for field, field_type in all_fields.items() if field_type != Optional[Ordering] }
        
        for field, field_type in cls.expand_fields(filtering_fields):
            
            if not field_type in filter_mappings:
                raise ValueError(f"Unsupported filtering type: '{field_type}' for field '{field}'")
            
            filter_class = filter_mappings[field_type]
            filter_kwargs = filters_kwargs.get(field, {})
            filterset[field] = filter_class(**filter_kwargs, field_name=field)
        
        has_ordering = Optional[Ordering] in all_fields.values()
        
        if has_ordering:
            unique_fields = set(field.field_name for field in filterset.values())
            filterset['order'] = cls.ordering_filter(ordering_fields=unique_fields)
        
        filterset['_model'] = _model
        filterset['_criteria_type'] = criteria
        filterset['to_dict'] = cls.filterset_to_dict
        
        return type(f'Filters[{criteria.__name__}]', (cls,), filterset)
    
    @cached_property
    def values(self) -> TCriteria:
        if not self.is_valid():
            raise ValueError("Can't build criteria from invalid filters, check .is_valid() first.")
        return self._create_criteria(self._criteria_type, filters_dict=self.to_dict())

    @cached_property
    def expressions_values(self) -> dict[str, Any]:
        vals = self.values.to_dict()
        expressions = {
            f"{f.field_name}__{f.lookup_expr}": vals[raw_name] for raw_name, f in self.filters.items()
            if raw_name in vals
            and not isinstance(vals[raw_name], Ordering)
            and vals[raw_name] is not None
        }
        return expressions

import uuid
from typing import Any, Optional
from django.db import models
from .events import DomainEvent


class Entity(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    @classmethod
    def new_id(cls) -> uuid.UUID:
        return uuid.uuid4()
    
    @classmethod
    def get_field(cls, field_lookup: str, instance: Optional["Entity"] = None) -> tuple[Optional["Entity"], models.Field]:
        
        field = None
        
        for part in field_lookup.split('__'):
            field = cls._meta.get_field(part)
            
            if not field.is_relation or not hasattr(field, 'related_model'):
                break
            
            cls = field.related_model
            
            if not hasattr(field, 'value_from_object'):
                raise ValueError(f"Field '{field_lookup}' doen't point to an Entity")
            
            if instance:
                instance = field.value_from_object(instance)
        
        return instance, field
    
    @classmethod
    def parse_field_value(cls, field_lookup: str, value: Any) -> Any:
        _, field = cls.get_field(field_lookup)
        return field.to_python(value)
    
    def get_field_value(self, field_lookup: str) -> Any:
        model_instance, field = self.get_field(field_lookup, instance=self)
        return field.value_from_object(model_instance) # type: ignore
    
    class Meta:
        abstract = True


class AbstractRoot(Entity):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._domain_events: list[DomainEvent] = []
    
    def pull_events(self) -> list[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
    
    class Meta:
        abstract = True

from uuid import uuid4
from warnings import warn
from logging import Logger, getLogger
from functools import cache
from typing import Callable, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from django.conf import settings
from django.dispatch import Signal
from django.utils import timezone
from django.utils.module_loading import import_string
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class DomainEvent:
    id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=timezone.now)


def event_listener(event_class: Type[DomainEvent]) -> Callable:
    """
    Helper decorator to register an event listener.
    """
    def wrapper(func: Callable) -> Callable:
        broker = DomainEventBroker.resolve()
        broker.register_listener(event_class, func)
        return func
    return wrapper


class DomainEventBroker(ABC):
    """
    Base class for all domain event brokers.
    """
    
    if not hasattr(settings, "DOMAIN_EVENTS_BROKER"):
        raise ImproperlyConfigured("DOMAIN_EVENTS_BROKER setting is not configured yet")
    
    @cache
    @staticmethod
    def resolve(python_path: str = settings.DOMAIN_EVENTS_BROKER) -> "DomainEventBroker":
        broker_cls = import_string(python_path)
        if not issubclass(broker_cls, DomainEventBroker):
            raise RuntimeError(f"Class {broker_cls} is not an implementation of DomainEventBroker")
        return broker_cls()
    
    @abstractmethod
    def register_listener(self, event_class: Type[DomainEvent], listener: Callable):
        ...
    
    @abstractmethod
    def dispatch(self, event: DomainEvent):
        ...


class DjangoSignalDomainEventBroker(DomainEventBroker):
    """
    Domain event broker using Django signals backend.
    """
    
    def __init__(self, logger: Logger = getLogger("domain-events")):
        self._signals = {}
        self._logger = logger
    
    def register_listener(self, event_class: Type[DomainEvent], listener: Callable):
        if not event_class in self._signals:
            self._signals[event_class] = Signal(["event"])
        self._signals[event_class].connect(listener, sender=event_class)
    
    def dispatch(self, events: list[DomainEvent]):
        
        for event in events:
            try:
                signal = self._signals.get(type(event))
                
                if signal is None:
                    warn(f"No signal registered for event {event.__class__.__name__}")
                    continue
                
                signal.send(sender=event.__class__, event=event)
            except Exception as e:
                self._logger.exception(e)


class InMemoryDomainEventBroker(DomainEventBroker):
    """
    Emulates a domain event broker using an in-memory dictionary.
    Useful for testing purposes.
    """
    
    def __init__(self, logger: Logger = getLogger("domain-events"), call_listeners: bool = False):
        self._logger = logger
        self._listeners = {}
        self._dispatched_events = []
        self._call_listeners = call_listeners
    
    def register_listener(self, event_class: Type[DomainEvent], listener: Callable):
        if not event_class in self._listeners:
            self._listeners[event_class] = []
        self._listeners[event_class].append(listener)
    
    def dispatch(self, events: list[DomainEvent]):
        for event in events:
            self._dispatched_events.append(event)
            if self._call_listeners:
                for listener in self._listeners.get(type(event), []):
                    try:
                        listener(event)
                    except Exception as e:
                        self._logger.exception(e)
    
    def dispatched_event(self, event: DomainEvent) -> bool:
        return event in self._dispatched_events

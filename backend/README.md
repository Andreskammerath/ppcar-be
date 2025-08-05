# Blacar Backend

A Django-based backend following Domain-Driven Design (DDD) principles for the Blacar ride-sharing platform.

## 🏗️ Architecture Overview

This backend is structured following Domain-Driven Design principles with clear separation of concerns:

```
backend/
├── blacar/                 # Django project root
│   ├── startup/           # Domain layer (DDD bounded contexts)
│   │   ├── shared/        # Shared kernel - common domain utilities
│   │   └── accounts/      # Accounts bounded context
│   ├── api/               # Application layer (REST API)
│   └── blacar/            # Infrastructure layer (Django settings)
├── pyproject.toml         # Dependencies and project config
└── README.md             # This file
```

## 🎯 Domain-Driven Design Structure

### 1. Domain Layer (`startup/`)

The domain layer contains the core business logic organized into bounded contexts:

#### Shared Kernel (`startup/shared/`)

Common utilities and patterns used across all bounded contexts:

- **`models.py`** - Base domain entities and value objects
- **`repository.py`** - Repository pattern implementation
- **`events.py`** - Domain event system
- **`exceptions.py`** - Domain-specific exceptions
- **`filters.py`** - Query filtering and criteria
- **`transactions.py`** - Transaction management
- **`images.py`** - Image handling utilities

#### Bounded Contexts (`startup/{context_name}/`)

Each bounded context represents a cohesive business domain:

- **`accounts/`** - User management and authentication
- **Future contexts**: `trips/`, `payments/`, `notifications/`, etc.

### 2. Application Layer (`api/`)

The application layer handles use cases and coordinates between the domain and infrastructure:

- **`views/`** - REST API endpoints
- **`urls.py`** - URL routing
- **`router.py`** - API router configuration

### 3. Infrastructure Layer (`blacar/`)

Django-specific configuration and infrastructure concerns:

- **`settings.py`** - Django settings
- **`urls.py`** - Main URL configuration
- **`wsgi.py`** / **`asgi.py`** - WSGI/ASGI entry points

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- uv (dependency management)

### Installation

1. **Clone the repository and navigate to backend:**

   ```bash
   cd backend
   ```

2. **Install dependencies:**

   ```bash
   uv sync
   ```

3. **Activate the virtual environment:**

   ```bash
   uv shell
   ```

4. **Run migrations:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser:**

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

## 📋 How to Implement Features Following DDD

### Step 1: Define the Bounded Context

First, identify which bounded context your feature belongs to or create a new one:

```bash
mkdir startup/your_context
touch startup/your_context/__init__.py
touch startup/your_context/models.py
touch startup/your_context/repositories.py
touch startup/your_context/features.py
touch startup/your_context/events.py
```

### Step 2: Create Domain Models

Define your domain entities in `startup/your_context/models.py`:

```python
from startup.shared.exceptions import ValidationError
from startup.shared.models import AbstractRoot
from startup.shared.events import DomainEvent
from dataclasses import dataclass
from datetime import datetime
from returns.result import safe, Result, Success, Failure


@dataclass(frozen=True)
class YourEntityCreated(DomainEvent):
    entity_id: str
    name: str

class YourEntity(AbstractRoot):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    @safe(exceptions=ValidationError)
    def create(cls, name: str, description: str = "") -> Result["YourEntity", ValidationError]:
        entity = cls(name=name, description=description)
        entity.full_clean()
        # Add more logic and return ValidationError(...) if needed
        entity._domain_events.append(
            YourEntityCreated(entity_id=str(entity.id), name=name)
        )
        return Success(entity)

    @safe(exceptions=ValidationError)
    def update(self, **fields) -> Result["YourEntity", ValidationError]:
        self.name = fields['name']
        self.full_clean()
        return Success(self)
        # Add domain events as needed
```

### Step 3: Create Repository

Implement the repository pattern in `startup/your_context/repositories.py`:

```python
from startup.shared.repository import DjangoRepository, Filters
from startup.shared.filters import Criteria
from .models import YourEntity

class YourEntityCriteria(Criteria):
    id: str = None
    name: str = None
    created_after: datetime = None

class YourEntityRepository(DjangoRepository[YourEntity, YourEntityCriteria]):
    model = YourEntity

    def _get_queryset(self):
        return self.model.objects.all()
```

### Step 4: Create Feature-Based Classes

Define use cases in `startup/your_context/features.py`:

```python
from returns.result import Result, Success, Failure
from startup.shared.exceptions import Error
from .models import YourEntity
from .repositories import YourEntityRepository, YourEntityCriteria

class CreateYourEntity:
    """Feature: Create a new entity with validation and event dispatching"""

    def __init__(self, repository: YourEntityRepository):
        self.repository = repository

    def execute(self, name: str, description: str = "") -> Result[YourEntity, Error]:
        return (
            YourEntity.create(name=name, description=description)
                .bind(lambda new_instance: self.repository.store(new_instance))
        )


class UpdateYourEntityName:
    """Feature: Update an existing entity's name"""

    def __init__(self, repository: YourEntityRepository):
        self.repository = repository

    def execute(self, entity_id: str, name: str = None) -> Result[YourEntity, Error]:
        search_criteria = YourEntityCriteria(id=entity_id)
        return (
            self.repository.get(search_criteria) # or simply use .get_by_id(entity_id) instead
                .bind(lambda entity: entity.update_name(name))
        )
```

### Step 5: Create API Views

Implement REST endpoints in `api/views/your_context.py`:

```python
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from startup.shared.exceptions import ValidationError
from startup.your_context.features import CreateYourEntity, UpdateYourEntity
from startup.your_context.repositories import YourEntityRepository
from returns.result import Success, Failure

class YourEntityViewSet(ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = YourEntityRepository()
        self.create_feature = CreateYourEntity(self.repository)
        self.update_feature = UpdateYourEntityName(self.repository)

    @action(detail=False, methods=['post'])
    def create_entity(self, request):
        name = request.data.get('name')
        description = request.data.get('description', '')

        match self.create_feature.execute(name=name, description=description):

            case Success(entity):
                return Response({
                    'id': str(entity.id),
                    'name': entity.name,
                    'description': entity.description,
                    'updated_at': entity.updated_at
                }, status=status.HTTP_201_CREATED)

            case ValidationError() as error:
                return Response(
                    {'error': error.message},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(detail=True, methods=['put'])
    def update_entity(self, request, pk=None):

        name = request.data.get('name')

        match self.update_feature.execute(entity_id=pk, name=name):

            case Success(entity):
                return Response({
                    'id': str(entity.id),
                    'name': entity.name,
                    'description': entity.description,
                    'updated_at': entity.updated_at
                }, status=status.HTTP_200_OK)

            case ValidationError() as error:
                return Response(
                    {'error': error.message},
                    status=status.HTTP_400_BAD_REQUEST
                )
```

### Step 6: Register URLs

Add your views to the API router in `api/router.py`:

```python
from rest_framework.routers import DefaultRouter
from .views.your_context import YourEntityViewSet

router = DefaultRouter()
router.register(r'your-entities', YourEntityViewSet, basename='your-entity')
```

### Step 7: Handle Domain Events

Create event listeners in `startup/your_context/events.py`:

```python
from startup.shared.events import event_listener
from .models import YourEntityCreated

@event_listener(YourEntityCreated)
def handle_entity_created(event: YourEntityCreated):
    # Handle the domain event
    # e.g., send notifications, update analytics, etc.
    print(f"Entity {event.entity_id} with name '{event.name}' was created")
```

## 🔧 Key DDD Patterns Used

### 1. Repository Pattern

- **Purpose**: Abstract data access and provide a collection-like interface
- **Implementation**: `startup/shared/repository.py`
- **Usage**: Encapsulate data access logic and provide domain-friendly interfaces

### 2. Domain Events

- **Purpose**: Decouple domain logic and enable side effects
- **Implementation**: `startup/shared/events.py`
- **Usage**: Notify other parts of the system about domain changes

### 3. Entity Pattern

- **Purpose**: Represent domain objects with identity
- **Implementation**: `startup/shared/models.py`
- **Usage**: Base classes for domain entities with UUID primary keys

### 4. Value Objects

- **Purpose**: Represent immutable concepts in the domain
- **Implementation**: Dataclasses with frozen=True
- **Usage**: Represent concepts like money, dates, addresses

### 5. Aggregate Pattern

- **Purpose**: Ensure consistency boundaries
- **Implementation**: AbstractRoot class
- **Usage**: Group related entities and ensure business rules

### 6. Railway-Oriented Programming

- **Purpose**: Handle errors functionally without try-catch blocks
- **Implementation**: `returns` library with `.bind()`, `.map()`, and `.alt()`
- **Usage**: Chain operations that can fail, with automatic error propagation

### 7. Feature-Based Classes

- **Purpose**: Group related functionality into cohesive business features
- **Implementation**: Classes with single `execute()` method per feature
- **Usage**: Encapsulate complete use cases with validation, business logic, and side effects

#### Feature-Based Classes Explained

Feature-based classes follow the Command pattern and encapsulate complete business use cases:

```python
# Instead of a service with multiple methods:
class UserService:
    def create_user(self, email: str, name: str) -> Result[User, Error]: ...
    def update_user(self, user_id: str, name: str) -> Result[User, Error]: ...
    def delete_user(self, user_id: str) -> Result[None, Error]: ...

# Use feature-based classes:
class CreateUser:
    def execute(self, email: str, name: str) -> Result[User, Error]: ...

class UpdateUser:
    def execute(self, user_id: str, name: str) -> Result[User, Error]: ...

class DeleteUser:
    def execute(self, user_id: str) -> Result[None, Error]: ...
```

**Benefits:**

- **Single Responsibility**: Each class handles one specific feature
- **Better Testability**: Test each feature in isolation
- **Clear Intent**: Class names clearly express business intent
- **Easier Maintenance**: Changes to one feature don't affect others
- **Better Composition**: Features can be easily composed or reused

#### Railway Approach Explained

The railway approach treats your code as a railway track with two paths:

- **Success track**: Operations succeed and continue
- **Failure track**: Operations fail and skip subsequent steps

```python
from returns.result import Result, Success, Failure

# Instead of nested try-catch blocks:
def traditional_approach(data):
    try:
        result1 = operation1(data)
        try:
            result2 = operation2(result1)
            try:
                result3 = operation3(result2)
                return Success(result3)
            except Exception as e:
                return Failure(e)
        except Exception as e:
            return Failure(e)
    except Exception as e:
        return Failure(e)

# Use railway approach with dot methods:
def railway_approach(data):
    return (
        operation1(data)  # Returns Result[T, E]
        .bind(operation2)  # Binds to success track, skips on failure
        .bind(operation3)  # Binds to success track, skips on failure
    )
```

**Key Methods:**

- `.bind()`: Chains operations that return `Result` types
- `.map()`: Transforms success values without changing the Result type
- `.alt()`: Transforms failure values
- `.rescue()`: Recovers from failures
- `.value_or()`: Extracts value or returns default

#### Advanced Railway Example

```python
from returns.result import Result, Success, Failure

def create_user_with_fallback(email: str, name: str) -> Result[User, Error]:
    return (
        create_user(email, name)
        .rescue(lambda error: create_user_with_defaults(email, name))
        .map(add_user_metadata)
        .alt(log_and_return_default_error)
    )

def create_user(email: str, name: str) -> Result[User, Error]:
    # Implementation that might fail
    pass

def create_user_with_defaults(email: str, name: str) -> Result[User, Error]:
    # Fallback implementation
    pass

def add_user_metadata(user: User) -> User:
    # Transformation that can't fail
    user.metadata = {"created_via": "fallback"}
    return user

def log_and_return_default_error(error: Error) -> Error:
    # Error transformation
    logger.error(f"User creation failed: {error}")
    return Error(code="user_creation_failed", message="Unable to create user")
```

## 🧪 Testing

### Running Tests

```bash
python manage.py test
```

### Test Structure

Follow the same structure as your domain:

```
tests/
├── test_your_context/
│   ├── test_models.py
│   ├── test_repositories.py
│   ├── test_services.py
│   └── test_events.py
```

## 📚 Best Practices

### 1. Domain Modeling

- Keep domain models focused on business logic
- Use rich domain models with behavior, not just data
- Implement business rules in the domain layer

### 2. Repository Implementation

- Return `Result` types for error handling
- Use criteria objects for complex queries
- Implement both Django and in-memory repositories for testing

### 3. Railway-Oriented Programming

- Use `.bind()` method chaining instead of try-catch blocks
- Break complex operations into small, composable functions
- Let errors propagate automatically through the railway
- Use `.map()` for transformations that can't fail
- Use `.alt()` or `.rescue()` for error recovery when needed

### 4. Feature-Based Classes

- Create one class per business feature (e.g., `CreateUser`, `UpdateUser`)
- Use descriptive class names that reflect the business intent
- Implement a single `execute()` method per feature class
- Include validation, business logic, and side effects in the feature
- Keep features focused and cohesive

### 5. Event Handling

- Keep event handlers lightweight
- Use events for side effects, not core business logic
- Implement event sourcing when needed for audit trails

### 6. API Design

- Use ViewSets for CRUD operations
- Implement proper error handling and status codes
- Keep API layer thin - delegate to feature classes

### 7. Testing

- Test domain logic in isolation
- Use in-memory repositories for fast unit tests
- Test domain events and their handlers
- Test each feature class independently

## 🔍 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
DOMAIN_EVENTS_BROKER=startup.shared.events.DjangoSignalDomainEventBroker
```

### Django Settings

Key DDD-related settings in `blacar/settings.py`:

```python
# Domain Events Configuration
DOMAIN_EVENTS_BROKER = 'startup.shared.events.DjangoSignalDomainEventBroker'

# Custom User Model
AUTH_USER_MODEL = 'startup.User'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

## 🤝 Contributing

1. Follow DDD principles when adding new features
2. Write tests for domain logic
3. Use type hints throughout the codebase
4. Follow the existing code structure and patterns
5. Document complex business rules and domain concepts

## 📖 Additional Resources

- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
- [Implementing Domain-Driven Design by Vaughn Vernon](https://www.oreilly.com/library/view/implementing-domain-driven-design/9780133039900/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)

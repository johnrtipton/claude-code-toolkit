# Advanced Typing Patterns for Django

A comprehensive guide to advanced Python typing features with Django-specific examples.

## Table of Contents

1. [Generics and TypeVars](#generics-and-typevars)
2. [Protocols for Structural Typing](#protocols-for-structural-typing)
3. [TypedDict](#typeddict)
4. [Type Guards and Narrowing](#type-guards-and-narrowing)
5. [Literal Types and Enums](#literal-types-and-enums)
6. [Union Types and Type Aliases](#union-types-and-type-aliases)
7. [Callable Types and Decorators](#callable-types-and-decorators)
8. [Generic Classes and Methods](#generic-classes-and-methods)
9. [Runtime Type Checking](#runtime-type-checking)
10. [Advanced Mypy Features](#advanced-mypy-features)

---

## Generics and TypeVars

### Basic TypeVar

TypeVars allow you to create generic functions and classes that work with multiple types while maintaining type safety.

```python
from typing import TypeVar, List, Optional
from django.db import models

T = TypeVar('T')

def first_or_none(items: List[T]) -> Optional[T]:
    """Get the first item from a list or None if empty."""
    return items[0] if items else None

# Usage with Django models
users: List[User] = list(User.objects.all())
first_user: Optional[User] = first_or_none(users)  # Type is inferred correctly
```

### Bounded TypeVars

Bounded TypeVars restrict the types that can be used to specific base classes.

```python
from typing import TypeVar, List
from django.db import models

# Only accept Django Model subclasses
ModelT = TypeVar('ModelT', bound=models.Model)

def bulk_create_with_logging(
    model_class: type[ModelT],
    instances: List[ModelT]
) -> List[ModelT]:
    """Bulk create instances with logging."""
    created = model_class.objects.bulk_create(instances)
    print(f"Created {len(created)} {model_class.__name__} instances")
    return created

# Usage
users = [User(username=f"user{i}") for i in range(10)]
created_users: List[User] = bulk_create_with_logging(User, users)
```

### Constrained TypeVars

Constrained TypeVars limit types to a specific set of allowed types.

```python
from typing import TypeVar, Union
from django.contrib.auth.models import User, Group
from django.db import models

# Only User or Group allowed
UserOrGroup = TypeVar('UserOrGroup', User, Group)

def get_permissions_count(obj: UserOrGroup) -> int:
    """Get permission count for User or Group."""
    if isinstance(obj, User):
        return obj.user_permissions.count() + sum(
            g.permissions.count() for g in obj.groups.all()
        )
    else:
        return obj.permissions.count()

# Type checker ensures only User or Group can be passed
user = User.objects.first()
group = Group.objects.first()
count1: int = get_permissions_count(user)   # OK
count2: int = get_permissions_count(group)  # OK
# get_permissions_count("invalid")  # Type error!
```

### Covariance and Contravariance

Understanding variance is crucial for generic types in inheritance hierarchies.

```python
from typing import TypeVar, Generic, List
from django.db import models

# Covariant TypeVar (for return types)
T_co = TypeVar('T_co', covariant=True)

# Contravariant TypeVar (for parameter types)
T_contra = TypeVar('T_contra', contravariant=True)

class QuerySetWrapper(Generic[T_co]):
    """Wrapper that returns instances (covariant)."""

    def __init__(self, qs: models.QuerySet[T_co]) -> None:
        self._qs = qs

    def get(self) -> T_co:
        return self._qs.first()

    def all(self) -> List[T_co]:
        return list(self._qs)

class Validator(Generic[T_contra]):
    """Validator that accepts instances (contravariant)."""

    def validate(self, obj: T_contra) -> bool:
        """Validate an object."""
        raise NotImplementedError

# Covariance example
class Animal(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        abstract = True

class Dog(Animal):
    breed = models.CharField(max_length=100)

    class Meta:
        app_label = 'myapp'

# Covariant: QuerySetWrapper[Dog] is a subtype of QuerySetWrapper[Animal]
dog_wrapper: QuerySetWrapper[Dog] = QuerySetWrapper(Dog.objects.all())
animal_wrapper: QuerySetWrapper[Animal] = dog_wrapper  # OK (covariant)

# Contravariant: Validator[Animal] is a subtype of Validator[Dog]
animal_validator: Validator[Animal] = Validator()
dog_validator: Validator[Dog] = animal_validator  # OK (contravariant)
```

### Multiple TypeVars

Use multiple TypeVars for complex generic relationships.

```python
from typing import TypeVar, Dict, Tuple
from django.db import models

K = TypeVar('K')
V = TypeVar('V')
ModelT = TypeVar('ModelT', bound=models.Model)

def group_by_field(
    queryset: models.QuerySet[ModelT],
    field_name: str
) -> Dict[K, List[ModelT]]:
    """Group queryset instances by a field value."""
    result: Dict[K, List[ModelT]] = {}
    for obj in queryset:
        key: K = getattr(obj, field_name)
        if key not in result:
            result[key] = []
        result[key].append(obj)
    return result

# Usage
users_by_country: Dict[str, List[User]] = group_by_field(
    User.objects.all(),
    'country'
)
```

### Generic Django Repositories

Implementing the repository pattern with generics.

```python
from typing import TypeVar, Generic, Optional, List, Type
from django.db import models
from django.db.models import Q

ModelT = TypeVar('ModelT', bound=models.Model)

class Repository(Generic[ModelT]):
    """Generic repository for Django models."""

    def __init__(self, model_class: Type[ModelT]) -> None:
        self.model_class = model_class

    def get_by_id(self, id: int) -> Optional[ModelT]:
        """Get instance by ID."""
        try:
            return self.model_class.objects.get(pk=id)
        except self.model_class.DoesNotExist:
            return None

    def filter(self, **kwargs) -> List[ModelT]:
        """Filter instances."""
        return list(self.model_class.objects.filter(**kwargs))

    def create(self, **kwargs) -> ModelT:
        """Create a new instance."""
        return self.model_class.objects.create(**kwargs)

    def update(self, instance: ModelT, **kwargs) -> ModelT:
        """Update an instance."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: ModelT) -> None:
        """Delete an instance."""
        instance.delete()

    def search(self, query: str, *fields: str) -> List[ModelT]:
        """Search across multiple fields."""
        q = Q()
        for field in fields:
            q |= Q(**{f"{field}__icontains": query})
        return list(self.model_class.objects.filter(q))

# Usage
user_repo: Repository[User] = Repository(User)
user: Optional[User] = user_repo.get_by_id(1)
active_users: List[User] = user_repo.filter(is_active=True)
new_user: User = user_repo.create(username="newuser", email="new@example.com")
```

---

## Protocols for Structural Typing

Protocols enable structural subtyping (duck typing with static type checking).

### Basic Protocol

```python
from typing import Protocol
from django.db import models

class Timestamped(Protocol):
    """Protocol for models with timestamp fields."""
    created_at: models.DateTimeField
    updated_at: models.DateTimeField

def get_recent_items(items: List[Timestamped], days: int = 7) -> List[Timestamped]:
    """Get items created in the last N days."""
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=days)
    return [item for item in items if item.created_at >= cutoff]

# Any model with created_at and updated_at satisfies the protocol
class Article(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Comment(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Both work with get_recent_items
articles: List[Article] = get_recent_items(list(Article.objects.all()))
comments: List[Comment] = get_recent_items(list(Comment.objects.all()))
```

### Protocol with Methods

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Publishable(Protocol):
    """Protocol for models that can be published."""

    is_published: bool
    published_at: Optional[models.DateTimeField]

    def publish(self) -> None:
        """Publish the item."""
        ...

    def unpublish(self) -> None:
        """Unpublish the item."""
        ...

def publish_items(items: List[Publishable]) -> int:
    """Publish multiple items and return count."""
    count = 0
    for item in items:
        if not item.is_published:
            item.publish()
            count += 1
    return count

# Implementation
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def publish(self) -> None:
        from django.utils import timezone
        self.is_published = True
        self.published_at = timezone.now()
        self.save()

    def unpublish(self) -> None:
        self.is_published = False
        self.published_at = None
        self.save()

# Runtime checking
post = BlogPost()
assert isinstance(post, Publishable)  # True at runtime
```

### Generic Protocols

```python
from typing import Protocol, TypeVar, Generic

T_co = TypeVar('T_co', covariant=True)

class Serializable(Protocol[T_co]):
    """Protocol for objects that can be serialized."""

    def serialize(self) -> T_co:
        """Serialize to type T."""
        ...

class JsonSerializable(Protocol):
    """Protocol for JSON serialization."""

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dict."""
        ...

def serialize_items(items: List[Serializable[str]]) -> List[str]:
    """Serialize items to strings."""
    return [item.serialize() for item in items]

# Django implementation
class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()

    def serialize(self) -> str:
        """Serialize to string."""
        return f"{self.username}:{self.email}"

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON dict."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

users: List[User] = list(User.objects.all())
serialized: List[str] = serialize_items(users)
```

### Protocol for Django Views

```python
from typing import Protocol
from django.http import HttpRequest, HttpResponse

class ViewCallable(Protocol):
    """Protocol for Django view callables."""

    def __call__(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        ...

def log_view_call(view: ViewCallable) -> ViewCallable:
    """Decorator that logs view calls."""
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        print(f"View called: {view.__name__}")
        return view(request, *args, **kwargs)
    return wrapper

@log_view_call
def my_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Hello")
```

### Protocol for Django Forms

```python
from typing import Protocol, Dict, Any
from django import forms

class FormProtocol(Protocol):
    """Protocol for Django forms."""

    is_valid: bool
    cleaned_data: Dict[str, Any]
    errors: Dict[str, List[str]]

    def save(self, commit: bool = True) -> models.Model:
        """Save the form."""
        ...

def process_form(form: FormProtocol) -> Optional[models.Model]:
    """Process a form and return saved instance."""
    if form.is_valid:
        return form.save()
    return None
```

---

## TypedDict

TypedDict provides a way to use dictionaries with specific string keys and typed values.

### Basic TypedDict

```python
from typing import TypedDict
from django.http import HttpRequest, JsonResponse

class UserDict(TypedDict):
    """Type for user dictionary."""
    id: int
    username: str
    email: str
    is_active: bool

def user_to_dict(user: User) -> UserDict:
    """Convert user to typed dictionary."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
    }

def create_user_from_dict(data: UserDict) -> User:
    """Create user from typed dictionary."""
    return User.objects.create(
        username=data['username'],
        email=data['email'],
        is_active=data['is_active']
    )

# Usage in views
def user_detail_api(request: HttpRequest, user_id: int) -> JsonResponse:
    user = User.objects.get(pk=user_id)
    user_dict: UserDict = user_to_dict(user)
    return JsonResponse(user_dict)
```

### Required vs Not Required

```python
from typing import TypedDict, NotRequired, Required

class ArticleCreateDict(TypedDict):
    """Data for creating an article."""
    title: str  # Required by default
    content: str  # Required by default
    slug: NotRequired[str]  # Optional
    published: NotRequired[bool]  # Optional

class ArticleUpdateDict(TypedDict, total=False):
    """Data for updating an article (all fields optional)."""
    title: str
    content: str
    slug: str
    published: bool

def create_article(data: ArticleCreateDict) -> Article:
    """Create article from dict."""
    article = Article(
        title=data['title'],
        content=data['content']
    )

    # Optional fields
    if 'slug' in data:
        article.slug = data['slug']
    if 'published' in data:
        article.published = data['published']

    article.save()
    return article

def update_article(article: Article, data: ArticleUpdateDict) -> Article:
    """Update article with partial data."""
    for key, value in data.items():
        setattr(article, key, value)
    article.save()
    return article

# Usage
create_data: ArticleCreateDict = {
    'title': 'My Article',
    'content': 'Content here',
    # slug and published are optional
}

update_data: ArticleUpdateDict = {
    'title': 'Updated Title',
    # All other fields optional
}
```

### TypedDict Inheritance

```python
from typing import TypedDict, NotRequired

class BaseModelDict(TypedDict):
    """Base fields for all models."""
    id: int
    created_at: str
    updated_at: str

class UserBaseDict(BaseModelDict):
    """User without sensitive data."""
    username: str
    email: str
    is_active: bool

class UserDetailDict(UserBaseDict):
    """User with additional details."""
    first_name: str
    last_name: str
    date_joined: str
    last_login: NotRequired[str]

class UserWithPermissionsDict(UserDetailDict):
    """User with permissions."""
    is_staff: bool
    is_superuser: bool
    groups: List[str]
    permissions: List[str]

def user_to_detail_dict(user: User) -> UserDetailDict:
    """Convert user to detailed dict."""
    result: UserDetailDict = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'created_at': user.date_joined.isoformat(),
        'updated_at': user.last_login.isoformat() if user.last_login else '',
        'date_joined': user.date_joined.isoformat(),
    }

    if user.last_login:
        result['last_login'] = user.last_login.isoformat()

    return result
```

### TypedDict with Nested Structures

```python
from typing import TypedDict, List, NotRequired

class AddressDict(TypedDict):
    """Address information."""
    street: str
    city: str
    state: str
    zip_code: str
    country: str

class PhoneDict(TypedDict):
    """Phone number information."""
    number: str
    type: str  # 'mobile', 'home', 'work'
    is_primary: bool

class ContactInfoDict(TypedDict):
    """Contact information."""
    email: str
    phones: List[PhoneDict]
    address: NotRequired[AddressDict]

class UserProfileDict(TypedDict):
    """Complete user profile."""
    id: int
    username: str
    full_name: str
    contact: ContactInfoDict
    preferences: Dict[str, Any]

def profile_to_dict(profile: UserProfile) -> UserProfileDict:
    """Convert profile to nested dict."""
    phones: List[PhoneDict] = [
        {
            'number': phone.number,
            'type': phone.phone_type,
            'is_primary': phone.is_primary
        }
        for phone in profile.phones.all()
    ]

    contact: ContactInfoDict = {
        'email': profile.user.email,
        'phones': phones,
    }

    if profile.address:
        contact['address'] = {
            'street': profile.address.street,
            'city': profile.address.city,
            'state': profile.address.state,
            'zip_code': profile.address.zip_code,
            'country': profile.address.country,
        }

    return {
        'id': profile.user.id,
        'username': profile.user.username,
        'full_name': profile.get_full_name(),
        'contact': contact,
        'preferences': profile.preferences,
    }
```

### TypedDict for API Responses

```python
from typing import TypedDict, List, Literal, NotRequired

class PaginationDict(TypedDict):
    """Pagination metadata."""
    page: int
    page_size: int
    total_pages: int
    total_items: int
    has_next: bool
    has_previous: bool

class ErrorDict(TypedDict):
    """Error information."""
    code: str
    message: str
    field: NotRequired[str]

class ApiResponseDict(TypedDict):
    """Standard API response."""
    success: bool
    data: NotRequired[Any]
    errors: NotRequired[List[ErrorDict]]
    pagination: NotRequired[PaginationDict]

def success_response(data: Any, pagination: Optional[PaginationDict] = None) -> ApiResponseDict:
    """Create success response."""
    response: ApiResponseDict = {
        'success': True,
        'data': data,
    }
    if pagination:
        response['pagination'] = pagination
    return response

def error_response(errors: List[ErrorDict]) -> ApiResponseDict:
    """Create error response."""
    return {
        'success': False,
        'errors': errors,
    }

# Usage in views
def list_users_api(request: HttpRequest) -> JsonResponse:
    from django.core.paginator import Paginator

    users = User.objects.all()
    paginator = Paginator(users, 20)
    page_num = int(request.GET.get('page', 1))
    page = paginator.get_page(page_num)

    users_data = [user_to_dict(user) for user in page]

    pagination: PaginationDict = {
        'page': page.number,
        'page_size': paginator.per_page,
        'total_pages': paginator.num_pages,
        'total_items': paginator.count,
        'has_next': page.has_next(),
        'has_previous': page.has_previous(),
    }

    response = success_response(users_data, pagination)
    return JsonResponse(response)
```

---

## Type Guards and Narrowing

Type guards help narrow types within conditional blocks.

### Basic Type Guards

```python
from typing import Union, Optional
from django.contrib.auth.models import User, AnonymousUser

def is_authenticated_user(user: Union[User, AnonymousUser]) -> bool:
    """Type guard for authenticated users."""
    return isinstance(user, User) and user.is_authenticated

def get_user_email(user: Union[User, AnonymousUser]) -> Optional[str]:
    """Get email for authenticated users."""
    if is_authenticated_user(user):
        # Type narrowed to User here
        return user.email
    return None
```

### Custom Type Guards with TypeGuard

```python
from typing import TypeGuard, Union, List, Any
from django.db import models

def is_model_instance(obj: Any) -> TypeGuard[models.Model]:
    """Type guard for Django model instances."""
    return isinstance(obj, models.Model)

def is_queryset(obj: Any) -> TypeGuard[models.QuerySet]:
    """Type guard for Django QuerySets."""
    return isinstance(obj, models.QuerySet)

def process_data(data: Union[models.Model, models.QuerySet, List[Any]]) -> List[models.Model]:
    """Process various data types."""
    if is_model_instance(data):
        # Type narrowed to models.Model
        return [data]
    elif is_queryset(data):
        # Type narrowed to models.QuerySet
        return list(data)
    else:
        # Type narrowed to List[Any]
        return [item for item in data if is_model_instance(item)]
```

### Type Guards for Model Attributes

```python
from typing import TypeGuard, Any
from django.db import models

def has_slug(obj: models.Model) -> TypeGuard[models.Model]:
    """Check if model has slug field."""
    return hasattr(obj, 'slug') and isinstance(
        obj._meta.get_field('slug'), models.SlugField
    )

def has_timestamps(obj: models.Model) -> TypeGuard[models.Model]:
    """Check if model has timestamp fields."""
    return (
        hasattr(obj, 'created_at') and
        hasattr(obj, 'updated_at') and
        isinstance(obj._meta.get_field('created_at'), models.DateTimeField) and
        isinstance(obj._meta.get_field('updated_at'), models.DateTimeField)
    )

def get_model_slug(model: models.Model) -> Optional[str]:
    """Get slug if model has one."""
    if has_slug(model):
        return model.slug  # Type checker knows slug exists
    return None
```

### Type Narrowing with isinstance

```python
from typing import Union
from django.contrib.auth.models import User, Group
from django.db import models

def get_name(obj: Union[User, Group, models.Model]) -> str:
    """Get name from various objects."""
    if isinstance(obj, User):
        # Type narrowed to User
        return obj.username
    elif isinstance(obj, Group):
        # Type narrowed to Group
        return obj.name
    else:
        # Type narrowed to models.Model
        return str(obj)

def process_related_object(
    obj: Union[User, Group, None]
) -> Optional[str]:
    """Process related object."""
    if obj is None:
        return None
    elif isinstance(obj, User):
        return f"User: {obj.username}"
    else:
        # Type narrowed to Group
        return f"Group: {obj.name}"
```

### Type Guards for Form Validation

```python
from typing import TypeGuard, Dict, Any
from django import forms

def is_valid_form_data(data: Dict[str, Any]) -> TypeGuard[Dict[str, Any]]:
    """Type guard for validated form data."""
    required_fields = ['username', 'email', 'password']
    return all(
        field in data and isinstance(data[field], str) and data[field]
        for field in required_fields
    )

def create_user_from_form(data: Dict[str, Any]) -> Optional[User]:
    """Create user if form data is valid."""
    if is_valid_form_data(data):
        # Type checker knows all required fields exist
        return User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
    return None
```

### Type Guards for Request Data

```python
from typing import TypeGuard, Any
from django.http import HttpRequest

def has_json_body(request: HttpRequest) -> TypeGuard[HttpRequest]:
    """Type guard for requests with JSON body."""
    return (
        request.content_type == 'application/json' and
        len(request.body) > 0
    )

def has_authenticated_user(request: HttpRequest) -> TypeGuard[HttpRequest]:
    """Type guard for authenticated requests."""
    return (
        hasattr(request, 'user') and
        request.user.is_authenticated
    )

def process_api_request(request: HttpRequest) -> JsonResponse:
    """Process API request with type guards."""
    if not has_authenticated_user(request):
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    # Type checker knows request.user is authenticated
    if not has_json_body(request):
        return JsonResponse({'error': 'Invalid content type'}, status=400)

    # Process request...
    return JsonResponse({'success': True})
```

---

## Literal Types and Enums

Literal types and Enums provide type-safe constants.

### Literal Types

```python
from typing import Literal, Union
from django.db import models

# Define allowed choices as literals
OrderStatus = Literal['pending', 'processing', 'shipped', 'delivered', 'cancelled']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def update_status(self, new_status: OrderStatus) -> None:
        """Update order status with type checking."""
        self.status = new_status
        self.save()

# Usage
order = Order.objects.first()
order.update_status('shipped')  # OK
# order.update_status('invalid')  # Type error!
```

### Literal Types for View Names

```python
from typing import Literal
from django.urls import reverse
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

ViewName = Literal[
    'home',
    'user-list',
    'user-detail',
    'user-create',
    'user-update',
    'user-delete',
]

def safe_reverse(view_name: ViewName, **kwargs) -> str:
    """Type-safe URL reversing."""
    return reverse(view_name, kwargs=kwargs)

def redirect_to_view(view_name: ViewName, **kwargs) -> HttpResponseRedirect:
    """Type-safe redirect."""
    url = safe_reverse(view_name, **kwargs)
    return HttpResponseRedirect(url)

# Usage
url = safe_reverse('user-detail', pk=1)  # OK
# url = safe_reverse('invalid-view')  # Type error!
```

### Enums for Model Choices

```python
from enum import Enum
from django.db import models

class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = 'admin'
    MANAGER = 'manager'
    STAFF = 'staff'
    CUSTOMER = 'customer'

    @classmethod
    def choices(cls):
        """Get choices for Django model field."""
        return [(item.value, item.name.title()) for item in cls]

class User(models.Model):
    username = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.CUSTOMER.value
    )

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role."""
        return self.role == role.value

    def assign_role(self, role: UserRole) -> None:
        """Assign role to user."""
        self.role = role.value
        self.save()

# Usage
user = User.objects.first()
user.assign_role(UserRole.ADMIN)
if user.has_role(UserRole.ADMIN):
    print("User is admin")
```

### IntEnum for Numeric Choices

```python
from enum import IntEnum
from django.db import models

class Priority(IntEnum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

    def __str__(self) -> str:
        return self.name.title()

class Task(models.Model):
    title = models.CharField(max_length=200)
    priority = models.IntegerField(
        choices=Priority.choices(),
        default=Priority.MEDIUM
    )

    def set_priority(self, priority: Priority) -> None:
        """Set task priority."""
        self.priority = priority.value
        self.save()

    def get_priority(self) -> Priority:
        """Get task priority as enum."""
        return Priority(self.priority)

    def is_urgent(self) -> bool:
        """Check if task is urgent."""
        return self.get_priority() >= Priority.HIGH

# Usage
task = Task.objects.first()
task.set_priority(Priority.URGENT)
if task.is_urgent():
    print("Handle immediately!")
```

### Enum with Methods

```python
from enum import Enum
from typing import List
from django.db import models

class SubscriptionTier(str, Enum):
    """Subscription tier with pricing logic."""
    FREE = 'free'
    BASIC = 'basic'
    PRO = 'pro'
    ENTERPRISE = 'enterprise'

    def get_price(self) -> float:
        """Get monthly price for tier."""
        prices = {
            self.FREE: 0.0,
            self.BASIC: 9.99,
            self.PRO: 29.99,
            self.ENTERPRISE: 99.99,
        }
        return prices[self]

    def get_features(self) -> List[str]:
        """Get features for tier."""
        features = {
            self.FREE: ['Basic features'],
            self.BASIC: ['Basic features', 'Email support'],
            self.PRO: ['All Basic features', 'Priority support', 'Advanced analytics'],
            self.ENTERPRISE: ['All Pro features', '24/7 support', 'Custom integrations'],
        }
        return features[self]

    def can_upgrade_to(self, tier: 'SubscriptionTier') -> bool:
        """Check if can upgrade to tier."""
        tier_order = [self.FREE, self.BASIC, self.PRO, self.ENTERPRISE]
        return tier_order.index(tier) > tier_order.index(self)

    @classmethod
    def choices(cls):
        return [(item.value, item.name.title()) for item in cls]

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices(),
        default=SubscriptionTier.FREE.value
    )

    def get_tier(self) -> SubscriptionTier:
        """Get subscription tier as enum."""
        return SubscriptionTier(self.tier)

    def upgrade_to(self, tier: SubscriptionTier) -> bool:
        """Upgrade subscription."""
        current_tier = self.get_tier()
        if current_tier.can_upgrade_to(tier):
            self.tier = tier.value
            self.save()
            return True
        return False

    def get_monthly_cost(self) -> float:
        """Get monthly cost."""
        return self.get_tier().get_price()
```

### Flag Enum for Permissions

```python
from enum import Flag, auto
from typing import Set
from django.db import models

class Permission(Flag):
    """Permission flags."""
    NONE = 0
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    ADMIN = auto()

    # Compound permissions
    READ_WRITE = READ | WRITE
    ALL = READ | WRITE | DELETE | ADMIN

class UserPermissions(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    permissions = models.IntegerField(default=Permission.NONE.value)

    def has_permission(self, perm: Permission) -> bool:
        """Check if user has permission."""
        return bool(Permission(self.permissions) & perm)

    def grant_permission(self, perm: Permission) -> None:
        """Grant permission to user."""
        current = Permission(self.permissions)
        self.permissions = (current | perm).value
        self.save()

    def revoke_permission(self, perm: Permission) -> None:
        """Revoke permission from user."""
        current = Permission(self.permissions)
        self.permissions = (current & ~perm).value
        self.save()

    def get_permissions(self) -> Set[Permission]:
        """Get all granted permissions."""
        current = Permission(self.permissions)
        return {p for p in Permission if current & p}

# Usage
perms = UserPermissions.objects.get(user=user)
perms.grant_permission(Permission.READ_WRITE)
if perms.has_permission(Permission.WRITE):
    print("Can write")
```

---

## Union Types and Type Aliases

Union types and aliases improve code readability and maintainability.

### Basic Union Types

```python
from typing import Union, Optional
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect

# Type alias for response types
ResponseType = Union[HttpResponse, JsonResponse, HttpResponseRedirect]

def handle_request(request: HttpRequest, format: str) -> ResponseType:
    """Handle request with various response types."""
    data = {'message': 'Hello'}

    if format == 'json':
        return JsonResponse(data)
    elif format == 'redirect':
        return HttpResponseRedirect('/')
    else:
        return HttpResponse('Hello')
```

### Optional Type Alias

```python
from typing import Optional
from django.contrib.auth.models import User

# Type alias for optional user
MaybeUser = Optional[User]

def get_user_by_username(username: str) -> MaybeUser:
    """Get user by username or None."""
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

def process_user(user: MaybeUser) -> str:
    """Process optional user."""
    if user is None:
        return "No user"
    return f"User: {user.username}"
```

### Complex Type Aliases

```python
from typing import Union, Dict, List, Tuple, Any
from django.db import models

# Type aliases for common patterns
QuerySetOrList = Union[models.QuerySet, List[models.Model]]
JsonData = Dict[str, Any]
QueryParams = Dict[str, Union[str, int, bool]]
ModelPk = Union[int, str]
FilterDict = Dict[str, Union[str, int, bool, List[Any]]]

def filter_queryset(
    queryset: models.QuerySet,
    filters: FilterDict
) -> models.QuerySet:
    """Apply filters to queryset."""
    return queryset.filter(**filters)

def serialize_models(
    objects: QuerySetOrList
) -> List[JsonData]:
    """Serialize models to JSON data."""
    return [model_to_dict(obj) for obj in objects]
```

### Union with Literal Types

```python
from typing import Union, Literal

# Success or error response
SuccessResponse = Dict[Literal['status', 'data'], Union[str, Any]]
ErrorResponse = Dict[Literal['status', 'error'], str]
ApiResponse = Union[SuccessResponse, ErrorResponse]

def api_endpoint(request: HttpRequest) -> JsonResponse:
    """API endpoint with typed responses."""
    try:
        data = process_request(request)
        response: SuccessResponse = {
            'status': 'success',
            'data': data
        }
        return JsonResponse(response)
    except Exception as e:
        response: ErrorResponse = {
            'status': 'error',
            'error': str(e)
        }
        return JsonResponse(response, status=400)
```

### Type Aliases for Model Relations

```python
from typing import Union, List
from django.db import models

# Type aliases for related objects
RelatedUser = Union[User, int]  # User instance or ID
RelatedUsers = Union[List[User], List[int]]  # List of users or IDs

class Article(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    collaborators = models.ManyToManyField(User, related_name='articles')

    def set_author(self, author: RelatedUser) -> None:
        """Set article author."""
        if isinstance(author, int):
            self.author_id = author
        else:
            self.author = author
        self.save()

    def add_collaborators(self, users: RelatedUsers) -> None:
        """Add collaborators."""
        if users and isinstance(users[0], int):
            self.collaborators.add(*users)
        else:
            self.collaborators.add(*users)
```

### Discriminated Unions

```python
from typing import Union, Literal, TypedDict

class SuccessResult(TypedDict):
    """Success result."""
    status: Literal['success']
    data: Any

class ErrorResult(TypedDict):
    """Error result."""
    status: Literal['error']
    error: str
    code: int

Result = Union[SuccessResult, ErrorResult]

def process_payment(amount: float) -> Result:
    """Process payment and return result."""
    try:
        # Process payment...
        return {
            'status': 'success',
            'data': {'transaction_id': '12345'}
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'code': 500
        }

def handle_result(result: Result) -> None:
    """Handle result with type narrowing."""
    if result['status'] == 'success':
        # Type narrowed to SuccessResult
        print(f"Success: {result['data']}")
    else:
        # Type narrowed to ErrorResult
        print(f"Error {result['code']}: {result['error']}")
```

---

## Callable Types and Decorators

Typing for functions, decorators, and callbacks.

### Basic Callable Types

```python
from typing import Callable
from django.http import HttpRequest, HttpResponse

# Type alias for view functions
ViewFunction = Callable[[HttpRequest], HttpResponse]
ViewFunctionWithArgs = Callable[[HttpRequest, ...], HttpResponse]

def log_view(view_func: ViewFunction) -> ViewFunction:
    """Decorator that logs view calls."""
    def wrapper(request: HttpRequest) -> HttpResponse:
        print(f"View called: {view_func.__name__}")
        return view_func(request)
    return wrapper

@log_view
def my_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Hello")
```

### Generic Callable Decorators

```python
from typing import TypeVar, Callable, cast
from functools import wraps

F = TypeVar('F', bound=Callable[..., Any])

def require_login(view_func: F) -> F:
    """Decorator that requires user login."""
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login/')
        return view_func(request, *args, **kwargs)
    return cast(F, wrapper)

def cache_result(ttl: int = 300) -> Callable[[F], F]:
    """Decorator factory for caching results."""
    def decorator(func: F) -> F:
        cache: Dict[str, Any] = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str((args, kwargs))
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return cast(F, wrapper)
    return decorator

# Usage
@require_login
@cache_result(ttl=600)
def expensive_view(request: HttpRequest) -> HttpResponse:
    # Expensive computation...
    return HttpResponse("Result")
```

### Callback Types

```python
from typing import Callable, Optional
from django.db.models.signals import post_save
from django.dispatch import receiver

# Type aliases for callbacks
SaveCallback = Callable[[models.Model], None]
ErrorCallback = Callable[[Exception], None]
ProgressCallback = Callable[[int, int], None]  # current, total

class BatchProcessor:
    """Process models in batches with callbacks."""

    def __init__(
        self,
        on_success: Optional[SaveCallback] = None,
        on_error: Optional[ErrorCallback] = None,
        on_progress: Optional[ProgressCallback] = None
    ) -> None:
        self.on_success = on_success
        self.on_error = on_error
        self.on_progress = on_progress

    def process(self, queryset: models.QuerySet) -> None:
        """Process queryset with callbacks."""
        total = queryset.count()

        for i, obj in enumerate(queryset, 1):
            try:
                # Process object...
                if self.on_success:
                    self.on_success(obj)
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

            if self.on_progress:
                self.on_progress(i, total)

# Usage
def success_handler(obj: models.Model) -> None:
    print(f"Processed {obj}")

def error_handler(error: Exception) -> None:
    print(f"Error: {error}")

def progress_handler(current: int, total: int) -> None:
    print(f"Progress: {current}/{total}")

processor = BatchProcessor(
    on_success=success_handler,
    on_error=error_handler,
    on_progress=progress_handler
)
processor.process(User.objects.all())
```

### Method Decorators

```python
from typing import TypeVar, Callable, Any, cast
from functools import wraps

Self = TypeVar('Self')
Method = Callable[[Self], Any]

def cache_method(method: Method[Self]) -> Method[Self]:
    """Cache method results."""
    cache_attr = f'_cache_{method.__name__}'

    @wraps(method)
    def wrapper(self: Self) -> Any:
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, method(self))
        return getattr(self, cache_attr)

    return cast(Method[Self], wrapper)

class User(models.Model):
    username = models.CharField(max_length=100)

    @cache_method
    def get_permissions(self) -> List[str]:
        """Get user permissions (cached)."""
        # Expensive query...
        return list(self.user_permissions.values_list('codename', flat=True))
```

### Parameterized Decorators

```python
from typing import TypeVar, Callable, ParamSpec, Any
from functools import wraps

P = ParamSpec('P')
R = TypeVar('R')

def retry(
    max_attempts: int = 3,
    exception_types: Tuple[type, ...] = (Exception,)
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry decorator with configurable attempts."""
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}")
            raise RuntimeError("Should not reach here")
        return wrapper
    return decorator

@retry(max_attempts=5, exception_types=(ConnectionError,))
def fetch_data(url: str) -> Dict[str, Any]:
    """Fetch data with retry logic."""
    # Make API call...
    pass
```

### Django Middleware Type

```python
from typing import Callable, Protocol
from django.http import HttpRequest, HttpResponse

class MiddlewareProtocol(Protocol):
    """Protocol for Django middleware."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        ...

    def __call__(self, request: HttpRequest) -> HttpResponse:
        ...

class TimingMiddleware:
    """Middleware that times requests."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        import time
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start
        response['X-Request-Duration'] = str(duration)
        return response
```

---

## Generic Classes and Methods

Creating reusable generic components for Django.

### Generic Model Manager

```python
from typing import TypeVar, Generic, Type, Optional, List
from django.db import models

ModelT = TypeVar('ModelT', bound=models.Model)

class BaseManager(Generic[ModelT], models.Manager):
    """Generic base manager with typed methods."""

    def get_or_none(self, **kwargs) -> Optional[ModelT]:
        """Get object or return None."""
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None

    def bulk_update_field(
        self,
        instances: List[ModelT],
        field: str,
        value: Any
    ) -> List[ModelT]:
        """Bulk update a field."""
        for instance in instances:
            setattr(instance, field, value)
        self.bulk_update(instances, [field])
        return instances

    def filter_active(self) -> models.QuerySet[ModelT]:
        """Filter active instances."""
        return self.filter(is_active=True)

class User(models.Model):
    username = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    objects: BaseManager['User'] = BaseManager()

# Usage with full type safety
user: Optional[User] = User.objects.get_or_none(username='john')
active_users: models.QuerySet[User] = User.objects.filter_active()
```

### Generic QuerySet

```python
from typing import TypeVar, Generic, Type, List, Optional
from django.db import models

ModelT = TypeVar('ModelT', bound=models.Model)

class TypedQuerySet(Generic[ModelT], models.QuerySet):
    """Generic typed queryset."""

    def first_or_none(self) -> Optional[ModelT]:
        """Get first object or None."""
        try:
            return self.first()
        except self.model.DoesNotExist:
            return None

    def ids(self) -> List[int]:
        """Get list of IDs."""
        return list(self.values_list('pk', flat=True))

    def random(self) -> Optional[ModelT]:
        """Get random object."""
        return self.order_by('?').first()

    def chunk(self, size: int):
        """Iterate in chunks."""
        count = self.count()
        for start in range(0, count, size):
            yield self[start:start + size]

class ArticleQuerySet(TypedQuerySet['Article']):
    """Article-specific queryset."""

    def published(self) -> 'ArticleQuerySet':
        """Get published articles."""
        return self.filter(is_published=True)

    def by_author(self, author: User) -> 'ArticleQuerySet':
        """Get articles by author."""
        return self.filter(author=author)

class Article(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    objects: ArticleQuerySet = ArticleQuerySet.as_manager()

# Usage
articles: ArticleQuerySet = Article.objects.published()
first: Optional[Article] = articles.first_or_none()
```

### Generic Service Class

```python
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from django.db import models, transaction

ModelT = TypeVar('ModelT', bound=models.Model)

class CrudService(Generic[ModelT]):
    """Generic CRUD service for models."""

    def __init__(self, model_class: Type[ModelT]) -> None:
        self.model_class = model_class

    def get_by_id(self, id: int) -> Optional[ModelT]:
        """Get instance by ID."""
        try:
            return self.model_class.objects.get(pk=id)
        except self.model_class.DoesNotExist:
            return None

    def get_all(self) -> List[ModelT]:
        """Get all instances."""
        return list(self.model_class.objects.all())

    def filter(self, **kwargs) -> List[ModelT]:
        """Filter instances."""
        return list(self.model_class.objects.filter(**kwargs))

    @transaction.atomic
    def create(self, **kwargs) -> ModelT:
        """Create instance."""
        return self.model_class.objects.create(**kwargs)

    @transaction.atomic
    def update(self, instance: ModelT, **kwargs) -> ModelT:
        """Update instance."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    @transaction.atomic
    def delete(self, instance: ModelT) -> None:
        """Delete instance."""
        instance.delete()

    def exists(self, **kwargs) -> bool:
        """Check if instance exists."""
        return self.model_class.objects.filter(**kwargs).exists()

    def count(self, **kwargs) -> int:
        """Count instances."""
        return self.model_class.objects.filter(**kwargs).count()

# Usage
user_service: CrudService[User] = CrudService(User)
user: Optional[User] = user_service.get_by_id(1)
new_user: User = user_service.create(username='john', email='john@example.com')
updated: User = user_service.update(user, is_active=True)
```

### Generic Form Handler

```python
from typing import TypeVar, Generic, Type, Optional, Dict, Any
from django import forms
from django.db import models

ModelT = TypeVar('ModelT', bound=models.Model)
FormT = TypeVar('FormT', bound=forms.ModelForm)

class FormHandler(Generic[ModelT, FormT]):
    """Generic form handler."""

    def __init__(
        self,
        model_class: Type[ModelT],
        form_class: Type[FormT]
    ) -> None:
        self.model_class = model_class
        self.form_class = form_class

    def get_form(
        self,
        instance: Optional[ModelT] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> FormT:
        """Get form instance."""
        return self.form_class(data=data, instance=instance)

    def create(self, data: Dict[str, Any]) -> Optional[ModelT]:
        """Create instance from form data."""
        form = self.get_form(data=data)
        if form.is_valid():
            return form.save()
        return None

    def update(
        self,
        instance: ModelT,
        data: Dict[str, Any]
    ) -> Optional[ModelT]:
        """Update instance from form data."""
        form = self.get_form(instance=instance, data=data)
        if form.is_valid():
            return form.save()
        return None

    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data."""
        form = self.get_form(data=data)
        return form.is_valid()

    def get_errors(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get validation errors."""
        form = self.get_form(data=data)
        form.is_valid()
        return form.errors

# Usage
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

handler: FormHandler[User, UserForm] = FormHandler(User, UserForm)
user: Optional[User] = handler.create({'username': 'john', 'email': 'john@example.com'})
```

### Generic Serializer

```python
from typing import TypeVar, Generic, Type, Dict, Any, List
from django.db import models

ModelT = TypeVar('ModelT', bound=models.Model)

class Serializer(Generic[ModelT]):
    """Generic model serializer."""

    def __init__(
        self,
        model_class: Type[ModelT],
        fields: List[str],
        related_fields: Optional[Dict[str, List[str]]] = None
    ) -> None:
        self.model_class = model_class
        self.fields = fields
        self.related_fields = related_fields or {}

    def serialize_one(self, instance: ModelT) -> Dict[str, Any]:
        """Serialize single instance."""
        data = {
            field: getattr(instance, field)
            for field in self.fields
        }

        # Serialize related fields
        for field, sub_fields in self.related_fields.items():
            related = getattr(instance, field)
            if related is None:
                data[field] = None
            elif hasattr(related, 'all'):
                data[field] = [
                    {f: getattr(obj, f) for f in sub_fields}
                    for obj in related.all()
                ]
            else:
                data[field] = {f: getattr(related, f) for f in sub_fields}

        return data

    def serialize_many(self, instances: List[ModelT]) -> List[Dict[str, Any]]:
        """Serialize multiple instances."""
        return [self.serialize_one(inst) for inst in instances]

# Usage
user_serializer: Serializer[User] = Serializer(
    User,
    fields=['id', 'username', 'email'],
    related_fields={'profile': ['bio', 'avatar']}
)

users = User.objects.all()
data: List[Dict[str, Any]] = user_serializer.serialize_many(list(users))
```

---

## Runtime Type Checking

Using typing extensions and runtime checks for validation.

### Runtime Type Validation

```python
from typing import get_type_hints, get_args, get_origin, Any, Union
from django.core.exceptions import ValidationError

def validate_types(obj: Any, cls: type) -> None:
    """Validate object attributes match type hints."""
    hints = get_type_hints(cls)

    for attr_name, expected_type in hints.items():
        if not hasattr(obj, attr_name):
            continue

        value = getattr(obj, attr_name)

        # Handle Optional types
        origin = get_origin(expected_type)
        if origin is Union:
            args = get_args(expected_type)
            if type(None) in args:
                if value is None:
                    continue
                expected_type = next(arg for arg in args if arg is not type(None))

        if not isinstance(value, expected_type):
            raise ValidationError(
                f"{attr_name} should be {expected_type}, got {type(value)}"
            )

# Usage
class UserData:
    username: str
    email: str
    age: int

data = UserData()
data.username = "john"
data.email = "john@example.com"
data.age = "25"  # Wrong type!

try:
    validate_types(data, UserData)
except ValidationError as e:
    print(e)  # age should be <class 'int'>, got <class 'str'>
```

### TypedDict Runtime Validation

```python
from typing import TypedDict, get_type_hints
from django.core.exceptions import ValidationError

def validate_typed_dict(data: Dict[str, Any], typed_dict: type) -> None:
    """Validate dictionary matches TypedDict structure."""
    hints = get_type_hints(typed_dict)

    # Check required fields
    required_fields = getattr(typed_dict, '__required_keys__', set())
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")

    # Validate types
    for field, expected_type in hints.items():
        if field in data:
            value = data[field]
            if not isinstance(value, expected_type):
                raise ValidationError(
                    f"{field} should be {expected_type}, got {type(value)}"
                )

class UserCreateData(TypedDict):
    username: str
    email: str
    password: str

def create_user_validated(data: Dict[str, Any]) -> User:
    """Create user with runtime validation."""
    validate_typed_dict(data, UserCreateData)
    return User.objects.create_user(**data)
```

### Pydantic with Django

```python
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from django.db import models

class UserSchema(BaseModel):
    """Pydantic schema for user validation."""
    username: str
    email: EmailStr
    age: Optional[int] = None

    @validator('username')
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username too short')
        return v

    @validator('age')
    def age_valid(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Invalid age')
        return v

    class Config:
        from_attributes = True

def create_user_from_schema(data: Dict[str, Any]) -> User:
    """Create user from validated Pydantic schema."""
    schema = UserSchema(**data)  # Validates at runtime
    return User.objects.create(
        username=schema.username,
        email=schema.email
    )

def user_to_schema(user: User) -> UserSchema:
    """Convert Django model to Pydantic schema."""
    return UserSchema.from_orm(user)
```

### Type Assertion Helper

```python
from typing import TypeVar, Type, cast, Any

T = TypeVar('T')

def assert_type(value: Any, expected_type: Type[T]) -> T:
    """Assert value is of expected type."""
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__}, got {type(value).__name__}"
        )
    return cast(T, value)

# Usage
def process_user(obj: Any) -> str:
    """Process user with type assertion."""
    user = assert_type(obj, User)
    return user.username  # Type checker knows this is User
```

### Dataclass with Django Models

```python
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from django.db import models

@dataclass
class UserProfile:
    """User profile data class."""
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    groups: List[str] = field(default_factory=list)

    @classmethod
    def from_model(cls, user: User) -> 'UserProfile':
        """Create from Django model."""
        return cls(
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            groups=list(user.groups.values_list('name', flat=True))
        )

    def to_model(self) -> User:
        """Convert to Django model."""
        user = User.objects.create(
            username=self.username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            is_active=self.is_active
        )
        # Set groups...
        return user

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

# Usage
user = User.objects.first()
profile = UserProfile.from_model(user)
data = profile.to_dict()
```

---

## Advanced Mypy Features

Advanced mypy features for better type checking.

### Final Annotations

```python
from typing import Final, final
from django.db import models

# Final constant
MAX_USERNAME_LENGTH: Final = 100

class User(models.Model):
    # Final field (value can't be reassigned)
    username: Final[str] = models.CharField(max_length=MAX_USERNAME_LENGTH)

    @final
    def get_username(self) -> str:
        """Final method (can't be overridden)."""
        return self.username

# Can't override final method
class AdminUser(User):
    # def get_username(self):  # Error: Cannot override final method
    #     return f"Admin: {self.username}"
    pass
```

### Overload for Multiple Signatures

```python
from typing import overload, Union, Optional, Literal
from django.db import models

class UserManager(models.Manager):
    """User manager with overloaded methods."""

    @overload
    def get_user(self, *, username: str) -> Optional[User]: ...

    @overload
    def get_user(self, *, email: str) -> Optional[User]: ...

    @overload
    def get_user(self, *, id: int) -> Optional[User]: ...

    def get_user(
        self,
        *,
        username: Optional[str] = None,
        email: Optional[str] = None,
        id: Optional[int] = None
    ) -> Optional[User]:
        """Get user by username, email, or ID."""
        try:
            if username:
                return self.get(username=username)
            elif email:
                return self.get(email=email)
            elif id:
                return self.get(pk=id)
            else:
                raise ValueError("Must provide username, email, or id")
        except self.model.DoesNotExist:
            return None

# Type checker understands all signatures
user1: Optional[User] = User.objects.get_user(username='john')
user2: Optional[User] = User.objects.get_user(email='john@example.com')
user3: Optional[User] = User.objects.get_user(id=1)
```

### Overload for Different Return Types

```python
from typing import overload, Literal

@overload
def serialize_user(user: User, format: Literal['dict']) -> Dict[str, Any]: ...

@overload
def serialize_user(user: User, format: Literal['json']) -> str: ...

@overload
def serialize_user(user: User, format: Literal['xml']) -> str: ...

def serialize_user(
    user: User,
    format: Literal['dict', 'json', 'xml'] = 'dict'
) -> Union[Dict[str, Any], str]:
    """Serialize user in different formats."""
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email
    }

    if format == 'dict':
        return data
    elif format == 'json':
        import json
        return json.dumps(data)
    else:  # xml
        # Convert to XML...
        return "<user>...</user>"

# Type checker infers correct return type
dict_data: Dict[str, Any] = serialize_user(user, 'dict')
json_data: str = serialize_user(user, 'json')
xml_data: str = serialize_user(user, 'xml')
```

### reveal_type for Debugging

```python
from django.db import models

def process_users(queryset: models.QuerySet) -> List[User]:
    """Process users with type debugging."""
    # Mypy will show: Revealed type is 'django.db.models.query.QuerySet[*User*]'
    reveal_type(queryset)

    users = list(queryset)
    # Mypy will show: Revealed type is 'builtins.list[*User*]'
    reveal_type(users)

    first_user = users[0]
    # Mypy will show: Revealed type is '*User*'
    reveal_type(first_user)

    return users
```

### assert_type for Type Verification

```python
from typing import assert_type
from django.db import models

def get_user_email(user_id: int) -> str:
    """Get user email with type verification."""
    user = User.objects.get(pk=user_id)

    # Verify type at compile time
    assert_type(user, User)
    assert_type(user.email, str)

    return user.email
```

### TypeGuard with reveal_type

```python
from typing import TypeGuard, Union
from django.contrib.auth.models import User, AnonymousUser

def is_authenticated(
    user: Union[User, AnonymousUser]
) -> TypeGuard[User]:
    """Type guard for authenticated users."""
    reveal_type(user)  # Union[User, AnonymousUser]
    return isinstance(user, User) and user.is_authenticated

def get_username(user: Union[User, AnonymousUser]) -> str:
    """Get username with type narrowing."""
    reveal_type(user)  # Union[User, AnonymousUser]

    if is_authenticated(user):
        reveal_type(user)  # User (narrowed!)
        return user.username
    else:
        reveal_type(user)  # AnonymousUser
        return "Anonymous"
```

### NoReturn Type

```python
from typing import NoReturn
from django.http import Http404
from django.core.exceptions import PermissionDenied

def abort_404(message: str) -> NoReturn:
    """Abort with 404 error."""
    raise Http404(message)

def abort_403(message: str) -> NoReturn:
    """Abort with permission denied."""
    raise PermissionDenied(message)

def get_object_or_404(model_class: type, **kwargs) -> Any:
    """Get object or raise 404."""
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        abort_404(f"{model_class.__name__} not found")
        # Mypy knows this line is unreachable

# Usage
def view(request: HttpRequest, user_id: int) -> HttpResponse:
    user = get_object_or_404(User, pk=user_id)
    # Type checker knows user is not None here
    return HttpResponse(f"User: {user.username}")
```

### Type Narrowing with isinstance

```python
from typing import Union
from django.db import models

def get_display_name(
    obj: Union[User, Group, models.Model]
) -> str:
    """Get display name with type narrowing."""
    if isinstance(obj, User):
        reveal_type(obj)  # User
        return obj.get_full_name() or obj.username
    elif isinstance(obj, Group):
        reveal_type(obj)  # Group
        return obj.name
    else:
        reveal_type(obj)  # models.Model
        return str(obj)
```

### Strict Optional Checking

```python
# mypy.ini:
# [mypy]
# strict_optional = True

from typing import Optional
from django.db import models

def get_user_email(user: Optional[User]) -> str:
    """Get email with strict optional checking."""
    # Error: Item "None" of "Optional[User]" has no attribute "email"
    # return user.email

    # Correct way 1: Type guard
    if user is None:
        return ""
    return user.email

    # Correct way 2: assert
    assert user is not None
    return user.email

    # Correct way 3: Optional chaining (Python 3.10+)
    return user.email if user else ""
```

### Exhaustiveness Checking

```python
from typing import Literal, NoReturn
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'

def assert_never(value: NoReturn) -> NoReturn:
    """Helper for exhaustiveness checking."""
    raise AssertionError(f"Unhandled value: {value}")

def process_order(order: Order) -> str:
    """Process order with exhaustiveness checking."""
    status = OrderStatus(order.status)

    if status == OrderStatus.PENDING:
        return "Order is pending"
    elif status == OrderStatus.PROCESSING:
        return "Order is being processed"
    elif status == OrderStatus.SHIPPED:
        return "Order has shipped"
    elif status == OrderStatus.DELIVERED:
        return "Order delivered"
    else:
        # If we add new status, mypy will error here
        assert_never(status)
```

---

## Best Practices Summary

### 1. Use Type Aliases for Complex Types

```python
# Good
UserId = int
UserDict = Dict[str, Union[str, int, bool]]
QuerySetOrList = Union[models.QuerySet, List[models.Model]]

def process_users(users: QuerySetOrList) -> List[UserDict]:
    ...
```

### 2. Prefer Protocols Over Abstract Base Classes

```python
# Good: Flexible, supports duck typing
class Serializable(Protocol):
    def serialize(self) -> Dict[str, Any]: ...

# Less flexible: Requires explicit inheritance
class Serializable(ABC):
    @abstractmethod
    def serialize(self) -> Dict[str, Any]: ...
```

### 3. Use TypedDict for Dictionary Structures

```python
# Good: Type-safe dictionary
class UserData(TypedDict):
    username: str
    email: str
    age: int

# Bad: No type safety
UserData = Dict[str, Any]
```

### 4. Use Generics for Reusable Components

```python
# Good: Reusable with type safety
class Repository(Generic[ModelT]):
    def get_by_id(self, id: int) -> Optional[ModelT]:
        ...

# Bad: No type information
class Repository:
    def get_by_id(self, id: int) -> Any:
        ...
```

### 5. Use Literal Types for String Unions

```python
# Good: Type-safe choices
Status = Literal['pending', 'active', 'completed']

# Bad: Any string accepted
Status = str
```

### 6. Use overload for Multiple Signatures

```python
# Good: Clear signatures for different use cases
@overload
def get_user(*, id: int) -> User: ...
@overload
def get_user(*, username: str) -> User: ...

# Bad: Unclear what parameters are valid
def get_user(**kwargs) -> User: ...
```

### 7. Enable Strict Mypy Settings

```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_generics = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
strict_optional = True
strict_equality = True
```

### 8. Use reveal_type During Development

```python
# Debug type inference
users = User.objects.all()
reveal_type(users)  # Remove before committing
```

### 9. Document Complex Types

```python
# Good: Clear documentation
def process_data(
    data: Dict[str, Union[List[int], Tuple[str, ...]]],
    callback: Callable[[int], bool]
) -> Iterator[str]:
    """
    Process data with callback.

    Args:
        data: Dict mapping strings to lists of ints or tuples of strings
        callback: Function that takes int and returns bool

    Returns:
        Iterator of processed strings
    """
    ...
```

### 10. Test Your Types

```python
# test_types.py
from mypy import api

def test_mypy_passes():
    """Ensure type checking passes."""
    result = api.run(['myapp'])
    assert 'Success' in result[0]
```

---

## Conclusion

This guide covers advanced typing patterns that can significantly improve Django codebases:

1. **Generics and TypeVars** enable flexible, reusable code with type safety
2. **Protocols** provide structural typing for flexible interfaces
3. **TypedDict** offers typed dictionaries for data structures
4. **Type guards** enable safe type narrowing
5. **Literal types and Enums** provide type-safe constants
6. **Union types and aliases** improve code readability
7. **Callable types** enable typed decorators and callbacks
8. **Generic classes** create reusable components
9. **Runtime checking** validates types at runtime
10. **Advanced mypy features** catch more errors during development

By applying these patterns, you can:
- Catch more bugs during development
- Improve IDE autocompletion and navigation
- Make code more maintainable and self-documenting
- Reduce runtime errors
- Facilitate refactoring

Remember: Type hints are documentation that can be validated. Use them liberally but pragmatically, focusing on public APIs and complex logic where they provide the most value.

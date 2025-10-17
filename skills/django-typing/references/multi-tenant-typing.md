# Complete Guide to Multi-Tenant Django Typing

A comprehensive reference for building type-safe multi-tenant Django applications with proper tenant isolation, generic types, and performance patterns.

## Table of Contents

1. [Introduction](#introduction)
2. [Type-Safe Tenant-Aware Base Models](#type-safe-tenant-aware-base-models)
3. [Generic Tenant Types and Constraints](#generic-tenant-types-and-constraints)
4. [Tenant Context Typing](#tenant-context-typing)
5. [Tenant-Aware Managers and QuerySets](#tenant-aware-managers-and-querysets)
6. [Tenant Isolation in Views and APIs](#tenant-isolation-in-views-and-apis)
7. [Cross-Tenant Reference Validation](#cross-tenant-reference-validation)
8. [Middleware Typing for Tenant Resolution](#middleware-typing-for-tenant-resolution)
9. [Admin Panel Typing with Tenant Filtering](#admin-panel-typing-with-tenant-filtering)
10. [Testing Multi-Tenant Code with Types](#testing-multi-tenant-code-with-types)
11. [Performance Patterns with Type Safety](#performance-patterns-with-type-safety)
12. [Common Pitfalls](#common-pitfalls)
13. [Best Practices](#best-practices)

---

## Introduction

### Why Type Multi-Tenant Code?

Multi-tenant architectures introduce complexity:
- **Tenant isolation bugs**: Accidental cross-tenant data leaks
- **Complex generic patterns**: Managers, querysets, and context managers need proper typing
- **Thread-local context**: Type-safe access to current tenant
- **Foreign key constraints**: Ensuring references stay within tenant boundaries
- **Performance pitfalls**: N+1 queries and missing tenant filters

Type hints help by:
- **Preventing data leaks**: Compile-time checks for tenant isolation
- **Generic type safety**: Proper types for tenant-aware managers and querysets
- **Context validation**: Type-safe tenant context access
- **Refactoring confidence**: Change tenant models without breaking code
- **Documentation**: Clear tenant boundaries and patterns

### Multi-Tenant Architecture Patterns

This guide covers **shared database, shared schema** patterns where:
- All tenants share the same database and tables
- Each tenant-aware model has a `tenant` foreign key
- Row-level security enforces tenant isolation
- Middleware sets the current tenant context

### Setup Requirements

```bash
pip install django django-stubs mypy typing-extensions
```

**Additional type stubs:**
```bash
pip install types-contextvars types-psycopg2
```

---

## Type-Safe Tenant-Aware Base Models

### Basic Tenant Model

```python
from django.db import models
from typing import ClassVar, TYPE_CHECKING

class Tenant(models.Model):
    """
    Base tenant model representing an organization or workspace.

    This is the anchor model for all tenant-scoped data.
    """

    # Primary identification
    id: int
    slug: str = models.SlugField(unique=True, max_length=63)
    name: str = models.CharField(max_length=255)

    # Tenant status
    is_active: bool = models.BooleanField(default=True)

    # Subscription tier affects feature access
    tier: str = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('pro', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='free',
    )

    # Timestamps
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    # Manager typing
    objects: ClassVar['models.Manager[Tenant]'] = models.Manager()

    class Meta:
        db_table = 'tenants'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def has_feature(self, feature: str) -> bool:
        """Check if tenant's tier includes a feature."""
        feature_matrix = {
            'free': {'basic_features'},
            'pro': {'basic_features', 'advanced_reports', 'api_access'},
            'enterprise': {'basic_features', 'advanced_reports', 'api_access',
                          'sso', 'custom_branding'},
        }
        return feature in feature_matrix.get(self.tier, set())
```

### Tenant-Aware Abstract Base Model

```python
from django.db import models
from typing import ClassVar, Generic, TypeVar, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from .managers import TenantManager

T = TypeVar('T', bound='TenantAwareModel')

class TenantAwareModel(models.Model):
    """
    Abstract base model for all tenant-scoped data.

    Automatically filters queries to current tenant context.
    Prevents cross-tenant data access.
    """

    # Every tenant-aware model MUST have this field
    tenant: Tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,  # Critical for performance
    )

    # Timestamps for audit trail
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    # Use tenant-aware manager by default
    objects: ClassVar['TenantManager[T]']

    class Meta:
        abstract = True
        # Ensure tenant is always included in queries
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
        ]

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: list[str] | None = None,
    ) -> None:
        """Override save to validate tenant context."""
        from .context import get_current_tenant

        # For new objects, auto-set tenant from context
        if not self.pk and not self.tenant_id:
            current_tenant = get_current_tenant()
            if current_tenant is None:
                raise ValueError(
                    f"Cannot save {self.__class__.__name__} without tenant context"
                )
            self.tenant = current_tenant

        super().save(force_insert, force_update, using, update_fields)

    def clean(self) -> None:
        """Validate tenant relationships."""
        super().clean()
        self._validate_tenant_references()

    def _validate_tenant_references(self) -> None:
        """Ensure all FK references belong to same tenant."""
        from django.core.exceptions import ValidationError

        for field in self._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                if field.name == 'tenant':
                    continue

                related_obj = getattr(self, field.name, None)
                if related_obj is None:
                    continue

                # Check if related model is tenant-aware
                if isinstance(related_obj, TenantAwareModel):
                    if related_obj.tenant_id != self.tenant_id:
                        raise ValidationError(
                            f"{field.name} belongs to different tenant"
                        )
```

### Concrete Tenant-Aware Models

```python
from django.db import models
from django.contrib.auth.models import AbstractUser
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .managers import TenantManager

class User(AbstractUser):
    """
    User model with tenant relationships.

    Users can belong to multiple tenants with different roles.
    """

    id: int

    # User can be member of multiple tenants
    tenants: models.ManyToManyField[Tenant, 'TenantMembership'] = models.ManyToManyField(
        'Tenant',
        through='TenantMembership',
        related_name='users',
    )

    # Default tenant for UI convenience
    default_tenant: Tenant | None = models.ForeignKey(
        'Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_users',
    )

    class Meta:
        db_table = 'users'

class TenantMembership(models.Model):
    """
    Links users to tenants with role-based access.

    This is the join table for many-to-many with additional fields.
    """

    id: int
    tenant: Tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)

    role: str = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Administrator'),
            ('member', 'Member'),
            ('guest', 'Guest'),
        ],
        default='member',
    )

    is_active: bool = models.BooleanField(default=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    objects: ClassVar['models.Manager[TenantMembership]'] = models.Manager()

    class Meta:
        db_table = 'tenant_memberships'
        unique_together = [['tenant', 'user']]
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.tenant.name} ({self.role})"

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        role_permissions = {
            'owner': {'read', 'write', 'delete', 'admin', 'billing'},
            'admin': {'read', 'write', 'delete', 'admin'},
            'member': {'read', 'write'},
            'guest': {'read'},
        }
        return permission in role_permissions.get(self.role, set())


class Project(TenantAwareModel):
    """
    Example tenant-scoped model: Projects within a tenant.
    """

    id: int
    name: str = models.CharField(max_length=255)
    description: str = models.TextField(blank=True)

    # Owner within the tenant
    owner: User = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_projects',
    )

    is_archived: bool = models.BooleanField(default=False)

    objects: ClassVar['TenantManager[Project]']

    class Meta:
        db_table = 'projects'
        unique_together = [['tenant', 'name']]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.tenant.slug}/{self.name}"


class Task(TenantAwareModel):
    """
    Example nested tenant-scoped model: Tasks within projects.
    """

    id: int
    project: Project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
    )

    title: str = models.CharField(max_length=255)
    description: str = models.TextField(blank=True)

    status: str = models.CharField(
        max_length=20,
        choices=[
            ('todo', 'To Do'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
        ],
        default='todo',
    )

    assignee: User | None = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )

    due_date: models.DateField | None = models.DateField(null=True, blank=True)

    objects: ClassVar['TenantManager[Task]']

    class Meta:
        db_table = 'tasks'
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'project', 'status']),
            models.Index(fields=['tenant', 'assignee', 'status']),
        ]

    def __str__(self) -> str:
        return f"{self.project.name}: {self.title}"

    def clean(self) -> None:
        """Additional validation for task relationships."""
        super().clean()

        from django.core.exceptions import ValidationError

        # Ensure project belongs to same tenant
        if self.project_id and self.project.tenant_id != self.tenant_id:
            raise ValidationError("Project must belong to same tenant")

        # Ensure assignee is member of tenant
        if self.assignee_id:
            if not TenantMembership.objects.filter(
                tenant_id=self.tenant_id,
                user_id=self.assignee_id,
                is_active=True,
            ).exists():
                raise ValidationError("Assignee must be member of tenant")
```

---

## Generic Tenant Types and Constraints

### Type Variables for Tenant Models

```python
from typing import TypeVar, Protocol, TYPE_CHECKING
from django.db import models

if TYPE_CHECKING:
    from .models import Tenant, TenantAwareModel

# Type variable for any tenant-aware model
T = TypeVar('T', bound='TenantAwareModel')

# Type variable for the tenant model itself
TenantT = TypeVar('TenantT', bound='Tenant')

# Type variable constrained to models.Model for broader use
ModelT = TypeVar('ModelT', bound=models.Model)

# Covariant type variable for read-only operations
T_co = TypeVar('T_co', bound='TenantAwareModel', covariant=True)

# Contravariant type variable for write operations
T_contra = TypeVar('T_contra', bound='TenantAwareModel', contravariant=True)
```

### Protocol for Tenant-Aware Objects

```python
from typing import Protocol, runtime_checkable
from django.db import models

@runtime_checkable
class TenantAwareProtocol(Protocol):
    """
    Protocol for objects that are tenant-aware.

    Use this for duck-typing instead of inheritance checks.
    """

    tenant_id: int | None
    tenant: 'Tenant'

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: list[str] | None = None,
    ) -> None:
        ...

    def clean(self) -> None:
        ...


def is_tenant_aware(obj: object) -> bool:
    """Type guard to check if object is tenant-aware."""
    return isinstance(obj, TenantAwareProtocol)


@runtime_checkable
class TenantProtocol(Protocol):
    """Protocol for the tenant model itself."""

    id: int
    slug: str
    name: str
    is_active: bool
    tier: str

    def has_feature(self, feature: str) -> bool:
        ...
```

### Generic Tenant Context Type

```python
from typing import Generic, TypeVar, cast, overload
from contextvars import ContextVar
from dataclasses import dataclass

T = TypeVar('T', bound='TenantAwareModel')
TenantT = TypeVar('TenantT', bound='Tenant')

@dataclass(frozen=True)
class TenantContext(Generic[TenantT]):
    """
    Immutable tenant context holder.

    Stores current tenant and related metadata for request lifecycle.
    """

    tenant: TenantT
    user_id: int | None = None
    membership_role: str | None = None

    def has_permission(self, permission: str) -> bool:
        """Check if current user has permission in this tenant."""
        if self.membership_role is None:
            return False

        role_permissions = {
            'owner': {'read', 'write', 'delete', 'admin', 'billing'},
            'admin': {'read', 'write', 'delete', 'admin'},
            'member': {'read', 'write'},
            'guest': {'read'},
        }
        return permission in role_permissions.get(self.membership_role, set())

    def can_read(self) -> bool:
        """Check if user can read data in this tenant."""
        return self.has_permission('read')

    def can_write(self) -> bool:
        """Check if user can write data in this tenant."""
        return self.has_permission('write')

    def can_admin(self) -> bool:
        """Check if user has admin privileges in this tenant."""
        return self.has_permission('admin')


# Global context variable for current tenant
_current_tenant_context: ContextVar[TenantContext[Tenant] | None] = ContextVar(
    'current_tenant_context',
    default=None,
)
```

---

## Tenant Context Typing

### Thread-Safe Context Management

```python
from typing import Any, cast, overload, Callable, TypeVar, ParamSpec
from contextvars import ContextVar, Token
from contextlib import contextmanager
from functools import wraps
import threading

if TYPE_CHECKING:
    from .models import Tenant, User, TenantMembership

# Context variable for current tenant
_current_tenant_context: ContextVar[TenantContext[Tenant] | None] = ContextVar(
    'current_tenant_context',
    default=None,
)

P = ParamSpec('P')
R = TypeVar('R')


def get_current_tenant() -> 'Tenant | None':
    """
    Get the current tenant from context.

    Returns None if no tenant is set in current context.
    This is the most common way to access tenant context.
    """
    context = _current_tenant_context.get()
    return context.tenant if context else None


def get_current_tenant_context() -> TenantContext[Tenant] | None:
    """Get the full tenant context including user and role."""
    return _current_tenant_context.get()


def require_tenant() -> 'Tenant':
    """
    Get current tenant or raise error if not set.

    Use this in code paths that must have a tenant.

    Raises:
        RuntimeError: If no tenant is set in current context
    """
    tenant = get_current_tenant()
    if tenant is None:
        raise RuntimeError(
            "No tenant in context. Ensure tenant middleware is active."
        )
    return tenant


def require_tenant_context() -> TenantContext[Tenant]:
    """
    Get current tenant context or raise error if not set.

    Raises:
        RuntimeError: If no tenant context is set
    """
    context = get_current_tenant_context()
    if context is None:
        raise RuntimeError("No tenant context set")
    return context


def set_current_tenant(
    tenant: 'Tenant',
    user: 'User | None' = None,
    membership: 'TenantMembership | None' = None,
) -> Token[TenantContext[Tenant] | None]:
    """
    Set the current tenant context.

    Returns a token that can be used to reset the context.

    Args:
        tenant: The tenant to set as current
        user: Optional user for permission checks
        membership: Optional membership for role information

    Returns:
        Token to reset context later
    """
    context = TenantContext(
        tenant=tenant,
        user_id=user.id if user else None,
        membership_role=membership.role if membership else None,
    )
    return _current_tenant_context.set(context)


def clear_current_tenant() -> Token[TenantContext[Tenant] | None]:
    """Clear the current tenant context."""
    return _current_tenant_context.set(None)


@contextmanager
def tenant_context(
    tenant: 'Tenant',
    user: 'User | None' = None,
    membership: 'TenantMembership | None' = None,
):
    """
    Context manager to temporarily set tenant context.

    Usage:
        with tenant_context(my_tenant):
            # Code here runs with my_tenant as current tenant
            project = Project.objects.create(name="New Project")

    Args:
        tenant: The tenant to use in this context
        user: Optional user for the context
        membership: Optional membership for role information
    """
    token = set_current_tenant(tenant, user, membership)
    try:
        yield
    finally:
        _current_tenant_context.reset(token)


def with_tenant(tenant: 'Tenant') -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to run a function with a specific tenant context.

    Usage:
        @with_tenant(my_tenant)
        def create_project(name: str) -> Project:
            return Project.objects.create(name=name)

    Args:
        tenant: The tenant to use when calling the function
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with tenant_context(tenant):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_context_decorator(
    func: Callable[P, R]
) -> Callable[P, R]:
    """
    Decorator to ensure tenant context is set before calling function.

    Usage:
        @require_tenant_context_decorator
        def create_project(name: str) -> Project:
            # This will raise if no tenant context is set
            return Project.objects.create(name=name)
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        require_tenant()
        return func(*args, **kwargs)
    return wrapper
```

### Context Variable Best Practices

```python
from typing import AsyncContextManager, AsyncIterator
from contextvars import copy_context
import asyncio

async def run_in_tenant_context(
    tenant: 'Tenant',
    coro: Callable[[], Awaitable[R]],
) -> R:
    """
    Run an async function in a specific tenant context.

    Useful for background tasks and async operations.

    Usage:
        result = await run_in_tenant_context(
            my_tenant,
            lambda: send_email_to_users()
        )
    """
    # Copy current context and set tenant in the copy
    ctx = copy_context()

    def set_context():
        set_current_tenant(tenant)
        return asyncio.create_task(coro())

    task = ctx.run(set_context)
    return await task


@contextmanager
def tenant_isolation_scope():
    """
    Create an isolation scope for tenant context.

    Ensures that tenant changes inside don't leak outside.
    Useful for tests and batch operations.

    Usage:
        with tenant_isolation_scope():
            set_current_tenant(tenant1)
            # Work with tenant1
            set_current_tenant(tenant2)
            # Work with tenant2
        # Original context restored here
    """
    # Save the current context
    current_context = get_current_tenant_context()
    token = _current_tenant_context.set(current_context)

    try:
        yield
    finally:
        _current_tenant_context.reset(token)
```

---

## Tenant-Aware Managers and QuerySets

### Generic Tenant-Aware QuerySet

```python
from django.db import models
from django.db.models import QuerySet
from typing import Generic, TypeVar, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import TenantAwareModel, Tenant

T = TypeVar('T', bound='TenantAwareModel')


class TenantQuerySet(QuerySet[T], Generic[T]):
    """
    QuerySet that automatically filters by current tenant.

    Provides type-safe methods for tenant-scoped queries.
    """

    def for_tenant(self, tenant: 'Tenant') -> 'TenantQuerySet[T]':
        """
        Filter queryset to specific tenant.

        This is explicit and should be used when you need a specific tenant.
        """
        return self.filter(tenant=tenant)

    def for_current_tenant(self) -> 'TenantQuerySet[T]':
        """
        Filter queryset to current tenant from context.

        Raises RuntimeError if no tenant is set in context.
        """
        from .context import require_tenant
        tenant = require_tenant()
        return self.filter(tenant=tenant)

    def all_tenants(self) -> 'TenantQuerySet[T]':
        """
        Get queryset without tenant filtering.

        Use with caution! Only for superuser operations.
        Make this explicit to avoid accidental cross-tenant queries.
        """
        return self

    def active_only(self) -> 'TenantQuerySet[T]':
        """Filter to records from active tenants only."""
        return self.filter(tenant__is_active=True)

    def with_tenant_info(self) -> 'TenantQuerySet[T]':
        """Optimize queryset by selecting related tenant."""
        return self.select_related('tenant')

    def bulk_create(
        self,
        objs: list[T],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
    ) -> list[T]:
        """
        Bulk create with automatic tenant assignment.

        Sets tenant from context for objects without tenant set.
        """
        from .context import require_tenant

        tenant = require_tenant()
        for obj in objs:
            if obj.tenant_id is None:
                obj.tenant = tenant

        return super().bulk_create(objs, batch_size, ignore_conflicts)

    def update(self, **kwargs: Any) -> int:
        """
        Update with tenant validation.

        Prevents updating tenant field to avoid moving objects between tenants.
        """
        if 'tenant' in kwargs or 'tenant_id' in kwargs:
            raise ValueError(
                "Cannot change tenant on existing objects. "
                "Create new objects in target tenant instead."
            )
        return super().update(**kwargs)


class TenantManager(models.Manager[T], Generic[T]):
    """
    Manager that automatically filters by current tenant.

    Provides the default interface for accessing tenant-scoped data.
    """

    _queryset_class = TenantQuerySet

    def get_queryset(self) -> TenantQuerySet[T]:
        """
        Return a queryset filtered to current tenant.

        This is the key method that enables automatic tenant filtering.
        Override in subclasses if you need different default behavior.
        """
        qs = self._queryset_class(self.model, using=self._db)

        from .context import get_current_tenant
        tenant = get_current_tenant()

        if tenant is not None:
            # Automatically filter to current tenant
            return qs.filter(tenant=tenant)

        # No tenant in context - return empty queryset for safety
        # This prevents accidental cross-tenant data access
        return qs.none()

    def for_tenant(self, tenant: 'Tenant') -> TenantQuerySet[T]:
        """Get queryset for specific tenant, bypassing context."""
        return self.get_queryset().for_tenant(tenant)

    def all_tenants(self) -> TenantQuerySet[T]:
        """
        Get queryset for all tenants, bypassing context.

        Use with extreme caution! Only for superuser operations.
        """
        return self._queryset_class(self.model, using=self._db)

    def create(self, **kwargs: Any) -> T:
        """
        Create object with automatic tenant assignment.

        Sets tenant from context if not provided.
        """
        from .context import get_current_tenant

        if 'tenant' not in kwargs and 'tenant_id' not in kwargs:
            tenant = get_current_tenant()
            if tenant is None:
                raise ValueError(
                    f"Cannot create {self.model.__name__} without tenant context"
                )
            kwargs['tenant'] = tenant

        return super().create(**kwargs)


# Apply the manager to TenantAwareModel
TenantAwareModel.objects = TenantManager()
```

### Specialized Managers for Specific Models

```python
from django.db import models
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Project, Task, User


class ProjectQuerySet(TenantQuerySet['Project']):
    """Specialized queryset for projects with additional methods."""

    def active(self) -> 'ProjectQuerySet':
        """Filter to non-archived projects."""
        return self.filter(is_archived=False)

    def archived(self) -> 'ProjectQuerySet':
        """Filter to archived projects."""
        return self.filter(is_archived=True)

    def owned_by(self, user: 'User') -> 'ProjectQuerySet':
        """Filter to projects owned by specific user."""
        return self.filter(owner=user)

    def with_task_counts(self) -> 'ProjectQuerySet':
        """Annotate with task counts."""
        return self.annotate(
            task_count=models.Count('tasks'),
            open_task_count=models.Count(
                'tasks',
                filter=models.Q(tasks__status__in=['todo', 'in_progress']),
            ),
        )


class ProjectManager(TenantManager['Project']):
    """Manager for Project model with specialized methods."""

    _queryset_class = ProjectQuerySet

    def get_queryset(self) -> ProjectQuerySet:
        """Return ProjectQuerySet with tenant filtering."""
        return super().get_queryset()  # type: ignore[return-value]

    def active(self) -> ProjectQuerySet:
        """Shortcut for getting active projects."""
        return self.get_queryset().active()

    def for_user(self, user: 'User') -> ProjectQuerySet:
        """Get projects accessible to user in current tenant."""
        return self.get_queryset().filter(
            models.Q(owner=user) | models.Q(tasks__assignee=user)
        ).distinct()


class TaskQuerySet(TenantQuerySet['Task']):
    """Specialized queryset for tasks."""

    def todo(self) -> 'TaskQuerySet':
        """Filter to tasks in 'todo' status."""
        return self.filter(status='todo')

    def in_progress(self) -> 'TaskQuerySet':
        """Filter to tasks in 'in_progress' status."""
        return self.filter(status='in_progress')

    def done(self) -> 'TaskQuerySet':
        """Filter to completed tasks."""
        return self.filter(status='done')

    def assigned_to(self, user: 'User') -> 'TaskQuerySet':
        """Filter to tasks assigned to specific user."""
        return self.filter(assignee=user)

    def unassigned(self) -> 'TaskQuerySet':
        """Filter to tasks without assignee."""
        return self.filter(assignee__isnull=True)

    def in_project(self, project: 'Project') -> 'TaskQuerySet':
        """Filter to tasks in specific project."""
        return self.filter(project=project)

    def overdue(self) -> 'TaskQuerySet':
        """Filter to tasks past due date."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.filter(
            due_date__lt=today,
            status__in=['todo', 'in_progress'],
        )

    def due_soon(self, days: int = 7) -> 'TaskQuerySet':
        """Filter to tasks due within specified days."""
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        future_date = today + timedelta(days=days)

        return self.filter(
            due_date__range=(today, future_date),
            status__in=['todo', 'in_progress'],
        )


class TaskManager(TenantManager['Task']):
    """Manager for Task model."""

    _queryset_class = TaskQuerySet

    def get_queryset(self) -> TaskQuerySet:
        """Return TaskQuerySet with tenant filtering."""
        return super().get_queryset()  # type: ignore[return-value]

    def my_tasks(self, user: 'User') -> TaskQuerySet:
        """Get tasks assigned to user in current tenant."""
        return self.get_queryset().assigned_to(user)

    def create_task(
        self,
        project: 'Project',
        title: str,
        assignee: 'User | None' = None,
        **kwargs: Any,
    ) -> 'Task':
        """
        Create a task with validation.

        Ensures project belongs to current tenant.
        """
        from .context import require_tenant
        tenant = require_tenant()

        if project.tenant_id != tenant.id:
            raise ValueError("Project must belong to current tenant")

        if assignee is not None:
            # Verify assignee is member of tenant
            from .models import TenantMembership
            if not TenantMembership.objects.filter(
                tenant=tenant,
                user=assignee,
                is_active=True,
            ).exists():
                raise ValueError("Assignee must be member of tenant")

        return self.create(
            project=project,
            title=title,
            assignee=assignee,
            **kwargs,
        )


# Set managers on models
Project.objects = ProjectManager()
Task.objects = TaskManager()
```

---

## Tenant Isolation in Views and APIs

### Type-Safe Class-Based Views

```python
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.http import HttpRequest, HttpResponse, Http404
from typing import Any, Generic, TypeVar, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import TenantAwareModel, Tenant, User, Project, Task

T = TypeVar('T', bound='TenantAwareModel')


class TenantMixin:
    """
    Mixin to add tenant context to views.

    Automatically sets tenant from middleware and validates access.
    """

    request: HttpRequest

    def get_current_tenant(self) -> 'Tenant':
        """Get tenant from request, set by middleware."""
        tenant = getattr(self.request, 'tenant', None)
        if tenant is None:
            raise Http404("Tenant not found")
        return tenant

    def get_current_user(self) -> 'User':
        """Get authenticated user or raise 404."""
        if not self.request.user.is_authenticated:
            raise Http404("User not authenticated")
        return cast('User', self.request.user)

    def check_tenant_access(self) -> None:
        """Override to add custom access checks."""
        tenant = self.get_current_tenant()
        user = self.get_current_user()

        # Check user is member of tenant
        from .models import TenantMembership
        if not TenantMembership.objects.filter(
            tenant=tenant,
            user=user,
            is_active=True,
        ).exists():
            raise Http404("User is not member of tenant")


class TenantListView(TenantMixin, ListView[T], Generic[T]):
    """
    ListView that automatically filters to current tenant.

    Usage:
        class ProjectListView(TenantListView['Project']):
            model = Project
            template_name = 'projects/list.html'
    """

    def get_queryset(self) -> TenantQuerySet[T]:
        """Get queryset filtered to current tenant."""
        self.check_tenant_access()
        qs = super().get_queryset()
        # Manager already filters to current tenant
        return cast(TenantQuerySet[T], qs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add tenant to context."""
        context = super().get_context_data(**kwargs)
        context['tenant'] = self.get_current_tenant()
        return context


class TenantDetailView(TenantMixin, DetailView[T], Generic[T]):
    """
    DetailView that validates object belongs to current tenant.

    Usage:
        class ProjectDetailView(TenantDetailView['Project']):
            model = Project
            template_name = 'projects/detail.html'
    """

    def get_queryset(self) -> TenantQuerySet[T]:
        """Get queryset filtered to current tenant."""
        self.check_tenant_access()
        qs = super().get_queryset()
        return cast(TenantQuerySet[T], qs)

    def get_object(self, queryset: TenantQuerySet[T] | None = None) -> T:
        """Get object and verify it belongs to current tenant."""
        obj = super().get_object(queryset)

        # Verify tenant match (defense in depth)
        if obj.tenant_id != self.get_current_tenant().id:
            raise Http404("Object not found in this tenant")

        return obj


class TenantCreateView(TenantMixin, CreateView[T], Generic[T]):
    """
    CreateView that automatically sets tenant on new objects.

    Usage:
        class ProjectCreateView(TenantCreateView['Project']):
            model = Project
            fields = ['name', 'description', 'owner']
            template_name = 'projects/create.html'
    """

    def form_valid(self, form: Any) -> HttpResponse:
        """Set tenant before saving."""
        self.check_tenant_access()

        # Set tenant on the object
        form.instance.tenant = self.get_current_tenant()

        return super().form_valid(form)

    def get_form_kwargs(self) -> dict[str, Any]:
        """Pass tenant to form for validation."""
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.get_current_tenant()
        return kwargs


class TenantUpdateView(TenantMixin, UpdateView[T], Generic[T]):
    """
    UpdateView that validates object belongs to current tenant.

    Usage:
        class ProjectUpdateView(TenantUpdateView['Project']):
            model = Project
            fields = ['name', 'description']
            template_name = 'projects/update.html'
    """

    def get_queryset(self) -> TenantQuerySet[T]:
        """Get queryset filtered to current tenant."""
        self.check_tenant_access()
        qs = super().get_queryset()
        return cast(TenantQuerySet[T], qs)

    def get_object(self, queryset: TenantQuerySet[T] | None = None) -> T:
        """Get object and verify it belongs to current tenant."""
        obj = super().get_object(queryset)

        if obj.tenant_id != self.get_current_tenant().id:
            raise Http404("Object not found in this tenant")

        return obj


# Concrete view examples

class ProjectListView(TenantListView['Project']):
    """List all projects in current tenant."""

    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'
    paginate_by = 20

    def get_queryset(self) -> ProjectQuerySet:
        """Get projects with task counts."""
        return super().get_queryset().active().with_task_counts()


class ProjectDetailView(TenantDetailView['Project']):
    """Show project details."""

    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add project tasks to context."""
        context = super().get_context_data(**kwargs)

        # Get tasks for this project
        context['tasks'] = Task.objects.filter(
            project=self.object
        ).select_related('assignee')

        return context


class TaskCreateView(TenantCreateView['Task']):
    """Create a new task in a project."""

    model = Task
    fields = ['title', 'description', 'status', 'assignee', 'due_date']
    template_name = 'tasks/create.html'

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Load project before processing."""
        project_id = self.kwargs.get('project_id')
        if project_id is None:
            raise Http404("Project ID required")

        try:
            self.project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise Http404("Project not found")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: Any) -> HttpResponse:
        """Set project on task."""
        form.instance.project = self.project
        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add project to context."""
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
```

### Django REST Framework Views

```python
from rest_framework import viewsets, serializers, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from typing import Any, TYPE_CHECKING
from django.db.models import QuerySet

if TYPE_CHECKING:
    from .models import Project, Task, Tenant


class TenantPermission(permissions.BasePermission):
    """
    Permission class that checks tenant membership.

    Requires user to be authenticated member of current tenant.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        """Check if user has access to tenant."""
        if not request.user.is_authenticated:
            return False

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return False

        from .models import TenantMembership
        return TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
        ).exists()

    def has_object_permission(
        self,
        request: Request,
        view: Any,
        obj: Any,
    ) -> bool:
        """Check if user has access to specific object."""
        from .models import TenantAwareModel

        if not isinstance(obj, TenantAwareModel):
            return True

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return False

        return obj.tenant_id == tenant.id


class TenantSerializer(serializers.ModelSerializer['Tenant']):
    """Serializer for tenant model."""

    class Meta:
        model = Tenant  # type: ignore[misc]
        fields = ['id', 'slug', 'name', 'tier', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProjectSerializer(serializers.ModelSerializer['Project']):
    """Serializer for project model."""

    tenant_slug = serializers.CharField(source='tenant.slug', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project  # type: ignore[misc]
        fields = [
            'id',
            'name',
            'description',
            'owner',
            'owner_username',
            'is_archived',
            'tenant_slug',
            'task_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_owner(self, value: 'User') -> 'User':
        """Validate owner is member of tenant."""
        request = self.context.get('request')
        if request is None:
            return value

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            raise serializers.ValidationError("No tenant in context")

        from .models import TenantMembership
        if not TenantMembership.objects.filter(
            tenant=tenant,
            user=value,
            is_active=True,
        ).exists():
            raise serializers.ValidationError("Owner must be member of tenant")

        return value


class TaskSerializer(serializers.ModelSerializer['Task']):
    """Serializer for task model."""

    project_name = serializers.CharField(source='project.name', read_only=True)
    assignee_username = serializers.CharField(
        source='assignee.username',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Task  # type: ignore[misc]
        fields = [
            'id',
            'project',
            'project_name',
            'title',
            'description',
            'status',
            'assignee',
            'assignee_username',
            'due_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_project(self, value: 'Project') -> 'Project':
        """Validate project belongs to current tenant."""
        request = self.context.get('request')
        if request is None:
            return value

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            raise serializers.ValidationError("No tenant in context")

        if value.tenant_id != tenant.id:
            raise serializers.ValidationError("Project not found in this tenant")

        return value

    def validate_assignee(self, value: 'User | None') -> 'User | None':
        """Validate assignee is member of tenant."""
        if value is None:
            return value

        request = self.context.get('request')
        if request is None:
            return value

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            raise serializers.ValidationError("No tenant in context")

        from .models import TenantMembership
        if not TenantMembership.objects.filter(
            tenant=tenant,
            user=value,
            is_active=True,
        ).exists():
            raise serializers.ValidationError("Assignee must be member of tenant")

        return value


class TenantViewSetMixin:
    """Mixin for tenant-aware viewsets."""

    permission_classes = [permissions.IsAuthenticated, TenantPermission]

    def get_queryset(self) -> QuerySet[Any]:
        """
        Get queryset filtered to current tenant.

        Override this to add additional filtering.
        """
        # Queryset is already filtered by manager
        return super().get_queryset()  # type: ignore[misc]

    def perform_create(self, serializer: Any) -> None:
        """Set tenant when creating objects."""
        # Tenant is set automatically by model save method
        serializer.save()


class ProjectViewSet(TenantViewSetMixin, viewsets.ModelViewSet['Project']):
    """ViewSet for project CRUD operations."""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self) -> ProjectQuerySet:
        """Get projects with annotations."""
        qs = super().get_queryset()
        return qs.active().with_task_counts()  # type: ignore[return-value]


class TaskViewSet(TenantViewSetMixin, viewsets.ModelViewSet['Task']):
    """ViewSet for task CRUD operations."""

    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def get_queryset(self) -> TaskQuerySet:
        """Get tasks with optional filtering."""
        qs = super().get_queryset()

        # Filter by project if provided
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)

        # Filter by assignee if provided
        assignee_id = self.request.query_params.get('assignee')
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)

        # Filter by status if provided
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)

        return qs  # type: ignore[return-value]
```

---

## Cross-Tenant Reference Validation

### Preventing Cross-Tenant Data Leaks

```python
from django.core.exceptions import ValidationError
from django.db import models
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import TenantAwareModel, Tenant


class CrossTenantValidator:
    """
    Validator to ensure foreign key references stay within tenant boundaries.

    Add this to model clean() methods or form validators.
    """

    @staticmethod
    def validate_foreign_keys(instance: 'TenantAwareModel') -> None:
        """
        Validate all foreign keys belong to same tenant.

        Raises ValidationError if any FK points to different tenant.
        """
        for field in instance._meta.get_fields():
            if not isinstance(field, models.ForeignKey):
                continue

            if field.name == 'tenant':
                continue

            related_obj = getattr(instance, field.name, None)
            if related_obj is None:
                continue

            # Check if related model is tenant-aware
            from .models import TenantAwareModel
            if not isinstance(related_obj, TenantAwareModel):
                continue

            # Validate tenant match
            if related_obj.tenant_id != instance.tenant_id:
                raise ValidationError({
                    field.name: f"{field.verbose_name} must belong to same tenant"
                })

    @staticmethod
    def validate_many_to_many(instance: 'TenantAwareModel') -> None:
        """
        Validate all M2M relationships stay within tenant.

        Call this after save when M2M fields are accessible.
        """
        for field in instance._meta.get_fields():
            if not isinstance(field, models.ManyToManyField):
                continue

            related_manager = getattr(instance, field.name)

            # Check each related object
            from .models import TenantAwareModel
            for related_obj in related_manager.all():
                if isinstance(related_obj, TenantAwareModel):
                    if related_obj.tenant_id != instance.tenant_id:
                        raise ValidationError({
                            field.name: f"All {field.verbose_name} must belong to same tenant"
                        })


def validate_tenant_reference(
    instance: 'TenantAwareModel',
    field_name: str,
    related_obj: Any,
) -> None:
    """
    Validate a single foreign key reference.

    Usage:
        def clean(self):
            super().clean()
            if self.project_id:
                validate_tenant_reference(self, 'project', self.project)
    """
    from .models import TenantAwareModel

    if not isinstance(related_obj, TenantAwareModel):
        return

    if related_obj.tenant_id != instance.tenant_id:
        raise ValidationError({
            field_name: f"{field_name} must belong to same tenant"
        })


# Add validation to base model
def _enhanced_clean(self: 'TenantAwareModel') -> None:
    """Enhanced clean with automatic cross-tenant validation."""
    # Call original clean
    super(TenantAwareModel, self).clean()

    # Validate all foreign keys
    CrossTenantValidator.validate_foreign_keys(self)

TenantAwareModel.clean = _enhanced_clean  # type: ignore[assignment]
```

### Database Constraints for Tenant Isolation

```python
from django.db import models
from django.db.models import UniqueConstraint, CheckConstraint, Q, F

class TaskWithConstraints(TenantAwareModel):
    """
    Example model with database-level tenant isolation constraints.

    These constraints provide defense-in-depth against application bugs.
    """

    project: Project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks_constrained',
    )

    title: str = models.CharField(max_length=255)
    assignee: User | None = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'tasks_with_constraints'

        constraints = [
            # Ensure task and project have same tenant
            CheckConstraint(
                check=Q(tenant=F('project__tenant')),
                name='task_project_same_tenant',
            ),

            # Unique task title within project
            UniqueConstraint(
                fields=['tenant', 'project', 'title'],
                name='unique_task_title_per_project',
            ),
        ]

        indexes = [
            models.Index(fields=['tenant', 'project', 'assignee']),
        ]


class ProjectMembershipWithConstraints(models.Model):
    """
    Example of join table with tenant constraints.

    Users can be assigned to projects, but only within tenant boundaries.
    """

    id: int
    tenant: Tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    project: Project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE)

    role: str = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('editor', 'Editor'),
            ('viewer', 'Viewer'),
        ],
        default='viewer',
    )

    class Meta:
        db_table = 'project_memberships'

        constraints = [
            # Project must belong to same tenant
            CheckConstraint(
                check=Q(tenant=F('project__tenant')),
                name='project_membership_same_tenant',
            ),

            # User can only be added once per project
            UniqueConstraint(
                fields=['project', 'user'],
                name='unique_user_per_project',
            ),
        ]
```

---

## Middleware Typing for Tenant Resolution

### Tenant Resolution Middleware

```python
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from typing import Callable, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .models import Tenant, User, TenantMembership

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to resolve tenant from request and set in context.

    Supports multiple resolution strategies:
    1. Subdomain-based (tenant.example.com)
    2. Header-based (X-Tenant-Slug)
    3. Path-based (/tenants/{slug}/...)
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Resolve tenant and set in request and context.

        Sets request.tenant and request.tenant_context.
        """
        tenant = self._resolve_tenant(request)

        if tenant is not None:
            # Set tenant on request for view access
            request.tenant = tenant  # type: ignore[attr-defined]

            # Get user's membership if authenticated
            membership = None
            if request.user.is_authenticated:
                membership = self._get_membership(request.user, tenant)  # type: ignore[arg-type]

            # Set tenant in context for automatic filtering
            from .context import set_current_tenant
            set_current_tenant(tenant, request.user if request.user.is_authenticated else None, membership)  # type: ignore[arg-type]

            logger.debug(f"Tenant resolved: {tenant.slug}")
        else:
            # Clear tenant context for non-tenant requests
            request.tenant = None  # type: ignore[attr-defined]
            from .context import clear_current_tenant
            clear_current_tenant()

            logger.debug("No tenant resolved")

    def _resolve_tenant(self, request: HttpRequest) -> 'Tenant | None':
        """
        Resolve tenant from request using configured strategy.

        Returns None if no tenant can be resolved.
        """
        # Try strategies in order
        tenant = (
            self._resolve_from_subdomain(request)
            or self._resolve_from_header(request)
            or self._resolve_from_path(request)
        )

        return tenant

    def _resolve_from_subdomain(self, request: HttpRequest) -> 'Tenant | None':
        """
        Resolve tenant from subdomain.

        Example: acme.example.com -> tenant with slug 'acme'
        """
        host = request.get_host().split(':')[0]  # Remove port
        parts = host.split('.')

        # Check if subdomain exists (more than 2 parts)
        if len(parts) < 3:
            return None

        subdomain = parts[0]

        # Skip special subdomains
        if subdomain in {'www', 'api', 'admin'}:
            return None

        from .models import Tenant
        try:
            return Tenant.objects.get(slug=subdomain, is_active=True)
        except Tenant.DoesNotExist:
            return None

    def _resolve_from_header(self, request: HttpRequest) -> 'Tenant | None':
        """
        Resolve tenant from HTTP header.

        Example: X-Tenant-Slug: acme
        """
        tenant_slug = request.headers.get('X-Tenant-Slug')
        if not tenant_slug:
            return None

        from .models import Tenant
        try:
            return Tenant.objects.get(slug=tenant_slug, is_active=True)
        except Tenant.DoesNotExist:
            return None

    def _resolve_from_path(self, request: HttpRequest) -> 'Tenant | None':
        """
        Resolve tenant from URL path.

        Example: /tenants/acme/projects -> tenant with slug 'acme'
        """
        path = request.path

        # Check for /tenants/{slug}/ pattern
        if not path.startswith('/tenants/'):
            return None

        parts = path.split('/')
        if len(parts) < 3:
            return None

        tenant_slug = parts[2]

        from .models import Tenant
        try:
            return Tenant.objects.get(slug=tenant_slug, is_active=True)
        except Tenant.DoesNotExist:
            return None

    def _get_membership(
        self,
        user: 'User',
        tenant: 'Tenant',
    ) -> 'TenantMembership | None':
        """Get user's membership in tenant."""
        from .models import TenantMembership
        try:
            return TenantMembership.objects.get(
                tenant=tenant,
                user=user,
                is_active=True,
            )
        except TenantMembership.DoesNotExist:
            return None

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        """Clean up tenant context after request."""
        from .context import clear_current_tenant
        clear_current_tenant()
        return response


class TenantAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce tenant access restrictions.

    Must run after TenantMiddleware.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """
        Check if user has access to tenant.

        Returns 403 if user is authenticated but not a member.
        """
        tenant = getattr(request, 'tenant', None)

        # Skip check if no tenant or user not authenticated
        if tenant is None or not request.user.is_authenticated:
            return None

        # Skip check for superusers
        if request.user.is_superuser:
            return None

        # Check membership
        from .models import TenantMembership
        is_member = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
        ).exists()

        if not is_member:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have access to this tenant")

        return None
```

### Middleware Configuration

```python
# settings.py type-safe middleware configuration

from typing import List

MIDDLEWARE: List[str] = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Tenant middleware MUST come after auth middleware
    # so request.user is available
    'myapp.middleware.TenantMiddleware',
    'myapp.middleware.TenantAccessMiddleware',
]
```

---

## Admin Panel Typing with Tenant Filtering

### Tenant-Aware Admin Base Classes

```python
from django.contrib import admin
from django.http import HttpRequest
from django.db.models import QuerySet, Count
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import TenantAwareModel, Tenant, Project, Task


class TenantAdminMixin:
    """
    Mixin for tenant-aware admin interfaces.

    Automatically filters querysets to current tenant context.
    """

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        """
        Filter queryset to current tenant.

        Superusers see all tenants unless they've selected a specific tenant.
        """
        qs = super().get_queryset(request)  # type: ignore[misc]

        # Superusers can see everything
        if request.user.is_superuser:
            # Check if tenant filter is applied
            tenant_id = request.GET.get('tenant__id__exact')
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            return qs

        # Regular users only see their tenant's data
        from .context import get_current_tenant
        tenant = get_current_tenant()

        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        else:
            # No tenant context - return empty queryset
            qs = qs.none()

        return qs

    def save_model(
        self,
        request: HttpRequest,
        obj: 'TenantAwareModel',
        form: Any,
        change: bool,
    ) -> None:
        """
        Save model with tenant validation.

        Sets tenant from context if creating new object.
        """
        if not change and obj.tenant_id is None:
            from .context import get_current_tenant
            tenant = get_current_tenant()
            if tenant is None:
                raise ValueError("Cannot create object without tenant context")
            obj.tenant = tenant

        super().save_model(request, obj, form, change)  # type: ignore[misc]

    def get_list_display(self, request: HttpRequest) -> tuple[str, ...]:
        """
        Customize list display based on user permissions.

        Superusers see tenant column, regular users don't.
        """
        list_display = super().get_list_display(request)  # type: ignore[misc]

        if request.user.is_superuser:
            # Add tenant column for superusers
            if 'tenant' not in list_display:
                list_display = ('tenant',) + tuple(list_display)

        return list_display


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin['Tenant']):
    """Admin interface for tenant management."""

    list_display = ('name', 'slug', 'tier', 'is_active', 'user_count', 'created_at')
    list_filter = ('tier', 'is_active', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'tier'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_count(self, obj: Tenant) -> int:
        """Show number of users in tenant."""
        return obj.users.filter(tenantmembership__is_active=True).count()

    user_count.short_description = 'Users'  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tenant]:
        """Annotate queryset with user count."""
        qs = super().get_queryset(request)
        qs = qs.annotate(
            _user_count=Count('users', filter=models.Q(tenantmembership__is_active=True))
        )
        return qs


@admin.register(Project)
class ProjectAdmin(TenantAdminMixin, admin.ModelAdmin['Project']):
    """Admin interface for projects."""

    list_display = ('name', 'owner', 'task_count', 'is_archived', 'created_at')
    list_filter = ('is_archived', 'created_at', 'tenant')
    search_fields = ('name', 'description', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')

    autocomplete_fields = ('owner',)

    fieldsets = (
        ('Project Information', {
            'fields': ('name', 'description', 'owner'),
        }),
        ('Status', {
            'fields': ('is_archived',),
        }),
        ('Tenant', {
            'fields': ('tenant',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def task_count(self, obj: Project) -> int:
        """Show number of tasks in project."""
        return obj.tasks.count()

    task_count.short_description = 'Tasks'  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Project]:
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        qs = qs.select_related('tenant', 'owner').annotate(
            _task_count=Count('tasks')
        )
        return qs

    def formfield_for_foreignkey(
        self,
        db_field: models.Field,
        request: HttpRequest,
        **kwargs: Any,
    ) -> Any:
        """
        Filter foreign key choices to current tenant.

        Ensures only valid users from tenant can be selected as owner.
        """
        if db_field.name == 'owner':
            from .context import get_current_tenant
            tenant = get_current_tenant()

            if tenant is not None:
                # Filter to users in current tenant
                from .models import TenantMembership
                user_ids = TenantMembership.objects.filter(
                    tenant=tenant,
                    is_active=True,
                ).values_list('user_id', flat=True)

                kwargs['queryset'] = User.objects.filter(id__in=user_ids)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Task)
class TaskAdmin(TenantAdminMixin, admin.ModelAdmin['Task']):
    """Admin interface for tasks."""

    list_display = (
        'title',
        'project',
        'status',
        'assignee',
        'due_date',
        'is_overdue',
        'created_at',
    )
    list_filter = ('status', 'due_date', 'created_at', 'tenant', 'project')
    search_fields = ('title', 'description', 'project__name')
    readonly_fields = ('created_at', 'updated_at')

    autocomplete_fields = ('project', 'assignee')

    fieldsets = (
        ('Task Information', {
            'fields': ('project', 'title', 'description'),
        }),
        ('Assignment', {
            'fields': ('status', 'assignee', 'due_date'),
        }),
        ('Tenant', {
            'fields': ('tenant',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def is_overdue(self, obj: Task) -> bool:
        """Check if task is past due date."""
        if obj.due_date is None:
            return False

        if obj.status == 'done':
            return False

        from django.utils import timezone
        return obj.due_date < timezone.now().date()

    is_overdue.boolean = True  # type: ignore[attr-defined]
    is_overdue.short_description = 'Overdue'  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Task]:
        """Optimize queryset."""
        qs = super().get_queryset(request)
        qs = qs.select_related('tenant', 'project', 'assignee')
        return qs

    def formfield_for_foreignkey(
        self,
        db_field: models.Field,
        request: HttpRequest,
        **kwargs: Any,
    ) -> Any:
        """Filter choices to current tenant."""
        from .context import get_current_tenant
        tenant = get_current_tenant()

        if tenant is None:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == 'project':
            kwargs['queryset'] = Project.objects.filter(tenant=tenant)

        elif db_field.name == 'assignee':
            from .models import TenantMembership
            user_ids = TenantMembership.objects.filter(
                tenant=tenant,
                is_active=True,
            ).values_list('user_id', flat=True)
            kwargs['queryset'] = User.objects.filter(id__in=user_ids)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Custom admin action
@admin.action(description='Archive selected projects')
def archive_projects(
    modeladmin: admin.ModelAdmin[Project],
    request: HttpRequest,
    queryset: QuerySet[Project],
) -> None:
    """Archive multiple projects at once."""
    queryset.update(is_archived=True)

    count = queryset.count()
    modeladmin.message_user(
        request,
        f"Successfully archived {count} project(s).",
    )

ProjectAdmin.actions = [archive_projects]  # type: ignore[misc]
```

---

## Testing Multi-Tenant Code with Types

### Test Utilities

```python
from django.test import TestCase, TransactionTestCase
from typing import TYPE_CHECKING, TypeVar, cast
import pytest

if TYPE_CHECKING:
    from .models import Tenant, User, TenantMembership, Project, Task

T = TypeVar('T', bound='TenantAwareModel')


class TenantTestCase(TestCase):
    """
    Base test case for multi-tenant tests.

    Provides utilities for creating tenants and setting context.
    """

    tenant1: 'Tenant'
    tenant2: 'Tenant'
    user1: 'User'
    user2: 'User'

    @classmethod
    def setUpTestData(cls) -> None:
        """Create test tenants and users."""
        super().setUpTestData()

        from .models import Tenant, User, TenantMembership

        # Create tenants
        cls.tenant1 = Tenant.objects.create(
            slug='tenant1',
            name='Tenant 1',
            tier='pro',
        )
        cls.tenant2 = Tenant.objects.create(
            slug='tenant2',
            name='Tenant 2',
            tier='free',
        )

        # Create users
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123',
        )
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123',
        )

        # Create memberships
        TenantMembership.objects.create(
            tenant=cls.tenant1,
            user=cls.user1,
            role='owner',
        )
        TenantMembership.objects.create(
            tenant=cls.tenant2,
            user=cls.user2,
            role='owner',
        )

    def setUp(self) -> None:
        """Set up tenant context for each test."""
        super().setUp()

        # Clear any existing context
        from .context import clear_current_tenant
        clear_current_tenant()

    def set_tenant(self, tenant: 'Tenant', user: 'User | None' = None) -> None:
        """Set tenant context for test."""
        from .context import set_current_tenant
        from .models import TenantMembership

        membership = None
        if user is not None:
            membership = TenantMembership.objects.filter(
                tenant=tenant,
                user=user,
            ).first()

        set_current_tenant(tenant, user, membership)


class TenantIsolationTests(TenantTestCase):
    """Test that tenant isolation works correctly."""

    def test_queryset_filtered_to_tenant(self) -> None:
        """Test that querysets are automatically filtered to current tenant."""
        from .models import Project
        from .context import tenant_context

        # Create projects in different tenants
        with tenant_context(self.tenant1):
            project1 = Project.objects.create(
                name='Project 1',
                owner=self.user1,
            )

        with tenant_context(self.tenant2):
            project2 = Project.objects.create(
                name='Project 2',
                owner=self.user2,
            )

        # Query in tenant1 context
        with tenant_context(self.tenant1):
            projects = list(Project.objects.all())
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].id, project1.id)

        # Query in tenant2 context
        with tenant_context(self.tenant2):
            projects = list(Project.objects.all())
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].id, project2.id)

    def test_cannot_access_cross_tenant_object(self) -> None:
        """Test that direct access to wrong tenant's object fails."""
        from .models import Project
        from .context import tenant_context

        # Create project in tenant1
        with tenant_context(self.tenant1):
            project1 = Project.objects.create(
                name='Project 1',
                owner=self.user1,
            )

        # Try to access from tenant2
        with tenant_context(self.tenant2):
            with self.assertRaises(Project.DoesNotExist):
                Project.objects.get(pk=project1.pk)

    def test_create_without_tenant_context_fails(self) -> None:
        """Test that creating objects without tenant context fails."""
        from .models import Project
        from .context import clear_current_tenant

        clear_current_tenant()

        with self.assertRaises(ValueError):
            Project.objects.create(
                name='Project',
                owner=self.user1,
            )

    def test_cross_tenant_foreign_key_validation(self) -> None:
        """Test that foreign keys cannot reference other tenants."""
        from .models import Project, Task
        from .context import tenant_context
        from django.core.exceptions import ValidationError

        # Create project in tenant1
        with tenant_context(self.tenant1):
            project1 = Project.objects.create(
                name='Project 1',
                owner=self.user1,
            )

        # Try to create task in tenant2 pointing to tenant1's project
        with tenant_context(self.tenant2):
            task = Task(
                project=project1,  # Wrong tenant!
                title='Task',
            )

            with self.assertRaises(ValidationError):
                task.full_clean()


class PerformanceTests(TenantTestCase):
    """Test performance patterns and query optimization."""

    def test_queryset_uses_tenant_index(self) -> None:
        """Test that queries use tenant index."""
        from .models import Project
        from .context import tenant_context
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        # Create some projects
        with tenant_context(self.tenant1):
            for i in range(10):
                Project.objects.create(
                    name=f'Project {i}',
                    owner=self.user1,
                )

        # Query and check SQL
        with tenant_context(self.tenant1):
            with CaptureQueriesContext(connection) as ctx:
                list(Project.objects.all())

                # Should only be one query
                self.assertEqual(len(ctx.captured_queries), 1)

                # Query should include tenant filter
                sql = ctx.captured_queries[0]['sql']
                self.assertIn('tenant_id', sql)

    def test_bulk_create_sets_tenant(self) -> None:
        """Test that bulk_create sets tenant correctly."""
        from .models import Project
        from .context import tenant_context

        with tenant_context(self.tenant1):
            projects = [
                Project(name=f'Project {i}', owner=self.user1)
                for i in range(100)
            ]

            created = Project.objects.bulk_create(projects)

            # All should have tenant set
            for project in created:
                self.assertEqual(project.tenant_id, self.tenant1.id)


@pytest.fixture
def tenant1() -> 'Tenant':
    """Pytest fixture for tenant1."""
    from .models import Tenant
    return Tenant.objects.create(slug='test1', name='Test Tenant 1')


@pytest.fixture
def tenant2() -> 'Tenant':
    """Pytest fixture for tenant2."""
    from .models import Tenant
    return Tenant.objects.create(slug='test2', name='Test Tenant 2')


@pytest.fixture
def user(tenant1: 'Tenant') -> 'User':
    """Pytest fixture for user with tenant membership."""
    from .models import User, TenantMembership

    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='password',
    )

    TenantMembership.objects.create(
        tenant=tenant1,
        user=user,
        role='owner',
    )

    return user


@pytest.mark.django_db
def test_tenant_isolation_with_pytest(tenant1: 'Tenant', tenant2: 'Tenant') -> None:
    """Test tenant isolation using pytest."""
    from .models import Project
    from .context import tenant_context

    # Create projects
    with tenant_context(tenant1):
        project1 = Project.objects.create(name='P1', owner=user)

    with tenant_context(tenant2):
        project2 = Project.objects.create(name='P2', owner=user)

    # Verify isolation
    with tenant_context(tenant1):
        assert Project.objects.count() == 1
        assert Project.objects.first().id == project1.id

    with tenant_context(tenant2):
        assert Project.objects.count() == 1
        assert Project.objects.first().id == project2.id
```

---

## Performance Patterns with Type Safety

### Query Optimization

```python
from django.db import models
from django.db.models import Prefetch, Q, F, Count, Exists, OuterRef
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Project, Task, User


class OptimizedQueryPatterns:
    """
    Collection of optimized query patterns for multi-tenant apps.

    All patterns maintain type safety and tenant isolation.
    """

    @staticmethod
    def get_projects_with_tasks(tenant: 'Tenant') -> ProjectQuerySet:
        """
        Get projects with their tasks efficiently.

        Uses prefetch_related to avoid N+1 queries.
        """
        from .models import Project, Task
        from .context import tenant_context

        with tenant_context(tenant):
            return Project.objects.prefetch_related(
                Prefetch(
                    'tasks',
                    queryset=Task.objects.select_related('assignee'),
                )
            )

    @staticmethod
    def get_projects_with_counts(tenant: 'Tenant') -> ProjectQuerySet:
        """
        Get projects with task counts efficiently.

        Uses annotations to count in database.
        """
        from .models import Project
        from .context import tenant_context

        with tenant_context(tenant):
            return Project.objects.annotate(
                total_tasks=Count('tasks'),
                open_tasks=Count('tasks', filter=Q(tasks__status__in=['todo', 'in_progress'])),
                done_tasks=Count('tasks', filter=Q(tasks__status='done')),
            )

    @staticmethod
    def get_users_with_task_counts(tenant: 'Tenant') -> QuerySet['User']:
        """
        Get users with their task counts in tenant.

        Filters tasks to current tenant to maintain isolation.
        """
        from .models import User, TenantMembership
        from .context import tenant_context

        with tenant_context(tenant):
            # Get users in tenant
            user_ids = TenantMembership.objects.filter(
                tenant=tenant,
                is_active=True,
            ).values_list('user_id', flat=True)

            return User.objects.filter(
                id__in=user_ids
            ).annotate(
                assigned_tasks=Count(
                    'assigned_tasks',
                    filter=Q(assigned_tasks__tenant=tenant),
                ),
                open_tasks=Count(
                    'assigned_tasks',
                    filter=Q(
                        assigned_tasks__tenant=tenant,
                        assigned_tasks__status__in=['todo', 'in_progress'],
                    ),
                ),
            )

    @staticmethod
    def get_overdue_tasks(tenant: 'Tenant') -> TaskQuerySet:
        """
        Get overdue tasks efficiently.

        Uses database-level date comparison.
        """
        from .models import Task
        from .context import tenant_context
        from django.utils import timezone

        today = timezone.now().date()

        with tenant_context(tenant):
            return Task.objects.filter(
                due_date__lt=today,
                status__in=['todo', 'in_progress'],
            ).select_related(
                'project',
                'assignee',
            )

    @staticmethod
    def get_projects_with_recent_activity(
        tenant: 'Tenant',
        days: int = 7,
    ) -> ProjectQuerySet:
        """
        Get projects with recent task updates.

        Uses subquery with Exists for efficiency.
        """
        from .models import Project, Task
        from .context import tenant_context
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=days)

        # Subquery to check for recent tasks
        recent_tasks = Task.objects.filter(
            project=OuterRef('pk'),
            updated_at__gte=cutoff,
        )

        with tenant_context(tenant):
            return Project.objects.filter(
                Exists(recent_tasks)
            ).select_related('owner')


class CachingPatterns:
    """
    Caching patterns for multi-tenant applications.

    Ensures cache keys include tenant to avoid leaks.
    """

    @staticmethod
    def get_cache_key(tenant: 'Tenant', key: str) -> str:
        """
        Generate tenant-specific cache key.

        Always include tenant ID to prevent cross-tenant cache hits.
        """
        return f"tenant:{tenant.id}:{key}"

    @staticmethod
    def cache_project_data(project: 'Project') -> None:
        """Cache project data with tenant-specific key."""
        from django.core.cache import cache

        key = CachingPatterns.get_cache_key(
            project.tenant,
            f"project:{project.id}",
        )

        cache.set(key, {
            'id': project.id,
            'name': project.name,
            'description': project.description,
        }, timeout=300)  # 5 minutes

    @staticmethod
    def get_cached_project_data(
        tenant: 'Tenant',
        project_id: int,
    ) -> dict[str, Any] | None:
        """Get cached project data."""
        from django.core.cache import cache

        key = CachingPatterns.get_cache_key(tenant, f"project:{project_id}")
        return cache.get(key)


class BatchOperationPatterns:
    """
    Patterns for efficient batch operations with tenant safety.
    """

    @staticmethod
    def bulk_update_status(
        tenant: 'Tenant',
        task_ids: list[int],
        new_status: str,
    ) -> int:
        """
        Bulk update task status with tenant validation.

        Returns number of tasks updated.
        """
        from .models import Task
        from .context import tenant_context

        with tenant_context(tenant):
            # Filter ensures only tenant's tasks are updated
            return Task.objects.filter(
                id__in=task_ids
            ).update(status=new_status)

    @staticmethod
    def bulk_assign_tasks(
        tenant: 'Tenant',
        task_ids: list[int],
        assignee: 'User',
    ) -> int:
        """
        Bulk assign tasks to user with validation.

        Validates user is member of tenant before assigning.
        """
        from .models import Task, TenantMembership
        from .context import tenant_context

        # Verify assignee is member
        if not TenantMembership.objects.filter(
            tenant=tenant,
            user=assignee,
            is_active=True,
        ).exists():
            raise ValueError("User is not member of tenant")

        with tenant_context(tenant):
            return Task.objects.filter(
                id__in=task_ids
            ).update(assignee=assignee)


# Example usage in views
def project_list_optimized(request: HttpRequest) -> HttpResponse:
    """Example view using optimized queries."""
    from django.shortcuts import render

    tenant = request.tenant  # type: Tenant

    # Get projects with counts - single query with annotations
    projects = OptimizedQueryPatterns.get_projects_with_counts(tenant)

    return render(request, 'projects/list.html', {
        'projects': projects,
        'tenant': tenant,
    })
```

---

## Common Pitfalls

### Pitfall 1: Forgetting Tenant Context

```python
# BAD: No tenant context set
def bad_create_project(name: str, owner: User) -> Project:
    """This will fail or create objects in wrong tenant!"""
    return Project.objects.create(name=name, owner=owner)

# GOOD: Use tenant context
def good_create_project(tenant: Tenant, name: str, owner: User) -> Project:
    """Explicitly set tenant context."""
    from .context import tenant_context

    with tenant_context(tenant):
        return Project.objects.create(name=name, owner=owner)

# BETTER: Use decorator
@require_tenant_context_decorator
def better_create_project(name: str, owner: User) -> Project:
    """Decorator ensures tenant context exists."""
    return Project.objects.create(name=name, owner=owner)
```

### Pitfall 2: Using all_tenants() Without Caution

```python
# BAD: Exposes all tenant data
def bad_get_all_projects() -> QuerySet[Project]:
    """Returns projects from ALL tenants - data leak!"""
    return Project.objects.all_tenants()

# GOOD: Only use for superuser operations
def good_get_all_projects_for_admin(user: User) -> QuerySet[Project]:
    """Safely get all projects for superuser."""
    if not user.is_superuser:
        raise PermissionError("Only superusers can access all tenants")

    return Project.objects.all_tenants()
```

### Pitfall 3: Not Validating Cross-Tenant References

```python
# BAD: No validation
def bad_assign_task(task: Task, assignee: User) -> None:
    """Might assign user from different tenant!"""
    task.assignee = assignee
    task.save()

# GOOD: Validate tenant membership
def good_assign_task(task: Task, assignee: User) -> None:
    """Validate assignee belongs to task's tenant."""
    from .models import TenantMembership

    if not TenantMembership.objects.filter(
        tenant=task.tenant,
        user=assignee,
        is_active=True,
    ).exists():
        raise ValueError("Assignee must be member of task's tenant")

    task.assignee = assignee
    task.save()
```

### Pitfall 4: Cache Key Collisions

```python
# BAD: Cache keys without tenant
def bad_cache_project(project: Project) -> None:
    """Cache key might collide across tenants!"""
    from django.core.cache import cache
    cache.set(f"project:{project.id}", project)

# GOOD: Include tenant in cache key
def good_cache_project(project: Project) -> None:
    """Tenant-specific cache key prevents collisions."""
    from django.core.cache import cache
    key = f"tenant:{project.tenant_id}:project:{project.id}"
    cache.set(key, project)
```

### Pitfall 5: Bulk Operations Without Tenant Filter

```python
# BAD: Updates across all tenants
def bad_bulk_update(task_ids: list[int], status: str) -> None:
    """Updates tasks from ANY tenant!"""
    Task.objects.filter(id__in=task_ids).update(status=status)

# GOOD: Filter to current tenant
def good_bulk_update(task_ids: list[int], status: str) -> None:
    """Only updates tasks in current tenant."""
    from .context import require_tenant

    tenant = require_tenant()
    Task.objects.filter(
        tenant=tenant,
        id__in=task_ids,
    ).update(status=status)
```

---

## Best Practices

### 1. Always Use Type Hints

```python
# Type all tenant-related functions
def create_project_for_tenant(
    tenant: Tenant,
    name: str,
    owner: User,
) -> Project:
    """Explicit types make intent clear."""
    ...

# Type manager and queryset methods
class ProjectManager(TenantManager[Project]):
    def active(self) -> ProjectQuerySet:
        """Return type makes chaining safe."""
        ...
```

### 2. Use Context Managers for Tenant Operations

```python
# Good: Explicit context boundaries
with tenant_context(tenant):
    project = Project.objects.create(name="New Project")
    task = Task.objects.create(project=project, title="Task 1")

# Also good: Decorator for functions
@with_tenant(tenant)
def create_project_data() -> tuple[Project, list[Task]]:
    project = Project.objects.create(name="New Project")
    tasks = [
        Task.objects.create(project=project, title=f"Task {i}")
        for i in range(10)
    ]
    return project, tasks
```

### 3. Add Database Constraints

```python
class Meta:
    constraints = [
        # Ensure FK references match tenant
        CheckConstraint(
            check=Q(tenant=F('project__tenant')),
            name='task_project_same_tenant',
        ),

        # Unique constraints should include tenant
        UniqueConstraint(
            fields=['tenant', 'name'],
            name='unique_project_name_per_tenant',
        ),
    ]
```

### 4. Test Tenant Isolation Thoroughly

```python
class TenantIsolationTests(TenantTestCase):
    """Always test isolation at boundaries."""

    def test_cannot_see_other_tenant_data(self) -> None:
        """Verify queries don't leak across tenants."""
        ...

    def test_cannot_create_cross_tenant_references(self) -> None:
        """Verify FK validation prevents cross-tenant refs."""
        ...

    def test_bulk_operations_respect_tenant(self) -> None:
        """Verify bulk operations are tenant-safe."""
        ...
```

### 5. Use Protocol Types for Flexibility

```python
def process_tenant_aware_object(obj: TenantAwareProtocol) -> None:
    """Accept any tenant-aware object."""
    print(f"Processing {obj} for tenant {obj.tenant.name}")

# Works with any model that has tenant attribute
process_tenant_aware_object(project)
process_tenant_aware_object(task)
```

### 6. Monitor Performance with Tenant-Specific Metrics

```python
def log_query_performance(tenant: Tenant, operation: str, duration: float) -> None:
    """Log performance metrics per tenant."""
    logger.info(
        "tenant_query",
        extra={
            'tenant_id': tenant.id,
            'tenant_slug': tenant.slug,
            'operation': operation,
            'duration_ms': duration * 1000,
        }
    )
```

### 7. Document Tenant Assumptions

```python
def process_user_data(user: User) -> None:
    """
    Process user data within current tenant context.

    REQUIRES: Tenant context must be set before calling.
    ENSURES: Only processes data from current tenant.
    RAISES: RuntimeError if no tenant context set.
    """
    tenant = require_tenant()
    # Process data...
```

---

## Conclusion

Multi-tenant Django applications require careful attention to:

1. **Type Safety**: Use generic types, protocols, and type variables to ensure tenant operations are type-safe
2. **Isolation**: Automatically filter queries to current tenant and validate cross-tenant references
3. **Context Management**: Use context variables and context managers for thread-safe tenant access
4. **Performance**: Optimize queries with proper indexes, annotations, and prefetching
5. **Testing**: Thoroughly test tenant isolation at all boundaries
6. **Database Constraints**: Use CHECK constraints for defense-in-depth

Following these patterns ensures your multi-tenant application is:
- Safe from data leaks between tenants
- Type-safe throughout the codebase
- Performant with proper query optimization
- Testable with clear tenant boundaries
- Maintainable with explicit typing and validation

Remember: **Tenant isolation is a security requirement, not just a feature**. Use types, database constraints, and thorough testing to ensure isolation is maintained throughout your application.

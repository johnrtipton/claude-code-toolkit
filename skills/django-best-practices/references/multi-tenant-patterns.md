# Multi-Tenant Architecture Patterns

This reference documents the multi-tenant architecture patterns used in this Django project.

## Overview

The project implements **row-level multi-tenancy** where all data is scoped to a `Tenant`. Data isolation is enforced at multiple layers:

1. **Database layer**: Foreign key constraints
2. **Application layer**: Middleware sets tenant context
3. **View layer**: QuerySets automatically filtered by tenant
4. **Model layer**: Validation ensures tenant consistency

## Base Models

### TenantBaseModel

Abstract base class for all tenant-scoped models. Provides:

- `tenant` ForeignKey field
- Automatic tenant filtering via `TenantManager`
- Validation that tenant is set
- Helper methods for tenant operations

```python
from apps.core.models.base import TenantBaseModel

class MyModel(TenantBaseModel):
    name = models.CharField(max_length=100)
    # tenant field inherited automatically
    # objects manager automatically filters by tenant
```

**Key Features:**
- `tenant` field with CASCADE delete
- `objects` manager returns `TenantQuerySet` (auto-filtered)
- `all_objects` manager bypasses tenant filter (admin only!)
- Auto-sets tenant from current context on save()
- Validates tenant is set before saving

### TenantAwareModel

Extended base class that adds common timestamp fields:

```python
from apps.core.models.base import TenantAwareModel

class MyModel(TenantAwareModel):
    name = models.CharField(max_length=100)
    # Inherits: id (UUID), tenant, created_at, updated_at
```

**Adds:**
- `id` - UUIDField primary key
- `created_at` - DateTimeField (auto_now_add)
- `updated_at` - DateTimeField (auto_now)
- Default ordering by `-created_at`

## Tenant QuerySet and Manager

### TenantQuerySet

Automatically filters queries by current tenant from thread-local storage.

```python
# Automatic filtering
MyModel.objects.all()  # Filtered by request.tenant

# Bypass filter (admin only!)
MyModel.objects.unfiltered().all()  # See all tenants

# Explicit tenant filter
MyModel.objects.for_tenant(specific_tenant)
```

### TenantManager

Returns `TenantQuerySet` with automatic tenant filtering.

```python
class MyModel(TenantBaseModel):
    name = models.CharField(max_length=100)

    # Default manager - auto-filtered by tenant
    objects = TenantManager()  # Inherited from TenantBaseModel

    # Unfiltered manager for admin
    all_objects = models.Manager()  # Inherited from TenantBaseModel
```

## Middleware Integration

`TenantMiddleware` sets tenant context from authenticated user:

```python
# In settings.py
MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.users.middleware.TenantMiddleware',  # After auth!
    ...
]
```

The middleware:
1. Checks if user is authenticated
2. Gets tenant from `request.user.profile.tenant`
3. Sets `request.tenant`
4. Stores tenant in thread-local storage via `set_current_tenant()`

## Getting Current Tenant

```python
from apps.users.middleware import get_current_tenant

# In views/serializers/models
tenant = get_current_tenant()

# Or from request
tenant = request.tenant
```

## Model Patterns

### Inheriting from TenantBaseModel

**DO:**
```python
from apps.core.models.base import TenantAwareModel

class Conversation(TenantAwareModel):
    """Conversations are tenant-scoped."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    class Meta:
        indexes = [
            # Put tenant first for query optimization
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'workspace', '-created_at']),
        ]
        unique_together = [
            # Include tenant in unique constraints
            ['tenant', 'workspace', 'slug'],
        ]
```

**DON'T:**
```python
# ❌ Don't add tenant field manually
class Conversation(models.Model):
    tenant = models.ForeignKey(Tenant, ...)  # TenantBaseModel provides this!
```

### Tenant Consistency Validation

Ensure related objects belong to same tenant:

```python
from apps.core.models.base import TenantAwareModel
from django.core.exceptions import ValidationError

class Conversation(TenantAwareModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)

    def clean(self):
        super().clean()

        # Validate workspace belongs to same tenant
        if self.workspace and self.tenant:
            if self.workspace.tenant != self.tenant:
                raise ValidationError({
                    'workspace': 'Workspace must belong to the same tenant'
                })

        # Validate user belongs to same tenant
        if self.user and self.tenant and hasattr(self.user, 'profile'):
            if self.user.profile.tenant != self.tenant:
                raise ValidationError({
                    'user': 'User must belong to the same tenant'
                })
```

### Auto-Setting Tenant

Automatically set tenant from related objects:

```python
def save(self, *args, **kwargs):
    # TenantBaseModel already tries to set from current context
    # But we can also set from related objects
    if not self.tenant_id and self.workspace:
        self.tenant = self.workspace.tenant

    # Or from user
    if not self.tenant_id and self.user and hasattr(self.user, 'profile'):
        self.tenant = self.user.profile.tenant

    super().save(*args, **kwargs)
```

## Index Strategy

**Always put `tenant` first in composite indexes:**

```python
class Meta:
    indexes = [
        # ✅ Tenant first - efficient filtering
        models.Index(fields=['tenant', 'user', '-created_at']),
        models.Index(fields=['tenant', 'workspace', '-created_at']),
        models.Index(fields=['tenant', 'status', '-updated_at']),

        # ❌ Don't put tenant last
        # models.Index(fields=['user', '-created_at', 'tenant']),
    ]
```

**Why tenant-first?**
- PostgreSQL uses leftmost index columns first
- Queries filter by tenant in WHERE clause
- Enables partition pruning if using table partitioning
- Prevents cross-tenant data access

## Unique Constraints

**Include `tenant` in all unique constraints:**

```python
class Meta:
    unique_together = [
        ['tenant', 'user', 'slug'],  # Slug unique per user per tenant
        ['tenant', 'workspace', 'name'],  # Name unique per workspace per tenant
    ]

    # Or use UniqueConstraint for more control
    constraints = [
        models.UniqueConstraint(
            fields=['tenant', 'external_id'],
            name='unique_tenant_external_id'
        ),
    ]
```

## Querying Patterns

### Basic Queries (Automatic Filtering)

```python
# All automatically filtered by current tenant
conversations = Conversation.objects.all()
my_conversations = Conversation.objects.filter(user=request.user)
workspace_conversations = Conversation.objects.filter(workspace=workspace)
```

### Admin/Superuser Queries

```python
# View all tenants (use sparingly!)
all_conversations = Conversation.objects.unfiltered().all()

# Query specific tenant
tenant = Tenant.objects.get(slug='acme')
tenant_conversations = Conversation.objects.unfiltered().for_tenant(tenant)
```

### Related Object Queries

```python
# Related queries also respect tenant filtering
workspace = Workspace.objects.get(id=workspace_id)
conversations = workspace.conversations.all()  # Auto-filtered by tenant

# Reverse relations
user = request.user
conversations = user.conversation_set.all()  # Auto-filtered
```

## Testing Multi-Tenancy

```python
from apps.users.models import Tenant
from apps.users.middleware import set_current_tenant

def test_tenant_isolation():
    # Create two tenants
    tenant1 = Tenant.objects.create(name="Acme Corp", slug="acme")
    tenant2 = Tenant.objects.create(name="Globex Inc", slug="globex")

    # Set tenant context for tenant1
    set_current_tenant(tenant1)

    # Create data for tenant1
    conversation1 = Conversation.objects.create(
        title="Tenant 1 Conv",
        # tenant auto-set from context
    )

    # Switch to tenant2
    set_current_tenant(tenant2)

    # Verify isolation - shouldn't see tenant1 data
    assert Conversation.objects.count() == 0
    assert not Conversation.objects.filter(id=conversation1.id).exists()

    # Create data for tenant2
    conversation2 = Conversation.objects.create(title="Tenant 2 Conv")

    # Verify each tenant sees only their data
    assert Conversation.objects.count() == 1

    # Admin view - see all
    set_current_tenant(None)
    assert Conversation.objects.unfiltered().count() == 2
```

## Common Pitfalls

### ❌ Don't Query Without Tenant Context

```python
# ❌ Bad - no tenant context
conversation = Conversation.objects.create(title="Test")
# Will fail! Tenant not set

# ✅ Good - tenant set from context
from apps.users.middleware import set_current_tenant
set_current_tenant(some_tenant)
conversation = Conversation.objects.create(title="Test")
```

### ❌ Don't Use `all_objects` in Views

```python
# ❌ Bad - bypasses tenant filter in view!
def my_view(request):
    conversations = Conversation.all_objects.all()  # Sees all tenants!

# ✅ Good - use default objects manager
def my_view(request):
    conversations = Conversation.objects.all()  # Auto-filtered
```

### ❌ Don't Forget Tenant in Unique Constraints

```python
# ❌ Bad - slug unique globally
class Meta:
    unique_together = [['user', 'slug']]

# ✅ Good - slug unique per tenant
class Meta:
    unique_together = [['tenant', 'user', 'slug']]
```

### ❌ Don't Create Cross-Tenant References

```python
# ❌ Bad - workspace from different tenant
conversation = Conversation.objects.create(
    workspace=workspace,  # workspace.tenant != current tenant
)
# Will fail validation in clean()

# ✅ Good - ensure same tenant
assert workspace.tenant == request.tenant
conversation = Conversation.objects.create(workspace=workspace)
```

## Security Considerations

1. **Always use TenantBaseModel** for tenant-scoped data
2. **Never use `all_objects` in views** - only in admin
3. **Validate tenant consistency** in `clean()` methods
4. **Include tenant in all indexes** for query optimization
5. **Test tenant isolation** in test suites
6. **Audit cross-tenant access attempts**
7. **Use PostgreSQL RLS** (Row-Level Security) for defense in depth

## Migration Pattern

When adding tenant support to existing models:

### Step 1: Add Nullable Tenant FK

```python
class Migration(migrations.Migration):
    dependencies = [...]

    operations = [
        migrations.AddField(
            model_name='mymodel',
            name='tenant',
            field=models.ForeignKey(
                'users.Tenant',
                on_delete=models.CASCADE,
                null=True,  # Nullable for migration
                blank=True
            ),
        ),
    ]
```

### Step 2: Assign Default Tenant

```python
def assign_default_tenant(apps, schema_editor):
    Tenant = apps.get_model('users', 'Tenant')
    MyModel = apps.get_model('myapp', 'MyModel')

    # Get or create default tenant
    default_tenant, _ = Tenant.objects.get_or_create(
        slug='default',
        defaults={'name': 'Default Organization'}
    )

    # Assign to all existing records
    MyModel.objects.filter(tenant__isnull=True).update(tenant=default_tenant)

class Migration(migrations.Migration):
    dependencies = [('myapp', '0001_add_tenant_field')]

    operations = [
        migrations.RunPython(assign_default_tenant),
    ]
```

### Step 3: Make Tenant Required

```python
class Migration(migrations.Migration):
    dependencies = [('myapp', '0002_assign_default_tenant')]

    operations = [
        migrations.AlterField(
            model_name='mymodel',
            name='tenant',
            field=models.ForeignKey(
                'users.Tenant',
                on_delete=models.CASCADE,
                null=False  # Now required
            ),
        ),
    ]
```

### Step 4: Add Indexes and Constraints

```python
class Migration(migrations.Migration):
    dependencies = [('myapp', '0003_make_tenant_required')]

    operations = [
        # Add tenant-first indexes
        migrations.AddIndex(
            model_name='mymodel',
            index=models.Index(fields=['tenant', 'user', '-created_at']),
        ),
        # Update unique constraints to include tenant
        migrations.AlterUniqueTogether(
            name='mymodel',
            unique_together={('tenant', 'user', 'slug')},
        ),
    ]
```

### Step 5: Switch to TenantBaseModel

```python
# In models.py - after migrations complete
from apps.core.models.base import TenantBaseModel

class MyModel(TenantBaseModel):  # Changed from models.Model
    # Remove tenant field definition - inherited from base
    # tenant = models.ForeignKey(...)  # DELETE THIS

    name = models.CharField(max_length=100)
    # ... other fields
```

## Summary

**Key Principles:**
1. All tenant-scoped models inherit from `TenantBaseModel` or `TenantAwareModel`
2. Tenant context set by middleware from authenticated user
3. QuerySets automatically filtered by current tenant
4. Indexes and constraints include tenant
5. Validate tenant consistency across related objects
6. Test tenant isolation thoroughly
7. Use `all_objects` manager only in admin code

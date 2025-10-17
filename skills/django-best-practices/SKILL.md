---
name: django-best-practices
description: This skill should be used when working with Django models, admin interfaces, tests, or migrations in this multi-tenant Django project. It provides templates, patterns, and best practices for creating tenant-aware models with proper isolation, admin interfaces with optimized queries, and comprehensive tests. Use when creating new Django models, admin configurations, writing tests, or when you need to follow the multi-tenant architecture patterns used in this codebase.
---

# Django Best Practices

Guide for creating Django models, admin interfaces, and tests following the multi-tenant architecture and best practices used in this project.

## Overview

Create Django models, admin interfaces, and tests that follow the multi-tenant architecture patterns established in this codebase. All models should inherit from `TenantBaseModel` or `TenantAwareModel` to ensure proper data isolation, and all code should follow Django best practices for performance, security, and maintainability.

## When to Use This Skill

Use this skill when:
- Creating a new Django model
- Building an admin interface for a model
- Writing tests for models or views
- Working with multi-tenant data isolation
- Optimizing Django queries
- Creating migrations for multi-tenant models
- Needing to understand the multi-tenant patterns in this project

## Quick Start

### Creating a New Model

1. **Use the model template** from `assets/model_template.py` or generate boilerplate with the script
2. **Inherit from `TenantAwareModel`** for automatic tenant support
3. **Create proper indexes** (tenant-first for all composite indexes!)
4. **Add validation** in `clean()` method for cross-field validation
5. **Create admin interface** using `assets/admin_template.py`
6. **Write tests** using `assets/test_template.py`

### Quick Generation Script

Use the generation script to create boilerplate quickly:

```bash
python scripts/generate_model.py notifications Notification \
    --description "Represents a user notification" \
    --with-admin \
    --with-tests
```

This generates:
- Model code with multi-tenant support
- Admin interface with optimized queries
- Comprehensive test suite

## Core Concepts

### Multi-Tenant Architecture

All data in this project is scoped to a `Tenant` (organization). The architecture enforces isolation at multiple layers:

**Base Models:**
- `TenantBaseModel` - Provides `tenant` FK and automatic filtering
- `TenantAwareModel` - Adds UUID `id`, `created_at`, `updated_at` timestamps

**Key Patterns:**
- Tenant context set by middleware from `request.user.profile.tenant`
- QuerySets automatically filtered by current tenant via `TenantManager`
- Indexes always put `tenant` first in composite indexes
- Unique constraints include `tenant` field
- Validation ensures cross-tenant references don't occur

**Read the detailed guide:** `references/multi-tenant-patterns.md`

### Model Best Practices

**Standard Model Structure:**
1. Inherit from `TenantAwareModel`
2. Define fields with `help_text`
3. Set up relationships with explicit `related_name`
4. Configure Meta with indexes (tenant-first!), constraints, ordering
5. Implement `__str__` and `__repr__`
6. Override `save()` for auto-population logic
7. Implement `clean()` for validation
8. Add business logic methods

**Read the detailed guide:** `references/model-patterns.md`

### Admin Interface Best Practices

**Standard Admin Configuration:**
1. Use `@admin.register()` decorator
2. Configure `list_display`, `list_filter`, `search_fields`
3. Optimize with `list_select_related` or `get_queryset()`
4. Organize form with `fieldsets`
5. Mark metadata as `readonly_fields`
6. Use `raw_id_fields` or `autocomplete_fields` for ForeignKeys
7. Add custom actions for bulk operations
8. Filter by tenant for non-superusers

**Read the detailed guide:** `references/admin-patterns.md`

## Creating a New Model

### Step 1: Choose Your Base Class

```python
from apps.core.models.base import TenantAwareModel  # Recommended

class MyModel(TenantAwareModel):
    """
    Your model description.

    Inherits:
    - id (UUIDField)
    - tenant (ForeignKey)
    - created_at, updated_at (DateTimeField)
    """
    pass
```

### Step 2: Define Fields

```python
class MyModel(TenantAwareModel):
    # Core fields
    name = models.CharField(max_length=200, help_text='...')
    slug = models.SlugField(max_length=200, help_text='...')

    # Relationships
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='mymodel_set'
    )
    workspace = models.ForeignKey(
        'workspace.Workspace',
        on_delete=models.CASCADE,
        related_name='mymodels'
    )

    # Status
    is_active = models.BooleanField(default=True)
```

### Step 3: Configure Meta

```python
class Meta:
    db_table = 'app_mymodel'
    verbose_name = 'My Model'
    ordering = ['-created_at']

    # Indexes - TENANT FIRST!
    indexes = [
        models.Index(fields=['tenant', 'user', '-created_at']),
        models.Index(fields=['tenant', 'workspace', '-created_at']),
    ]

    # Constraints - include tenant
    constraints = [
        models.UniqueConstraint(
            fields=['tenant', 'workspace', 'slug'],
            name='unique_mymodel_slug'
        ),
    ]
```

### Step 4: Add Methods

```python
def __str__(self):
    return f"{self.name} ({self.workspace.name})"

def save(self, *args, **kwargs):
    """Auto-populate fields."""
    if not self.slug:
        from django.utils.text import slugify
        self.slug = slugify(self.name)

    if not self.tenant_id and self.workspace:
        self.tenant = self.workspace.tenant

    super().save(*args, **kwargs)

def clean(self):
    """Validate data."""
    super().clean()

    # Validate tenant consistency
    if self.workspace and self.tenant:
        if self.workspace.tenant != self.tenant:
            raise ValidationError({
                'workspace': 'Must belong to same tenant'
            })
```

## Creating an Admin Interface

### Step 1: Basic Registration

```python
from django.contrib import admin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    """Admin interface for MyModel."""
    pass
```

### Step 2: Configure List View

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'workspace', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username', 'workspace__name']
    list_select_related = ['user', 'workspace', 'tenant']
    date_hierarchy = 'created_at'
```

### Step 3: Configure Form

```python
readonly_fields = ['id', 'created_at', 'updated_at']
raw_id_fields = ['user']
autocomplete_fields = ['workspace']

fieldsets = (
    ('Basic Information', {
        'fields': ('name', 'slug')
    }),
    ('Relationships', {
        'fields': ('user', 'workspace')
    }),
    ('Metadata', {
        'fields': ('id', 'created_at', 'updated_at'),
        'classes': ('collapse',)
    }),
)
```

### Step 4: Optimize Queries

```python
def get_queryset(self, request):
    """Optimize and filter by tenant."""
    qs = super().get_queryset(request)
    qs = qs.select_related('user', 'workspace', 'tenant')

    # Filter by tenant for non-superusers
    if not request.user.is_superuser and hasattr(request.user, 'profile'):
        qs = qs.filter(tenant=request.user.profile.tenant)

    return qs
```

### Step 5: Add Actions

```python
actions = ['activate_selected', 'deactivate_selected']

def activate_selected(self, request, queryset):
    """Activate selected records."""
    updated = queryset.update(is_active=True)
    self.message_user(request, f"Activated {updated} records")
activate_selected.short_description = "Activate selected items"
```

## Writing Tests

### Step 1: Set Up Test Case

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import Tenant, UserProfile
from apps.users.middleware import set_current_tenant
from .models import MyModel

User = get_user_model()

class MyModelTest(TestCase):
    def setUp(self):
        # Create tenant
        self.tenant = Tenant.objects.create(name="Test Org", slug="test")
        set_current_tenant(self.tenant)

        # Create user with profile
        self.user = User.objects.create_user(username='test', password='pass')
        self.user.profile = UserProfile.objects.create(
            user=self.user,
            tenant=self.tenant
        )

    def tearDown(self):
        set_current_tenant(None)
```

### Step 2: Test Basic Operations

```python
def test_create_model(self):
    """Test creating instance."""
    obj = MyModel.objects.create(
        name="Test",
        user=self.user
    )
    self.assertEqual(obj.name, "Test")
    self.assertEqual(obj.tenant, self.tenant)

def test_str_representation(self):
    """Test __str__ method."""
    obj = MyModel.objects.create(name="Test", user=self.user)
    self.assertEqual(str(obj), "Test")
```

### Step 3: Test Tenant Isolation

```python
def test_tenant_isolation(self):
    """Test multi-tenant isolation."""
    # Create object for tenant1
    obj1 = MyModel.objects.create(name="T1", user=self.user)

    # Create tenant2
    tenant2 = Tenant.objects.create(name="Org2", slug="org2")
    user2 = User.objects.create_user(username='user2', password='pass')
    user2.profile = UserProfile.objects.create(user=user2, tenant=tenant2)

    # Switch to tenant2
    set_current_tenant(tenant2)
    obj2 = MyModel.objects.create(name="T2", user=user2)

    # Verify isolation
    self.assertEqual(MyModel.objects.count(), 1)
    self.assertEqual(MyModel.objects.first(), obj2)

    # Switch back
    set_current_tenant(self.tenant)
    self.assertEqual(MyModel.objects.count(), 1)
    self.assertEqual(MyModel.objects.first(), obj1)

    # Unfiltered sees both
    set_current_tenant(None)
    self.assertEqual(MyModel.objects.unfiltered().count(), 2)
```

### Step 4: Test Validation

```python
def test_cross_tenant_validation(self):
    """Test cross-tenant reference prevention."""
    tenant2 = Tenant.objects.create(name="Org2", slug="org2")
    # ... create user2, workspace2 for tenant2

    obj = MyModel(
        name="Test",
        user=self.user,  # tenant1
        workspace=workspace2,  # tenant2
        tenant=self.tenant
    )

    with self.assertRaises(ValidationError):
        obj.clean()
```

## Common Patterns

### Pattern: Soft Delete

```python
class SoftDeleteModel(TenantAwareModel):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def delete(self, *args, **kwargs):
        """Soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
```

### Pattern: Audit Trail

```python
class AuditedModel(TenantAwareModel):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user:
            if not self.pk:
                self.created_by = user
            self.modified_by = user
        super().save(*args, **kwargs)
```

### Pattern: Custom Manager/QuerySet

```python
class MyModelQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_user(self, user):
        return self.filter(user=user)

class MyModelManager(models.Manager):
    def get_queryset(self):
        return MyModelQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

class MyModel(TenantAwareModel):
    # ... fields ...
    objects = MyModelManager()
```

## Creating and Managing Migrations

### Quick Start with Migrations

**Basic workflow:**

```bash
# 1. Make model changes in models.py

# 2. Generate migration
python manage.py makemigrations app_name

# 3. Review generated migration file

# 4. Test migration
python manage.py migrate

# 5. Test reversibility
python manage.py migrate app_name previous_migration_name
python manage.py migrate  # Re-apply
```

**Use the migration helper for validation:**

```bash
# Check status and validate
python scripts/migration_helper.py status

# Create migration with validation
python scripts/migration_helper.py create app_name

# Validate existing migrations
python scripts/migration_helper.py validate
```

### Schema Migrations

**Adding fields:**
- Provide default value or make nullable
- Consider tenant-first indexes for new fields
- Review auto-generated migration before applying

**Removing fields (two-step):**
1. Make field nullable, deploy
2. Remove field entirely in next release

**Changing field types:**
- Add new field → data migration → remove old field → rename new field

**Adding indexes:**
```python
class Meta:
    indexes = [
        # Always put tenant first!
        models.Index(fields=['tenant', 'status', '-created_at']),
    ]
```

### Data Migrations

**Create empty migration:**
```bash
python manage.py makemigrations --empty app_name --name populate_field
```

**Use the template:** Copy `assets/data_migration_template.py` for comprehensive examples.

**Key principles:**
- Always use `apps.get_model()` (never import models directly)
- Batch large updates to avoid memory issues
- Provide reverse function for reversibility
- Handle null/missing data gracefully

**Example:**
```python
def forward(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')

    for obj in MyModel.objects.iterator(chunk_size=1000):
        obj.new_field = obj.old_field.upper()
        obj.save(update_fields=['new_field'])

def reverse(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')

    for obj in MyModel.objects.iterator(chunk_size=1000):
        obj.old_field = obj.new_field.lower()
        obj.save(update_fields=['old_field'])

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward, reverse),
    ]
```

### Multi-Tenant Migration Patterns

**Adding tenant support to existing models (4-step process):**

1. Add nullable tenant FK
2. Data migration to assign default tenant
3. Make tenant required
4. Add tenant-first indexes and constraints

See `references/migration-patterns.md` for complete examples.

### Migration Best Practices

**Always do:**
- ✅ Review generated migrations before committing
- ✅ Test reversibility (migrate backward then forward)
- ✅ Use apps.get_model() in data migrations
- ✅ Put tenant first in all composite indexes
- ✅ Batch large data updates
- ✅ Test on production-like data

**Never do:**
- ❌ Edit applied migrations (create new one instead)
- ❌ Import models directly in migrations
- ❌ Skip testing reversibility
- ❌ Forget tenant in indexes/constraints
- ❌ Use --fake without understanding implications

### Migration Resources

**Checklist:** Use `assets/schema_migration_checklist.md` for common scenarios:
- Adding/removing fields
- Changing field types
- Adding indexes and constraints
- Data migrations
- Multi-tenant migrations

**Reference:** See `references/migration-patterns.md` for:
- Detailed migration patterns
- Complex scenarios
- Troubleshooting guide
- Advanced techniques

**Helper script:** `scripts/migration_helper.py` validates migrations and checks for:
- Tenant-first indexes
- Unique constraints with tenant
- Direct model imports
- Missing reverse functions
- Common pitfalls

## Critical Requirements

**Always follow these rules:**

1. ✅ **Inherit from `TenantAwareModel`** for tenant-scoped models
2. ✅ **Put `tenant` first** in all composite indexes
3. ✅ **Include `tenant`** in all unique constraints
4. ✅ **Validate tenant consistency** in `clean()` method
5. ✅ **Use `help_text`** on all fields for documentation
6. ✅ **Specify `related_name`** on all ForeignKeys
7. ✅ **Optimize admin queries** with `select_related`/`prefetch_related`
8. ✅ **Test tenant isolation** in all test suites
9. ✅ **Use `readonly_fields`** for metadata in admin
10. ✅ **Filter by tenant** for non-superusers in admin

**Never do these:**

1. ❌ **Don't use `all_objects`** manager in views (admin only!)
2. ❌ **Don't create cross-tenant references** without validation
3. ❌ **Don't forget tenant field** in indexes and constraints
4. ❌ **Don't manually add `tenant` field** (use TenantBaseModel)
5. ❌ **Don't skip `clean()` validation**
6. ❌ **Don't use N+1 queries** in admin (optimize with select_related)

## Resources

### scripts/

**`generate_model.py`** - Generate Django model boilerplate with multi-tenant support

Usage:
```bash
python scripts/generate_model.py <app_name> <model_name> [--with-admin] [--with-tests]
```

Example:
```bash
python scripts/generate_model.py notifications Notification \
    --description "User notification" \
    --with-admin \
    --with-tests
```

**`migration_helper.py`** - Django migration helper with validation and best practice checks

Usage:
```bash
# Check migration status
python scripts/migration_helper.py status

# Create migration with validation
python scripts/migration_helper.py create app_name

# Validate existing migrations
python scripts/migration_helper.py validate

# Check for conflicts
python scripts/migration_helper.py check-conflicts

# Show SQL for migration
python scripts/migration_helper.py sql app_name migration_number
```

### assets/

**Copy-paste templates for quick development:**

- `model_template.py` - Complete model template with all best practices
- `admin_template.py` - Admin interface template with optimization
- `test_template.py` - Comprehensive test suite template
- `data_migration_template.py` - Data migration template with RunPython examples
- `schema_migration_checklist.md` - Checklist for common migration scenarios

Copy these templates and customize for your specific model.

### references/

**Detailed documentation for deep understanding:**

- `multi-tenant-patterns.md` - Complete guide to multi-tenant architecture
  - TenantBaseModel and TenantAwareModel
  - TenantQuerySet and TenantManager
  - Middleware integration
  - Query patterns
  - Testing multi-tenancy
  - Multi-tenant migration patterns

- `model-patterns.md` - Django model best practices
  - Model structure and organization
  - Field patterns and choices
  - Meta options (indexes, constraints, ordering)
  - Validation patterns

- `migration-patterns.md` - Django migration comprehensive guide
  - Schema migrations (adding/removing/altering fields, indexes, constraints)
  - Data migrations (RunPython, RunSQL patterns)
  - Multi-tenant migration patterns
  - Migration dependencies and ordering
  - Reversible migrations
  - Testing migrations
  - Squashing migrations
  - Troubleshooting (conflicts, rollbacks, debugging)

- `admin-patterns.md` - Django admin best practices
  - List display and filters
  - Custom display methods
  - QuerySet optimization
  - Permissions and tenant filtering
  - Custom actions
  - Inline admin

**To access references:** Read the files when you need detailed information about specific patterns. The SKILL.md provides overview and quick patterns; references provide comprehensive details.

## Examples

### Example 1: Create a Notification Model

```python
# apps/notifications/models.py
from apps.core.models.base import TenantAwareModel
from django.db import models

class Notification(TenantAwareModel):
    """User notification."""

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True)

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'user', 'is_read', '-created_at']),
        ]
```

### Example 2: Create Admin with Bulk Actions

```python
# apps/notifications/admin.py
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"Marked {queryset.count()} as read")
    mark_as_read.short_description = "Mark selected as read"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'tenant')
```

### Example 3: Test Tenant Isolation

```python
# apps/notifications/tests.py
class NotificationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Org", slug="org")
        set_current_tenant(self.tenant)
        self.user = User.objects.create_user(username='user', password='pass')
        self.user.profile = UserProfile.objects.create(
            user=self.user,
            tenant=self.tenant
        )

    def test_isolation(self):
        n1 = Notification.objects.create(
            user=self.user,
            title="Test",
            message="Message"
        )
        self.assertEqual(n1.tenant, self.tenant)

        # Create tenant2
        tenant2 = Tenant.objects.create(name="Org2", slug="org2")
        set_current_tenant(tenant2)

        # Shouldn't see n1
        self.assertEqual(Notification.objects.count(), 0)
```

## Getting Help

If you encounter issues:

1. Check the reference documentation for detailed patterns
2. Review the templates in `assets/` for complete examples
3. Use the generation script to create boilerplate quickly
4. Ensure you're following the critical requirements checklist

The multi-tenant architecture is the foundation of this project. When in doubt, prioritize tenant isolation and data security.

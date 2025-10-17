# Django Model Patterns and Best Practices

Comprehensive guide to Django model best practices used in this project.

## Model Structure

### Standard Model Template

```python
from apps.core.models.base import TenantAwareModel
from django.db import models
from django.core.exceptions import ValidationError
import uuid

class MyModel(TenantAwareModel):
    """
    Brief description of what this model represents.

    Longer description if needed, explaining relationships,
    business logic, and usage patterns.
    """

    # ===== Identity Fields =====
    # id, tenant, created_at, updated_at inherited from TenantAwareModel

    # ===== Core Fields =====
    name = models.CharField(
        max_length=200,
        help_text='Human-readable name'
    )
    slug = models.SlugField(
        max_length=200,
        help_text='URL-friendly identifier'
    )
    description = models.TextField(
        blank=True,
        help_text='Optional detailed description'
    )

    # ===== Relationships =====
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='mymodel_set',
        help_text='User who owns this record'
    )
    workspace = models.ForeignKey(
        'workspace.Workspace',
        on_delete=models.CASCADE,
        related_name='mymodels',
        help_text='Workspace this belongs to'
    )

    # ===== Status/Configuration =====
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this record is active'
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional configuration settings'
    )

    class Meta:
        db_table = 'myapp_mymodel'
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
        ordering = ['-created_at']
        get_latest_by = 'created_at'

        indexes = [
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'workspace', '-created_at']),
            models.Index(fields=['tenant', 'is_active']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'workspace', 'slug'],
                name='unique_mymodel_slug_per_workspace'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"

    def __repr__(self):
        return f"<MyModel id={self.id} name={self.name} tenant={self.tenant_id}>"

    def save(self, *args, **kwargs):
        """Override save to add custom logic."""
        # Auto-generate slug if not provided
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)

        # Auto-set tenant from workspace
        if not self.tenant_id and self.workspace:
            self.tenant = self.workspace.tenant

        super().save(*args, **kwargs)

    def clean(self):
        """Validate model data."""
        super().clean()

        # Validate tenant consistency
        if self.workspace and self.tenant:
            if self.workspace.tenant != self.tenant:
                raise ValidationError({
                    'workspace': 'Workspace must belong to the same tenant'
                })

        if self.user and self.tenant and hasattr(self.user, 'profile'):
            if self.user.profile.tenant != self.tenant:
                raise ValidationError({
                    'user': 'User must belong to the same tenant'
                })

    def get_absolute_url(self):
        """Return canonical URL for this object."""
        from django.urls import reverse
        return reverse('myapp:mymodel-detail', kwargs={'pk': self.pk})

    # ===== Custom Methods =====
    def activate(self):
        """Activate this record."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    def deactivate(self):
        """Deactivate this record."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
```

## Field Patterns

### Primary Keys

**Use UUIDs for distributed systems:**
```python
id = models.UUIDField(
    primary_key=True,
    default=uuid.uuid4,
    editable=False
)
```

**Use AutoField for simple cases:**
```python
# Django default - no need to specify
id = models.AutoField(primary_key=True)
```

### Timestamps

**Always include created/updated timestamps:**
```python
created_at = models.DateTimeField(
    auto_now_add=True,
    db_index=True,  # Often used for filtering/ordering
    help_text='When this record was created'
)
updated_at = models.DateTimeField(
    auto_now=True,
    help_text='When this record was last modified'
)
```

### Foreign Keys

**Specify `related_name` explicitly:**
```python
# ✅ Good - explicit related_name
workspace = models.ForeignKey(
    'workspace.Workspace',
    on_delete=models.CASCADE,
    related_name='conversations',  # workspace.conversations.all()
)

# ❌ Bad - default related_name 'mymodel_set'
workspace = models.ForeignKey(
    'workspace.Workspace',
    on_delete=models.CASCADE,
)
```

**Choose appropriate `on_delete`:**
```python
# CASCADE - delete child when parent deleted
user = models.ForeignKey(User, on_delete=models.CASCADE)

# PROTECT - prevent deletion if children exist
category = models.ForeignKey(Category, on_delete=models.PROTECT)

# SET_NULL - set to null when parent deleted
deleted_by = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)

# SET_DEFAULT - set to default when parent deleted
status = models.ForeignKey(
    Status,
    on_delete=models.SET_DEFAULT,
    default=get_default_status
)
```

### Character Fields

**Use appropriate max_length:**
```python
# Short identifiers
slug = models.SlugField(max_length=100)
code = models.CharField(max_length=50)

# Names
name = models.CharField(max_length=200)
title = models.CharField(max_length=255)

# Email
email = models.EmailField(max_length=254)  # RFC 5321 max

# URLs
url = models.URLField(max_length=500)
```

### Boolean Fields

**Provide sensible defaults:**
```python
is_active = models.BooleanField(
    default=True,
    help_text='Whether this record is active'
)
is_deleted = models.BooleanField(
    default=False,
    db_index=True,  # If used for filtering
    help_text='Soft delete flag'
)
```

**Use BooleanField (not NullBooleanField):**
```python
# ✅ Good - explicit True/False
is_public = models.BooleanField(default=False)

# ❌ Avoid - NullBooleanField deprecated
# is_public = models.NullBooleanField()

# If you need None, use null=True
is_verified = models.BooleanField(null=True, blank=True)
```

### JSON Fields

**Use for flexible configuration:**
```python
settings = models.JSONField(
    default=dict,  # Empty dict as default
    blank=True,
    help_text='Additional configuration'
)

# Access in code
obj.settings['theme'] = 'dark'
obj.save()
```

**Define schema in docstring:**
```python
metadata = models.JSONField(
    default=dict,
    blank=True,
    help_text='''
    Metadata structure:
    {
        "tags": ["tag1", "tag2"],
        "priority": int,
        "custom_fields": {...}
    }
    '''
)
```

## Meta Options

### Indexes

**Create indexes for:**
1. Foreign keys (automatic in most DBs, but explicit is better)
2. Fields used in WHERE clauses
3. Fields used in ORDER BY
4. Composite queries

```python
class Meta:
    indexes = [
        # Tenant-first for multi-tenant
        models.Index(fields=['tenant', 'user', '-created_at']),

        # Specific query patterns
        models.Index(fields=['workspace', 'is_active', '-updated_at']),

        # Single field indexes
        models.Index(fields=['email']),
        models.Index(fields=['-created_at']),

        # Named indexes for clarity
        models.Index(
            fields=['tenant', 'status'],
            name='idx_tenant_status'
        ),
    ]
```

### Constraints

**Unique constraints:**
```python
class Meta:
    # Simple unique together
    unique_together = [
        ['tenant', 'slug'],
        ['tenant', 'user', 'name'],
    ]

    # Or use UniqueConstraint for more control
    constraints = [
        models.UniqueConstraint(
            fields=['tenant', 'email'],
            name='unique_tenant_email'
        ),
        # Conditional unique constraint
        models.UniqueConstraint(
            fields=['tenant', 'external_id'],
            condition=models.Q(is_active=True),
            name='unique_active_external_id'
        ),
    ]
```

**Check constraints:**
```python
class Meta:
    constraints = [
        # Ensure positive values
        models.CheckConstraint(
            check=models.Q(credits__gte=0),
            name='credits_non_negative'
        ),
        # Ensure date ranges make sense
        models.CheckConstraint(
            check=models.Q(end_date__gte=models.F('start_date')),
            name='valid_date_range'
        ),
    ]
```

### Ordering

```python
class Meta:
    # Default ordering
    ordering = ['-created_at']

    # Multiple fields
    ordering = ['priority', '-created_at']

    # Avoid random ordering in production!
    # ordering = ['?']  # ❌ Slow!

    # Use get_latest_by for .latest()
    get_latest_by = 'created_at'
```

### Database Table Name

```python
class Meta:
    # Explicit table name
    db_table = 'myapp_mymodel'

    # For legacy database
    db_table = 'legacy_table_name'
```

## Validation

### Model-Level Validation

**Use `clean()` for cross-field validation:**
```python
def clean(self):
    super().clean()

    # Validate date ranges
    if self.end_date and self.start_date:
        if self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after start date'
            })

    # Validate tenant consistency
    if self.workspace and self.tenant:
        if self.workspace.tenant != self.tenant:
            raise ValidationError({
                'workspace': 'Workspace must belong to same tenant'
            })

    # Validate business rules
    if self.is_primary:
        # Check no other primary exists
        existing_primary = self.__class__.objects.filter(
            tenant=self.tenant,
            user=self.user,
            is_primary=True
        ).exclude(pk=self.pk).exists()

        if existing_primary:
            raise ValidationError({
                'is_primary': 'User already has a primary item'
            })
```

### Field-Level Validation

**Use validators for single fields:**
```python
from django.core.validators import MinValueValidator, MaxValueValidator

class MyModel(models.Model):
    percentage = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    priority = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
```

**Custom validators:**
```python
from django.core.exceptions import ValidationError

def validate_slug(value):
    """Ensure slug doesn't contain special characters."""
    if not value.replace('-', '').replace('_', '').isalnum():
        raise ValidationError(
            'Slug must contain only letters, numbers, hyphens, and underscores'
        )

class MyModel(models.Model):
    slug = models.SlugField(
        validators=[validate_slug]
    )
```

## Custom Managers and QuerySets

### Custom QuerySet

```python
class MyModelQuerySet(models.QuerySet):
    """Custom queryset with business logic."""

    def active(self):
        """Get only active records."""
        return self.filter(is_active=True)

    def for_user(self, user):
        """Get records for specific user."""
        return self.filter(user=user)

    def recent(self, days=7):
        """Get recent records."""
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

    def with_related(self):
        """Optimize by selecting related objects."""
        return self.select_related('user', 'workspace').prefetch_related('tags')

    def search(self, query):
        """Full-text search."""
        from django.db.models import Q
        return self.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
```

### Custom Manager

```python
class MyModelManager(models.Manager):
    """Custom manager."""

    def get_queryset(self):
        """Return custom queryset."""
        return MyModelQuerySet(self.model, using=self._db)

    def active(self):
        """Proxy to queryset method."""
        return self.get_queryset().active()

    def for_user(self, user):
        """Proxy to queryset method."""
        return self.get_queryset().for_user(user)

    def create_with_defaults(self, **kwargs):
        """Create with intelligent defaults."""
        if 'slug' not in kwargs and 'name' in kwargs:
            from django.utils.text import slugify
            kwargs['slug'] = slugify(kwargs['name'])

        return self.create(**kwargs)
```

### Using Custom Managers

```python
class MyModel(TenantAwareModel):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    # Custom manager
    objects = MyModelManager()

# Usage
active_items = MyModel.objects.active()
user_items = MyModel.objects.for_user(request.user)
recent_items = MyModel.objects.recent(days=30)
```

## Model Methods

### Standard Methods

**`__str__()` - Human-readable representation:**
```python
def __str__(self):
    return self.name

# Or more context
def __str__(self):
    return f"{self.name} - {self.workspace.name}"
```

**`__repr__()` - Developer representation:**
```python
def __repr__(self):
    return f"<{self.__class__.__name__} id={self.id} name={self.name!r}>"
```

**`get_absolute_url()` - Canonical URL:**
```python
def get_absolute_url(self):
    from django.urls import reverse
    return reverse('myapp:detail', kwargs={'pk': self.pk})
```

### Business Logic Methods

**Action methods:**
```python
def activate(self):
    """Activate this record."""
    self.is_active = True
    self.save(update_fields=['is_active', 'updated_at'])

def archive(self):
    """Archive this record."""
    self.is_archived = True
    self.archived_at = timezone.now()
    self.save(update_fields=['is_archived', 'archived_at', 'updated_at'])
```

**Query methods:**
```python
def get_active_members(self):
    """Get active members."""
    return self.members.filter(is_active=True)

def has_permission(self, user, permission):
    """Check if user has permission."""
    return self.members.filter(
        user=user,
        permissions__contains=permission
    ).exists()
```

**Calculation methods:**
```python
@property
def member_count(self):
    """Count members (cached)."""
    if not hasattr(self, '_member_count'):
        self._member_count = self.members.count()
    return self._member_count

def calculate_total(self):
    """Calculate total from related objects."""
    return self.items.aggregate(
        total=models.Sum('amount')
    )['total'] or 0
```

## Properties

**Use `@property` for computed values:**
```python
@property
def full_name(self):
    """Get full name."""
    return f"{self.first_name} {self.last_name}"

@property
def is_expired(self):
    """Check if expired."""
    from django.utils import timezone
    return self.expires_at and self.expires_at < timezone.now()

@property
def remaining_credits(self):
    """Calculate remaining credits."""
    return self.total_credits - self.used_credits
```

**Cached properties for expensive operations:**
```python
from django.utils.functional import cached_property

@cached_property
def total_conversations(self):
    """Get total conversation count (cached)."""
    return self.conversations.count()

@cached_property
def latest_activity(self):
    """Get latest activity timestamp (cached)."""
    return self.activities.latest('created_at')
```

## Common Patterns

### Soft Delete

```python
class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft delete queryset."""
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        """Actually delete from database."""
        return super().delete()

    def alive(self):
        """Get non-deleted records."""
        return self.filter(is_deleted=False)

class SoftDeleteModel(TenantAwareModel):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    def hard_delete(self):
        """Actually delete from database."""
        super().delete()
```

### Versioning

```python
class VersionedModel(TenantAwareModel):
    version = models.IntegerField(default=1)
    previous_version = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='next_versions'
    )

    class Meta:
        abstract = True

    def create_new_version(self):
        """Create new version of this object."""
        old_pk = self.pk
        self.pk = None
        self.previous_version_id = old_pk
        self.version += 1
        self.save()
        return self
```

### Audit Trail

```python
class AuditedModel(TenantAwareModel):
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_modified'
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user:
            if not self.pk:
                self.created_by = user
            self.modified_by = user
        super().save(*args, **kwargs)
```

## Performance Optimization

### Select/Prefetch Related

```python
# ❌ Bad - N+1 queries
conversations = Conversation.objects.all()
for conv in conversations:
    print(conv.user.username)  # Queries for each conv
    print(conv.workspace.name)  # Queries for each conv

# ✅ Good - 1 query with joins
conversations = Conversation.objects.select_related('user', 'workspace').all()
for conv in conversations:
    print(conv.user.username)  # No extra query
    print(conv.workspace.name)  # No extra query

# ✅ Good - for many-to-many or reverse FK
workspaces = Workspace.objects.prefetch_related('members', 'conversations').all()
```

### Only/Defer

```python
# Only load specific fields
users = User.objects.only('id', 'username', 'email')

# Exclude large fields
articles = Article.objects.defer('content', 'raw_html')
```

### Bulk Operations

```python
# Bulk create (1 query instead of N)
objects = [MyModel(name=f"Item {i}") for i in range(100)]
MyModel.objects.bulk_create(objects)

# Bulk update (1 query instead of N)
MyModel.objects.filter(is_active=False).update(status='inactive')

# Bulk update individual objects
objects = MyModel.objects.all()
for obj in objects:
    obj.is_processed = True
MyModel.objects.bulk_update(objects, ['is_processed'])
```

## Best Practices Summary

1. **Always inherit from TenantBaseModel/TenantAwareModel** for tenant-scoped data
2. **Include docstrings** for models and complex methods
3. **Use `help_text`** on fields for documentation
4. **Specify `related_name`** explicitly on ForeignKeys
5. **Create indexes** for filtered/ordered fields (tenant-first!)
6. **Use `clean()`** for validation involving multiple fields
7. **Override `save()`** sparingly and always call `super()`
8. **Use custom managers/querysets** for reusable business logic
9. **Optimize queries** with select_related/prefetch_related
10. **Test your models** thoroughly, especially multi-tenant isolation

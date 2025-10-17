# Django Admin Patterns and Best Practices

Comprehensive guide to creating effective Django admin interfaces.

## Basic Admin Registration

### Simple Registration

```python
from django.contrib import admin
from .models import MyModel

# Simple registration
admin.site.register(MyModel)

# Or with decorator
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    pass
```

### Standard Admin Template

```python
from django.contrib import admin
from django.utils.html import format_html
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    """Admin interface for MyModel."""

    # ===== List View Configuration =====
    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'user__username', 'user__email']
    list_select_related = ['user', 'workspace']  # Optimize queries
    list_per_page = 50
    date_hierarchy = 'created_at'

    # ===== Form Configuration =====
    fields = ['name', 'user', 'workspace', 'is_active']  # Or use fieldsets
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']  # For ForeignKeys with many objects
    autocomplete_fields = ['workspace']  # For autocomplete search
    filter_horizontal = ['tags']  # For ManyToMany
    prepopulated_fields = {'slug': ('name',)}  # Auto-populate from other field

    # ===== Detail View Configuration =====
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Relationships', {
            'fields': ('user', 'workspace')
        }),
        ('Settings', {
            'fields': ('is_active', 'settings')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)  # Collapsible section
        }),
    )

    # ===== Actions =====
    actions = ['activate_selected', 'deactivate_selected']

    def activate_selected(self, request, queryset):
        """Activate selected records."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} records")
    activate_selected.short_description = "Activate selected items"

    def deactivate_selected(self, request, queryset):
        """Deactivate selected records."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} records")
    deactivate_selected.short_description = "Deactivate selected items"

    # ===== Custom Methods =====
    def get_queryset(self, request):
        """Optimize queryset with select_related/prefetch_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'workspace').prefetch_related('tags')
```

## List Display

### Basic List Display

```python
list_display = [
    'name',           # Model field
    'user',           # ForeignKey
    'is_active',      # Boolean
    'created_at',     # DateTime
    'custom_method',  # Custom method
]
```

### Custom Display Methods

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'user_email', 'member_count', 'status_badge']

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'  # Enable sorting

    def member_count(self, obj):
        """Display member count."""
        return obj.members.count()
    member_count.short_description = 'Members'

    def status_badge(self, obj):
        """Display colored status badge."""
        if obj.is_active:
            color = 'green'
            text = 'Active'
        else:
            color = 'red'
            text = 'Inactive'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )
    status_badge.short_description = 'Status'

    def get_queryset(self, request):
        """Optimize for custom methods that use related objects."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('members')  # For member_count
```

### Boolean Display

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_verified']

    # Boolean fields show icons automatically
    # Customize with:
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True  # Shows ✓ or ✗
    is_active.short_description = 'Active?'
```

## List Filters

### Standard Filters

```python
list_filter = [
    'is_active',                    # Boolean
    'created_at',                   # Date/DateTime (auto hierarchy)
    'user',                         # ForeignKey
    'workspace__organization',      # Related field
]
```

### Custom Filters

```python
from django.contrib.admin import SimpleListFilter

class RecentActivityFilter(SimpleListFilter):
    """Filter by recent activity."""
    title = 'recent activity'
    parameter_name = 'activity'

    def lookups(self, request, model_admin):
        """Return filter options."""
        return [
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
        ]

    def queryset(self, request, queryset):
        """Filter queryset based on selection."""
        from django.utils import timezone
        from datetime import timedelta

        if self.value() == 'today':
            cutoff = timezone.now().date()
            return queryset.filter(created_at__date=cutoff)
        elif self.value() == 'week':
            cutoff = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=cutoff)
        elif self.value() == 'month':
            cutoff = timezone.now() - timedelta(days=30)
            return queryset.filter(created_at__gte=cutoff)

        return queryset

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_filter = [RecentActivityFilter, 'is_active']
```

### Tenant-Aware Filters

```python
class TenantFilter(SimpleListFilter):
    """Filter by tenant (for superuser admin)."""
    title = 'tenant'
    parameter_name = 'tenant'

    def lookups(self, request, model_admin):
        """Return tenant options."""
        from apps.users.models import Tenant
        return [(t.id, t.name) for t in Tenant.objects.all()]

    def queryset(self, request, queryset):
        """Filter by selected tenant."""
        if self.value():
            # Use unfiltered queryset for superusers
            return queryset.unfiltered().filter(tenant_id=self.value())
        return queryset
```

## Search Fields

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    # Search across multiple fields
    search_fields = [
        'name',                    # Exact field
        'description',             # Text field
        'user__username',          # Related field
        'user__email',             # Related field
        'workspace__name',         # Related field
        '=id',                     # Exact match (prefix with =)
        '^slug',                   # Starts with (prefix with ^)
    ]

    # Case-insensitive by default
    # MySQL: case-insensitive automatically
    # PostgreSQL: uses ILIKE
```

## Fieldsets

### Organizing Form Fields

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    fieldsets = (
        # Section 1 - Basic info (always expanded)
        ('Basic Information', {
            'fields': ('name', 'slug', 'description'),
            'description': 'Core identification fields'
        }),

        # Section 2 - Relationships
        ('Relationships', {
            'fields': ('user', 'workspace', 'parent'),
        }),

        # Section 3 - Configuration
        ('Configuration', {
            'fields': ('is_active', 'settings', 'priority'),
            'classes': ('wide',),  # Wide layout
        }),

        # Section 4 - Advanced (collapsed by default)
        ('Advanced Options', {
            'fields': ('cache_timeout', 'retry_count'),
            'classes': ('collapse',),  # Collapsed
            'description': 'Advanced configuration options'
        }),

        # Section 5 - Metadata (collapsed)
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['id', 'created_at', 'updated_at']
```

### Inline Layouts

```python
# Wide layout for complex forms
fieldsets = (
    (None, {
        'fields': (('name', 'slug'), ('user', 'workspace')),  # Two columns
        'classes': ('wide',)
    }),
)
```

## Inline Admin

### Tabular Inline (Compact)

```python
from django.contrib import admin

class MessageInline(admin.TabularInline):
    """Inline for messages (tabular layout)."""
    model = Message
    extra = 0  # Don't show empty forms
    max_num = 10  # Limit number shown
    readonly_fields = ['created_at']
    fields = ['user', 'content', 'created_at']
    raw_id_fields = ['user']  # Use popup for user selection

    def has_add_permission(self, request, obj=None):
        """Control add permission."""
        return True

    def has_delete_permission(self, request, obj=None):
        """Control delete permission."""
        return True

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    inlines = [MessageInline]
```

### Stacked Inline (Detailed)

```python
class WorkspaceMemberInline(admin.StackedInline):
    """Inline for workspace members (stacked layout)."""
    model = WorkspaceMember
    extra = 1
    readonly_fields = ['joined_at']

    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'joined_at')
        }),
    )

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    inlines = [WorkspaceMemberInline]
```

### Many-to-Many Through Inline

```python
class GroupMembershipInline(admin.TabularInline):
    """Inline for ManyToMany through model."""
    model = Group.members.through  # Through model
    extra = 0
    raw_id_fields = ['user']
    verbose_name = "Member"
    verbose_name_plural = "Members"

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    inlines = [GroupMembershipInline]
```

## Custom Actions

### Bulk Actions

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    actions = [
        'activate_selected',
        'deactivate_selected',
        'export_as_csv',
        'send_notification',
    ]

    def activate_selected(self, request, queryset):
        """Activate selected records."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Successfully activated {updated} records",
            level='success'  # or 'warning', 'error', 'info'
        )
    activate_selected.short_description = "Activate selected items"

    def deactivate_selected(self, request, queryset):
        """Deactivate selected records."""
        count = queryset.count()

        # Can iterate for complex logic
        for obj in queryset:
            obj.deactivate()  # Call model method

        self.message_user(request, f"Deactivated {count} items")
    deactivate_selected.short_description = "Deactivate selected items"

    def export_as_csv(self, request, queryset):
        """Export selected records as CSV."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Created At'])  # Header

        for obj in queryset:
            writer.writerow([obj.id, obj.name, obj.created_at])

        return response
    export_as_csv.short_description = "Export selected as CSV"

    def send_notification(self, request, queryset):
        """Send notification to selected users."""
        # Import celery task
        from apps.notifications.tasks import send_bulk_notification

        user_ids = queryset.values_list('user_id', flat=True)

        # Queue celery task
        send_bulk_notification.delay(list(user_ids), 'Your notification')

        self.message_user(
            request,
            f"Queued notifications for {len(user_ids)} users"
        )
    send_notification.short_description = "Send notification to selected"
```

## QuerySet Optimization

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_select_related = ['user', 'workspace']  # For ForeignKeys in list_display
    list_display = ['name', 'user', 'workspace', 'member_count']

    def get_queryset(self, request):
        """Optimize queryset for list view."""
        qs = super().get_queryset(request)

        # For list view
        qs = qs.select_related('user', 'workspace')  # ForeignKeys
        qs = qs.prefetch_related('members', 'tags')  # ManyToMany

        # Add annotations for calculations
        from django.db.models import Count
        qs = qs.annotate(member_count_cached=Count('members'))

        return qs

    def member_count(self, obj):
        """Display member count (uses annotation)."""
        return obj.member_count_cached
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count_cached'  # Enable sorting

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Optimize ForeignKey choices."""
        if db_field.name == "workspace":
            # Limit choices based on user
            if not request.user.is_superuser:
                kwargs["queryset"] = Workspace.objects.filter(
                    tenant=request.user.profile.tenant
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
```

## Permissions

### Controlling Permissions

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        """Control who can add records."""
        # Only superusers can add
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Control who can edit records."""
        if obj is None:
            # List view
            return True

        # Check if user owns the record
        return obj.user == request.user or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Control who can delete records."""
        # Prevent deletion of system records
        if obj and getattr(obj, 'is_system', False):
            return False

        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Control who can view records."""
        return request.user.has_perm('myapp.view_mymodel')
```

### Tenant-Aware Admin

```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Filter by user's tenant for non-superusers."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            # Superusers see all tenants
            return qs.unfiltered()

        # Regular users see only their tenant
        if hasattr(request.user, 'profile'):
            return qs.filter(tenant=request.user.profile.tenant)

        return qs.none()

    def save_model(self, request, obj, form, change):
        """Auto-set tenant from user."""
        if not obj.tenant_id and hasattr(request.user, 'profile'):
            obj.tenant = request.user.profile.tenant

        super().save_model(request, obj, form, change)
```

## Read-Only Admin (Logs)

```python
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin for audit logs."""

    list_display = ['user', 'action', 'model', 'created_at']
    list_filter = ['action', 'model', 'created_at']
    search_fields = ['user__username', 'details']
    readonly_fields = ['id', 'user', 'action', 'model', 'details', 'created_at']

    fieldsets = (
        ('Log Information', {
            'fields': ('user', 'action', 'model', 'object_id')
        }),
        ('Details', {
            'fields': ('details',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual creation."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete for cleanup."""
        return request.user.is_superuser

    # Make all fields readonly
    def get_readonly_fields(self, request, obj=None):
        """All fields readonly."""
        return [f.name for f in self.model._meta.fields]
```

## Custom Forms

```python
from django import forms
from django.contrib import admin

class MyModelAdminForm(forms.ModelForm):
    """Custom admin form with validation."""

    class Meta:
        model = MyModel
        fields = '__all__'

    def clean_slug(self):
        """Validate slug."""
        slug = self.cleaned_data.get('slug')
        if slug and '--' in slug:
            raise forms.ValidationError('Slug cannot contain double hyphens')
        return slug

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date must be after start date')

        return cleaned_data

@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    form = MyModelAdminForm
```

## Autocomplete Fields

```python
@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    search_fields = ['name', 'slug']  # Required for autocomplete

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    autocomplete_fields = ['workspace']  # Enables autocomplete search
```

## Displaying Related Counts

```python
@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'owner',
        'member_count',
        'conversation_count',
        'created_at'
    ]

    def get_queryset(self, request):
        """Annotate with counts."""
        qs = super().get_queryset(request)
        return qs.annotate(
            member_count_cached=Count('members', distinct=True),
            conversation_count_cached=Count('conversations', distinct=True),
        )

    def member_count(self, obj):
        return obj.member_count_cached
    member_count.short_description = 'Members'
    member_count.admin_order_field = 'member_count_cached'

    def conversation_count(self, obj):
        return obj.conversation_count_cached
    conversation_count.short_description = 'Conversations'
    conversation_count.admin_order_field = 'conversation_count_cached'
```

## Best Practices Summary

1. **Always provide docstrings** for admin classes
2. **Use `list_display`** to show important fields
3. **Add `list_filter`** for common filtering needs
4. **Enable search** with `search_fields`
5. **Optimize queries** with `list_select_related` and `get_queryset()`
6. **Use `fieldsets`** to organize forms
7. **Make metadata readonly** (`created_at`, `updated_at`, etc.)
8. **Use `raw_id_fields`** for ForeignKeys with many objects
9. **Use `autocomplete_fields`** for better UX
10. **Add custom actions** for bulk operations
11. **Enforce permissions** with `has_*_permission` methods
12. **Filter by tenant** for non-superusers
13. **Use inlines** for related objects
14. **Make log models read-only**
15. **Add helpful `short_description`** to custom methods

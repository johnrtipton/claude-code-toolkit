"""
Template for creating a Django admin interface.

Copy this template and customize for your model.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import MyModel


@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    """Admin interface for MyModel."""

    # ===== List View Configuration =====
    list_display = [
        'name',
        'user',
        'workspace',
        'status_badge',
        'priority',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'created_at',
        'updated_at',
        'workspace',
    ]
    search_fields = [
        'name',
        'slug',
        'description',
        'user__username',
        'user__email',
        'workspace__name',
    ]
    list_select_related = ['user', 'workspace', 'tenant']
    list_per_page = 50
    date_hierarchy = 'created_at'

    # ===== Form Configuration =====
    readonly_fields = ['id', 'slug', 'created_at', 'updated_at']
    raw_id_fields = ['user']
    autocomplete_fields = ['workspace']
    prepopulated_fields = {'slug': ('name',)}

    # ===== Detail View Configuration =====
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description'),
            'description': 'Core identification fields'
        }),
        ('Relationships', {
            'fields': ('user', 'workspace'),
        }),
        ('Settings', {
            'fields': ('is_active', 'priority', 'settings'),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ===== Actions =====
    actions = ['activate_selected', 'deactivate_selected', 'export_as_csv']

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

    def export_as_csv(self, request, queryset):
        """Export selected records as CSV."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mymodel_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'User', 'Workspace', 'Created'])

        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.name,
                obj.user.username,
                obj.workspace.name,
                obj.created_at
            ])

        return response
    export_as_csv.short_description = "Export selected as CSV"

    # ===== Custom Display Methods =====
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

    # ===== QuerySet Optimization =====
    def get_queryset(self, request):
        """Optimize queryset for list view."""
        qs = super().get_queryset(request)

        # Select related for ForeignKeys
        qs = qs.select_related('user', 'workspace', 'tenant')

        # Prefetch related for ManyToMany (if any)
        # qs = qs.prefetch_related('tags', 'categories')

        # Filter by tenant for non-superusers
        if not request.user.is_superuser and hasattr(request.user, 'profile'):
            qs = qs.filter(tenant=request.user.profile.tenant)

        return qs

    # ===== Permissions =====
    def has_add_permission(self, request):
        """Control who can add records."""
        return request.user.has_perm('myapp.add_mymodel')

    def has_change_permission(self, request, obj=None):
        """Control who can edit records."""
        return request.user.has_perm('myapp.change_mymodel')

    def has_delete_permission(self, request, obj=None):
        """Control who can delete records."""
        # Prevent deletion of certain records
        if obj and getattr(obj, 'is_system', False):
            return False

        return request.user.has_perm('myapp.delete_mymodel')

    # ===== Form Customization =====
    def save_model(self, request, obj, form, change):
        """Auto-set tenant and user when saving."""
        if not change:  # Creating new object
            if not obj.tenant_id and hasattr(request.user, 'profile'):
                obj.tenant = request.user.profile.tenant

        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit choices for ForeignKey fields."""
        if db_field.name == "workspace":
            # Only show workspaces from user's tenant
            if not request.user.is_superuser and hasattr(request.user, 'profile'):
                kwargs["queryset"] = Workspace.objects.filter(
                    tenant=request.user.profile.tenant
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ===== Inline Admin Example =====
class RelatedItemInline(admin.TabularInline):
    """Inline for related items."""
    model = MyModel.related_items.through  # For ManyToMany
    # model = RelatedItem  # For ForeignKey from related item
    extra = 0
    raw_id_fields = ['related_item']
    fields = ['related_item', 'order']


@admin.register(MyModel)
class MyModelAdminWithInline(admin.ModelAdmin):
    """MyModel admin with inline."""

    list_display = ['name', 'user']
    inlines = [RelatedItemInline]

    # ... rest of admin configuration

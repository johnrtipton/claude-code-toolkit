"""
Template for creating a new Django model with multi-tenant support.

Copy this template and customize for your needs.
"""

from apps.core.models.base import TenantAwareModel
from django.db import models
from django.core.exceptions import ValidationError


class MyModel(TenantAwareModel):
    """
    Brief description of what this model represents.

    Inherits from TenantAwareModel:
    - id (UUIDField) - Primary key
    - tenant (ForeignKey) - Tenant this record belongs to
    - created_at (DateTimeField) - When record was created
    - updated_at (DateTimeField) - When record was last updated

    Additional fields and relationships are defined below.
    """

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
    priority = models.IntegerField(
        default=0,
        help_text='Priority level (higher = more important)'
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

        # Indexes - always put tenant first!
        indexes = [
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'workspace', '-created_at']),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['slug']),
        ]

        # Constraints - include tenant in unique constraints
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'workspace', 'slug'],
                name='unique_mymodel_slug_per_workspace'
            ),
        ]

    def __str__(self):
        """Human-readable string representation."""
        return f"{self.name} ({self.workspace.name})"

    def __repr__(self):
        """Developer-friendly representation."""
        return f"<MyModel id={self.id} name={self.name!r} tenant={self.tenant_id}>"

    def save(self, *args, **kwargs):
        """Override save to add custom logic."""
        # Auto-generate slug if not provided
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)

        # Auto-set tenant from workspace if not set
        if not self.tenant_id and self.workspace:
            self.tenant = self.workspace.tenant

        # Call parent save
        super().save(*args, **kwargs)

    def clean(self):
        """Validate model data before saving."""
        super().clean()

        # Validate tenant consistency across related objects
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

        # Custom validation logic
        if self.priority < 0:
            raise ValidationError({
                'priority': 'Priority cannot be negative'
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

    @property
    def is_owned_by_user(self, user):
        """Check if this record is owned by the given user."""
        return self.user == user

    def can_be_edited_by(self, user):
        """Check if user has permission to edit this record."""
        # Owner can always edit
        if self.user == user:
            return True

        # Workspace admins can edit
        if self.workspace.members.filter(user=user, role='admin').exists():
            return True

        return False

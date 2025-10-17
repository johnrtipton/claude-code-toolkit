#!/usr/bin/env python
"""
Generate Django model boilerplate with multi-tenant support.

Usage:
    python generate_model.py <app_name> <model_name> [options]

Example:
    python generate_model.py notifications Notification --with-admin --with-tests
"""

import argparse
import os
from pathlib import Path


MODEL_TEMPLATE = '''"""
{model_name} model for {app_name} app.
"""

from apps.core.models.base import TenantAwareModel
from django.db import models
from django.core.exceptions import ValidationError


class {model_name}(TenantAwareModel):
    """
    {description}

    Inherits from TenantAwareModel:
    - id (UUID)
    - tenant (ForeignKey)
    - created_at (DateTimeField)
    - updated_at (DateTimeField)
    """

    # ===== Core Fields =====
    name = models.CharField(
        max_length=200,
        help_text='Name of the {model_name_lower}'
    )

    # ===== Relationships =====
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='{model_name_lower}_set',
        help_text='User who owns this {model_name_lower}'
    )

    # ===== Status Fields =====
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this {model_name_lower} is active'
    )

    class Meta:
        db_table = '{app_name}_{model_name_lower}'
        verbose_name = '{model_name}'
        verbose_name_plural = '{model_name}s'
        ordering = ['-created_at']
        get_latest_by = 'created_at'

        indexes = [
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'is_active']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user', 'name'],
                name='unique_{model_name_lower}_per_user'
            ),
        ]

    def __str__(self):
        return f"{{self.name}} ({{self.user.username}})"

    def __repr__(self):
        return f"<{model_name} id={{self.id}} name={{self.name!r}} tenant={{self.tenant_id}}>"

    def save(self, *args, **kwargs):
        """Override save to add custom logic."""
        # Add any custom save logic here
        super().save(*args, **kwargs)

    def clean(self):
        """Validate model data."""
        super().clean()

        # Add validation logic here
        # Example: Validate tenant consistency
        if self.user and self.tenant and hasattr(self.user, 'profile'):
            if self.user.profile.tenant != self.tenant:
                raise ValidationError({{
                    'user': 'User must belong to the same tenant'
                }})

    # ===== Custom Methods =====
    def activate(self):
        """Activate this {model_name_lower}."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    def deactivate(self):
        """Deactivate this {model_name_lower}."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
'''


ADMIN_TEMPLATE = '''"""
Django admin configuration for {model_name}.
"""

from django.contrib import admin
from apps.{app_name}.models import {model_name}


@admin.register({model_name})
class {model_name}Admin(admin.ModelAdmin):
    """Admin interface for {model_name}."""

    list_display = ['name', 'user', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']

    fieldsets = (
        ('{model_name} Information', {{
            'fields': ('name', 'user')
        }}),
        ('Settings', {{
            'fields': ('is_active',)
        }}),
        ('Metadata', {{
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }}),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'tenant')

    actions = ['activate_selected', 'deactivate_selected']

    def activate_selected(self, request, queryset):
        """Activate selected records."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {{updated}} {model_name_lower}s")
    activate_selected.short_description = "Activate selected {model_name_lower}s"

    def deactivate_selected(self, request, queryset):
        """Deactivate selected records."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {{updated}} {model_name_lower}s")
    deactivate_selected.short_description = "Deactivate selected {model_name_lower}s"
'''


TEST_TEMPLATE = '''"""
Tests for {model_name} model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.users.models import Tenant
from apps.users.middleware import set_current_tenant
from apps.{app_name}.models import {model_name}

User = get_user_model()


class {model_name}ModelTest(TestCase):
    """Test {model_name} model."""

    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Org",
            slug="test-org"
        )
        set_current_tenant(self.tenant)

        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Link user to tenant
        from apps.users.models import UserProfile
        self.user.profile = UserProfile.objects.create(
            user=self.user,
            tenant=self.tenant
        )

    def tearDown(self):
        """Clean up after tests."""
        set_current_tenant(None)

    def test_create_{model_name_lower}(self):
        """Test creating a {model_name}."""
        {model_name_lower} = {model_name}.objects.create(
            name="Test {model_name}",
            user=self.user
        )

        self.assertEqual({model_name_lower}.name, "Test {model_name}")
        self.assertEqual({model_name_lower}.user, self.user)
        self.assertEqual({model_name_lower}.tenant, self.tenant)
        self.assertTrue({model_name_lower}.is_active)

    def test_str_representation(self):
        """Test __str__ method."""
        {model_name_lower} = {model_name}.objects.create(
            name="Test {model_name}",
            user=self.user
        )

        expected = f"Test {model_name} ({{self.user.username}})"
        self.assertEqual(str({model_name_lower}), expected)

    def test_tenant_auto_set(self):
        """Test tenant is automatically set from user."""
        {model_name_lower} = {model_name}.objects.create(
            name="Test {model_name}",
            user=self.user
            # tenant not explicitly set
        )

        self.assertEqual({model_name_lower}.tenant, self.tenant)

    def test_tenant_isolation(self):
        """Test tenant isolation."""
        # Create {model_name_lower} for tenant1
        {model_name_lower}1 = {model_name}.objects.create(
            name="Tenant 1 {model_name}",
            user=self.user
        )

        # Create second tenant
        tenant2 = Tenant.objects.create(name="Org 2", slug="org-2")
        user2 = User.objects.create_user(username='user2', password='pass')
        from apps.users.models import UserProfile
        user2.profile = UserProfile.objects.create(user=user2, tenant=tenant2)

        # Switch tenant context
        set_current_tenant(tenant2)

        # Create {model_name_lower} for tenant2
        {model_name_lower}2 = {model_name}.objects.create(
            name="Tenant 2 {model_name}",
            user=user2
        )

        # Verify isolation - tenant2 shouldn't see tenant1 data
        self.assertEqual({model_name}.objects.count(), 1)
        self.assertEqual({model_name}.objects.first(), {model_name_lower}2)

        # Switch back to tenant1
        set_current_tenant(self.tenant)
        self.assertEqual({model_name}.objects.count(), 1)
        self.assertEqual({model_name}.objects.first(), {model_name_lower}1)

        # Verify unfiltered queryset sees both
        set_current_tenant(None)
        self.assertEqual({model_name}.objects.unfiltered().count(), 2)

    def test_activate_deactivate(self):
        """Test activate/deactivate methods."""
        {model_name_lower} = {model_name}.objects.create(
            name="Test {model_name}",
            user=self.user,
            is_active=False
        )

        # Test activate
        {model_name_lower}.activate()
        {model_name_lower}.refresh_from_db()
        self.assertTrue({model_name_lower}.is_active)

        # Test deactivate
        {model_name_lower}.deactivate()
        {model_name_lower}.refresh_from_db()
        self.assertFalse({model_name_lower}.is_active)
'''


def generate_model(app_name, model_name, description="", with_admin=False, with_tests=False):
    """Generate model boilerplate."""
    model_name_lower = model_name.lower()

    # Generate model code
    model_code = MODEL_TEMPLATE.format(
        app_name=app_name,
        model_name=model_name,
        model_name_lower=model_name_lower,
        description=description or f"Represents a {model_name} in the system."
    )

    print(f"\n{'='*60}")
    print(f"Generated Model Code for {model_name}")
    print(f"{'='*60}\n")
    print(model_code)

    if with_admin:
        admin_code = ADMIN_TEMPLATE.format(
            app_name=app_name,
            model_name=model_name,
            model_name_lower=model_name_lower
        )
        print(f"\n{'='*60}")
        print(f"Generated Admin Code for {model_name}")
        print(f"{'='*60}\n")
        print(admin_code)

    if with_tests:
        test_code = TEST_TEMPLATE.format(
            app_name=app_name,
            model_name=model_name,
            model_name_lower=model_name_lower
        )
        print(f"\n{'='*60}")
        print(f"Generated Test Code for {model_name}")
        print(f"{'='*60}\n")
        print(test_code)

    print(f"\n{'='*60}")
    print("Next Steps:")
    print(f"{'='*60}")
    print(f"1. Add the model code to apps/{app_name}/models/")
    print(f"2. Import the model in apps/{app_name}/models/__init__.py")
    if with_admin:
        print(f"3. Add the admin code to apps/{app_name}/admin.py")
    if with_tests:
        print(f"4. Add the test code to apps/{app_name}/tests/test_models.py")
    print(f"5. Run: python manage.py makemigrations {app_name}")
    print(f"6. Run: python manage.py migrate")
    if with_tests:
        print(f"7. Run: python manage.py test apps.{app_name}")


def main():
    parser = argparse.ArgumentParser(description='Generate Django model boilerplate')
    parser.add_argument('app_name', help='Django app name (e.g., notifications)')
    parser.add_argument('model_name', help='Model name (e.g., Notification)')
    parser.add_argument('--description', '-d', help='Model description', default='')
    parser.add_argument('--with-admin', action='store_true', help='Generate admin code')
    parser.add_argument('--with-tests', action='store_true', help='Generate test code')

    args = parser.parse_args()

    generate_model(
        app_name=args.app_name,
        model_name=args.model_name,
        description=args.description,
        with_admin=args.with_admin,
        with_tests=args.with_tests
    )


if __name__ == '__main__':
    main()

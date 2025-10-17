"""
Template for Django model tests with multi-tenant support.

Copy this template and customize for your model.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.users.models import Tenant, UserProfile
from apps.users.middleware import set_current_tenant
from apps.workspace.models import Workspace
from .models import MyModel

User = get_user_model()


class MyModelTestCase(TestCase):
    """Test cases for MyModel."""

    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Organization",
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
        self.user.profile = UserProfile.objects.create(
            user=self.user,
            tenant=self.tenant
        )

        # Create workspace
        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            slug="test-workspace",
            owner=self.user,
            tenant=self.tenant
        )

    def tearDown(self):
        """Clean up after tests."""
        set_current_tenant(None)

    def test_create_model(self):
        """Test creating a MyModel instance."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace
        )

        self.assertEqual(obj.name, "Test Model")
        self.assertEqual(obj.user, self.user)
        self.assertEqual(obj.workspace, self.workspace)
        self.assertEqual(obj.tenant, self.tenant)
        self.assertTrue(obj.is_active)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

    def test_str_representation(self):
        """Test __str__ method."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace
        )

        expected = f"Test Model ({self.workspace.name})"
        self.assertEqual(str(obj), expected)

    def test_slug_auto_generation(self):
        """Test slug is automatically generated from name."""
        obj = MyModel.objects.create(
            name="Test Model Name",
            user=self.user,
            workspace=self.workspace
        )

        self.assertEqual(obj.slug, "test-model-name")

    def test_tenant_auto_set_from_workspace(self):
        """Test tenant is automatically set from workspace."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace
            # tenant not explicitly set
        )

        self.assertEqual(obj.tenant, self.workspace.tenant)
        self.assertEqual(obj.tenant, self.tenant)

    def test_tenant_isolation(self):
        """Test that tenant isolation works correctly."""
        # Create object for tenant1
        obj1 = MyModel.objects.create(
            name="Tenant 1 Model",
            user=self.user,
            workspace=self.workspace
        )

        # Create second tenant and user
        tenant2 = Tenant.objects.create(name="Org 2", slug="org-2")
        user2 = User.objects.create_user(username='user2', password='pass')
        user2.profile = UserProfile.objects.create(user=user2, tenant=tenant2)

        workspace2 = Workspace.objects.create(
            name="Workspace 2",
            slug="workspace-2",
            owner=user2,
            tenant=tenant2
        )

        # Switch to tenant2
        set_current_tenant(tenant2)

        # Create object for tenant2
        obj2 = MyModel.objects.create(
            name="Tenant 2 Model",
            user=user2,
            workspace=workspace2
        )

        # Verify tenant2 only sees their data
        self.assertEqual(MyModel.objects.count(), 1)
        self.assertEqual(MyModel.objects.first(), obj2)
        self.assertNotIn(obj1, MyModel.objects.all())

        # Switch back to tenant1
        set_current_tenant(self.tenant)
        self.assertEqual(MyModel.objects.count(), 1)
        self.assertEqual(MyModel.objects.first(), obj1)
        self.assertNotIn(obj2, MyModel.objects.all())

        # Verify unfiltered queryset sees both
        set_current_tenant(None)
        self.assertEqual(MyModel.objects.unfiltered().count(), 2)
        self.assertIn(obj1, MyModel.objects.unfiltered())
        self.assertIn(obj2, MyModel.objects.unfiltered())

    def test_cross_tenant_reference_validation(self):
        """Test that cross-tenant references are prevented."""
        # Create second tenant
        tenant2 = Tenant.objects.create(name="Org 2", slug="org-2")
        user2 = User.objects.create_user(username='user2', password='pass')
        user2.profile = UserProfile.objects.create(user=user2, tenant=tenant2)

        workspace2 = Workspace.objects.create(
            name="Workspace 2",
            slug="workspace-2",
            owner=user2,
            tenant=tenant2
        )

        # Try to create object with workspace from different tenant
        obj = MyModel(
            name="Cross-tenant Test",
            user=self.user,  # tenant1
            workspace=workspace2,  # tenant2
            tenant=self.tenant
        )

        # Should raise validation error
        with self.assertRaises(ValidationError) as cm:
            obj.clean()

        self.assertIn('workspace', cm.exception.message_dict)

    def test_activate_deactivate_methods(self):
        """Test activate and deactivate methods."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace,
            is_active=False
        )

        # Test activate
        obj.activate()
        obj.refresh_from_db()
        self.assertTrue(obj.is_active)

        # Test deactivate
        obj.deactivate()
        obj.refresh_from_db()
        self.assertFalse(obj.is_active)

    def test_unique_constraint(self):
        """Test unique constraint enforcement."""
        # Create first object
        MyModel.objects.create(
            name="Test Model",
            slug="test-model",
            user=self.user,
            workspace=self.workspace
        )

        # Try to create duplicate with same slug in same workspace
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MyModel.objects.create(
                name="Another Test Model",
                slug="test-model",  # Same slug
                user=self.user,
                workspace=self.workspace  # Same workspace
            )

    def test_queryset_methods(self):
        """Test custom queryset methods (if any)."""
        # Create test data
        active_obj = MyModel.objects.create(
            name="Active Model",
            user=self.user,
            workspace=self.workspace,
            is_active=True
        )

        inactive_obj = MyModel.objects.create(
            name="Inactive Model",
            user=self.user,
            workspace=self.workspace,
            is_active=False
        )

        # Test active() queryset method (if implemented)
        # active_objects = MyModel.objects.active()
        # self.assertIn(active_obj, active_objects)
        # self.assertNotIn(inactive_obj, active_objects)

    def test_model_validation(self):
        """Test model validation in clean() method."""
        obj = MyModel(
            name="Test Model",
            user=self.user,
            workspace=self.workspace,
            priority=-1  # Invalid priority
        )

        with self.assertRaises(ValidationError) as cm:
            obj.clean()

        self.assertIn('priority', cm.exception.message_dict)

    def test_ordering(self):
        """Test default ordering."""
        import time

        obj1 = MyModel.objects.create(
            name="First",
            user=self.user,
            workspace=self.workspace
        )

        time.sleep(0.01)  # Ensure different timestamps

        obj2 = MyModel.objects.create(
            name="Second",
            user=self.user,
            workspace=self.workspace
        )

        objects = list(MyModel.objects.all())

        # Should be ordered by -created_at (newest first)
        self.assertEqual(objects[0], obj2)
        self.assertEqual(objects[1], obj1)


class MyModelManagerTestCase(TestCase):
    """Test custom manager methods (if any)."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(name="Test Org", slug="test-org")
        set_current_tenant(self.tenant)

        self.user = User.objects.create_user(username='testuser', password='pass')
        self.user.profile = UserProfile.objects.create(user=self.user, tenant=self.tenant)

        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            slug="test-workspace",
            owner=self.user,
            tenant=self.tenant
        )

    def tearDown(self):
        """Clean up."""
        set_current_tenant(None)

    def test_custom_manager_method(self):
        """Test custom manager method."""
        # Example: MyModel.objects.recent(days=7)
        pass


class MyModelIntegrationTestCase(TestCase):
    """Integration tests for MyModel with other models."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(name="Test Org", slug="test-org")
        set_current_tenant(self.tenant)

        self.user = User.objects.create_user(username='testuser', password='pass')
        self.user.profile = UserProfile.objects.create(user=self.user, tenant=self.tenant)

        self.workspace = Workspace.objects.create(
            name="Test Workspace",
            slug="test-workspace",
            owner=self.user,
            tenant=self.tenant
        )

    def tearDown(self):
        """Clean up."""
        set_current_tenant(None)

    def test_related_object_creation(self):
        """Test creating related objects."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace
        )

        # Test related object access
        # related = obj.related_items.create(name="Related Item")
        # self.assertEqual(related.mymodel, obj)

    def test_cascade_delete(self):
        """Test cascade deletion."""
        obj = MyModel.objects.create(
            name="Test Model",
            user=self.user,
            workspace=self.workspace
        )

        obj_id = obj.id

        # Delete workspace
        self.workspace.delete()

        # Object should be deleted due to CASCADE
        self.assertFalse(MyModel.objects.unfiltered().filter(id=obj_id).exists())

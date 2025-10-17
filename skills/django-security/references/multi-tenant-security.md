# Multi-Tenant Security

Comprehensive guide to securing multi-tenant Django applications. Covers tenant isolation, data leakage prevention, cross-tenant attacks, and security testing.

## Overview

Multi-tenant applications serve multiple organizations (tenants) from a single instance. Security failures in multi-tenant systems can lead to catastrophic data breaches where one tenant accesses another tenant's data.

**Critical Principle**: Every query, view, API endpoint, and admin action must enforce tenant isolation.

## Tenant Isolation Strategies

### Row-Level Isolation (Shared Database, Shared Schema)

**Architecture**: All tenants share the same database and tables. Each row has a `tenant_id` column.

**Pros**:
- Cost-effective
- Easy to manage
- Simple backups

**Cons**:
- Highest risk of data leakage
- Performance can degrade with many tenants
- Requires strict application-level enforcement

**Security Implementation**:

```python
# models.py
from django.db import models

class TenantBaseModel(models.Model):
    """Base model for all tenant-scoped data."""
    tenant = models.ForeignKey(
        'users.Tenant',
        on_delete=models.CASCADE,
        db_index=True  # CRITICAL: Index for performance
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Validate tenant is set
        if not self.tenant_id:
            from apps.users.middleware import get_current_tenant
            self.tenant = get_current_tenant()

        if not self.tenant_id:
            raise ValueError("Tenant must be set")

        super().save(*args, **kwargs)

class Document(TenantBaseModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            # CRITICAL: Put tenant first in all composite indexes
            models.Index(fields=['tenant', 'owner', '-created_at']),
            models.Index(fields=['tenant', 'title']),
        ]
        unique_together = [
            # CRITICAL: Include tenant in unique constraints
            ['tenant', 'owner', 'title'],
        ]
```

### Database-Per-Tenant (Shared Server, Separate Databases)

**Architecture**: Each tenant has their own database on the same server.

**Pros**:
- Strong isolation
- Easy to backup/restore individual tenants
- Better performance per tenant

**Cons**:
- More complex to manage
- Higher overhead
- Limited scalability (database connection limits)

**Implementation with django-tenants**:

```python
# Install: pip install django-tenants

# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        # ...
    }
}

TENANT_MODEL = "customers.Client"
TENANT_DOMAIN_MODEL = "customers.Domain"
```

### Server-Per-Tenant (Complete Isolation)

**Architecture**: Each tenant has completely separate infrastructure.

**Pros**:
- Perfect isolation
- Customizable per tenant
- No noisy neighbor issues

**Cons**:
- Expensive
- Complex to manage
- Harder to maintain/upgrade

## Critical Security Rules

### Rule 1: Always Filter by Tenant

```python
# ❌ DANGEROUS: No tenant filter
def get_documents(request):
    documents = Document.objects.all()  # LEAKS DATA!
    return documents

# ✅ SECURE: Always filter by tenant
def get_documents(request):
    documents = Document.objects.filter(tenant=request.tenant)
    return documents
```

### Rule 2: Validate Tenant on Object Access

```python
# ❌ VULNERABLE: No tenant check
def view_document(request, doc_id):
    doc = Document.objects.get(id=doc_id)  # Can access any tenant!
    return render(request, 'document.html', {'doc': doc})

# ✅ SECURE: Validate tenant ownership
def view_document(request, doc_id):
    doc = get_object_or_404(
        Document,
        id=doc_id,
        tenant=request.tenant  # CRITICAL
    )
    return render(request, 'document.html', {'doc': doc})

# ✅ EVEN BETTER: Additional validation
from django.core.exceptions import PermissionDenied

def view_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # Explicit tenant check
    if doc.tenant != request.tenant:
        # Log the attempt
        logger.warning(
            f"Cross-tenant access attempt: User {request.user.id} "
            f"tried to access tenant {doc.tenant.id} data"
        )
        raise PermissionDenied("Access denied")

    # Additional ownership check if needed
    if doc.owner != request.user and not request.user.is_staff:
        raise PermissionDenied("Access denied")

    return render(request, 'document.html', {'doc': doc})
```

### Rule 3: Use Automatic Tenant Filtering

**Implement custom QuerySet and Manager**:

```python
# managers.py
from django.db import models
from django.db.models import Q

class TenantQuerySet(models.QuerySet):
    """Automatically filters by current tenant."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._add_tenant_filter()

    def _add_tenant_filter(self):
        """Add tenant filter to queryset."""
        from apps.users.middleware import get_current_tenant

        tenant = get_current_tenant()
        if tenant is not None:
            # Only filter if tenant is set
            return self.filter(tenant=tenant)
        return self

    def unfiltered(self):
        """Remove tenant filter - USE WITH EXTREME CAUTION!"""
        # Only for admin/system operations
        return self.model.objects.db_manager(self.db).get_queryset()

    def for_tenant(self, tenant):
        """Explicitly filter by specific tenant."""
        return self.filter(tenant=tenant)

class TenantManager(models.Manager):
    """Manager that automatically filters by tenant."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def unfiltered(self):
        """Bypass tenant filtering - DANGEROUS, admin only!"""
        return super().get_queryset()

# models.py
class Document(TenantBaseModel):
    title = models.CharField(max_length=200)

    # Default manager - auto-filters by tenant
    objects = TenantManager()

    # Unfiltered manager - ONLY for admin
    all_objects = models.Manager()
```

### Rule 4: Middleware for Tenant Context

```python
# middleware.py
import threading

# Thread-local storage for current tenant
_thread_locals = threading.local()

def get_current_tenant():
    """Get current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)

def set_current_tenant(tenant):
    """Set current tenant in thread-local storage."""
    _thread_locals.tenant = tenant

class TenantMiddleware:
    """Middleware to set current tenant from authenticated user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set tenant from authenticated user
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            tenant = request.user.profile.tenant
            set_current_tenant(tenant)
            request.tenant = tenant
        else:
            set_current_tenant(None)
            request.tenant = None

        response = self.get_response(request)

        # Clear tenant after request
        set_current_tenant(None)

        return response
```

### Rule 5: Validate Cross-Tenant References

```python
# models.py
from django.core.exceptions import ValidationError

class Document(TenantBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def clean(self):
        """Validate tenant consistency."""
        super().clean()

        # Validate workspace belongs to same tenant
        if self.workspace and self.tenant:
            if self.workspace.tenant != self.tenant:
                raise ValidationError({
                    'workspace': 'Workspace must belong to the same tenant'
                })

        # Validate user belongs to same tenant
        if self.owner and self.tenant:
            if hasattr(self.owner, 'profile'):
                if self.owner.profile.tenant != self.tenant:
                    raise ValidationError({
                        'owner': 'User must belong to the same tenant'
                    })

    def save(self, *args, **kwargs):
        # Run validation before save
        self.full_clean()
        super().save(*args, **kwargs)
```

## Common Attack Vectors

### Attack 1: Direct Object Reference

**Attack**: User guesses/enumerates object IDs to access other tenants' data.

```python
# Attacker request:
GET /api/documents/12345/  # Trying random IDs
```

**Defense**:

```python
# ✅ SECURE: Always check tenant
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document(request, doc_id):
    doc = get_object_or_404(
        Document,
        id=doc_id,
        tenant=request.tenant  # CRITICAL
    )
    return Response(DocumentSerializer(doc).data)

# ✅ BETTER: Use UUIDs instead of sequential IDs
class Document(TenantBaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Harder to enumerate than sequential integers
```

### Attack 2: Parameter Tampering

**Attack**: User modifies request parameters to access different tenant.

```python
# Attacker request:
POST /api/documents/
{
  "title": "My Doc",
  "tenant_id": 999  # Trying to set different tenant
}
```

**Defense**:

```python
# ✅ SECURE: Never trust client-provided tenant_id
from rest_framework import serializers

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['title', 'content']
        # tenant_id NOT included - set from request

# views.py
@api_view(['POST'])
def create_document(request):
    serializer = DocumentSerializer(data=request.data)
    if serializer.is_valid():
        # Force tenant from authenticated user
        serializer.save(
            tenant=request.tenant,  # From middleware
            owner=request.user
        )
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
```

### Attack 3: SQL Injection to Bypass Tenant Filter

**Attack**: Use SQL injection to bypass tenant filtering.

```python
# Attacker input:
search = "test' OR tenant_id != tenant_id OR 'a'='a"
```

**Defense**:

```python
# ✅ SECURE: Use Django ORM (parameterized queries)
def search_documents(request):
    query = request.GET.get('q', '')

    # Django ORM prevents SQL injection
    documents = Document.objects.filter(
        tenant=request.tenant,
        title__icontains=query  # Safely parameterized
    )
    return documents

# ❌ NEVER do this:
def search_documents_vulnerable(request):
    query = request.GET.get('q', '')
    sql = f"SELECT * FROM documents WHERE title LIKE '%{query}%' AND tenant_id = {request.tenant.id}"
    # VULNERABLE to SQL injection!
```

### Attack 4: GraphQL/API Over-fetching

**Attack**: Request related objects from different tenants.

```graphql
# Attacker query:
query {
  document(id: "123") {
    title
    workspace {
      documents {  # Trying to fetch all workspace docs
        id
        title
      }
    }
  }
}
```

**Defense**:

```python
# GraphQL (using graphene-django)
import graphene
from graphene_django import DjangoObjectType

class DocumentType(DjangoObjectType):
    class Meta:
        model = Document
        fields = ['id', 'title', 'content', 'workspace']

class Query(graphene.ObjectType):
    document = graphene.Field(DocumentType, id=graphene.ID())

    def resolve_document(self, info, id):
        # ✅ SECURE: Filter by tenant
        return Document.objects.filter(
            id=id,
            tenant=info.context.tenant  # From request
        ).first()

# Ensure related queries also filter
class WorkspaceType(DjangoObjectType):
    class Meta:
        model = Workspace

    def resolve_documents(self, info):
        # ✅ SECURE: Filter by tenant
        return self.documents.filter(tenant=info.context.tenant)
```

### Attack 5: Subdomain Takeover

**Attack**: Register expired subdomain to impersonate tenant.

**Defense**:

```python
# Validate subdomains
class TenantMiddleware:
    def __call__(self, request):
        # Get subdomain
        host = request.get_host().split(':')[0]
        parts = host.split('.')

        if len(parts) > 2:
            subdomain = parts[0]

            # ✅ Validate subdomain exists and is active
            try:
                tenant = Tenant.objects.get(
                    subdomain=subdomain,
                    is_active=True  # Prevent inactive tenant access
                )
                request.tenant = tenant
            except Tenant.DoesNotExist:
                # Log suspicious subdomain access
                logger.warning(f"Invalid subdomain access: {subdomain}")
                return HttpResponseForbidden("Invalid tenant")

        response = self.get_response(request)
        return response

# Regularly audit and cleanup
def cleanup_inactive_tenants():
    """Remove DNS records for inactive tenants."""
    inactive_tenants = Tenant.objects.filter(is_active=False)
    for tenant in inactive_tenants:
        # Remove DNS record, disable subdomain
        remove_dns_record(tenant.subdomain)
```

## Admin Panel Security

### Tenant Filtering in Admin

```python
# admin.py
from django.contrib import admin

class TenantAdminMixin:
    """Mixin to add tenant filtering to admin."""

    def get_queryset(self, request):
        """Filter queryset by tenant for non-superusers."""
        qs = super().get_queryset(request)

        # Superusers see all
        if request.user.is_superuser:
            return qs

        # Regular admin users only see their tenant
        if hasattr(request.user, 'profile') and request.user.profile.tenant:
            return qs.filter(tenant=request.user.profile.tenant)

        # No tenant = no access
        return qs.none()

    def has_change_permission(self, request, obj=None):
        """Check tenant permission for changes."""
        has_perm = super().has_change_permission(request, obj)

        if not has_perm:
            return False

        # Superusers can change anything
        if request.user.is_superuser:
            return True

        # Check tenant match
        if obj is not None:
            if not hasattr(request.user, 'profile'):
                return False
            return obj.tenant == request.user.profile.tenant

        return True

    def has_delete_permission(self, request, obj=None):
        """Check tenant permission for deletes."""
        return self.has_change_permission(request, obj)

@admin.register(Document)
class DocumentAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'owner', 'tenant', 'created_at']
    list_filter = ['tenant', 'created_at']
    search_fields = ['title', 'content']

    def get_readonly_fields(self, request, obj=None):
        """Make tenant readonly after creation."""
        if obj:  # Editing
            return ['tenant', 'created_at']
        return ['created_at']

    def save_model(self, request, obj, form, change):
        """Auto-set tenant on creation."""
        if not change:  # Creating new object
            if not obj.tenant_id and hasattr(request.user, 'profile'):
                obj.tenant = request.user.profile.tenant
        super().save_model(request, obj, form, change)
```

### IP Whitelisting for Admin

```python
# middleware/admin_security.py
from django.core.exceptions import PermissionDenied
from django.conf import settings
import logging

logger = logging.getLogger('security')

class AdminTenantSecurityMiddleware:
    """Enhanced security for admin panel."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            # IP whitelist check
            if hasattr(settings, 'ADMIN_ALLOWED_IPS'):
                ip = self.get_client_ip(request)
                if ip not in settings.ADMIN_ALLOWED_IPS:
                    logger.warning(
                        f"Admin access denied from IP: {ip}, "
                        f"User: {request.user}"
                    )
                    raise PermissionDenied("Access denied")

            # Require 2FA for admin (if using django-otp)
            if request.user.is_authenticated:
                if not request.user.is_verified():
                    logger.warning(
                        f"Admin access without 2FA: {request.user}"
                    )
                    return redirect('two_factor:login')

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

## API Security

### Django REST Framework

```python
# permissions.py
from rest_framework import permissions

class IsSameTenant(permissions.BasePermission):
    """
    Permission to only allow access to objects in same tenant.
    """

    def has_object_permission(self, request, view, obj):
        # Check obj has tenant attribute
        if not hasattr(obj, 'tenant'):
            return False

        # Check request has tenant
        if not hasattr(request, 'tenant') or request.tenant is None:
            return False

        # Check tenant match
        return obj.tenant == request.tenant

# views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsSameTenant]

    def get_queryset(self):
        """Always filter by tenant."""
        return Document.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        """Force tenant on creation."""
        serializer.save(
            tenant=self.request.tenant,
            owner=self.request.user
        )
```

### GraphQL Security

```python
# schema.py
import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

class DocumentType(DjangoObjectType):
    class Meta:
        model = Document
        fields = ['id', 'title', 'content']

class Query(graphene.ObjectType):
    documents = graphene.List(DocumentType)
    document = graphene.Field(DocumentType, id=graphene.ID(required=True))

    def resolve_documents(self, info):
        # Check authentication
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required")

        # Filter by tenant
        tenant = getattr(info.context, 'tenant', None)
        if not tenant:
            raise GraphQLError("Tenant context required")

        return Document.objects.filter(tenant=tenant)

    def resolve_document(self, info, id):
        if not info.context.user.is_authenticated:
            raise GraphQLError("Authentication required")

        tenant = getattr(info.context, 'tenant', None)
        if not tenant:
            raise GraphQLError("Tenant context required")

        try:
            return Document.objects.get(id=id, tenant=tenant)
        except Document.DoesNotExist:
            raise GraphQLError("Document not found")
```

## Database-Level Security

### PostgreSQL Row-Level Security (RLS)

**Defense in depth**: Even if application code fails, database enforces isolation.

```sql
-- Enable RLS on table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create policy for tenant isolation
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::integer);

-- Grant access
GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO app_user;
```

**Django Integration**:

```python
# middleware.py
class PostgreSQLRLSMiddleware:
    """Set PostgreSQL session variable for RLS."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'tenant') and request.tenant:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [request.tenant.id]
                )

        response = self.get_response(request)
        return response
```

### Database Indexes for Performance and Security

```python
class Document(TenantBaseModel):
    class Meta:
        indexes = [
            # CRITICAL: Tenant-first indexes
            models.Index(fields=['tenant', 'owner', '-created_at']),
            models.Index(fields=['tenant', 'workspace', '-created_at']),

            # Unique constraints with tenant
            models.UniqueConstraint(
                fields=['tenant', 'slug'],
                name='unique_document_slug_per_tenant'
            ),
        ]

        # Partial indexes for active records
        models.Index(
            fields=['tenant', '-created_at'],
            condition=Q(is_deleted=False),
            name='active_documents_idx'
        )
```

## Audit Logging

```python
# models.py
class AuditLog(models.Model):
    """Log all tenant access for security auditing."""

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    details = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]

# middleware.py
class AuditMiddleware:
    """Log all tenant access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log access if tenant and user present
        if hasattr(request, 'tenant') and request.tenant:
            if request.user.is_authenticated:
                AuditLog.objects.create(
                    user=request.user,
                    tenant=request.tenant,
                    action=request.method,
                    model_name=request.path,
                    object_id='',
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'path': request.path,
                        'query': request.GET.dict(),
                    }
                )

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
```

## Testing Multi-Tenant Security

```python
# tests/test_tenant_security.py
from django.test import TestCase
from apps.users.models import Tenant, User, UserProfile
from apps.users.middleware import set_current_tenant
from myapp.models import Document

class TenantSecurityTest(TestCase):
    def setUp(self):
        # Create two tenants
        self.tenant1 = Tenant.objects.create(name='Tenant 1', slug='tenant1')
        self.tenant2 = Tenant.objects.create(name='Tenant 2', slug='tenant2')

        # Create users for each tenant
        self.user1 = User.objects.create_user('user1', password='pass')
        self.user1.profile = UserProfile.objects.create(
            user=self.user1,
            tenant=self.tenant1
        )

        self.user2 = User.objects.create_user('user2', password='pass')
        self.user2.profile = UserProfile.objects.create(
            user=self.user2,
            tenant=self.tenant2
        )

    def test_tenant_isolation(self):
        """Test basic tenant isolation."""
        # Create document for tenant1
        set_current_tenant(self.tenant1)
        doc1 = Document.objects.create(
            title='Tenant 1 Doc',
            owner=self.user1
        )

        # Create document for tenant2
        set_current_tenant(self.tenant2)
        doc2 = Document.objects.create(
            title='Tenant 2 Doc',
            owner=self.user2
        )

        # Verify isolation
        set_current_tenant(self.tenant1)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.first(), doc1)

        set_current_tenant(self.tenant2)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.first(), doc2)

    def test_cross_tenant_access_prevention(self):
        """Test users cannot access other tenant's data."""
        # Create doc for tenant1
        set_current_tenant(self.tenant1)
        doc = Document.objects.create(
            title='Private Doc',
            owner=self.user1
        )

        # Try to access as tenant2
        self.client.force_login(self.user2)
        response = self.client.get(f'/api/documents/{doc.id}/')

        # Should be 404 (not found) not 403 (to avoid leaking existence)
        self.assertEqual(response.status_code, 404)

    def test_parameter_tampering(self):
        """Test tenant cannot be tampered in requests."""
        self.client.force_login(self.user1)

        # Try to create doc with different tenant_id
        response = self.client.post('/api/documents/', {
            'title': 'Test',
            'tenant_id': self.tenant2.id  # Trying to set different tenant
        })

        # Should succeed but with correct tenant
        self.assertEqual(response.status_code, 201)
        doc = Document.objects.get(title='Test')
        self.assertEqual(doc.tenant, self.tenant1)  # Forced to user's tenant

    def test_admin_tenant_filtering(self):
        """Test admin panel filters by tenant."""
        # Create docs for both tenants
        set_current_tenant(self.tenant1)
        doc1 = Document.objects.create(title='Doc 1', owner=self.user1)

        set_current_tenant(self.tenant2)
        doc2 = Document.objects.create(title='Doc 2', owner=self.user2)

        # Login as tenant1 admin
        self.user1.is_staff = True
        self.user1.save()
        self.client.force_login(self.user1)

        # Access admin changelist
        response = self.client.get('/admin/myapp/document/')
        self.assertEqual(response.status_code, 200)

        # Should only see tenant1 docs
        self.assertContains(response, 'Doc 1')
        self.assertNotContains(response, 'Doc 2')
```

## Security Checklist

### Development Phase
- [ ] All models inherit from TenantBaseModel
- [ ] All composite indexes start with tenant field
- [ ] All unique constraints include tenant field
- [ ] Cross-tenant validation in clean() methods
- [ ] Custom managers filter by tenant
- [ ] Middleware sets tenant context
- [ ] Admin panels filter by tenant
- [ ] API endpoints validate tenant
- [ ] GraphQL resolvers filter by tenant

### Testing Phase
- [ ] Test basic tenant isolation
- [ ] Test cross-tenant access prevention
- [ ] Test parameter tampering prevention
- [ ] Test admin panel filtering
- [ ] Test API tenant validation
- [ ] Test SQL injection doesn't bypass filters
- [ ] Test with multiple tenants simultaneously

### Deployment Phase
- [ ] Enable PostgreSQL RLS (if using)
- [ ] Set up audit logging
- [ ] Monitor for cross-tenant access attempts
- [ ] Regular security audits
- [ ] Penetration testing for tenant isolation

### Monitoring
- [ ] Alert on cross-tenant access attempts
- [ ] Monitor unusual query patterns
- [ ] Track tenant access in audit logs
- [ ] Regular review of audit logs
- [ ] Automated tenant isolation testing

## Resources

- Django Multi-Tenant: https://django-tenants.readthedocs.io/
- PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- OWASP Multi-Tenancy Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Multitenant_Security_Cheat_Sheet.html

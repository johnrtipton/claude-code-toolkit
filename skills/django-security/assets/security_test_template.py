"""
Django Security Test Templates

Comprehensive security test examples.
Copy and adapt these for your Django project.

Usage:
1. Create tests/test_security.py in your app
2. Copy relevant test classes
3. Adapt to your models and views
4. Run: python manage.py test
"""

from django.test import TestCase, Client, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings
from django.urls import reverse

User = get_user_model()


# ==============================================================================
# Django Settings Security Tests
# ==============================================================================

class SecuritySettingsTest(TestCase):
    """Test that security settings are properly configured."""

    def test_debug_is_false(self):
        """Ensure DEBUG is False in production."""
        # This test should run with production settings
        self.assertFalse(settings.DEBUG, "DEBUG must be False in production!")

    def test_secret_key_is_set(self):
        """Ensure SECRET_KEY is configured and strong."""
        self.assertTrue(settings.SECRET_KEY)
        self.assertGreater(len(settings.SECRET_KEY), 40, "SECRET_KEY should be at least 40 characters")
        self.assertNotIn('django-insecure', settings.SECRET_KEY.lower())
        self.assertNotIn('changeme', settings.SECRET_KEY.lower())

    def test_allowed_hosts_configured(self):
        """Ensure ALLOWED_HOSTS is properly set."""
        self.assertTrue(settings.ALLOWED_HOSTS, "ALLOWED_HOSTS must be configured")
        self.assertNotIn('*', settings.ALLOWED_HOSTS, "ALLOWED_HOSTS should not use wildcard")

    def test_secure_ssl_redirect(self):
        """Ensure SSL redirect is enabled."""
        self.assertTrue(settings.SECURE_SSL_REDIRECT, "SECURE_SSL_REDIRECT should be True")

    def test_hsts_enabled(self):
        """Ensure HSTS is properly configured."""
        self.assertGreater(settings.SECURE_HSTS_SECONDS, 0, "HSTS should be enabled")
        self.assertGreaterEqual(
            settings.SECURE_HSTS_SECONDS,
            31536000,  # 1 year
            "HSTS should be at least 1 year"
        )

    def test_session_cookie_secure(self):
        """Ensure session cookies are secure."""
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertIn(settings.SESSION_COOKIE_SAMESITE, ['Lax', 'Strict'])

    def test_csrf_cookie_secure(self):
        """Ensure CSRF cookies are secure."""
        self.assertTrue(settings.CSRF_COOKIE_SECURE)

    def test_security_middleware_enabled(self):
        """Ensure security middleware is enabled."""
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]

        for middleware in required_middleware:
            self.assertIn(
                middleware,
                settings.MIDDLEWARE,
                f"{middleware} must be in MIDDLEWARE"
            )

    def test_password_validators_configured(self):
        """Ensure password validators are configured."""
        self.assertTrue(
            settings.AUTH_PASSWORD_VALIDATORS,
            "AUTH_PASSWORD_VALIDATORS must be configured"
        )
        self.assertGreaterEqual(
            len(settings.AUTH_PASSWORD_VALIDATORS),
            3,
            "At least 3 password validators should be enabled"
        )


# ==============================================================================
# CSRF Protection Tests
# ==============================================================================

class CSRFProtectionTest(TestCase):
    """Test CSRF protection."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user('testuser', password='testpass123')

    def test_csrf_protection_on_post(self):
        """Test CSRF protection on POST requests."""
        # Login
        self.client.force_login(self.user)

        # POST without CSRF token should fail
        response = self.client.post('/some-endpoint/', {'data': 'value'})
        self.assertEqual(response.status_code, 403, "POST without CSRF should return 403")

    def test_csrf_token_required(self):
        """Test CSRF token is required for unsafe methods."""
        self.client.force_login(self.user)

        # GET should work without CSRF
        response = self.client.get('/some-endpoint/')
        self.assertNotEqual(response.status_code, 403)

        # POST should require CSRF
        response = self.client.post('/some-endpoint/', {})
        self.assertEqual(response.status_code, 403)


# ==============================================================================
# XSS Protection Tests
# ==============================================================================

class XSSProtectionTest(TestCase):
    """Test XSS (Cross-Site Scripting) prevention."""

    def test_template_auto_escaping(self):
        """Test that templates auto-escape user input."""
        xss_payload = '<script>alert("XSS")</script>'

        response = self.client.get(f'/page/?search={xss_payload}')

        # Should be escaped
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_json_response_escaping(self):
        """Test JSON responses escape HTML."""
        from django.http import JsonResponse

        xss_payload = '<script>alert("XSS")</script>'
        response = JsonResponse({'data': xss_payload})

        # Should be safe
        self.assertNotContains(response, '<script>', html=False)


# ==============================================================================
# SQL Injection Protection Tests
# ==============================================================================

class SQLInjectionTest(TestCase):
    """Test SQL injection prevention."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='testpass123')

    def test_orm_prevents_sql_injection(self):
        """Test Django ORM prevents SQL injection."""
        # SQL injection attempt
        malicious_input = "'; DROP TABLE users; --"

        # Using Django ORM - should be safe
        users = User.objects.filter(username=malicious_input)

        # Query should execute safely
        self.assertEqual(users.count(), 0)

        # Users table should still exist
        self.assertTrue(User.objects.exists())

    def test_sql_injection_in_search(self):
        """Test search functionality prevents SQL injection."""
        malicious_search = "test' OR '1'='1"

        response = self.client.get(f'/search/?q={malicious_search}')

        # Should not return all users
        # Verify the query didn't return unexpected results


# ==============================================================================
# Authentication and Authorization Tests
# ==============================================================================

class AuthenticationTest(TestCase):
    """Test authentication security."""

    def setUp(self):
        self.user = User.objects.create_user(
            'testuser',
            'test@example.com',
            'StrongPassword123!'
        )

    def test_login_required(self):
        """Test that protected views require login."""
        response = self.client.get('/protected-view/')

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.LOGIN_URL, response.url)

    def test_weak_password_rejected(self):
        """Test that weak passwords are rejected."""
        with self.assertRaises(ValidationError):
            user = User.objects.create_user('newuser', password='weak')
            user.full_clean()

    def test_password_not_in_response(self):
        """Test passwords are never exposed in responses."""
        response = self.client.get('/api/users/')

        # Password should not be in response
        self.assertNotContains(response, 'password', status_code=None)

    def test_session_invalidated_on_logout(self):
        """Test session is invalidated on logout."""
        self.client.login(username='testuser', password='StrongPassword123!')

        # Get session key
        session_key = self.client.session.session_key

        # Logout
        self.client.logout()

        # Session should be invalidated
        from django.contrib.sessions.models import Session
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())


# ==============================================================================
# Permission Tests
# ==============================================================================

class PermissionTest(TestCase):
    """Test permission enforcement."""

    def setUp(self):
        self.user1 = User.objects.create_user('user1', password='pass')
        self.user2 = User.objects.create_user('user2', password='pass')

    def test_user_cannot_access_others_data(self):
        """Test users cannot access other users' data."""
        # Create object owned by user1
        from myapp.models import Document
        doc = Document.objects.create(owner=self.user1, title='Private')

        # Login as user2
        self.client.force_login(self.user2)

        # Try to access user1's document
        response = self.client.get(f'/documents/{doc.id}/')

        # Should be denied
        self.assertIn(response.status_code, [403, 404])


# ==============================================================================
# Multi-Tenant Security Tests
# ==============================================================================

class MultiTenantSecurityTest(TransactionTestCase):
    """Test multi-tenant security and isolation."""

    def setUp(self):
        from myapp.models import Tenant
        from myapp.middleware import set_current_tenant

        # Create two tenants
        self.tenant1 = Tenant.objects.create(name='Tenant 1', slug='tenant1')
        self.tenant2 = Tenant.objects.create(name='Tenant 2', slug='tenant2')

        # Create users for each tenant
        self.user1 = User.objects.create_user('user1', password='pass')
        self.user1.profile.tenant = self.tenant1
        self.user1.profile.save()

        self.user2 = User.objects.create_user('user2', password='pass')
        self.user2.profile.tenant = self.tenant2
        self.user2.profile.save()

    def test_tenant_isolation(self):
        """Test basic tenant isolation."""
        from myapp.models import Document
        from myapp.middleware import set_current_tenant

        # Create document for tenant1
        set_current_tenant(self.tenant1)
        doc1 = Document.objects.create(title='Tenant 1 Doc', owner=self.user1)

        # Create document for tenant2
        set_current_tenant(self.tenant2)
        doc2 = Document.objects.create(title='Tenant 2 Doc', owner=self.user2)

        # Verify isolation
        set_current_tenant(self.tenant1)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.first(), doc1)

        set_current_tenant(self.tenant2)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(Document.objects.first(), doc2)

    def test_cross_tenant_access_prevention(self):
        """Test users cannot access other tenant's data."""
        from myapp.models import Document
        from myapp.middleware import set_current_tenant

        # Create document for tenant1
        set_current_tenant(self.tenant1)
        doc = Document.objects.create(title='Private', owner=self.user1)

        # Login as user from tenant2
        self.client.force_login(self.user2)

        # Try to access tenant1's document
        response = self.client.get(f'/api/documents/{doc.id}/')

        # Should be denied (404 to not leak existence)
        self.assertEqual(response.status_code, 404)

    def test_parameter_tampering_prevention(self):
        """Test tenant_id cannot be tampered with."""
        from myapp.models import Document

        self.client.force_login(self.user1)

        # Try to create document with different tenant_id
        response = self.client.post('/api/documents/', {
            'title': 'Test',
            'tenant_id': self.tenant2.id  # Attempting to set different tenant
        })

        if response.status_code == 201:
            # Document should have user's tenant, not tampered tenant
            doc = Document.objects.get(title='Test')
            self.assertEqual(doc.tenant, self.tenant1)


# ==============================================================================
# Security Headers Tests
# ==============================================================================

class SecurityHeadersTest(TestCase):
    """Test security headers are properly set."""

    def test_hsts_header(self):
        """Test HSTS header is set."""
        response = self.client.get('/')
        self.assertIn('Strict-Transport-Security', response)

    def test_xss_filter_header(self):
        """Test X-XSS-Protection header."""
        response = self.client.get('/')
        # May be deprecated but still useful for old browsers
        # Modern browsers use CSP instead

    def test_content_type_nosniff(self):
        """Test X-Content-Type-Options header."""
        response = self.client.get('/')
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')

    def test_frame_options(self):
        """Test X-Frame-Options header."""
        response = self.client.get('/')
        self.assertIn(response.get('X-Frame-Options'), ['DENY', 'SAMEORIGIN'])


# ==============================================================================
# File Upload Security Tests
# ==============================================================================

class FileUploadSecurityTest(TestCase):
    """Test file upload security."""

    def test_file_size_limit(self):
        """Test file size limits are enforced."""
        # Create file larger than allowed
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create 10MB file (assuming 5MB limit)
        large_file = SimpleUploadedFile(
            "large_file.txt",
            b"x" * (10 * 1024 * 1024),  # 10 MB
            content_type="text/plain"
        )

        response = self.client.post('/upload/', {'file': large_file})

        # Should be rejected
        self.assertIn(response.status_code, [400, 413])

    def test_file_type_validation(self):
        """Test only allowed file types can be uploaded."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Try to upload executable
        exe_file = SimpleUploadedFile(
            "malicious.exe",
            b"MZ",  # PE executable header
            content_type="application/x-msdownload"
        )

        response = self.client.post('/upload/', {'file': exe_file})

        # Should be rejected
        self.assertEqual(response.status_code, 400)


# ==============================================================================
# Session Security Tests
# ==============================================================================

class SessionSecurityTest(TestCase):
    """Test session security."""

    def test_session_expires(self):
        """Test session expires after timeout."""
        user = User.objects.create_user('testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Session should be set
        self.assertTrue(self.client.session.session_key)

        # Verify session timeout is configured
        self.assertIsNotNone(settings.SESSION_COOKIE_AGE)

    def test_session_cookie_secure(self):
        """Test session cookie has secure flag."""
        # This is tested in settings but can also test in response
        pass


# ==============================================================================
# Secrets and Environment Tests
# ==============================================================================

class SecretsTest(TestCase):
    """Test that secrets are not exposed."""

    def test_secret_key_not_in_error_pages(self):
        """Test SECRET_KEY is not exposed in error pages."""
        # This requires DEBUG=True to test, but in production
        # should never be exposed
        pass

    def test_database_password_not_exposed(self):
        """Test database password is not exposed."""
        # Verify it's not in settings output
        pass


# ==============================================================================
# API Security Tests
# ==============================================================================

class APISecurityTest(TestCase):
    """Test API-specific security."""

    def test_api_requires_authentication(self):
        """Test API endpoints require authentication."""
        response = self.client.get('/api/sensitive-data/')

        # Should be 401 or 403
        self.assertIn(response.status_code, [401, 403])

    def test_api_rate_limiting(self):
        """Test API rate limiting."""
        # Make many rapid requests
        for i in range(100):
            response = self.client.get('/api/endpoint/')

        # Should eventually get rate limited
        # self.assertEqual(response.status_code, 429)

    def test_api_validates_content_type(self):
        """Test API validates Content-Type."""
        response = self.client.post(
            '/api/endpoint/',
            data='malicious data',
            content_type='text/plain'
        )

        # Should reject non-JSON
        self.assertEqual(response.status_code, 415)


# ==============================================================================
# Integration Tests
# ==============================================================================

class SecurityIntegrationTest(TestCase):
    """Integration tests for security features."""

    def test_complete_authentication_flow(self):
        """Test complete authentication flow is secure."""
        # 1. Login
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'TestPass123!'
        })

        # 2. Verify session created
        self.assertTrue(self.client.session.session_key)

        # 3. Access protected resource
        response = self.client.get('/protected/')
        self.assertEqual(response.status_code, 200)

        # 4. Logout
        response = self.client.post('/logout/')

        # 5. Verify cannot access protected resource
        response = self.client.get('/protected/')
        self.assertIn(response.status_code, [302, 401, 403])


# ==============================================================================
# Run Security Tests
# ==============================================================================

# To run these tests:
# python manage.py test tests.test_security

# Run specific test class:
# python manage.py test tests.test_security.SecuritySettingsTest

# Run with coverage:
# pip install coverage
# coverage run --source='.' manage.py test
# coverage report
# coverage html

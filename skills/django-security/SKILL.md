---
name: django-security
description: This skill should be used when conducting security reviews, auditing Django applications, hardening security settings, implementing OWASP Top 10 protections, managing secrets, or ensuring multi-tenant security isolation. Provides automated security auditor that scans settings, code, dependencies, and multi-tenant configurations with auto-fix capabilities.
---

# Django Security Best Practices

Comprehensive security guidance and automated auditing for Django applications, with special focus on multi-tenant security patterns.

## Overview

Secure Django applications against common vulnerabilities including OWASP Top 10, Django-specific security issues, multi-tenant data leakage, and configuration problems. Use the automated security auditor to scan your codebase and identify security issues with optional auto-fix capabilities.

## When to Use This Skill

Use this skill when:
- Conducting security audits or reviews
- Hardening Django security settings
- Implementing OWASP Top 10 protections
- Managing secrets and credentials
- Ensuring multi-tenant security isolation
- Preparing for security assessments or penetration testing
- Reviewing code for security vulnerabilities
- Setting up secure CI/CD pipelines
- Responding to security incidents

## Quick Start

### Run Security Audit

```bash
# Full security audit (all checks)
python scripts/security_auditor.py

# Report only (no auto-fixes)
python scripts/security_auditor.py --report-only

# Auto-fix mode (fixes safe issues)
python scripts/security_auditor.py --auto-fix

# Specific scans
python scripts/security_auditor.py --scan settings
python scripts/security_auditor.py --scan code
python scripts/security_auditor.py --scan dependencies
python scripts/security_auditor.py --scan multi-tenant

# JSON output for CI/CD
python scripts/security_auditor.py --format json > security-report.json
```

### Security Checklist

Use `assets/security_checklist.md` before deploying:
- Pre-deployment security review
- Settings hardening verification
- Dependency vulnerability check
- Multi-tenant isolation testing
- Secrets management validation

## OWASP Top 10 for Django

### A01: Broken Access Control

**Risk**: Users can access resources or perform actions they shouldn't.

**Django Protection:**
```python
# Use Django permissions
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('myapp.can_edit', raise_exception=True)
def edit_view(request, pk):
    obj = get_object_or_404(MyModel, pk=pk)
    # Always validate ownership/tenant
    if obj.tenant != request.tenant:
        raise PermissionDenied
    # Process request
```

**Multi-tenant:**
```python
# Always filter by tenant
queryset = MyModel.objects.filter(tenant=request.tenant)

# Validate in views
if obj.tenant != request.user.profile.tenant:
    raise PermissionDenied("Access denied")
```

### A02: Cryptographic Failures

**Risk**: Sensitive data exposed due to weak encryption.

**Django Protection:**
```python
# settings.py
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Never hardcode!

# Use strong password hashers
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# HTTPS only
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Encrypt sensitive fields
from django.db import models
from django_cryptography.fields import encrypt

class MyModel(models.Model):
    ssn = encrypt(models.CharField(max_length=11))
```

### A03: Injection

**SQL Injection Risk:**
```python
# ❌ VULNERABLE
query = f"SELECT * FROM myapp_user WHERE username = '{user_input}'"
User.objects.raw(query)

# ✅ SAFE: Use parameterized queries
User.objects.raw("SELECT * FROM myapp_user WHERE username = %s", [user_input])

# ✅ BEST: Use Django ORM
User.objects.filter(username=user_input)
```

**XSS Protection:**
```python
# Django auto-escapes by default in templates
{{ user_input }}  # ✅ Auto-escaped

# ❌ DANGEROUS: Only use when absolutely necessary
{{ html_content|safe }}
from django.utils.safestring import mark_safe
mark_safe(html_content)  # Be very careful!

# ✅ SAFE: Sanitize HTML
from django.utils.html import escape
{{ html_content|escape }}
```

### A04: Insecure Design

**Risk**: Fundamental design flaws in security architecture.

**Django Protection:**
```python
# Implement defense in depth
# 1. Authentication at view level
@login_required
def my_view(request):
    pass

# 2. Authorization checks
if not request.user.has_perm('myapp.view_data'):
    raise PermissionDenied

# 3. Object-level permissions
if obj.tenant != request.tenant:
    raise PermissionDenied

# 4. Rate limiting
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m')
def api_view(request):
    pass
```

### A05: Security Misconfiguration

**Critical Settings:**
```python
# settings.py - Production

# ❌ NEVER in production
DEBUG = False  # CRITICAL: Must be False in production

# ✅ Secure configuration
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ... other middleware
]

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
```

See `references/django-security-settings.md` for complete settings guide.

### A06: Vulnerable and Outdated Components

**Check Dependencies:**
```bash
# Check for known vulnerabilities
pip install safety
safety check

# Or use pip-audit
pip install pip-audit
pip-audit

# Security auditor includes dependency scanning
python scripts/security_auditor.py --scan dependencies
```

**Keep Updated:**
```bash
# Regular updates
pip list --outdated

# Update Django
pip install --upgrade Django

# Pin versions in requirements.txt
Django==4.2.7  # Specific version
```

### A07: Identification and Authentication Failures

**Strong Authentication:**
```python
# settings.py

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Session security
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Failed login protection
from django.contrib.auth import login
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    # Handle login
    pass
```

**Multi-Factor Authentication:**
```python
# Use django-otp or django-two-factor-auth
from django_otp.decorators import otp_required

@otp_required
def sensitive_view(request):
    pass
```

### A08: Software and Data Integrity Failures

**Validate Serialized Data:**
```python
# ❌ DANGEROUS: Pickle is unsafe
import pickle
data = pickle.loads(untrusted_data)  # Code execution risk!

# ✅ SAFE: Use JSON
import json
data = json.loads(untrusted_data)

# ✅ SAFE: Use Django serializers
from django.core import serializers
data = serializers.deserialize('json', untrusted_data)
```

**Verify File Uploads:**
```python
from django.core.exceptions import ValidationError

def validate_file_extension(value):
    import os
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.jpg', '.png']
    if ext.lower() not in valid_extensions:
        raise ValidationError('Unsupported file extension.')

class MyModel(models.Model):
    file = models.FileField(upload_to='uploads/', validators=[validate_file_extension])
```

### A09: Security Logging and Monitoring Failures

**Comprehensive Logging:**
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/security.log',
        },
        'security': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/security-events.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

**Audit Logging:**
```python
import logging
security_logger = logging.getLogger('django.security')

def sensitive_action(request):
    # Log security events
    security_logger.info(
        f"User {request.user.username} accessed sensitive data",
        extra={'ip': request.META.get('REMOTE_ADDR')}
    )
```

### A10: Server-Side Request Forgery (SSRF)

**Validate URLs:**
```python
from urllib.parse import urlparse
from django.core.exceptions import ValidationError

def validate_url(url):
    parsed = urlparse(url)

    # Block private IPs
    if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
        raise ValidationError("Internal URLs not allowed")

    # Whitelist allowed domains
    allowed_domains = ['api.example.com', 'cdn.example.com']
    if parsed.hostname not in allowed_domains:
        raise ValidationError("Domain not whitelisted")

    return url
```

See `references/owasp-top10-django.md` for detailed examples and mitigations.

## Django Security Settings

### Essential Production Settings

```python
# settings.py

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# SECURITY WARNING: define the allowed hosts!
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Security Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# HTTPS/SSL
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

See `assets/secure_settings_template.py` for complete production settings template.

See `references/django-security-settings.md` for comprehensive settings guide.

## Multi-Tenant Security

### Tenant Isolation

**Critical: Always filter by tenant**
```python
# ✅ SAFE: Always filter queries by tenant
def get_queryset(self):
    return MyModel.objects.filter(tenant=self.request.tenant)

# ❌ DANGEROUS: Unfiltered query
def get_all_data(self):
    return MyModel.objects.all()  # Leaks data across tenants!
```

### Cross-Tenant Attack Prevention

```python
# Validate tenant in views
def update_view(request, pk):
    obj = get_object_or_404(MyModel, pk=pk)

    # ✅ CRITICAL: Verify tenant ownership
    if obj.tenant != request.tenant:
        raise PermissionDenied("Access denied")

    # Safe to proceed
    obj.update(data=request.data)
```

### Admin Panel Security

```python
# admin.py
from django.contrib import admin

class MyModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # ✅ Filter by tenant for non-superusers
        if not request.user.is_superuser:
            qs = qs.filter(tenant=request.user.profile.tenant)

        return qs
```

See `references/multi-tenant-security.md` for complete multi-tenant security patterns.

## Secrets Management

### Environment Variables

```python
# ❌ NEVER hardcode secrets
SECRET_KEY = 'hardcoded-secret-key-123'  # DANGEROUS!
DATABASE_PASSWORD = 'mypassword'  # DANGEROUS!

# ✅ Use environment variables
import os
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DATABASE_PASSWORD = os.environ['DB_PASSWORD']

# ✅ Use django-environ
import environ
env = environ.Env()
SECRET_KEY = env('DJANGO_SECRET_KEY')
DATABASE_URL = env.db()
```

### .env Files

```bash
# .env (never commit this!)
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
DATABASE_URL=postgres://user:pass@localhost/dbname
```

```python
# .gitignore
.env
.env.local
.env.*.local
```

### Secret Scanning

```bash
# Check for accidentally committed secrets
python scripts/security_auditor.py --scan code

# Use git-secrets
git secrets --scan

# Use truffleHog
trufflehog git file://. --json
```

See `references/secrets-management.md` for complete secrets management guide.

## Security Testing

### Test Security Controls

```python
# tests/test_security.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class SecurityTestCase(TestCase):
    def test_csrf_protection(self):
        """Test CSRF protection is enabled"""
        response = self.client.post('/api/endpoint/', {})
        self.assertEqual(response.status_code, 403)  # CSRF failure

    def test_tenant_isolation(self):
        """Test users cannot access other tenant's data"""
        # Create two tenants and users
        tenant1 = Tenant.objects.create(name='Tenant 1')
        tenant2 = Tenant.objects.create(name='Tenant 2')

        user1 = User.objects.create_user('user1', tenant=tenant1)
        obj_tenant2 = MyModel.objects.create(tenant=tenant2, name='Secret')

        # Login as user1
        self.client.force_login(user1)

        # Try to access tenant2's object
        response = self.client.get(f'/api/mymodel/{obj_tenant2.pk}/')
        self.assertEqual(response.status_code, 404)  # Should not find it

    def test_sql_injection_protection(self):
        """Test SQL injection is prevented"""
        malicious = "'; DROP TABLE users; --"
        User.objects.filter(username=malicious)  # Should not execute DROP
        # Verify users table still exists
        self.assertTrue(User.objects.exists())
```

See `assets/security_test_template.py` for complete test examples.

## Resources

### scripts/

**`security_auditor.py`** - Automated security scanner

Scans for:
- Insecure Django settings (DEBUG, SECRET_KEY, ALLOWED_HOSTS, etc.)
- Code vulnerabilities (SQL injection, XSS, hardcoded secrets, etc.)
- Dependency vulnerabilities (known CVEs)
- Multi-tenant security issues (missing tenant filters, cross-tenant access)

Usage:
```bash
# Full audit
python scripts/security_auditor.py

# Specific scans
python scripts/security_auditor.py --scan settings
python scripts/security_auditor.py --scan code
python scripts/security_auditor.py --scan dependencies
python scripts/security_auditor.py --scan multi-tenant

# Modes
python scripts/security_auditor.py --report-only
python scripts/security_auditor.py --auto-fix

# Output formats
python scripts/security_auditor.py --format json
python scripts/security_auditor.py --format html
```

### references/

**Comprehensive security guides:**

- `owasp-top10-django.md` - OWASP Top 10 vulnerabilities in Django context
  - Detailed examples for each vulnerability
  - Django-specific mitigations
  - Real-world attack scenarios
  - Testing approaches

- `django-security-settings.md` - Complete Django security settings guide
  - All security-related settings explained
  - Production vs development configurations
  - Middleware security
  - Cookie and session security
  - CORS and CSRF configuration

- `multi-tenant-security.md` - Multi-tenant security patterns
  - Tenant isolation enforcement
  - Cross-tenant attack prevention
  - Admin panel security
  - API security
  - Audit logging

- `secrets-management.md` - Secrets and credentials management
  - Environment variables best practices
  - Vault integration (HashiCorp, AWS)
  - Secret rotation strategies
  - Git secret scanning
  - Production secrets deployment

### assets/

**Templates and checklists:**

- `security_checklist.md` - Pre-deployment security checklist
- `secure_settings_template.py` - Production-ready settings.py template
- `security_middleware_template.py` - Custom security middleware examples
- `security_test_template.py` - Security test case templates

## Critical Security Requirements

**Always follow these rules:**

1. ✅ **DEBUG = False in production** - CRITICAL
2. ✅ **Never hardcode SECRET_KEY** - Use environment variables
3. ✅ **Configure ALLOWED_HOSTS** - Never use ['*']
4. ✅ **Use HTTPS in production** - SECURE_SSL_REDIRECT = True
5. ✅ **Enable security middleware** - All Django security middleware
6. ✅ **Filter queries by tenant** - Multi-tenant isolation
7. ✅ **Validate user input** - Prevent injection attacks
8. ✅ **Use Django ORM** - Avoid raw SQL
9. ✅ **Auto-escape templates** - Prevent XSS
10. ✅ **Check permissions** - Authentication and authorization
11. ✅ **Update dependencies** - Check for CVEs regularly
12. ✅ **Log security events** - Monitor for attacks

**Never do these:**

1. ❌ **Never commit secrets** - Use .env files (gitignored)
2. ❌ **Never use mark_safe unnecessarily** - XSS risk
3. ❌ **Never trust user input** - Always validate and sanitize
4. ❌ **Never use eval/exec** - Code execution risk
5. ❌ **Never use pickle on untrusted data** - Code execution risk
6. ❌ **Never skip CSRF protection** - Use @csrf_protect or middleware
7. ❌ **Never use shell=True in subprocess** - Command injection risk
8. ❌ **Never expose admin panel publicly** - Use VPN or IP whitelist
9. ❌ **Never ignore security warnings** - Fix them immediately
10. ❌ **Never skip tenant validation** - Data leakage risk

## Quick Security Audit Workflow

1. **Run security auditor**: `python scripts/security_auditor.py`
2. **Review findings**: Check all CRITICAL and HIGH severity issues
3. **Fix issues**: Use auto-fix for safe fixes, manual for others
4. **Update dependencies**: `pip-audit` or `safety check`
5. **Review settings**: Use `assets/security_checklist.md`
6. **Test security**: Run security test suite
7. **Monitor logs**: Check for security events
8. **Regular audits**: Schedule weekly/monthly security reviews

## CI/CD Integration

```yaml
# .github/workflows/security.yml
name: Security Audit

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run security audit
        run: python scripts/security_auditor.py --format json --report-only
      - name: Check dependencies
        run: pip install pip-audit && pip-audit
      - name: Fail on high severity
        run: python scripts/security_auditor.py --fail-on high
```

## Getting Help

If you encounter security issues:

1. Review the reference documentation for detailed guidance
2. Use the security auditor to identify specific problems
3. Check the security checklist for missed items
4. Test fixes in development environment first
5. Never ignore CRITICAL or HIGH severity findings
6. When in doubt, assume it's a security issue and investigate

Security is not optional. When in doubt, be more restrictive.

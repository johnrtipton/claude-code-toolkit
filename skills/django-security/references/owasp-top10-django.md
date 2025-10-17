# OWASP Top 10 for Django Applications

Comprehensive guide to the OWASP Top 10 web application security risks in the context of Django development, with specific examples, attack vectors, and mitigations.

## Overview

The OWASP Top 10 is a standard awareness document for developers and web application security. It represents a broad consensus about the most critical security risks to web applications.

This guide focuses specifically on how these risks manifest in Django applications and how to mitigate them using Django's built-in security features and best practices.

## A01:2021 - Broken Access Control

### Description

Access control enforces policy such that users cannot act outside of their intended permissions. Failures typically lead to unauthorized information disclosure, modification, or destruction of data, or performing a business function outside the user's limits.

### Common Django Vulnerabilities

**Insecure Direct Object References (IDOR)**

```python
# ❌ VULNERABLE: No access control check
def view_document(request, doc_id):
    doc = Document.objects.get(id=doc_id)
    return render(request, 'document.html', {'doc': doc})
```

An attacker can enumerate doc_id values to access other users' documents.

**Missing Function Level Access Control**

```python
# ❌ VULNERABLE: No permission check
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return redirect('users')
```

Any authenticated user can delete any user account.

### Django Protections

**Use Django Permissions**

```python
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

@login_required
@permission_required('myapp.view_document', raise_exception=True)
def view_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # ✅ Object-level permission check
    if doc.owner != request.user and not request.user.is_staff:
        raise PermissionDenied

    return render(request, 'document.html', {'doc': doc})
```

**Class-Based Views with Mixins**

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class DocumentDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Document
    permission_required = 'myapp.view_document'

    def get_queryset(self):
        # ✅ Filter by ownership
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(owner=self.request.user)
        return qs
```

**Multi-Tenant Access Control**

```python
def view_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # ✅ Check tenant isolation
    if doc.tenant != request.tenant:
        raise PermissionDenied("Access denied")

    # ✅ Check user permissions
    if doc.owner != request.user and not request.user.has_perm('myapp.view_all_documents'):
        raise PermissionDenied("Access denied")

    return render(request, 'document.html', {'doc': doc})
```

**Django REST Framework**

```python
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read permissions allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # ✅ Write permissions only to owner
        return obj.owner == request.user

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        # ✅ Filter by user and tenant
        return Document.objects.filter(
            owner=self.request.user,
            tenant=self.request.tenant
        )
```

### Testing

```python
def test_access_control(self):
    """Test users cannot access other users' documents"""
    user1 = User.objects.create_user('user1')
    user2 = User.objects.create_user('user2')

    doc = Document.objects.create(owner=user1, title='Private')

    # Login as user2
    self.client.force_login(user2)

    # Try to access user1's document
    response = self.client.get(f'/documents/{doc.id}/')
    self.assertEqual(response.status_code, 403)  # Forbidden
```

## A02:2021 - Cryptographic Failures

### Description

Previously known as "Sensitive Data Exposure," this category focuses on failures related to cryptography (or lack thereof), which often leads to exposure of sensitive data.

### Common Django Vulnerabilities

**Weak Secret Key**

```python
# ❌ VULNERABLE: Weak or hardcoded secret key
SECRET_KEY = 'abc123'  # Too simple
SECRET_KEY = 'django-insecure-...'  # Default development key in production
```

**Unencrypted Communications**

```python
# ❌ VULNERABLE: HTTP instead of HTTPS
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
```

**Storing Sensitive Data in Plain Text**

```python
# ❌ VULNERABLE: Plain text sensitive data
class User(models.Model):
    ssn = models.CharField(max_length=11)  # Stored in plain text
    credit_card = models.CharField(max_length=16)  # Stored in plain text
```

### Django Protections

**Strong Secret Key**

```python
# ✅ SECURE: Use strong, random secret key from environment
import os
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# Generate strong secret key:
# python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**Enforce HTTPS**

```python
# settings.py
# ✅ SECURE: Enforce HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
```

**Encrypt Sensitive Fields**

```python
# ✅ SECURE: Encrypt sensitive data
from django_cryptography.fields import encrypt

class User(models.Model):
    ssn = encrypt(models.CharField(max_length=11))
    credit_card = encrypt(models.CharField(max_length=16))

    # Or use django-fernet-fields
    from fernet_fields import EncryptedCharField
    ssn = EncryptedCharField(max_length=11)
```

**Strong Password Hashing**

```python
# settings.py
# ✅ SECURE: Use Argon2 (strongest)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Install: pip install argon2-cffi
```

**Secure Database Connections**

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'OPTIONS': {
            'sslmode': 'require',  # ✅ Require SSL
        },
    }
}
```

## A03:2021 - Injection

### Description

An application is vulnerable to attack when user-supplied data is not validated, filtered, or sanitized. Injection flaws include SQL, NoSQL, OS command, ORM, LDAP, and Expression Language (EL) or Object Graph Navigation Library (OGNL) injection.

### SQL Injection

**Vulnerable Code**

```python
# ❌ VULNERABLE: String formatting in SQL
def search_users(request):
    search_term = request.GET.get('q', '')

    # String concatenation - DANGEROUS!
    query = f"SELECT * FROM users WHERE username = '{search_term}'"
    users = User.objects.raw(query)

    # Also dangerous:
    query = "SELECT * FROM users WHERE username = '%s'" % search_term
    query = "SELECT * FROM users WHERE username = '{}'".format(search_term)
```

Attack: `' OR '1'='1' --` would return all users.

**Safe Code**

```python
# ✅ SAFE: Use Django ORM
def search_users(request):
    search_term = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=search_term)
    return users

# ✅ SAFE: If raw SQL needed, use parameterized queries
def search_users_raw(request):
    search_term = request.GET.get('q', '')
    users = User.objects.raw(
        "SELECT * FROM users WHERE username = %s",
        [search_term]  # Parameters passed separately
    )
    return users

# ✅ SAFE: Using execute with parameters
from django.db import connection

def custom_query(user_input):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM mytable WHERE column = %s",
            [user_input]  # Parameterized
        )
        return cursor.fetchall()
```

### XSS (Cross-Site Scripting)

**Vulnerable Code**

```python
# ❌ VULNERABLE: Disabling auto-escaping
from django.utils.safestring import mark_safe

def display_comment(request):
    comment = request.GET.get('comment', '')
    # User input marked as safe - DANGEROUS!
    safe_comment = mark_safe(comment)
    return render(request, 'comment.html', {'comment': safe_comment})
```

```html
<!-- ❌ VULNERABLE: Using |safe filter -->
<div>{{ user_comment|safe }}</div>
```

Attack: `<script>alert('XSS')</script>` would execute JavaScript.

**Safe Code**

```python
# ✅ SAFE: Django auto-escapes by default
def display_comment(request):
    comment = request.GET.get('comment', '')
    # No mark_safe - will be auto-escaped in template
    return render(request, 'comment.html', {'comment': comment})
```

```html
<!-- ✅ SAFE: Auto-escaped by default -->
<div>{{ user_comment }}</div>

<!-- ✅ SAFE: Explicitly escape -->
<div>{{ user_comment|escape }}</div>

<!-- ✅ SAFE: Sanitize HTML if needed -->
{% load bleach_tags %}
<div>{{ user_html|bleach }}</div>
```

**When mark_safe is Necessary**

```python
# ✅ ACCEPTABLE: Only for trusted, sanitized content
import bleach

def display_rich_text(request):
    user_html = request.POST.get('content', '')

    # Sanitize HTML to allow only safe tags
    allowed_tags = ['p', 'b', 'i', 'u', 'a', 'ul', 'ol', 'li']
    allowed_attrs = {'a': ['href', 'title']}

    clean_html = bleach.clean(
        user_html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True
    )

    # Now safe to mark as safe
    return render(request, 'content.html', {
        'content': mark_safe(clean_html)
    })
```

### Command Injection

**Vulnerable Code**

```python
# ❌ VULNERABLE: Using shell=True with user input
import subprocess

def process_file(request):
    filename = request.GET.get('file', '')

    # DANGEROUS - command injection possible
    subprocess.call(f"cat {filename}", shell=True)

    # Also dangerous:
    os.system(f"cat {filename}")
```

Attack: `file.txt; rm -rf /` would delete files.

**Safe Code**

```python
# ✅ SAFE: Use subprocess without shell
import subprocess
from pathlib import Path

def process_file(request):
    filename = request.GET.get('file', '')

    # Validate filename
    allowed_dir = Path('/var/uploads/')
    file_path = (allowed_dir / filename).resolve()

    # Ensure file is within allowed directory
    if not str(file_path).startswith(str(allowed_dir)):
        raise ValueError("Invalid file path")

    # Use subprocess without shell=True
    result = subprocess.run(
        ['cat', str(file_path)],  # List of arguments
        capture_output=True,
        text=True
    )
    return result.stdout
```

### Template Injection

**Vulnerable Code**

```python
# ❌ VULNERABLE: Using user input in template string
from django.template import Template, Context

def render_custom(request):
    user_template = request.GET.get('template', '')

    # DANGEROUS - template injection
    t = Template(user_template)
    return HttpResponse(t.render(Context({})))
```

Attack: `{{ settings.SECRET_KEY }}` would leak the secret key.

**Safe Code**

```python
# ✅ SAFE: Use predefined templates
def render_custom(request):
    template_name = request.GET.get('template', 'default')

    # Whitelist allowed templates
    allowed_templates = {
        'default': 'default.html',
        'minimal': 'minimal.html',
    }

    template = allowed_templates.get(template_name, 'default.html')
    return render(request, template, {})
```

## A04:2021 - Insecure Design

### Description

Insecure design is a broad category representing different weaknesses, expressed as "missing or ineffective control design." These are flaws in the design and architecture of the application.

### Common Design Flaws in Django

**Lack of Rate Limiting**

```python
# ❌ VULNERABLE: No rate limiting on authentication
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
    return render(request, 'login.html')
```

Allows brute-force attacks.

**Safe Implementation**

```python
# ✅ SECURE: Rate limiting with django-ratelimit
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request):
    if request.method == 'POST':
        # Check if rate limited
        if getattr(request, 'limited', False):
            return HttpResponse('Too many attempts. Try again later.', status=429)

        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            return redirect('home')
        else:
            # Log failed attempt
            logger.warning(f"Failed login for {username} from {request.META.get('REMOTE_ADDR')}")

    return render(request, 'login.html')
```

**Missing Security by Design**

```python
# ❌ VULNERABLE: Implementing own authentication
def custom_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')

    # DANGEROUS - rolling your own crypto
    import hashlib
    password_hash = hashlib.md5(password.encode()).hexdigest()

    user = User.objects.filter(
        username=username,
        password=password_hash
    ).first()

    if user:
        # Set custom session - INSECURE
        request.session['user_id'] = user.id
        return redirect('home')
```

**Secure Implementation**

```python
# ✅ SECURE: Use Django's authentication system
from django.contrib.auth import authenticate, login

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Django handles secure password checking
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Django handles secure session management
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'login.html')
```

### Defense in Depth

```python
# ✅ SECURE: Multiple layers of security
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit

@never_cache  # Layer 1: No caching of sensitive data
@ratelimit(key='user', rate='10/m')  # Layer 2: Rate limiting
@login_required  # Layer 3: Authentication
@permission_required('myapp.delete_document')  # Layer 4: Authorization
def delete_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # Layer 5: Object-level permission
    if doc.owner != request.user and not request.user.is_staff:
        raise PermissionDenied

    # Layer 6: Tenant isolation
    if doc.tenant != request.tenant:
        raise PermissionDenied

    # Layer 7: Audit logging
    logger.info(f"User {request.user} deleted document {doc_id}")

    doc.delete()
    return redirect('documents')
```

## A05:2021 - Security Misconfiguration

### Description

Security misconfiguration can happen at any level of an application stack, including network services, platform, web server, application server, database, frameworks, custom code, and pre-installed virtual machines, containers, or storage.

### Common Django Misconfigurations

**DEBUG Enabled in Production**

```python
# ❌ CRITICAL: DEBUG = True in production
DEBUG = True  # Exposes sensitive information!
```

When DEBUG=True, Django shows detailed error pages with:
- Full tracebacks
- Local variables
- SQL queries
- Settings (potentially including SECRET_KEY)

**Secure Configuration**

```python
# ✅ SECURE: Use environment variables
import os

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# settings/production.py
DEBUG = False
ALLOWED_HOSTS = ['.yourdomain.com']
```

**Complete Security Settings**

```python
# settings/production.py

# Core Security
DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# File Uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# Session Security
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

## A06:2021 - Vulnerable and Outdated Components

### Description

You are likely vulnerable if you do not know the versions of all components you use or if the software is vulnerable, unsupported, or out of date.

### Detection and Prevention

**Check Dependencies**

```bash
# List outdated packages
pip list --outdated

# Check for known vulnerabilities
pip install safety
safety check

# Or use pip-audit (recommended)
pip install pip-audit
pip-audit
```

**Pin Dependencies**

```txt
# requirements.txt
# ✅ SECURE: Pin specific versions
Django==4.2.7
djangorestframework==3.14.0
celery==5.3.4

# ❌ INSECURE: Unpinned versions
# Django
# djangorestframework
```

**Regular Updates**

```bash
# Update Django
pip install --upgrade Django

# Update all dependencies
pip install --upgrade -r requirements.txt

# Use dependabot or renovate for automated updates
```

**Security Monitoring**

```yaml
# .github/workflows/security.yml
name: Security Check

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run security check
        run: pip-audit
```

## A07:2021 - Identification and Authentication Failures

### Description

Confirmation of the user's identity, authentication, and session management is critical to protect against authentication-related attacks.

### Common Vulnerabilities

**Weak Password Requirements**

```python
# ❌ VULNERABLE: No password validation
AUTH_PASSWORD_VALIDATORS = []
```

**Secure Configuration**

```python
# ✅ SECURE: Strong password requirements
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Minimum 12 characters
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

**Session Fixation**

```python
# ✅ SECURE: Rotate session on login
from django.contrib.auth import login

def login_view(request):
    user = authenticate(username=username, password=password)
    if user:
        # Django automatically rotates session ID
        login(request, user)
        return redirect('home')
```

**Multi-Factor Authentication**

```python
# ✅ SECURE: Add 2FA with django-otp
from django_otp.decorators import otp_required

@otp_required
def sensitive_view(request):
    # Only accessible with valid OTP
    pass
```

**Prevent Credential Stuffing**

```python
from django_ratelimit.decorators import ratelimit
import logging

logger = logging.getLogger('security')

@ratelimit(key='ip', rate='5/m', method='POST')
@ratelimit(key='post:username', rate='3/m', method='POST')
def login_view(request):
    if getattr(request, 'limited', False):
        logger.warning(f"Rate limit exceeded from {request.META.get('REMOTE_ADDR')}")
        return HttpResponse('Too many attempts', status=429)

    # Login logic
```

## A08:2021 - Software and Data Integrity Failures

### Description

Software and data integrity failures relate to code and infrastructure that does not protect against integrity violations.

### Vulnerable Patterns

**Unsafe Deserialization**

```python
# ❌ DANGEROUS: Using pickle with untrusted data
import pickle

def load_data(request):
    serialized_data = request.POST.get('data')
    # DANGEROUS - code execution risk!
    data = pickle.loads(serialized_data)
    return data
```

**Safe Alternatives**

```python
# ✅ SAFE: Use JSON
import json

def load_data(request):
    serialized_data = request.POST.get('data')
    data = json.loads(serialized_data)
    return data

# ✅ SAFE: Use Django serializers
from django.core import serializers

def load_objects(request):
    json_data = request.POST.get('data')
    objects = serializers.deserialize('json', json_data)
    return objects
```

**Unsigned Cookies**

```python
# ✅ SECURE: Django signs cookies by default
response = HttpResponse('...')
response.set_signed_cookie('user_id', user.id)

# Reading signed cookie
user_id = request.get_signed_cookie('user_id', default=None)
```

## A09:2021 - Security Logging and Monitoring Failures

### Description

Without logging and monitoring, breaches cannot be detected. Insufficient logging, detection, monitoring, and active response occurs any time.

### Secure Logging Configuration

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/app.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/security.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'myapp.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

**Security Event Logging**

```python
import logging

security_logger = logging.getLogger('myapp.security')

@login_required
def sensitive_action(request):
    # Log security-relevant events
    security_logger.info(
        f"User {request.user.username} accessed sensitive data",
        extra={
            'user_id': request.user.id,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'action': 'view_sensitive_data',
        }
    )
```

## A10:2021 - Server-Side Request Forgery (SSRF)

### Description

SSRF flaws occur whenever a web application is fetching a remote resource without validating the user-supplied URL.

### Vulnerable Code

```python
# ❌ VULNERABLE: Fetching user-supplied URL
import requests

def fetch_url(request):
    url = request.GET.get('url')
    # DANGEROUS - SSRF risk
    response = requests.get(url)
    return HttpResponse(response.content)
```

Attack: `http://localhost:8000/admin/` or `http://169.254.169.254/latest/meta-data/`

### Secure Implementation

```python
# ✅ SECURE: Validate and whitelist URLs
from urllib.parse import urlparse
import requests

ALLOWED_DOMAINS = ['api.example.com', 'cdn.example.com']
BLOCKED_IPS = ['127.0.0.1', 'localhost', '0.0.0.0']

def fetch_url(request):
    url = request.GET.get('url')

    parsed = urlparse(url)

    # Validate scheme
    if parsed.scheme not in ['http', 'https']:
        return HttpResponse('Invalid URL scheme', status=400)

    # Check against blocked IPs
    if parsed.hostname in BLOCKED_IPS:
        return HttpResponse('Blocked URL', status=403)

    # Whitelist domains
    if parsed.hostname not in ALLOWED_DOMAINS:
        return HttpResponse('Domain not whitelisted', status=403)

    # Fetch with timeout
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)
        return HttpResponse(response.content)
    except requests.exceptions.RequestException:
        return HttpResponse('Error fetching URL', status=500)
```

## Summary Checklist

### Quick Security Checklist for Django Apps

- [ ] **A01**: Implement authentication and authorization on all views
- [ ] **A01**: Check object-level permissions
- [ ] **A01**: Enforce tenant isolation in multi-tenant apps
- [ ] **A02**: Use HTTPS in production (SECURE_SSL_REDIRECT=True)
- [ ] **A02**: Use strong SECRET_KEY from environment
- [ ] **A02**: Encrypt sensitive database fields
- [ ] **A03**: Use Django ORM (avoid raw SQL)
- [ ] **A03**: Never use mark_safe with user input
- [ ] **A03**: Parameterize any raw queries
- [ ] **A04**: Implement rate limiting on authentication
- [ ] **A04**: Use Django's built-in auth system
- [ ] **A05**: Set DEBUG=False in production
- [ ] **A05**: Configure all security middleware
- [ ] **A05**: Set secure cookie flags
- [ ] **A06**: Keep Django and dependencies updated
- [ ] **A06**: Use pip-audit or safety to check for CVEs
- [ ] **A07**: Implement strong password validation
- [ ] **A07**: Consider multi-factor authentication
- [ ] **A07**: Rate limit login attempts
- [ ] **A08**: Never use pickle on untrusted data
- [ ] **A08**: Use JSON for serialization
- [ ] **A09**: Configure comprehensive security logging
- [ ] **A09**: Monitor logs for security events
- [ ] **A10**: Validate and whitelist external URLs
- [ ] **A10**: Block access to internal resources

## Testing for OWASP Top 10

```python
# tests/test_security.py
from django.test import TestCase

class OWASPSecurityTests(TestCase):
    def test_broken_access_control(self):
        """A01: Test access control"""
        user1 = User.objects.create_user('user1')
        obj = MyModel.objects.create(owner=user1)

        user2 = User.objects.create_user('user2')
        self.client.force_login(user2)

        response = self.client.get(f'/api/mymodel/{obj.id}/')
        self.assertEqual(response.status_code, 403)

    def test_sql_injection_protection(self):
        """A03: Test SQL injection protection"""
        malicious = "'; DROP TABLE users; --"
        User.objects.filter(username=malicious)
        # Verify table still exists
        self.assertTrue(User.objects.exists())

    def test_xss_protection(self):
        """A03: Test XSS protection"""
        xss = '<script>alert("XSS")</script>'
        response = self.client.get(f'/page/?q={xss}')
        # Verify script is escaped
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')

    def test_rate_limiting(self):
        """A04: Test rate limiting"""
        for i in range(10):
            response = self.client.post('/login/', {
                'username': 'test',
                'password': 'wrong'
            })
        # Should be rate limited
        self.assertEqual(response.status_code, 429)
```

## Resources

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- Django Deployment Checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

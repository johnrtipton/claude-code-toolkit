# Django Security Settings Comprehensive Guide

Complete reference for all Django security-related settings, middleware configuration, and production hardening.

## Overview

Django provides numerous settings to enhance application security. This guide covers every security-related setting, explains what it does, why it matters, and how to configure it properly for production environments.

## Core Security Settings

### DEBUG

**What it does**: Controls whether Django runs in debug mode.

**Why it matters**: When `DEBUG = True`, Django displays detailed error pages with:
- Complete stack traces
- Local variables at each stack frame
- SQL queries executed
- Settings module contents (potentially exposing SECRET_KEY)
- Environment variables

**Configuration**:

```python
# ❌ NEVER in production
DEBUG = True

# ✅ Production
DEBUG = False

# ✅ Best: Use environment variable
import os
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ✅ Alternative: Separate settings files
# settings/production.py
DEBUG = False

# settings/development.py
DEBUG = True
```

**Security Impact**: **CRITICAL**
- Exposing DEBUG=True in production can leak sensitive information
- Attackers can view internal code structure
- May reveal SECRET_KEY, API keys, database credentials

### SECRET_KEY

**What it does**: Cryptographic signing key used for:
- Session security
- Password reset tokens
- Cryptographic signing
- CSRF protection
- Django's signing framework

**Why it matters**: If SECRET_KEY is compromised:
- Attackers can forge session cookies
- Password reset tokens can be forged
- CSRF protection can be bypassed
- Any signed data can be forged

**Configuration**:

```python
# ❌ NEVER hardcode
SECRET_KEY = 'django-insecure-hardcoded-key-123'

# ❌ NEVER commit to git
SECRET_KEY = 'abc123def456'

# ✅ Use environment variable
import os
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# ✅ Use django-environ
import environ
env = environ.Env()
SECRET_KEY = env('SECRET_KEY')

# ✅ Use python-decouple
from decouple import config
SECRET_KEY = config('SECRET_KEY')
```

**Generate strong SECRET_KEY**:

```bash
# Method 1: Django utility
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Method 2: Python secrets module
python -c 'import secrets; print(secrets.token_urlsafe(50))'

# Method 3: OpenSSL
openssl rand -base64 50
```

**Security Impact**: **CRITICAL**
- Must be at least 50 characters
- Must be random and unpredictable
- Must be kept secret
- Should be rotated periodically in high-security environments

### ALLOWED_HOSTS

**What it does**: List of host/domain names this Django site can serve.

**Why it matters**: Protects against HTTP Host header attacks:
- DNS rebinding attacks
- Cache poisoning
- Password reset poisoning

**Configuration**:

```python
# ❌ VULNERABLE: Allows any host
ALLOWED_HOSTS = ['*']
ALLOWED_HOSTS = ['*']  # Using wildcard

# ❌ VULNERABLE: Too permissive
ALLOWED_HOSTS = ['*', 'localhost']

# ✅ Production: Specific hosts only
ALLOWED_HOSTS = [
    'example.com',
    'www.example.com',
    'api.example.com',
]

# ✅ With environment variable
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# ✅ Different per environment
# settings/production.py
ALLOWED_HOSTS = ['.example.com']  # Matches example.com and *.example.com

# settings/development.py
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# ✅ For load balancers/proxies
ALLOWED_HOSTS = [
    '.elasticbeanstalk.com',  # AWS
    '.herokuapp.com',          # Heroku
    'example.com',
]
```

**Wildcard Subdomain**:

```python
# Matches example.com and all subdomains
ALLOWED_HOSTS = ['.example.com']

# This matches:
# - example.com
# - www.example.com
# - api.example.com
# - subdomain.example.com
```

**Security Impact**: **HIGH**
- Always specify explicit hosts in production
- Never use '*' wildcard in production
- Regularly audit and update allowed hosts

## HTTPS/SSL Settings

### SECURE_SSL_REDIRECT

**What it does**: Redirects all HTTP requests to HTTPS.

**Configuration**:

```python
# Production
SECURE_SSL_REDIRECT = True

# Development (typically HTTP)
SECURE_SSL_REDIRECT = False

# Behind a proxy/load balancer
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

**Security Impact**: **HIGH**
- Ensures all traffic is encrypted
- Prevents man-in-the-middle attacks
- Required for HSTS to work

### SECURE_PROXY_SSL_HEADER

**What it does**: Tells Django which header indicates HTTPS when behind a proxy.

**Why it matters**: Load balancers/proxies terminate SSL, Django sees HTTP.

**Configuration**:

```python
# ✅ Behind AWS ELB, nginx, Heroku, etc.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ⚠️ Only set if actually behind a proxy!
# Setting this without a proxy can be a security vulnerability
```

**Security Impact**: **MEDIUM**
- Only set when actually behind SSL-terminating proxy
- Incorrect configuration can cause security issues

### HSTS (HTTP Strict Transport Security)

**What it does**: Forces browsers to use HTTPS for specified duration.

**SECURE_HSTS_SECONDS**

```python
# ❌ Disabled
SECURE_HSTS_SECONDS = 0

# ⚠️ Testing (1 hour)
SECURE_HSTS_SECONDS = 3600

# ✅ Production (1 year)
SECURE_HSTS_SECONDS = 31536000

# ✅ Production (2 years) - HSTS preload requirement
SECURE_HSTS_SECONDS = 63072000
```

**SECURE_HSTS_INCLUDE_SUBDOMAINS**

```python
# ✅ Include all subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ⚠️ Only if ALL subdomains support HTTPS!
```

**SECURE_HSTS_PRELOAD**

```python
# ✅ For HSTS preload list inclusion
SECURE_HSTS_PRELOAD = True

# Requirements for preload:
# - SECURE_HSTS_SECONDS >= 31536000 (1 year)
# - SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# - SECURE_HSTS_PRELOAD = True
# - Submit to https://hstspreload.org/
```

**Security Impact**: **HIGH**
- Prevents SSL stripping attacks
- Protects first-visit to site
- Start with low value, increase gradually
- Careful: Can lock out HTTP subdomains

## Cookie Security Settings

### Session Cookies

**SESSION_COOKIE_SECURE**

```python
# ✅ Production: Only send over HTTPS
SESSION_COOKIE_SECURE = True

# Development: Can use HTTP
SESSION_COOKIE_SECURE = False
```

**SESSION_COOKIE_HTTPONLY**

```python
# ✅ Always enable: Prevents JavaScript access
SESSION_COOKIE_HTTPONLY = True

# Prevents XSS attacks from stealing session cookies
```

**SESSION_COOKIE_SAMESITE**

```python
# ✅ Strict: Best CSRF protection
SESSION_COOKIE_SAMESITE = 'Strict'  # Never send cookie cross-site

# ✅ Lax: Good balance (default in Django 3.1+)
SESSION_COOKIE_SAMESITE = 'Lax'  # Send on top-level navigation

# ⚠️ None: Only if needed (requires Secure flag)
SESSION_COOKIE_SAMESITE = 'None'  # Send cross-site (must set Secure=True)
```

**SESSION_COOKIE_AGE**

```python
# Default: 2 weeks
SESSION_COOKIE_AGE = 1209600

# ✅ More secure: 1 hour for sensitive apps
SESSION_COOKIE_AGE = 3600

# ✅ Remember me: Different for authenticated users
SESSION_COOKIE_AGE = 86400  # 1 day
```

**SESSION_COOKIE_NAME**

```python
# Default
SESSION_COOKIE_NAME = 'sessionid'

# ✅ Obfuscate cookie purpose
SESSION_COOKIE_NAME = 'sid'
```

**SESSION_SAVE_EVERY_REQUEST**

```python
# ✅ Refresh session on every request
SESSION_SAVE_EVERY_REQUEST = True

# Extends session timeout on user activity
```

**SESSION_EXPIRE_AT_BROWSER_CLOSE**

```python
# ✅ More secure: Session ends when browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ❌ Less secure: Persistent sessions
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

### CSRF Cookies

**CSRF_COOKIE_SECURE**

```python
# ✅ Production: Only send over HTTPS
CSRF_COOKIE_SECURE = True
```

**CSRF_COOKIE_HTTPONLY**

```python
# ✅ Prevent JavaScript access
CSRF_COOKIE_HTTPONLY = True

# Note: May need False for AJAX with CSRF token from cookie
# In that case, use header-based CSRF token instead
```

**CSRF_COOKIE_SAMESITE**

```python
# ✅ Strict CSRF protection
CSRF_COOKIE_SAMESITE = 'Strict'

# or

CSRF_COOKIE_SAMESITE = 'Lax'
```

**CSRF_USE_SESSIONS**

```python
# ✅ Store CSRF token in session instead of cookie
CSRF_USE_SESSIONS = True

# More secure: No CSRF cookie sent to client
```

**CSRF_TRUSTED_ORIGINS**

```python
# For cross-origin requests (CORS)
CSRF_TRUSTED_ORIGINS = [
    'https://example.com',
    'https://api.example.com',
]
```

## Security Headers

### SECURE_BROWSER_XSS_FILTER

```python
# ✅ Enable browser's XSS filter
SECURE_BROWSER_XSS_FILTER = True

# Sets: X-XSS-Protection: 1; mode=block
```

**Security Impact**: **MEDIUM**
- Legacy header (modern browsers use CSP)
- Still useful for older browsers

### SECURE_CONTENT_TYPE_NOSNIFF

```python
# ✅ Prevent MIME-sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# Sets: X-Content-Type-Options: nosniff
```

**Security Impact**: **MEDIUM**
- Prevents browsers from MIME-sniffing responses
- Blocks malicious file uploads disguised as images

### X_FRAME_OPTIONS

```python
# ✅ Prevent clickjacking: Deny all framing
X_FRAME_OPTIONS = 'DENY'

# ✅ Allow same-origin framing only
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ❌ Don't use (deprecated)
X_FRAME_OPTIONS = 'ALLOW-FROM https://example.com'
```

**Security Impact**: **MEDIUM**
- Prevents clickjacking attacks
- Use 'DENY' unless you need iframe functionality

### Content Security Policy

Django doesn't have built-in CSP settings. Use `django-csp`:

```python
# Install: pip install django-csp

# settings.py
MIDDLEWARE = [
    ...
    'csp.middleware.CSPMiddleware',
]

# Strict CSP
CSP_DEFAULT_SRC = ("'none'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# Report violations
CSP_REPORT_URI = '/csp-report/'

# ⚠️  IMPORTANT: Report-only mode (django-csp 4.0+)
# CONTENT_SECURITY_POLICY_REPORT_ONLY must be None or a dict (NOT a boolean)
# ❌ WRONG: CONTENT_SECURITY_POLICY_REPORT_ONLY = DEBUG  # Causes AttributeError
# ✅ CORRECT options:

# Option 1: Don't use report-only mode (enforce CSP)
# (Simply don't set CONTENT_SECURITY_POLICY_REPORT_ONLY)

# Option 2: Use report-only mode with same policy
CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    "DIRECTIVES": {
        "default-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        # ... same as your CSP_* settings above
    }
}

# Option 3: Conditional configuration (correct way)
if DEBUG:
    # Report-only in development
    CONTENT_SECURITY_POLICY_REPORT_ONLY = {
        "DIRECTIVES": {
            "default-src": ["'none'"],
            "script-src": ["'self'"],
        }
    }
else:
    # Enforce in production (don't set CONTENT_SECURITY_POLICY_REPORT_ONLY)
    pass
```

**Common Mistake:**
```python
# ❌ DON'T DO THIS (django-csp 4.0+):
CONTENT_SECURITY_POLICY_REPORT_ONLY = DEBUG
# This causes: AttributeError: 'bool' object has no attribute 'get'
```

## Security Middleware

**Order matters!** Place security middleware early in the stack.

```python
MIDDLEWARE = [
    # ✅ Security first
    'django.middleware.security.SecurityMiddleware',

    # Session & CSRF
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # Authentication
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Clickjacking protection
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Other middleware...
    'django.middleware.common.CommonMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

### SecurityMiddleware

Provides several security enhancements:
- HSTS headers
- SSL redirects
- Content-Type nosniff
- XSS filter
- Referrer policy

**Always include this middleware!**

### CsrfViewMiddleware

Provides CSRF protection:
- Validates CSRF tokens
- Rejects unsafe methods without valid token

**Critical for form security!**

### ClickjackingMiddleware

Sets X-Frame-Options header.

## Password Validation

**AUTH_PASSWORD_VALIDATORS**

```python
# ✅ Strong password requirements
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        # Prevents passwords similar to user attributes
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # NIST recommends 12+ characters
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        # Checks against list of common passwords
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        # Prevents all-numeric passwords
    },
]
```

**Custom Validator**:

```python
# validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class UppercaseValidator:
    def validate(self, password, user=None):
        if not any(char.isupper() for char in password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )

    def get_help_text(self):
        return _("Your password must contain at least one uppercase letter.")

# settings.py
AUTH_PASSWORD_VALIDATORS = [
    # ... other validators
    {
        'NAME': 'myapp.validators.UppercaseValidator',
    },
]
```

## Password Hashing

**PASSWORD_HASHERS**

```python
# ✅ Use Argon2 (strongest, requires argon2-cffi)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Install: pip install argon2-cffi
```

**Security Impact**: **HIGH**
- First hasher in list is used for new passwords
- Others used for verifying existing passwords
- Argon2 is most resistant to GPU cracking

## File Upload Security

### FILE_UPLOAD_MAX_MEMORY_SIZE

```python
# ✅ Limit in-memory file upload size
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# Prevents memory exhaustion attacks
```

### DATA_UPLOAD_MAX_MEMORY_SIZE

```python
# ✅ Limit total request body size
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# Prevents DoS via large requests
```

### FILE_UPLOAD_PERMISSIONS

```python
# ✅ Set uploaded file permissions
FILE_UPLOAD_PERMISSIONS = 0o644  # rw-r--r--

# Prevents execution of uploaded files
```

### FILE_UPLOAD_DIRECTORY_PERMISSIONS

```python
# ✅ Set upload directory permissions
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755  # rwxr-xr-x
```

### MEDIA_ROOT and MEDIA_URL

```python
# ✅ Store uploads outside web root
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# ⚠️ Serve media files carefully in production
# Never serve MEDIA_ROOT directly with Django in production
# Use nginx, S3, CloudFront, etc.
```

## Database Security

### Secure Database Connections

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'OPTIONS': {
            # ✅ Require SSL for database connections
            'sslmode': 'require',

            # ✅ Verify certificate
            'sslmode': 'verify-full',
            'sslrootcert': '/path/to/ca-cert.pem',

            # Connection pooling
            'MAX_CONNS': 20,
        },
    }
}
```

### Connection Pool Security

```python
# Using django-db-pool or similar
DATABASES = {
    'default': {
        # ...
        'CONN_MAX_AGE': 600,  # 10 minutes
        # Prevents connection exhaustion
    }
}
```

## CORS (Cross-Origin Resource Sharing)

Using `django-cors-headers`:

```python
# Install: pip install django-cors-headers

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    # ...
]

# ❌ VULNERABLE: Allow all origins
CORS_ALLOW_ALL_ORIGINS = True

# ✅ SECURE: Whitelist specific origins
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://www.example.com",
    "https://app.example.com",
]

# ✅ Allow credentials
CORS_ALLOW_CREDENTIALS = True

# ✅ Specify allowed methods
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

# ✅ Specify allowed headers
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

## Logging Security

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/app.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/security.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

**Security Considerations**:
- Don't log sensitive data (passwords, tokens, PII)
- Protect log files (restrict permissions)
- Rotate logs to prevent disk filling
- Monitor security logs for attacks

## Email Security

### EMAIL_USE_TLS / EMAIL_USE_SSL

```python
# ✅ Use TLS (STARTTLS on port 587)
EMAIL_USE_TLS = True
EMAIL_PORT = 587

# Or use SSL (port 465)
EMAIL_USE_SSL = True
EMAIL_PORT = 465

# ❌ Never send unencrypted email
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
```

### EMAIL_HOST_USER / EMAIL_HOST_PASSWORD

```python
# ✅ From environment
EMAIL_HOST_USER = os.environ['EMAIL_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_PASSWORD']

# ❌ Never hardcode
EMAIL_HOST_PASSWORD = 'mypassword'
```

## Admin Site Security

### Admin URL Obfuscation

```python
# urls.py

# ❌ Default (predictable)
path('admin/', admin.site.urls),

# ✅ Obfuscated
path('secret-admin-portal/', admin.site.urls),

# ✅ Random
import uuid
admin_path = str(uuid.uuid4())
path(f'{admin_path}/', admin.site.urls),
```

### Admin Site Settings

```python
# Customize admin site
ADMIN_SITE_HEADER = "My Admin"
ADMIN_SITE_TITLE = "Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to Admin Portal"
```

### IP Whitelist for Admin

```python
# middleware/admin_ip.py
from django.core.exceptions import PermissionDenied
from django.conf import settings

class AdminIPWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            ip = self.get_client_ip(request)
            if ip not in settings.ADMIN_ALLOWED_IPS:
                raise PermissionDenied

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# settings.py
MIDDLEWARE = [
    # ...
    'myapp.middleware.admin_ip.AdminIPWhitelistMiddleware',
]

ADMIN_ALLOWED_IPS = [
    '192.168.1.1',
    '10.0.0.1',
]
```

## Environment-Specific Settings

### Development Settings

```python
# settings/development.py
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Disable security features for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Simple email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Production Settings

```python
# settings/production.py
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Full security
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# Production database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'OPTIONS': {'sslmode': 'require'},
    }
}

# Production logging
LOGGING = {
    # ... production logging config
}
```

## Security Checklist

Use Django's deployment checklist:

```bash
# Run security checks
python manage.py check --deploy

# Output shows warnings like:
# ?: (security.W004) SECURE_HSTS_SECONDS not set
# ?: (security.W008) SECURE_SSL_REDIRECT not set
# etc.
```

## Complete Production Settings Template

```python
# settings/production.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Your apps
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'OPTIONS': {'sslmode': 'require'},
        'CONN_MAX_AGE': 600,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Password hashers
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# HTTPS/SSL
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# File uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_PERMISSIONS = 0o644

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ['EMAIL_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_PASSWORD']
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# Logging (see logging section above for complete config)
```

## Testing Security Settings

```python
# tests/test_security_settings.py
from django.test import TestCase, override_settings
from django.conf import settings

class SecuritySettingsTest(TestCase):
    def test_debug_is_false(self):
        """Ensure DEBUG is False in production"""
        # This test should run in production settings
        self.assertFalse(settings.DEBUG)

    def test_secret_key_is_set(self):
        """Ensure SECRET_KEY is configured"""
        self.assertTrue(settings.SECRET_KEY)
        self.assertNotEqual(settings.SECRET_KEY, 'django-insecure-')

    def test_allowed_hosts_configured(self):
        """Ensure ALLOWED_HOSTS is set"""
        self.assertTrue(settings.ALLOWED_HOSTS)
        self.assertNotIn('*', settings.ALLOWED_HOSTS)

    def test_secure_ssl_redirect(self):
        """Ensure SSL redirect is enabled"""
        self.assertTrue(settings.SECURE_SSL_REDIRECT)

    def test_session_cookie_secure(self):
        """Ensure session cookies are secure"""
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    def test_csrf_cookie_secure(self):
        """Ensure CSRF cookies are secure"""
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
```

## Resources

- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- Django Deployment Checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- Django Settings Reference: https://docs.djangoproject.com/en/stable/ref/settings/
- Mozilla Security Headers: https://infosec.mozilla.org/guidelines/web_security

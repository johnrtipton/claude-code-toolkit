"""
Production-Ready Django Security Settings Template

Copy this template for your production settings.py file.
All security best practices included.

Usage:
1. Copy to your project's settings/production.py
2. Replace placeholder values
3. Set environment variables
4. Test with: python manage.py check --deploy
"""

import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY WARNING: Keep these secret and load from environment!
# ==============================================================================

# CRITICAL: Use strong random key, never hardcode
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# CRITICAL: Must be False in production
DEBUG = False

# CRITICAL: Specify allowed hosts, never use '*'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# ==============================================================================
# Application Definition
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party security apps (optional)
    # 'django_otp',  # 2FA
    # 'django_otp.plugins.otp_totp',
    # 'corsheaders',  # CORS
    # 'csp',  # Content Security Policy

    # Your apps
    # 'myapp',
]

# ==============================================================================
# Middleware - ORDER MATTERS!
# ==============================================================================

MIDDLEWARE = [
    # Security middleware FIRST
    'django.middleware.security.SecurityMiddleware',

    # CORS (if using django-cors-headers) - before CommonMiddleware
    # 'corsheaders.middleware.CorsMiddleware',

    # Session and common
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',

    # CSRF protection
    'django.middleware.csrf.CsrfViewMiddleware',

    # Authentication
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 2FA (if using django-otp)
    # 'django_otp.middleware.OTPMiddleware',

    # Messages
    'django.contrib.messages.middleware.MessageMiddleware',

    # Clickjacking protection
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Custom security middleware
    # 'myapp.middleware.SecurityHeadersMiddleware',
    # 'myapp.middleware.AuditMiddleware',
]

# ==============================================================================
# Database Configuration
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            # Require SSL connection
            'sslmode': 'require',

            # Connection pooling
            'MAX_CONNS': 20,
        },
        # Connection persistence
        'CONN_MAX_AGE': 600,  # 10 minutes
    }
}

# ==============================================================================
# Password Validation
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # NIST recommendation
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# Password Hashing - Use Argon2 (strongest)
# ==============================================================================

# Requires: pip install argon2-cffi
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ==============================================================================
# HTTPS / SSL Settings
# ==============================================================================

# Redirect all HTTP to HTTPS
SECURE_SSL_REDIRECT = True

# For proxies/load balancers (AWS ELB, nginx, Heroku, etc.)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ==============================================================================
# Cookie Security
# ==============================================================================

# Session cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # or 'Strict' for maximum security
SESSION_COOKIE_NAME = 'sessionid'  # or obfuscate: 'sid'
SESSION_COOKIE_AGE = 3600  # 1 hour (adjust as needed)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF cookies
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'csrftoken'  # or obfuscate: 'csrf'

# Alternative: Store CSRF in session instead of cookie
# CSRF_USE_SESSIONS = True

# Trusted origins for CSRF (if using CORS)
CSRF_TRUSTED_ORIGINS = [
    'https://example.com',
    'https://api.example.com',
]

# ==============================================================================
# Security Headers
# ==============================================================================

# XSS filter
SECURE_BROWSER_XSS_FILTER = True

# Prevent MIME-sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# Clickjacking protection
X_FRAME_OPTIONS = 'DENY'  # or 'SAMEORIGIN' if you need iframes

# Referrer policy
SECURE_REFERRER_POLICY = 'same-origin'

# ==============================================================================
# Content Security Policy (requires django-csp)
# ==============================================================================

# Uncomment if using django-csp
# CSP_DEFAULT_SRC = ("'none'",)
# CSP_SCRIPT_SRC = ("'self'",)
# CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # unsafe-inline only if necessary
# CSP_IMG_SRC = ("'self'", "data:", "https:")
# CSP_FONT_SRC = ("'self'",)
# CSP_CONNECT_SRC = ("'self'",)
# CSP_FRAME_ANCESTORS = ("'none'",)
# CSP_BASE_URI = ("'self'",)
# CSP_FORM_ACTION = ("'self'",)
# CSP_REPORT_URI = '/csp-report/'

# ==============================================================================
# CORS Configuration (requires django-cors-headers)
# ==============================================================================

# Uncomment if using django-cors-headers
# CORS_ALLOWED_ORIGINS = [
#     "https://example.com",
#     "https://www.example.com",
# ]
# CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']

# ==============================================================================
# File Upload Security
# ==============================================================================

# Maximum upload sizes
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# File permissions
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# ==============================================================================
# Static Files
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise for serving static files (if not using nginx/Apache)
# Add to MIDDLEWARE after SecurityMiddleware:
# 'whitenoise.middleware.WhiteNoiseMiddleware',

# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# Media Files
# ==============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# IMPORTANT: Never serve media files with Django in production
# Use nginx, S3, CloudFront, etc.

# Example: S3 storage (requires django-storages, boto3)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# ==============================================================================
# Email Configuration
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'server@example.com')

# ==============================================================================
# Logging Configuration
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
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
            'formatter': 'verbose',
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

# ==============================================================================
# Cache Configuration
# ==============================================================================

# Redis cache (recommended for production)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.environ.get('REDIS_PASSWORD', ''),
            'SSL': True,  # Enable for production
        }
    }
}

# Session backend (optional: use cache or database)
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ==============================================================================
# Internationalization
# ==============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# Admin Site Security
# ==============================================================================

# Obfuscate admin URL (configure in urls.py)
# path('secret-admin-portal-xyz/', admin.site.urls)

# IP whitelist for admin (implement in middleware)
ADMIN_ALLOWED_IPS = os.environ.get('ADMIN_ALLOWED_IPS', '').split(',')

# Admin site customization
ADMIN_SITE_HEADER = "Administration"
ADMIN_SITE_TITLE = "Admin Portal"

# ==============================================================================
# Third-Party API Keys (from environment)
# ==============================================================================

# AWS
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

# Stripe
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')

# SendGrid
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')

# Google
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')

# ==============================================================================
# Error Monitoring (Sentry example)
# ==============================================================================

# Uncomment if using Sentry
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
#
# sentry_sdk.init(
#     dsn=os.environ.get('SENTRY_DSN', ''),
#     integrations=[DjangoIntegration()],
#     environment=os.environ.get('ENVIRONMENT', 'production'),
#     traces_sample_rate=0.1,
#     send_default_pii=False,  # Don't send PII
# )

# ==============================================================================
# Security Checklist Verification
# ==============================================================================

# Run this command to verify security settings:
# python manage.py check --deploy

# Expected: No warnings or errors

# ==============================================================================
# Notes
# ==============================================================================

# 1. Set all environment variables in your deployment platform
# 2. Never commit .env files or secrets
# 3. Use secrets manager (AWS Secrets Manager, Vault, etc.) for production
# 4. Test with: python manage.py check --deploy
# 5. Run security auditor: python scripts/security_auditor.py
# 6. Review logs regularly for security events
# 7. Keep dependencies updated: pip-audit

# ==============================================================================
# Environment Variables Required
# ==============================================================================

# Required:
# - DJANGO_SECRET_KEY
# - ALLOWED_HOSTS (comma-separated)
# - DB_NAME
# - DB_USER
# - DB_PASSWORD
# - DB_HOST
# - EMAIL_HOST
# - EMAIL_HOST_USER
# - EMAIL_HOST_PASSWORD

# Optional:
# - DB_PORT (default: 5432)
# - REDIS_URL
# - REDIS_PASSWORD
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - STRIPE_SECRET_KEY
# - SENDGRID_API_KEY
# - SENTRY_DSN
# - ADMIN_ALLOWED_IPS

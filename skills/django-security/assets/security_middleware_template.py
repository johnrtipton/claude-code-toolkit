"""
Django Security Middleware Templates

Custom middleware examples for enhanced security.
Copy and adapt these for your Django project.

Usage:
1. Create middleware/ directory in your app
2. Copy relevant middleware classes
3. Add to MIDDLEWARE in settings.py
4. Configure as needed
"""

import logging
import time
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout

logger = logging.getLogger('security')


# ==============================================================================
# Security Headers Middleware
# ==============================================================================

class SecurityHeadersMiddleware:
    """
    Add additional security headers beyond Django's defaults.

    Usage:
        Add to MIDDLEWARE after SecurityMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Referrer Policy
        response['Referrer-Policy'] = 'same-origin'

        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=()'
        )

        # Expect-CT (Certificate Transparency)
        response['Expect-CT'] = 'max-age=86400, enforce'

        # Additional HSTS for all subdomains
        if settings.SECURE_HSTS_SECONDS:
            response['Strict-Transport-Security'] = (
                f'max-age={settings.SECURE_HSTS_SECONDS}; '
                f'includeSubDomains; preload'
            )

        return response


# ==============================================================================
# IP Whitelist Middleware
# ==============================================================================

class IPWhitelistMiddleware:
    """
    Restrict access to specific IP addresses.

    Settings:
        IP_WHITELIST = ['192.168.1.1', '10.0.0.1']
        IP_WHITELIST_PATHS = ['/admin/']  # Optional: only for specific paths
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.whitelist = getattr(settings, 'IP_WHITELIST', [])
        self.whitelist_paths = getattr(settings, 'IP_WHITELIST_PATHS', None)

    def __call__(self, request):
        # Skip if no whitelist configured
        if not self.whitelist:
            return self.get_response(request)

        # Check if path requires IP whitelist
        if self.whitelist_paths:
            path_match = any(
                request.path.startswith(path)
                for path in self.whitelist_paths
            )
            if not path_match:
                return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)

        # Check whitelist
        if ip not in self.whitelist:
            logger.warning(
                f"IP whitelist violation: {ip} attempted to access {request.path}",
                extra={'ip': ip, 'path': request.path}
            )
            return HttpResponseForbidden("Access denied")

        return self.get_response(request)

    def get_client_ip(self, request):
        """Get real client IP (handles proxies)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Admin IP Whitelist Middleware
# ==============================================================================

class AdminIPWhitelistMiddleware:
    """
    Restrict admin panel access to specific IPs.

    Settings:
        ADMIN_ALLOWED_IPS = ['192.168.1.1', '10.0.0.1']
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check admin paths
        if request.path.startswith('/admin/'):
            ip = self.get_client_ip(request)
            allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])

            if allowed_ips and ip not in allowed_ips:
                logger.warning(
                    f"Admin access denied for IP: {ip}",
                    extra={
                        'ip': ip,
                        'user': request.user.username if request.user.is_authenticated else 'anonymous',
                        'path': request.path
                    }
                )
                raise PermissionDenied("Admin access denied for your IP address")

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Rate Limiting Middleware (Simple)
# ==============================================================================

class SimpleRateLimitMiddleware:
    """
    Basic rate limiting middleware.

    For production, use django-ratelimit instead.
    This is a simple example for learning.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = {}  # In production, use Redis

    def __call__(self, request):
        ip = self.get_client_ip(request)
        key = f"rate_limit:{ip}"

        # Get current request count
        current_time = time.time()
        requests = self.cache.get(key, [])

        # Remove old requests (older than 1 minute)
        requests = [t for t in requests if current_time - t < 60]

        # Check limit
        if len(requests) >= 100:  # 100 requests per minute
            logger.warning(
                f"Rate limit exceeded for IP: {ip}",
                extra={'ip': ip, 'count': len(requests)}
            )
            return HttpResponse("Rate limit exceeded. Try again later.", status=429)

        # Add current request
        requests.append(current_time)
        self.cache[key] = requests

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Audit Logging Middleware
# ==============================================================================

class AuditMiddleware:
    """
    Log all requests for security auditing.

    Creates audit trail of who accessed what and when.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Record request start time
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request (only if authenticated or important paths)
        if request.user.is_authenticated or self.is_important_path(request.path):
            logger.info(
                f"{request.method} {request.path} - {response.status_code}",
                extra={
                    'user': request.user.username if request.user.is_authenticated else 'anonymous',
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'method': request.method,
                    'path': request.path,
                    'query_string': request.META.get('QUERY_STRING', ''),
                    'status_code': response.status_code,
                    'duration': round(duration, 3),
                    'referer': request.META.get('HTTP_REFERER', ''),
                }
            )

        return response

    def is_important_path(self, path):
        """Determine if path should be logged even for anonymous users."""
        important_paths = ['/admin/', '/api/', '/login/', '/logout/']
        return any(path.startswith(p) for p in important_paths)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Session Security Middleware
# ==============================================================================

class SessionSecurityMiddleware:
    """
    Enhanced session security:
    - Validate IP address hasn't changed
    - Validate User-Agent hasn't changed
    - Auto-logout on suspicious activity
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get current request details
            current_ip = self.get_client_ip(request)
            current_ua = request.META.get('HTTP_USER_AGENT', '')

            # Get stored session details
            stored_ip = request.session.get('security_ip')
            stored_ua = request.session.get('security_ua')

            # First visit - store details
            if not stored_ip or not stored_ua:
                request.session['security_ip'] = current_ip
                request.session['security_ua'] = current_ua
            else:
                # Validate IP hasn't changed
                if stored_ip != current_ip:
                    logger.warning(
                        f"Session hijacking attempt detected: IP changed from {stored_ip} to {current_ip}",
                        extra={
                            'user': request.user.username,
                            'old_ip': stored_ip,
                            'new_ip': current_ip
                        }
                    )
                    logout(request)
                    return HttpResponseForbidden("Session security violation detected")

                # Validate User-Agent hasn't changed
                if stored_ua != current_ua:
                    logger.warning(
                        f"Session hijacking attempt detected: User-Agent changed",
                        extra={
                            'user': request.user.username,
                            'ip': current_ip
                        }
                    )
                    logout(request)
                    return HttpResponseForbidden("Session security violation detected")

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Multi-Tenant Security Middleware
# ==============================================================================

class TenantSecurityMiddleware:
    """
    Enhanced security for multi-tenant applications.

    Ensures:
    - Tenant context is set
    - Cross-tenant access is prevented
    - Tenant access is audited
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set tenant from authenticated user
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'tenant'):
                request.tenant = request.user.profile.tenant

                # Store in thread-local for automatic filtering
                from myapp.middleware import set_current_tenant
                set_current_tenant(request.tenant)

                # Log tenant access
                logger.info(
                    f"User {request.user.username} accessing tenant {request.tenant.id}",
                    extra={
                        'user_id': request.user.id,
                        'tenant_id': request.tenant.id,
                        'ip_address': self.get_client_ip(request),
                    }
                )
            else:
                # User has no tenant - deny access
                logger.warning(
                    f"User {request.user.username} has no tenant",
                    extra={'user_id': request.user.id}
                )
                return HttpResponseForbidden("No tenant associated with user")
        else:
            request.tenant = None
            from myapp.middleware import set_current_tenant
            set_current_tenant(None)

        response = self.get_response(request)

        # Clear tenant context after request
        from myapp.middleware import set_current_tenant
        set_current_tenant(None)

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Content Security Policy Middleware (Simple)
# ==============================================================================

class SimpleCSPMiddleware:
    """
    Simple Content Security Policy middleware.

    For production, use django-csp instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Basic CSP policy
        csp_policy = "; ".join([
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",  # unsafe-inline for admin
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ])

        response['Content-Security-Policy'] = csp_policy

        return response


# ==============================================================================
# Request Size Limit Middleware
# ==============================================================================

class RequestSizeLimitMiddleware:
    """
    Enforce maximum request body size to prevent DoS attacks.

    Settings:
        MAX_REQUEST_SIZE = 5242880  # 5 MB
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_size = getattr(settings, 'MAX_REQUEST_SIZE', 5242880)  # 5 MB

    def __call__(self, request):
        # Check content length
        content_length = request.META.get('CONTENT_LENGTH')

        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(
                    f"Request size limit exceeded: {content_length} bytes",
                    extra={
                        'ip': self.get_client_ip(request),
                        'size': content_length
                    }
                )
                return HttpResponse(
                    f"Request too large. Maximum size: {self.max_size} bytes",
                    status=413
                )

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ==============================================================================
# Usage in settings.py
# ==============================================================================

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'myapp.middleware.security.SecurityHeadersMiddleware',
#     'myapp.middleware.security.AdminIPWhitelistMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'myapp.middleware.security.SessionSecurityMiddleware',
#     'myapp.middleware.security.TenantSecurityMiddleware',
#     'myapp.middleware.security.AuditMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# Settings:
# IP_WHITELIST = ['192.168.1.1']
# ADMIN_ALLOWED_IPS = ['192.168.1.1', '10.0.0.1']
# MAX_REQUEST_SIZE = 5242880  # 5 MB

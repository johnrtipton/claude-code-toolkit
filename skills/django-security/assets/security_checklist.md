# Django Security Pre-Deployment Checklist

Complete checklist for securing Django applications before deployment. Use this before every production deployment.

## Critical Security Settings

### Core Configuration
- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` is strong (50+ characters, random)
- [ ] `SECRET_KEY` loaded from environment variable (not hardcoded)
- [ ] `ALLOWED_HOSTS` configured with specific domains (no `['*']`)
- [ ] Different `SECRET_KEY` for each environment

### HTTPS/SSL
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SECURE_PROXY_SSL_HEADER` configured if behind proxy
- [ ] `SECURE_HSTS_SECONDS = 31536000` (1 year minimum)
- [ ] `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- [ ] `SECURE_HSTS_PRELOAD = True` (if submitting to preload list)

### Cookies
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `SESSION_COOKIE_HTTPONLY = True`
- [ ] `SESSION_COOKIE_SAMESITE = 'Lax'` or `'Strict'`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_HTTPONLY = True`
- [ ] `CSRF_COOKIE_SAMESITE = 'Lax'` or `'Strict'`
- [ ] Session timeout configured (`SESSION_COOKIE_AGE`)

### Security Headers
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True`
- [ ] `X_FRAME_OPTIONS = 'DENY'` or `'SAMEORIGIN'`
- [ ] Content Security Policy configured (if using django-csp)

## Middleware

- [ ] `SecurityMiddleware` enabled and first in MIDDLEWARE list
- [ ] `CsrfViewMiddleware` enabled
- [ ] `ClickjackingMiddleware` enabled
- [ ] All security middleware in correct order

## Password Security

- [ ] `AUTH_PASSWORD_VALIDATORS` configured with all 4 validators
- [ ] Minimum password length ≥ 12 characters
- [ ] Using Argon2 password hasher (install `argon2-cffi`)
- [ ] Multi-factor authentication implemented (optional but recommended)

## Database Security

- [ ] Database credentials in environment variables
- [ ] SSL/TLS enabled for database connections (`sslmode='require'`)
- [ ] Database user has minimal required permissions
- [ ] Different database credentials per environment
- [ ] Regular database backups configured
- [ ] PostgreSQL Row-Level Security enabled (if multi-tenant)

## Secrets Management

- [ ] No secrets hardcoded in code
- [ ] `.env` files in `.gitignore`
- [ ] Secrets loaded from environment variables or secrets manager
- [ ] Different secrets for dev/staging/production
- [ ] Secrets rotation plan in place
- [ ] API keys for third-party services secured
- [ ] AWS/GCP/Azure credentials secured

## File Upload Security

- [ ] `FILE_UPLOAD_MAX_MEMORY_SIZE` set (e.g., 5MB)
- [ ] `DATA_UPLOAD_MAX_MEMORY_SIZE` set (e.g., 5MB)
- [ ] `FILE_UPLOAD_PERMISSIONS` set (e.g., `0o644`)
- [ ] File type validation implemented
- [ ] Uploaded files stored outside web root
- [ ] Virus scanning for uploads (if applicable)
- [ ] Media files served securely (not via Django in production)

## Static Files

- [ ] `STATIC_ROOT` configured
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Static files served by web server (nginx/Apache) not Django
- [ ] WhiteNoise configured (if not using separate static server)

## Admin Security

- [ ] Admin URL changed from `/admin/` to custom path
- [ ] Admin access restricted by IP (if possible)
- [ ] Admin requires 2FA (if possible)
- [ ] Admin panel uses HTTPS only
- [ ] Separate admin credentials from regular users
- [ ] Admin actions logged

## Multi-Tenant Security (if applicable)

- [ ] All models inherit from `TenantBaseModel`
- [ ] All queries filter by tenant
- [ ] Tenant validation in views/APIs
- [ ] Cross-tenant references validated
- [ ] Admin panel filters by tenant
- [ ] Tenant isolation tested
- [ ] Audit logging for tenant access

## CORS (if applicable)

- [ ] `CORS_ALLOWED_ORIGINS` configured (no `CORS_ALLOW_ALL_ORIGINS = True`)
- [ ] `CORS_ALLOW_CREDENTIALS` set appropriately
- [ ] CORS only enabled if needed

## Email Security

- [ ] `EMAIL_USE_TLS = True` or `EMAIL_USE_SSL = True`
- [ ] Email credentials in environment variables
- [ ] `DEFAULT_FROM_EMAIL` configured

## Logging

- [ ] Security events logged
- [ ] Failed login attempts logged
- [ ] Logs don't contain sensitive data (passwords, tokens)
- [ ] Log files protected (permissions, encryption)
- [ ] Log rotation configured
- [ ] Logs monitored for security incidents

## Dependencies

- [ ] All dependencies up to date
- [ ] Vulnerability scanning enabled (`pip-audit` or `safety check`)
- [ ] `requirements.txt` with pinned versions
- [ ] Regular dependency updates scheduled

## Code Security

- [ ] No hardcoded secrets in code
- [ ] Using Django ORM (no raw SQL with user input)
- [ ] No `mark_safe` with user input
- [ ] No `eval()` or `exec()` with user input
- [ ] No `pickle` with untrusted data
- [ ] Input validation on all user inputs
- [ ] CSRF protection not disabled

## Third-Party Integrations

- [ ] API keys for external services secured
- [ ] Webhooks validated (signature verification)
- [ ] OAuth client secrets secured
- [ ] Service-to-service authentication secured

## Testing

- [ ] Security tests written and passing
- [ ] CSRF protection tested
- [ ] XSS prevention tested  
- [ ] SQL injection prevention tested
- [ ] Authentication/authorization tested
- [ ] Tenant isolation tested (if multi-tenant)

## Monitoring

- [ ] Error monitoring configured (Sentry, etc.)
- [ ] Performance monitoring configured
- [ ] Security event monitoring configured
- [ ] Failed authentication alerts configured
- [ ] Unusual activity alerts configured

## Deployment

- [ ] Environment variables set in deployment platform
- [ ] Secrets injected at deployment time
- [ ] Deployment uses HTTPS
- [ ] Health check endpoint configured
- [ ] Rollback plan documented
- [ ] Deployment checklist followed

## Documentation

- [ ] Security architecture documented
- [ ] Incident response plan documented
- [ ] Secret rotation procedures documented
- [ ] Security contact information available

## Compliance (if applicable)

- [ ] GDPR compliance addressed
- [ ] HIPAA compliance addressed (if handling health data)
- [ ] PCI DSS compliance addressed (if handling payment data)
- [ ] SOC 2 compliance addressed (if required)

## Final Checks

- [ ] Run `python manage.py check --deploy`
- [ ] Run security auditor: `python scripts/security_auditor.py`
- [ ] Manual penetration testing completed
- [ ] Security review by second developer
- [ ] Sign-off from security team (if applicable)

## Post-Deployment

- [ ] Monitor logs for first 24 hours
- [ ] Verify HTTPS certificate
- [ ] Test authentication flows
- [ ] Verify security headers with online tools
- [ ] Check for information disclosure
- [ ] Verify backups working

## Regular Maintenance

- [ ] Weekly: Review logs for security events
- [ ] Monthly: Update dependencies
- [ ] Monthly: Run security scan
- [ ] Quarterly: Penetration testing
- [ ] Quarterly: Security training
- [ ] Yearly: Comprehensive security audit

## Tools to Use

- **Django**: `python manage.py check --deploy`
- **Security Auditor**: `python scripts/security_auditor.py`
- **Dependencies**: `pip-audit` or `safety check`
- **Secrets**: `detect-secrets` or `truffleHog`
- **Headers**: https://securityheaders.com/
- **SSL**: https://www.ssllabs.com/ssltest/

## Emergency Contacts

- Security Team: _______________
- On-Call Engineer: _______________
- Incident Response: _______________

---

**Sign-off**:
- Developer: _________________ Date: _______
- Reviewer: _________________ Date: _______  
- Security: _________________ Date: _______

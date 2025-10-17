# Secrets Management for Django Applications

Comprehensive guide to managing secrets, credentials, API keys, and sensitive configuration in Django applications securely.

## Overview

Secrets include:
- Database passwords
- SECRET_KEY
- API keys (AWS, Stripe, SendGrid, etc.)
- OAuth client secrets
- Encryption keys
- SSL certificates
- SSH keys
- Service account credentials

**Critical Principle**: Never commit secrets to version control. Ever.

## The Problem

###❌ What NOT to Do

```python
# settings.py - NEVER DO THIS!
SECRET_KEY = 'django-insecure-hardcoded-key-123456789'
DATABASES = {
    'default': {
        'PASSWORD': 'my_database_password',  # EXPOSED!
    }
}
AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'  # EXPOSED!
STRIPE_SECRET_KEY = 'sk_live_51H...'  # EXPOSED!
```

**Why this is dangerous**:
- Committed to git history (forever)
- Visible in GitHub/GitLab
- Accessible to all developers
- Exposed if repo is compromised
- Can't rotate without code changes
- Different environments require different secrets

## Solution 1: Environment Variables

### Basic Environment Variables

**Step 1: Create .env file (NEVER commit)**

```.env
# .env - LOCAL DEVELOPMENT ONLY
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=myapp_db
DB_USER=myapp_user
DB_PASSWORD=strong_password_here
DB_HOST=localhost
DB_PORT=5432

AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

SENDGRID_API_KEY=SG.xxxxxxxxxxxxx

REDIS_URL=redis://localhost:6379/0
```

**Step 2: Add .env to .gitignore**

```gitignore
# .gitignore
.env
.env.local
.env.*.local
.env.production
*.env

# Also ignore common secret files
secrets/
*.pem
*.key
*.cert
credentials.json
```

**Step 3: Use environment variables in settings**

```python
# settings.py
import os

# ✅ SECURE: Read from environment
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
    }
}

# AWS credentials
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'my-bucket')

# Stripe
STRIPE_SECRET_KEY = os.environ['STRIPE_SECRET_KEY']
STRIPE_PUBLISHABLE_KEY = os.environ['STRIPE_PUBLISHABLE_KEY']
```

**Step 4: Load .env in development**

```python
# settings.py or manage.py
import os
from pathlib import Path

# Load .env file in development
if os.environ.get('DJANGO_ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

# Install: pip install python-dotenv
```

### Using django-environ

**More robust and type-safe environment variable handling.**

```bash
pip install django-environ
```

```python
# settings.py
import environ
import os

# Initialize environ
env = environ.Env(
    # Set casting and default values
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, 'sqlite:///db.sqlite3'),
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Access variables with type casting
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Database URL parsing
DATABASES = {
    'default': env.db()  # Parses DATABASE_URL automatically
}

# Redis
CACHES = {
    'default': env.cache('REDIS_URL')  # Parses REDIS_URL
}

# Email
EMAIL_CONFIG = env.email_url('EMAIL_URL', default='console://')
vars().update(EMAIL_CONFIG)

# AWS
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')

# API Keys
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY')
SENDGRID_API_KEY = env('SENDGRID_API_KEY')

# With defaults and type conversion
MAX_UPLOAD_SIZE = env.int('MAX_UPLOAD_SIZE', default=5242880)  # 5MB
ENABLE_FEATURE_X = env.bool('ENABLE_FEATURE_X', default=False)
```

**.env with django-environ**:

```.env
# Core Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com

# Database (single URL format)
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_URL=smtp+tls://user:password@smtp.gmail.com:587

# AWS
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_STORAGE_BUCKET_NAME=my-app-bucket

# API Keys
STRIPE_SECRET_KEY=sk_live_...
SENDGRID_API_KEY=SG.xxx

# Feature flags
ENABLE_FEATURE_X=True
MAX_UPLOAD_SIZE=10485760
```

### Using python-decouple

**Strict separation of settings from code.**

```bash
pip install python-decouple
```

```python
# settings.py
from decouple import config, Csv

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default=5432, cast=int),
    }
}
```

## Solution 2: Secrets Managers

### AWS Secrets Manager

**Centralized, encrypted secret storage with rotation.**

```bash
pip install boto3
```

```python
# utils/secrets.py
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(secret_name, region_name='us-east-1'):
    """
    Retrieve secret from AWS Secrets Manager.

    Cached to avoid repeated API calls.
    """
    client = boto3.client('secretsmanager', region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        raise Exception(f"Error retrieving secret {secret_name}: {e}")

    # Secrets can be string or binary
    if 'SecretString' in response:
        return json.loads(response['SecretString'])
    else:
        return response['SecretBinary']

# settings.py
from utils.secrets import get_secret
import os

# Get secret name from environment
SECRET_NAME = os.environ.get('AWS_SECRET_NAME', 'myapp/production')

# Retrieve secrets
secrets = get_secret(SECRET_NAME)

SECRET_KEY = secrets['SECRET_KEY']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': secrets['DB_NAME'],
        'USER': secrets['DB_USER'],
        'PASSWORD': secrets['DB_PASSWORD'],
        'HOST': secrets['DB_HOST'],
        'PORT': secrets['DB_PORT'],
    }
}

# API Keys from secrets
STRIPE_SECRET_KEY = secrets['STRIPE_SECRET_KEY']
SENDGRID_API_KEY = secrets['SENDGRID_API_KEY']
```

**Store secret in AWS Secrets Manager**:

```bash
# Create secret
aws secretsmanager create-secret \
    --name myapp/production \
    --secret-string '{
        "SECRET_KEY": "your-secret-key",
        "DB_PASSWORD": "db-password",
        "STRIPE_SECRET_KEY": "sk_live_...",
        "SENDGRID_API_KEY": "SG.xxx"
    }'

# Update secret
aws secretsmanager update-secret \
    --secret-id myapp/production \
    --secret-string '{...}'

# Enable automatic rotation
aws secretsmanager rotate-secret \
    --secret-id myapp/production \
    --rotation-lambda-arn arn:aws:lambda:...
```

### HashiCorp Vault

**Enterprise-grade secrets management.**

```bash
pip install hvac
```

```python
# utils/vault.py
import hvac
import os
from functools import lru_cache

class VaultClient:
    def __init__(self):
        self.client = hvac.Client(
            url=os.environ['VAULT_ADDR'],
            token=os.environ.get('VAULT_TOKEN'),
        )

        # Or use AppRole authentication
        if not self.client.is_authenticated():
            self.client.auth.approle.login(
                role_id=os.environ['VAULT_ROLE_ID'],
                secret_id=os.environ['VAULT_SECRET_ID'],
            )

    @lru_cache(maxsize=None)
    def get_secret(self, path):
        """Retrieve secret from Vault."""
        response = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point='secret',
        )
        return response['data']['data']

# settings.py
from utils.vault import VaultClient

vault = VaultClient()
secrets = vault.get_secret('myapp/production')

SECRET_KEY = secrets['SECRET_KEY']
DATABASES = {
    'default': {
        'PASSWORD': secrets['DB_PASSWORD'],
        # ... other config
    }
}
```

**Configure Vault**:

```bash
# Write secret to Vault
vault kv put secret/myapp/production \
    SECRET_KEY="your-secret-key" \
    DB_PASSWORD="db-password" \
    STRIPE_SECRET_KEY="sk_live_..."

# Read secret
vault kv get secret/myapp/production

# Enable dynamic database credentials
vault secrets enable database
vault write database/config/postgresql \
    plugin_name=postgresql-database-plugin \
    allowed_roles="myapp" \
    connection_url="postgresql://{{username}}:{{password}}@localhost:5432/mydb"
```

### Google Cloud Secret Manager

```bash
pip install google-cloud-secret-manager
```

```python
# utils/gcp_secrets.py
from google.cloud import secretmanager
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(project_id, secret_id, version_id='latest'):
    """Retrieve secret from GCP Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')

# settings.py
from utils.gcp_secrets import get_secret
import os
import json

PROJECT_ID = os.environ['GCP_PROJECT_ID']

# Get secrets
secrets = json.loads(get_secret(PROJECT_ID, 'myapp-secrets'))

SECRET_KEY = secrets['SECRET_KEY']
DB_PASSWORD = secrets['DB_PASSWORD']
```

### Azure Key Vault

```bash
pip install azure-keyvault-secrets azure-identity
```

```python
# utils/azure_secrets.py
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(vault_url, secret_name):
    """Retrieve secret from Azure Key Vault."""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    secret = client.get_secret(secret_name)
    return secret.value

# settings.py
from utils.azure_secrets import get_secret
import os

VAULT_URL = os.environ['AZURE_VAULT_URL']

SECRET_KEY = get_secret(VAULT_URL, 'SECRET-KEY')
DB_PASSWORD = get_secret(VAULT_URL, 'DB-PASSWORD')
```

## Secret Rotation

### Why Rotate Secrets

- Limit exposure window if compromised
- Comply with security policies
- Reduce impact of leaked credentials
- Best practice for high-security environments

### Rotation Strategy

**1. Database Credentials**

```python
# Rotate database password (zero-downtime)

# Step 1: Create new credentials
# ALTER USER myapp_user WITH PASSWORD 'new_password';

# Step 2: Update secret in vault/env
# (Application still uses old password)

# Step 3: Restart application
# (Picks up new password)

# Step 4: Revoke old credentials
# (After confirming application works)
```

**Automated with Secrets Manager**:

```python
# Lambda function for rotation
import boto3
import psycopg2

def lambda_handler(event, context):
    service_client = boto3.client('secretsmanager')
    secret = service_client.get_secret_value(SecretId=event['SecretId'])

    # Create new credentials
    new_password = generate_password()

    # Update database
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    cur.execute(f"ALTER USER myapp_user WITH PASSWORD '{new_password}'")
    conn.commit()

    # Update secret
    new_secret = {'password': new_password, ...}
    service_client.put_secret_value(
        SecretId=event['SecretId'],
        SecretString=json.dumps(new_secret)
    )

    return {'statusCode': 200}
```

**2. API Keys**

```python
# Graceful API key rotation

# Step 1: Generate new key in service (e.g., Stripe)
# Keep old key active

# Step 2: Add new key to secrets
STRIPE_SECRET_KEY_PRIMARY = secrets['STRIPE_SECRET_KEY_PRIMARY']
STRIPE_SECRET_KEY_BACKUP = secrets['STRIPE_SECRET_KEY_BACKUP']

# Step 3: Use new key, fallback to old
def make_stripe_request():
    try:
        stripe.api_key = STRIPE_SECRET_KEY_PRIMARY
        return stripe.Charge.create(...)
    except stripe.error.AuthenticationError:
        # Fallback to backup key
        stripe.api_key = STRIPE_SECRET_KEY_BACKUP
        return stripe.Charge.create(...)

# Step 4: Revoke old key after transition period
```

**3. SECRET_KEY Rotation (Django)**

```python
# Django supports multiple SECRET_KEYs

# settings.py
import os

# New key (current)
SECRET_KEY = os.environ['SECRET_KEY']

# Old keys (for reading old signatures)
SECRET_KEY_FALLBACKS = [
    os.environ.get('SECRET_KEY_OLD_1', ''),
    os.environ.get('SECRET_KEY_OLD_2', ''),
]

# Django will try keys in order when validating signatures
```

**Rotation process**:
1. Generate new SECRET_KEY
2. Set as SECRET_KEY, move old to SECRET_KEY_OLD_1
3. Deploy
4. Wait for all sessions to expire
5. Remove SECRET_KEY_OLD_1

## Preventing Secret Leaks

### Pre-Commit Hooks

**Use git-secrets or similar**:

```bash
# Install git-secrets
brew install git-secrets  # macOS
# or
pip install detect-secrets

# Set up for repo
git secrets --install
git secrets --register-aws

# Add patterns
git secrets --add 'SECRET_KEY\s*=\s*["\'][^"\']+["\']'
git secrets --add 'sk_live_[0-9a-zA-Z]{24,}'  # Stripe
git secrets --add 'AKIA[0-9A-Z]{16}'  # AWS

# Scan
git secrets --scan
```

**detect-secrets**:

```bash
# Install
pip install detect-secrets

# Create baseline
detect-secrets scan > .secrets.baseline

# Add to pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### Scanning Committed Secrets

**truffleHog**:

```bash
# Install
pip install truffleHog

# Scan entire repo history
trufflehog git file://. --json

# Scan specific branch
trufflehog git file://. --branch main

# Output high entropy findings
trufflehog git file://. --entropy=True
```

**git-filter-repo (Remove secrets from history)**:

```bash
# Install
pip install git-filter-repo

# Remove file from entire history
git filter-repo --path secrets.txt --invert-paths

# Remove string pattern from entire history
git filter-repo --replace-text <(echo 'regex:secret_key=.*==>secret_key=REDACTED')
```

**CRITICAL**: If secrets are committed:
1. Assume compromised
2. Rotate immediately
3. Clean git history
4. Force push (if possible)
5. Notify security team
6. Check for unauthorized access

### CI/CD Secret Scanning

**GitHub Actions**:

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          fetch-depth: 0  # Full history

      - name: Run detect-secrets
        uses: reviewdog/action-detect-secrets@master
        with:
          fail_on_error: true

      - name: Run truffleHog
        run: |
          pip install truffleHog
          trufflehog git file://. --fail
```

## Environment-Specific Secrets

### Development

```.env.development
# Use weak/fake secrets for development
DEBUG=True
SECRET_KEY=development-secret-key-not-for-production
DB_PASSWORD=dev_password

# Use test/sandbox API keys
STRIPE_SECRET_KEY=sk_test_...
SENDGRID_API_KEY=SG.test...
```

### Staging

```.env.staging
# Production-like but separate secrets
DEBUG=False
SECRET_KEY=<strong-key-from-vault>
DB_PASSWORD=<strong-password>

# Sandbox/test API keys
STRIPE_SECRET_KEY=sk_test_...
```

### Production

```bash
# NEVER use .env files in production!
# Use environment variables set by platform:

# AWS ECS
# Set in task definition

# Heroku
heroku config:set SECRET_KEY=xxx

# Kubernetes
# Use Secrets
kubectl create secret generic myapp-secrets \
  --from-literal=SECRET_KEY=xxx \
  --from-literal=DB_PASSWORD=yyy

# Docker
docker run -e SECRET_KEY=xxx myapp
```

## Container Secrets

### Docker Secrets (Swarm)

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    image: myapp:latest
    secrets:
      - db_password
      - secret_key
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
      SECRET_KEY_FILE: /run/secrets/secret_key

secrets:
  db_password:
    external: true
  secret_key:
    external: true
```

```python
# settings.py
def read_secret_file(path):
    """Read secret from Docker secret file."""
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

DB_PASSWORD_FILE = os.environ.get('DB_PASSWORD_FILE')
if DB_PASSWORD_FILE:
    DB_PASSWORD = read_secret_file(DB_PASSWORD_FILE)
else:
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
```

### Kubernetes Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: myapp-secrets
type: Opaque
data:
  SECRET_KEY: <base64-encoded-value>
  DB_PASSWORD: <base64-encoded-value>
```

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
        - name: myapp
          image: myapp:latest
          env:
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: myapp-secrets
                  key: SECRET_KEY
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: myapp-secrets
                  key: DB_PASSWORD
```

**Or use External Secrets Operator**:

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: myapp-secrets
  data:
    - secretKey: SECRET_KEY
      remoteRef:
        key: myapp/production
        property: SECRET_KEY
```

## Best Practices Checklist

### Development
- [ ] Use .env files for local development
- [ ] Never commit .env files
- [ ] Add .env* to .gitignore
- [ ] Use weak/fake secrets for development
- [ ] Document required environment variables

### Production
- [ ] Use secrets manager (AWS, Vault, etc.)
- [ ] Never use .env files in production
- [ ] Encrypt secrets at rest
- [ ] Encrypt secrets in transit (TLS)
- [ ] Limit access to secrets (IAM, RBAC)
- [ ] Audit secret access
- [ ] Rotate secrets regularly
- [ ] Use separate secrets per environment

### Code
- [ ] Never hardcode secrets
- [ ] Never log secrets
- [ ] Never include secrets in error messages
- [ ] Never send secrets to client
- [ ] Use environment variables or secrets manager
- [ ] Validate secrets exist at startup

### CI/CD
- [ ] Scan for secrets in commits
- [ ] Use platform secret storage (GitHub Secrets, etc.)
- [ ] Don't print secrets in logs
- [ ] Use short-lived credentials when possible
- [ ] Rotate CI/CD secrets regularly

### Monitoring
- [ ] Alert on secret access
- [ ] Alert on failed authentication
- [ ] Log secret rotation
- [ ] Monitor for leaked secrets (GitHub, public repos)
- [ ] Track secret age

## Example: Complete Secrets Setup

### 1. Local Development

```bash
# .env (gitignored)
SECRET_KEY=dev-secret-key
DEBUG=True
DB_PASSWORD=dev_password
STRIPE_SECRET_KEY=sk_test_...
```

```python
# settings/development.py
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = True
# ... use .env variables
```

### 2. Staging/Production

```bash
# Use AWS Secrets Manager

# Create secret
aws secretsmanager create-secret \
    --name myapp/production \
    --secret-string file://secrets.json
```

```python
# settings/production.py
from utils.secrets import get_secret

secrets = get_secret('myapp/production')

SECRET_KEY = secrets['SECRET_KEY']
DATABASES = {
    'default': {
        'PASSWORD': secrets['DB_PASSWORD'],
        # ...
    }
}
STRIPE_SECRET_KEY = secrets['STRIPE_SECRET_KEY']
```

### 3. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Don't include secrets in image!

CMD ["gunicorn", "myapp.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    environment:
      AWS_SECRET_NAME: myapp/production
      AWS_DEFAULT_REGION: us-east-1
    # Secrets pulled from AWS at runtime
```

### 4. Kubernetes Deployment

```yaml
# Use External Secrets Operator
# Pulls from AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
  target:
    name: myapp-secrets
  dataFrom:
    - extract:
        key: myapp/production
```

## Resources

- OWASP Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- AWS Secrets Manager: https://aws.amazon.com/secrets-manager/
- HashiCorp Vault: https://www.vaultproject.io/
- 12-Factor App Config: https://12factor.net/config
- django-environ: https://django-environ.readthedocs.io/
- detect-secrets: https://github.com/Yelp/detect-secrets

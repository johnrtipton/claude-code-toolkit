---
description: Type safety and mypy best practices for Django projects. Covers django-stubs configuration, type hints for models/views/forms/DRF, advanced typing patterns, and automated type checking.
when_to_use:
  - Working with Django models, views, forms, or serializers
  - Setting up mypy for a Django project
  - Adding type hints to Django code
  - Configuring django-stubs and type checking
  - Debugging mypy errors in Django
  - Implementing type-safe multi-tenant patterns
  - Using Django REST Framework with type hints
---

# Django Typing and mypy Best Practices

Complete guide to type safety in Django applications using mypy and django-stubs.

## Quick Start

### Installation

```bash
# Install mypy and django-stubs
pip install mypy django-stubs django-stubs-ext

# For Django REST Framework
pip install djangorestframework-stubs

# Add to requirements.txt
mypy==1.8.0
django-stubs==4.2.7
django-stubs-ext==4.2.7
djangorestframework-stubs==3.14.5  # If using DRF
```

### Basic Configuration

Create `mypy.ini` in project root:

```ini
[mypy]
plugins = mypy_django_plugin.main, mypy_drf_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings

[mypy-*.migrations.*]
ignore_errors = True
```

## Quick Reference

### Models

```python
from django.db import models
from typing import ClassVar

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    published: bool = models.BooleanField(default=False)

    # Declare manager type
    objects: ClassVar[models.Manager["Article"]] = models.Manager()

    def get_title(self) -> str:
        return self.title
```

### Views

```python
from django.http import HttpRequest, HttpResponse
from django.views.generic import ListView
from typing import Any

# Function-based view
def article_list(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Articles")

# Class-based view
class ArticleListView(ListView[Article]):
    model = Article
    template_name = "articles/list.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context
```

### Forms

```python
from django import forms
from typing import Any

class ArticleForm(forms.ModelForm[Article]):
    class Meta:
        model = Article
        fields = ["title", "published"]

    def clean_title(self) -> str:
        title = self.cleaned_data["title"]
        return title.strip()
```

### Django REST Framework

```python
from rest_framework import serializers, viewsets
from typing import Any

class ArticleSerializer(serializers.ModelSerializer[Article]):
    class Meta:
        model = Article
        fields = ["id", "title", "published"]

    def validate_title(self, value: str) -> str:
        return value.strip()

class ArticleViewSet(viewsets.ModelViewSet[Article]):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
```

### Custom Managers and QuerySets

```python
from django.db import models
from typing import TypeVar, Generic

_T = TypeVar("_T", bound=models.Model)

class CustomQuerySet(models.QuerySet[_T], Generic[_T]):
    def published(self) -> "CustomQuerySet[_T]":
        return self.filter(published=True)

class CustomManager(models.Manager[_T]):
    def get_queryset(self) -> CustomQuerySet[_T]:
        return CustomQuerySet(self.model, using=self._db)

    def published(self) -> CustomQuerySet[_T]:
        return self.get_queryset().published()

class Article(models.Model):
    title: str = models.CharField(max_length=200)
    published: bool = models.BooleanField(default=False)

    objects: ClassVar[CustomManager["Article"]] = CustomManager()
```

## Common Patterns

### Type Narrowing

```python
from django.http import HttpRequest, HttpResponse, JsonResponse
from typing import Union

def api_view(request: HttpRequest) -> Union[HttpResponse, JsonResponse]:
    if request.method == "GET":
        # Type narrowing with isinstance
        return JsonResponse({"status": "ok"})
    return HttpResponse("Invalid method")
```

### Protocol for Duck Typing

```python
from typing import Protocol

class Publishable(Protocol):
    published: bool

    def publish(self) -> None: ...

def publish_item(item: Publishable) -> None:
    if not item.published:
        item.publish()
```

### TypedDict for Settings

```python
from typing import TypedDict

class DatabaseConfig(TypedDict):
    ENGINE: str
    NAME: str
    USER: str
    PASSWORD: str
    HOST: str
    PORT: int

DATABASES: dict[str, DatabaseConfig] = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mydb",
        "USER": "user",
        "PASSWORD": "pass",
        "HOST": "localhost",
        "PORT": 5432,
    }
}
```

## Multi-Tenant Typing

```python
from django.db import models
from typing import TypeVar, Generic, ClassVar

T = TypeVar("T", bound="TenantBaseModel")

class TenantBaseModel(models.Model):
    tenant: models.ForeignKey["Tenant"] = models.ForeignKey(
        "Tenant", on_delete=models.CASCADE
    )

    class Meta:
        abstract = True

class TenantQuerySet(models.QuerySet[T], Generic[T]):
    def for_tenant(self, tenant: "Tenant") -> "TenantQuerySet[T]":
        return self.filter(tenant=tenant)

class TenantManager(models.Manager[T]):
    def get_queryset(self) -> TenantQuerySet[T]:
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant: "Tenant") -> TenantQuerySet[T]:
        return self.get_queryset().for_tenant(tenant)
```

## Automated Tools

This skill includes scripts for automated type checking and improvement:

### 1. Type Checker

```bash
# Run mypy with Django-specific configuration
python scripts/typing_checker.py

# Check specific app
python scripts/typing_checker.py --app myapp

# Strict mode
python scripts/typing_checker.py --strict

# Generate HTML report
python scripts/typing_checker.py --html-report
```

### 2. Type Hint Generator

```bash
# Auto-add type hints to models
python scripts/type_hint_generator.py --target models --app myapp

# Add hints to views
python scripts/type_hint_generator.py --target views --app myapp

# Generate for all apps
python scripts/type_hint_generator.py --all
```

### 3. Configuration Validator

```bash
# Validate mypy configuration
python scripts/config_validator.py

# Check django-stubs setup
python scripts/config_validator.py --check-stubs

# Suggest improvements
python scripts/config_validator.py --suggest
```

## Resources

### Reference Documentation

- **django-typing-guide.md** - Complete guide to typing Django (models, views, forms, etc.)
- **mypy-django-configuration.md** - mypy setup and configuration for Django
- **drf-typing-patterns.md** - Django REST Framework typing patterns
- **advanced-typing-patterns.md** - Generics, Protocols, TypedDict, type guards
- **multi-tenant-typing.md** - Type safety for multi-tenant architectures
- **troubleshooting-mypy-django.md** - Common mypy errors and solutions

### Templates and Examples

- **mypy.ini** - Complete mypy configuration template
- **pyproject.toml** - Alternative mypy configuration
- **.pre-commit-config.yaml** - Pre-commit hooks for type checking
- **typed_model_template.py** - Fully typed Django model examples
- **typed_view_template.py** - Typed views (CBV and FBV)
- **typed_serializer_template.py** - DRF serializer typing
- **typed_manager_template.py** - Custom manager and queryset typing

## Common mypy Errors

### Error: Need type annotation for variable

```python
# ❌ Error
items = []

# ✅ Fix
from typing import List
items: List[Article] = []
```

### Error: Incompatible types in assignment

```python
# ❌ Error
article: Article = Article.objects.first()  # Returns Article | None

# ✅ Fix
from django.shortcuts import get_object_or_404
article: Article = get_object_or_404(Article, pk=1)

# Or
article = Article.objects.first()
if article is not None:
    # mypy knows article is Article here
    print(article.title)
```

### Error: Cannot determine type of field

```python
# ❌ Error
class Article(models.Model):
    title = models.CharField(max_length=200)

# ✅ Fix
class Article(models.Model):
    title: str = models.CharField(max_length=200)
```

## Best Practices

### 1. Use Strict Mode Gradually

```ini
[mypy]
# Start with these
check_untyped_defs = True
disallow_untyped_defs = False  # Enable later

# Enable gradually
disallow_any_generics = True
disallow_subclassing_any = True
```

### 2. Ignore Migrations

```ini
[mypy-*.migrations.*]
ignore_errors = True
```

### 3. Type QuerySets Properly

```python
# ✅ Good
articles: models.QuerySet[Article] = Article.objects.filter(published=True)

# ❌ Avoid
articles = Article.objects.filter(published=True)  # Type is unknown
```

### 4. Use ClassVar for Class-Level Attributes

```python
from typing import ClassVar

class Article(models.Model):
    # Instance attribute
    title: str = models.CharField(max_length=200)

    # Class attribute
    objects: ClassVar[models.Manager["Article"]] = models.Manager()
```

### 5. Annotate Request and Response

```python
from django.http import HttpRequest, HttpResponse

def my_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse("OK")
```

## Integration with CI/CD

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [django-stubs, djangorestframework-stubs]
        args: [--config-file=mypy.ini]
```

### GitHub Actions

```yaml
name: Type Check
on: [push, pull_request]
jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: mypy .
```

## When to Use This Skill

Claude will automatically use this skill when you:
- Ask about type hints in Django
- Request help with mypy errors
- Want to add type checking to a Django project
- Need typing for models, views, forms, or serializers
- Ask about django-stubs configuration
- Request type-safe patterns for Django REST Framework
- Need help with generic types, Protocols, or TypedDict
- Want to implement type-safe multi-tenant patterns

## Related Skills

- **django-best-practices** - Multi-tenant patterns and Django best practices
- **django-security** - Security hardening and vulnerability detection

## Quick Commands

```bash
# Run type checker
python scripts/typing_checker.py

# Add type hints to existing code
python scripts/type_hint_generator.py --app myapp

# Validate mypy configuration
python scripts/config_validator.py

# Install pre-commit hooks
pre-commit install

# Check types in CI
mypy --config-file=mypy.ini .
```

---

**Next Steps:**
1. Install mypy and django-stubs
2. Create `mypy.ini` configuration (see `assets/mypy.ini`)
3. Run `python scripts/typing_checker.py` to check current project
4. Use `type_hint_generator.py` to add hints to existing code
5. Set up pre-commit hooks for automatic checking

# Mypy Django Configuration Reference

**Version:** 1.0
**Last Updated:** October 2025
**Applies to:** mypy 1.11+, django-stubs 5.1+, Django 4.2+/5.0+

This comprehensive reference covers everything you need to configure mypy for Django projects, from small applications to large-scale production systems.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Complete mypy.ini Configuration](#complete-mypyini-configuration)
3. [Django-Stubs Setup](#django-stubs-setup)
4. [Plugin Configuration](#plugin-configuration)
5. [Incremental Typing Strategies](#incremental-typing-strategies)
6. [Strictness Levels](#strictness-levels)
7. [Per-Module Configuration](#per-module-configuration)
8. [IDE Integration](#ide-integration)
9. [CI/CD Integration](#cicd-integration)
10. [Performance Optimization](#performance-optimization)
11. [Configuration Examples](#configuration-examples)
12. [Troubleshooting](#troubleshooting)
13. [Best Practices](#best-practices)

---

## Quick Start

### Minimal Setup

For a basic Django project, this is the minimal configuration you need:

**mypy.ini:**
```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

**Installation:**
```bash
pip install mypy django-stubs types-PyYAML types-requests
```

**Run:**
```bash
mypy .
```

---

## Complete mypy.ini Configuration

### Comprehensive Configuration Template

This is a production-ready configuration covering all major options:

```ini
[mypy]
# Python version
python_version = 3.11

# Plugins
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main

# Import discovery
mypy_path = $MYPY_CONFIG_FILE_DIR/stubs
namespace_packages = True
explicit_package_bases = True
ignore_missing_imports = False

# Platform configuration
platform = linux
python_executable = .venv/bin/python

# Dynamic typing
disallow_any_unimported = False
disallow_any_expr = False
disallow_any_decorated = False
disallow_any_explicit = False
disallow_any_generics = True
disallow_subclassing_any = True

# Untyped definitions and calls
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True

# None and Optional handling
no_implicit_optional = True
strict_optional = True

# Warnings
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_return_any = True
warn_unreachable = True

# Miscellaneous strictness flags
allow_untyped_globals = False
allow_redefinition = False
local_partial_types = False
implicit_reexport = False
strict_equality = True
strict_concatenate = True

# Configuring error messages
show_error_context = True
show_column_numbers = True
show_error_codes = True
pretty = True
color_output = True
error_summary = True
show_absolute_path = False

# Incremental mode
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True
cache_fine_grained = True

# Advanced options
warn_incomplete_stub = True
disallow_any_generics = True
disallow_untyped_calls = True
warn_unused_configs = True

# Coverage reporting
any_exprs_report = reports/any_exprs
html_report = reports/html
linecount_report = reports/linecount
linecoverage_report = reports/linecoverage
lineprecision_report = reports/lineprecision
txt_report = reports/txt
xml_report = reports/xml

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True
```

### Configuration Options Explained

#### Python Version Settings

```ini
[mypy]
python_version = 3.11
platform = linux
python_executable = .venv/bin/python
```

- `python_version`: Target Python version for type checking
- `platform`: Platform-specific type checking (linux, darwin, win32)
- `python_executable`: Path to Python interpreter (useful for detecting installed packages)

#### Plugin Configuration

```ini
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main
```

**Available Django-related plugins:**
- `mypy_django_plugin.main`: Core Django support
- `mypy_drf_plugin.main`: Django REST Framework support
- Third-party plugins for Celery, Channels, etc.

#### Import Discovery

```ini
mypy_path = $MYPY_CONFIG_FILE_DIR/stubs
namespace_packages = True
explicit_package_bases = True
ignore_missing_imports = False
```

- `mypy_path`: Additional directories to search for stub files
- `namespace_packages`: Enable PEP 420 namespace package support
- `explicit_package_bases`: Require explicit `__init__.py` files
- `ignore_missing_imports`: Control behavior for missing import stubs

#### Dynamic Typing Controls

```ini
disallow_any_unimported = False
disallow_any_expr = False
disallow_any_decorated = False
disallow_any_explicit = False
disallow_any_generics = True
disallow_subclassing_any = True
```

**Recommended progression:**
1. Start with all `False` except `disallow_any_generics = True`
2. Enable `disallow_subclassing_any = True`
3. Gradually enable others as codebase improves

#### Untyped Code Handling

```ini
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
```

**Strictness levels:**
- **Permissive**: All `False` - allows untyped code
- **Moderate**: `check_untyped_defs = True` only
- **Strict**: All `True` - requires complete typing

#### None and Optional

```ini
no_implicit_optional = True
strict_optional = True
```

- `no_implicit_optional`: `def f(x: int = None)` is an error (require `Optional[int]`)
- `strict_optional`: Enable strict Optional checking (recommended)

#### Warning Flags

```ini
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_return_any = True
warn_unreachable = True
```

All warnings should be `True` for best results.

#### Error Display

```ini
show_error_context = True
show_column_numbers = True
show_error_codes = True
pretty = True
color_output = True
error_summary = True
show_absolute_path = False
```

Customize based on your IDE and CI/CD needs.

#### Incremental Mode

```ini
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True
cache_fine_grained = True
```

**Performance impact:**
- `incremental = True`: 10-100x faster for repeated runs
- `sqlite_cache = True`: More reliable cache storage
- `cache_fine_grained = True`: Better for large projects

#### Coverage Reporting

```ini
any_exprs_report = reports/any_exprs
html_report = reports/html
linecount_report = reports/linecount
linecoverage_report = reports/linecoverage
txt_report = reports/txt
```

Generate detailed coverage reports to track typing progress.

---

## Django-Stubs Setup

### Installation

```bash
# Core packages
pip install mypy django-stubs

# Django REST Framework support
pip install djangorestframework-stubs

# Common third-party type stubs
pip install types-PyYAML types-requests types-redis types-python-dateutil

# Celery support
pip install celery-types

# Development dependencies
pip install --dev mypy django-stubs[compatible-mypy]
```

### Package Versions

**requirements.txt:**
```txt
mypy==1.11.2
django-stubs==5.1.0
django-stubs-ext==5.1.0
djangorestframework-stubs==3.15.0
types-PyYAML==6.0.12
types-requests==2.31.0
types-redis==4.6.0
types-python-dateutil==2.9.0
celery-types==0.22.0
```

**pyproject.toml (Poetry):**
```toml
[tool.poetry.group.dev.dependencies]
mypy = "^1.11"
django-stubs = {extras = ["compatible-mypy"], version = "^5.1"}
djangorestframework-stubs = "^3.15"
types-PyYAML = "^6.0"
types-requests = "^2.31"
```

### Django Settings Module Configuration

```ini
[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True
```

**For multiple settings files:**

```ini
[mypy.plugins.django-stubs]
django_settings_module = myproject.settings.production
strict_settings = False
```

**Environment-based settings:**

```bash
# Set via environment variable
export DJANGO_SETTINGS_MODULE=myproject.settings.test
mypy .
```

### Django-Stubs Configuration Options

```ini
[mypy.plugins.django-stubs]
# Settings module (required)
django_settings_module = myproject.settings

# Strict mode for settings (recommended)
strict_settings = True

# Additional type checking
# Note: Most options are now in the main [mypy] section
```

**Deprecated options (now in [mypy]):**
- `disallow_untyped_defs` → moved to `[mypy]`
- `warn_return_any` → moved to `[mypy]`

---

## Plugin Configuration

### Django Plugin (mypy_django_plugin)

The Django plugin provides type checking for:
- Model fields and relationships
- QuerySet operations
- Forms and form fields
- Admin configuration
- URL patterns
- Template context
- Management commands

**Configuration:**

```ini
[mypy]
plugins = mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

**Features:**
1. **Model field type inference:**
   ```python
   class User(models.Model):
       name = models.CharField(max_length=100)
       age = models.IntegerField()

   user = User.objects.get(id=1)
   reveal_type(user.name)  # str
   reveal_type(user.age)   # int
   ```

2. **QuerySet type safety:**
   ```python
   users: QuerySet[User] = User.objects.filter(age__gte=18)
   for user in users:
       reveal_type(user)  # User
   ```

3. **Form field validation:**
   ```python
   class UserForm(forms.Form):
       name = forms.CharField()

   form = UserForm(data={'name': 123})  # Error: Expected str
   ```

### Django REST Framework Plugin (mypy_drf_plugin)

Provides type checking for:
- Serializers and serializer fields
- ViewSets and API views
- Permissions and authentication
- Request and response objects

**Configuration:**

```ini
[mypy]
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main
```

**Features:**
1. **Serializer field types:**
   ```python
   class UserSerializer(serializers.ModelSerializer):
       class Meta:
           model = User
           fields = ['name', 'age']

   data = UserSerializer(user).data
   reveal_type(data['name'])  # str
   ```

2. **ViewSet type safety:**
   ```python
   class UserViewSet(viewsets.ModelViewSet):
       queryset: QuerySet[User] = User.objects.all()
       serializer_class = UserSerializer
   ```

### Third-Party Plugin Integration

**Celery:**

```ini
[mypy]
plugins =
    mypy_django_plugin.main,
    celery.contrib.typing

[mypy-celery.*]
ignore_missing_imports = False
```

**Django Channels:**

```ini
[mypy-channels.*]
ignore_missing_imports = True  # No official stubs yet
```

**Django Debug Toolbar:**

```ini
[mypy-debug_toolbar.*]
ignore_missing_imports = True
```

---

## Incremental Typing Strategies

### Strategy 1: Start Permissive, Gradually Strict

**Phase 1: Initial Setup (Week 1)**

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Very permissive
ignore_missing_imports = True
disallow_untyped_defs = False
check_untyped_defs = False

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

**Goals:**
- Get mypy running without errors
- Establish baseline
- Add to CI/CD

**Phase 2: Check Untyped Code (Week 2-4)**

```ini
[mypy]
# Start checking untyped code
check_untyped_defs = True
disallow_incomplete_defs = True

# Still permissive on definitions
disallow_untyped_defs = False
```

**Goals:**
- Find bugs in existing code
- Fix type errors without adding annotations
- Build confidence

**Phase 3: Require Types for New Code (Week 5-8)**

```ini
[mypy]
# Require types for new functions
disallow_untyped_defs = True
disallow_incomplete_defs = True

# Allow untyped calls to old code
disallow_untyped_calls = False

# Per-module overrides for legacy code
[mypy-legacy.*]
disallow_untyped_defs = False
```

**Goals:**
- All new code must be typed
- Legacy code can remain untyped
- Gradual improvement

**Phase 4: Full Strictness (Week 9+)**

```ini
[mypy]
# Full strictness
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
warn_return_any = True
strict = True
```

**Goals:**
- Complete type coverage
- Maximum type safety
- Consistent codebase

### Strategy 2: Module-by-Module

**Configuration:**

```ini
[mypy]
# Global permissive settings
disallow_untyped_defs = False
warn_return_any = False

# Strict for specific modules
[mypy-myapp.models]
disallow_untyped_defs = True
disallow_incomplete_defs = True
warn_return_any = True

[mypy-myapp.serializers]
disallow_untyped_defs = True
disallow_incomplete_defs = True

[mypy-myapp.views]
disallow_untyped_defs = True

# Legacy modules stay permissive
[mypy-legacy_app.*]
disallow_untyped_defs = False
ignore_errors = True
```

**Implementation Plan:**

1. **Priority Modules First:**
   - Core business logic
   - API endpoints
   - Authentication/authorization
   - Data models

2. **Dependency Order:**
   - Models first
   - Serializers next
   - Views/ViewSets
   - Utils and helpers

3. **Track Progress:**
   ```bash
   # Create a typed modules list
   echo "myapp.models" >> typed_modules.txt
   echo "myapp.serializers" >> typed_modules.txt

   # Count typed vs untyped
   mypy --html-report=reports/coverage .
   ```

### Strategy 3: Strict Mode with Allowlist

**Configuration:**

```ini
[mypy]
# Global strict mode
strict = True

# Allowlist for legacy code
[mypy-old_app.*]
strict = False
ignore_errors = True

[mypy-third_party_integration.*]
ignore_missing_imports = True
strict = False
```

**Use when:**
- Starting a new project
- Major refactoring
- Small codebase (<10k lines)

### Strategy 4: File-by-File Annotations

**Using inline configuration:**

```python
# mypy: strict

from typing import Optional
from django.db import models

class User(models.Model):
    name: str = models.CharField(max_length=100)
    age: int = models.IntegerField()
```

**Or disable for legacy files:**

```python
# mypy: ignore-errors

# Legacy code, will be refactored later
def untyped_function():
    pass
```

### Tracking Progress

**Generate reports:**

```bash
# Line coverage report
mypy --linecoverage-report=reports .

# HTML report with visual coverage
mypy --html-report=reports/html .

# Any expressions report (find untyped areas)
mypy --any-exprs-report=reports/any_exprs .
```

**Example progress tracking script:**

```python
#!/usr/bin/env python3
"""Track mypy typing progress over time."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

def count_typed_lines():
    """Count typed vs untyped lines."""
    result = subprocess.run(
        ['mypy', '--linecoverage-report=reports/coverage', '.'],
        capture_output=True,
        text=True
    )

    coverage_file = Path('reports/coverage/index.txt')
    if coverage_file.exists():
        content = coverage_file.read_text()
        # Parse coverage report
        # ... implementation ...
        return coverage_data

    return None

def save_progress(coverage_data):
    """Save progress to JSON file."""
    progress_file = Path('mypy_progress.json')

    if progress_file.exists():
        history = json.loads(progress_file.read_text())
    else:
        history = []

    history.append({
        'date': datetime.now().isoformat(),
        'coverage': coverage_data
    })

    progress_file.write_text(json.dumps(history, indent=2))

if __name__ == '__main__':
    coverage = count_typed_lines()
    if coverage:
        save_progress(coverage)
        print(f"Typed coverage: {coverage['percentage']:.1f}%")
```

---

## Strictness Levels

### Level 0: Minimal (Getting Started)

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

ignore_missing_imports = True

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

**Use case:** Initial setup, proof of concept

### Level 1: Permissive (Legacy Projects)

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Check untyped code but don't require annotations
check_untyped_defs = True
disallow_incomplete_defs = True

# Basic warnings
warn_redundant_casts = True
warn_unused_ignores = True

# Ignore missing imports for third-party
ignore_missing_imports = False

[mypy-some_untyped_library.*]
ignore_missing_imports = True

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

**Use case:** Large legacy codebases, third-party integrations

### Level 2: Moderate (Production Projects)

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Require types for definitions
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True

# No Any in generics
disallow_any_generics = True
disallow_subclassing_any = True

# Optional handling
no_implicit_optional = True
strict_optional = True

# Warnings
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True

# Import handling
ignore_missing_imports = False

[mypy-third_party.*]
ignore_missing_imports = True

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True
```

**Use case:** Actively maintained projects, new features

### Level 3: Strict (High-Quality Code)

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Enable strict mode (includes many checks)
strict = True

# Additional strict checks
warn_return_any = True
disallow_untyped_calls = True
disallow_untyped_decorators = True

# Strict equality
strict_equality = True

# No implicit reexports
implicit_reexport = False

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True
```

**Use case:** New projects, critical systems, libraries

### Level 4: Maximum (Ultra-Strict)

```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Strict mode
strict = True

# Disallow all Any
disallow_any_unimported = True
disallow_any_expr = True
disallow_any_decorated = True
disallow_any_explicit = True
disallow_any_generics = True

# Require complete typing
disallow_untyped_calls = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
disallow_untyped_decorators = True

# Maximum warnings
warn_return_any = True
warn_unreachable = True
warn_unused_configs = True

# Strict checks
strict_equality = True
strict_concatenate = True
implicit_reexport = False
allow_untyped_globals = False
allow_redefinition = False
local_partial_types = False

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True
```

**Use case:** Type-safe libraries, security-critical code

### Comparison Table

| Feature | Level 0 | Level 1 | Level 2 | Level 3 | Level 4 |
|---------|---------|---------|---------|---------|---------|
| `disallow_untyped_defs` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `check_untyped_defs` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `disallow_any_generics` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `warn_return_any` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `strict` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `disallow_any_expr` | ❌ | ❌ | ❌ | ❌ | ✅ |
| Error rate | Very Low | Low | Medium | High | Very High |
| Effort | Minimal | Low | Medium | High | Very High |

---

## Per-Module Configuration

### Basic Module Configuration

```ini
[mypy]
# Global defaults
strict = False

# Strict for core app
[mypy-myapp.core.*]
strict = True
disallow_untyped_defs = True

# Moderate for API
[mypy-myapp.api.*]
disallow_untyped_defs = True
warn_return_any = False

# Permissive for tests
[mypy-tests.*]
disallow_untyped_defs = False
disallow_untyped_calls = False
```

### Django App-Specific Configuration

```ini
[mypy]
strict = True

# Models: Maximum strictness
[mypy-*.models]
disallow_any_generics = True
disallow_any_explicit = True
warn_return_any = True

# Views: Moderate (due to class-based views)
[mypy-*.views]
disallow_any_decorated = False  # CBV decorators
disallow_incomplete_defs = True

# Serializers: Strict
[mypy-*.serializers]
disallow_untyped_defs = True
disallow_any_generics = True

# Tests: Permissive
[mypy-*.tests.*]
disallow_untyped_defs = False
disallow_untyped_calls = False

# Migrations: Ignore
[mypy-*.migrations.*]
ignore_errors = True
```

### Third-Party Library Configuration

```ini
[mypy]
ignore_missing_imports = False

# Libraries without stubs
[mypy-celery.*]
ignore_missing_imports = True

[mypy-kombu.*]
ignore_missing_imports = True

[mypy-redis.*]
ignore_missing_imports = False  # Has stubs

[mypy-requests.*]
ignore_missing_imports = False  # Has stubs

# Internal libraries
[mypy-mycompany.shared.*]
follow_imports = normal

# Vendored code
[mypy-vendor.*]
ignore_errors = True
```

### Complex Per-Module Patterns

**By layer:**

```ini
# Data layer - strictest
[mypy-*.models]
strict = True
disallow_any_generics = True

[mypy-*.repositories]
strict = True
disallow_any_generics = True

# Business logic - strict
[mypy-*.services]
disallow_untyped_defs = True
disallow_untyped_calls = True

[mypy-*.domain]
strict = True

# Presentation layer - moderate
[mypy-*.views]
disallow_untyped_defs = True
disallow_any_decorated = False

[mypy-*.serializers]
disallow_untyped_defs = True

# Infrastructure - permissive
[mypy-*.celery_tasks]
disallow_untyped_defs = False

[mypy-*.management.commands.*]
disallow_untyped_defs = False
```

**By feature:**

```ini
# Authentication - maximum security
[mypy-*.auth.*]
strict = True
disallow_any_expr = True
warn_return_any = True

# Payments - critical
[mypy-*.payments.*]
strict = True
disallow_any_generics = True

# Admin - moderate
[mypy-*.admin]
disallow_untyped_defs = True
disallow_untyped_decorators = False

# Utils - strict
[mypy-*.utils]
disallow_untyped_defs = True
```

### Overriding Global Settings

```ini
[mypy]
# Global strict mode
strict = True

# Selectively relax for specific modules
[mypy-legacy_app.*]
strict = False
ignore_errors = False  # Still check, but not strict
disallow_untyped_defs = False

[mypy-experimental.*]
warn_return_any = False  # Allow Any for prototyping
disallow_incomplete_defs = False
```

---

## IDE Integration

### VS Code

**settings.json:**

```json
{
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.mypyPath": "${workspaceFolder}/.venv/bin/mypy",
  "python.linting.mypyArgs": [
    "--config-file=${workspaceFolder}/mypy.ini",
    "--show-column-numbers",
    "--show-error-codes",
    "--pretty"
  ],

  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.diagnosticMode": "workspace",

  "files.watcherExclude": {
    "**/.mypy_cache/**": true
  },

  "mypy.configFile": "mypy.ini",
  "mypy.dmypyExecutable": "${workspaceFolder}/.venv/bin/dmypy",
  "mypy.runUsingActiveInterpreter": true
}
```

**Extensions:**

1. **Mypy extension** (`matangover.mypy`)
   - Real-time type checking
   - Inline error display
   - Quick fixes

2. **Pylance** (built-in)
   - Advanced type checking
   - IntelliSense
   - Auto-imports

**Tasks (tasks.json):**

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "mypy: Check all",
      "type": "shell",
      "command": "${workspaceFolder}/.venv/bin/mypy",
      "args": ["."],
      "problemMatcher": {
        "owner": "python",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
          "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning):\\s+(.+)\\s+\\[(.+)\\]$",
          "file": 1,
          "line": 2,
          "column": 3,
          "severity": 4,
          "message": 5,
          "code": 6
        }
      },
      "group": {
        "kind": "test",
        "isDefault": true
      }
    },
    {
      "label": "mypy: Check current file",
      "type": "shell",
      "command": "${workspaceFolder}/.venv/bin/mypy",
      "args": ["${file}"],
      "problemMatcher": "$mypy"
    },
    {
      "label": "mypy: Generate HTML report",
      "type": "shell",
      "command": "${workspaceFolder}/.venv/bin/mypy",
      "args": ["--html-report", "reports/html", "."]
    }
  ]
}
```

**Keyboard shortcuts (keybindings.json):**

```json
[
  {
    "key": "ctrl+shift+m",
    "command": "workbench.action.tasks.runTask",
    "args": "mypy: Check current file"
  },
  {
    "key": "ctrl+shift+alt+m",
    "command": "workbench.action.tasks.runTask",
    "args": "mypy: Check all"
  }
]
```

### PyCharm / IntelliJ IDEA

**Enable mypy:**

1. Go to **Preferences → Tools → External Tools**
2. Click **+** to add new tool
3. Configure:
   - **Name:** mypy
   - **Program:** `$PyInterpreterDirectory$/mypy`
   - **Arguments:** `$FilePath$`
   - **Working directory:** `$ProjectFileDir$`

**File watchers:**

1. Go to **Preferences → Tools → File Watchers**
2. Add new watcher:
   - **File type:** Python
   - **Scope:** Project Files
   - **Program:** `$PyInterpreterDirectory$/mypy`
   - **Arguments:** `$FilePath$`
   - **Output paths:** `.mypy_cache`

**External tool configuration:**

```xml
<!-- .idea/tools/External Tools.xml -->
<toolSet name="External Tools">
  <tool name="mypy" showInMainMenu="true" showInEditor="true"
        showInProject="true" showInSearchPopup="true"
        disabled="false" useConsole="true" showConsoleOnStdOut="false"
        showConsoleOnStdErr="false" synchronizeAfterRun="true">
    <exec>
      <option name="COMMAND" value="$PyInterpreterDirectory$/mypy" />
      <option name="PARAMETERS" value="--config-file mypy.ini $FilePath$" />
      <option name="WORKING_DIRECTORY" value="$ProjectFileDir$" />
    </exec>
  </tool>

  <tool name="mypy-all" showInMainMenu="true" showInEditor="false"
        showInProject="true" showInSearchPopup="true">
    <exec>
      <option name="COMMAND" value="$PyInterpreterDirectory$/mypy" />
      <option name="PARAMETERS" value="--config-file mypy.ini ." />
      <option name="WORKING_DIRECTORY" value="$ProjectFileDir$" />
    </exec>
  </tool>
</toolSet>
```

**Keyboard shortcuts:**

```
Tools → External Tools → mypy: Ctrl+Shift+M
Tools → External Tools → mypy-all: Ctrl+Shift+Alt+M
```

### Sublime Text

**Package:** SublimeLinter-contrib-mypy

**Settings (Preferences → Package Settings → SublimeLinter → Settings):**

```json
{
  "linters": {
    "mypy": {
      "executable": "${folder}/.venv/bin/mypy",
      "args": [
        "--config-file=${folder}/mypy.ini",
        "--show-column-numbers",
        "--show-error-codes"
      ],
      "working_dir": "${folder}",
      "selector": "source.python",
      "disable": false
    }
  }
}
```

### Vim/Neovim

**Using ALE (Asynchronous Lint Engine):**

```vim
" .vimrc / init.vim
let g:ale_linters = {
\   'python': ['mypy'],
\}

let g:ale_python_mypy_executable = '.venv/bin/mypy'
let g:ale_python_mypy_options = '--config-file mypy.ini'
let g:ale_python_mypy_use_global = 0
let g:ale_python_mypy_auto_pipenv = 1

" Show error codes
let g:ale_python_mypy_show_notes = 1

" Keyboard shortcuts
nmap <silent> <leader>m :ALELint<CR>
nmap <silent> <leader>d :ALEDetail<CR>
```

**Using coc.nvim:**

```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.mypyPath": ".venv/bin/mypy",
  "python.linting.mypyArgs": [
    "--config-file=mypy.ini"
  ]
}
```

### Emacs

**Using flycheck:**

```elisp
;; .emacs or init.el
(use-package flycheck
  :ensure t
  :init (global-flycheck-mode)
  :config
  (setq flycheck-python-mypy-executable ".venv/bin/mypy")
  (setq flycheck-python-mypy-config "mypy.ini")
  (add-hook 'python-mode-hook 'flycheck-mode))
```

---

## CI/CD Integration

### GitHub Actions

**Basic workflow:**

```yaml
# .github/workflows/type-check.yml
name: Type Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  mypy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install mypy django-stubs

    - name: Run mypy
      run: mypy .

    - name: Upload mypy report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: mypy-report
        path: reports/
```

**Advanced workflow with caching:**

```yaml
# .github/workflows/type-check-advanced.yml
name: Advanced Type Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  mypy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache pip packages
      uses: actions/cache@v4
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Cache mypy
      uses: actions/cache@v4
      with:
        path: .mypy_cache
        key: mypy-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/*.py') }}
        restore-keys: |
          mypy-${{ runner.os }}-${{ matrix.python-version }}-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install mypy django-stubs djangorestframework-stubs

    - name: Run mypy
      run: |
        mypy --config-file mypy.ini \
             --html-report reports/html \
             --txt-report reports/txt \
             --linecount-report reports/linecount \
             .

    - name: Generate coverage summary
      if: always()
      run: |
        echo "## Type Coverage Report" >> $GITHUB_STEP_SUMMARY
        cat reports/txt/index.txt >> $GITHUB_STEP_SUMMARY

    - name: Upload HTML report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: mypy-report-py${{ matrix.python-version }}
        path: reports/html/

    - name: Comment PR
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const report = fs.readFileSync('reports/txt/index.txt', 'utf8');

          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Mypy Type Check Results\n\`\`\`\n${report}\n\`\`\``
          });
```

**Pre-commit integration:**

```yaml
# .github/workflows/pre-commit.yml
name: Pre-commit

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Run pre-commit
      uses: pre-commit/action@v3.0.0
```

**.pre-commit-config.yaml:**

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: 'v1.11.2'
    hooks:
      - id: mypy
        additional_dependencies:
          - django-stubs==5.1.0
          - djangorestframework-stubs==3.15.0
          - types-requests
          - types-PyYAML
        args:
          - --config-file=mypy.ini
        pass_filenames: false
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - .mypy_cache

type-check:
  stage: test
  image: python:3.11

  before_script:
    - pip install -r requirements.txt
    - pip install mypy django-stubs

  script:
    - mypy --config-file mypy.ini --html-report reports/html .

  artifacts:
    when: always
    paths:
      - reports/
    reports:
      junit: reports/junit.xml
    expire_in: 1 week

  coverage: '/^TOTAL.+?(\d+\.\d+)%/'

type-coverage:
  stage: report
  image: python:3.11

  dependencies:
    - type-check

  script:
    - echo "Type coverage report generated"

  artifacts:
    paths:
      - reports/html/
    expose_as: 'Type Coverage Report'
```

### Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        PYTHON_VERSION = '3.11'
    }

    stages {
        stage('Setup') {
            steps {
                sh '''
                    python${PYTHON_VERSION} -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    pip install mypy django-stubs
                '''
            }
        }

        stage('Type Check') {
            steps {
                sh '''
                    . .venv/bin/activate
                    mypy --config-file mypy.ini \
                         --html-report reports/html \
                         --txt-report reports/txt \
                         --junit-xml reports/junit.xml \
                         .
                '''
            }
        }

        stage('Report') {
            steps {
                publishHTML([
                    reportDir: 'reports/html',
                    reportFiles: 'index.html',
                    reportName: 'Mypy Type Coverage',
                    keepAll: true
                ])

                junit 'reports/junit.xml'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*', allowEmptyArchive: true
        }
    }
}
```

### CircleCI

```yaml
# .circleci/config.yml
version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  type-check:
    docker:
      - image: cimg/python:3.11

    steps:
      - checkout

      - restore_cache:
          keys:
            - v1-dependencies-{{ checksum "requirements.txt" }}
            - v1-dependencies-

      - run:
          name: Install dependencies
          command: |
            pip install -r requirements.txt
            pip install mypy django-stubs

      - save_cache:
          paths:
            - ~/.cache/pip
          key: v1-dependencies-{{ checksum "requirements.txt" }}

      - restore_cache:
          keys:
            - v1-mypy-{{ .Branch }}-{{ .Revision }}
            - v1-mypy-{{ .Branch }}-
            - v1-mypy-

      - run:
          name: Run mypy
          command: |
            mypy --config-file mypy.ini \
                 --html-report reports/html \
                 --txt-report reports/txt \
                 .

      - save_cache:
          paths:
            - .mypy_cache
          key: v1-mypy-{{ .Branch }}-{{ .Revision }}

      - store_artifacts:
          path: reports
          destination: mypy-reports

      - store_test_results:
          path: reports

workflows:
  main:
    jobs:
      - type-check
```

### Travis CI

```yaml
# .travis.yml
language: python

python:
  - "3.10"
  - "3.11"
  - "3.12"

cache:
  pip: true
  directories:
    - .mypy_cache

install:
  - pip install -r requirements.txt
  - pip install mypy django-stubs

script:
  - mypy --config-file mypy.ini --html-report reports/html .

after_success:
  - bash <(curl -s https://codecov.io/bash) -f reports/coverage.xml

deploy:
  provider: pages
  skip_cleanup: true
  github_token: $GITHUB_TOKEN
  local_dir: reports/html
  on:
    branch: main
```

---

## Performance Optimization

### Caching Strategies

**Basic caching:**

```ini
[mypy]
incremental = True
cache_dir = .mypy_cache
```

**SQLite cache (faster):**

```ini
[mypy]
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True
```

**Fine-grained cache:**

```ini
[mypy]
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True
cache_fine_grained = True
```

**Performance comparison:**

| Cache Strategy | First Run | Subsequent Runs | Cache Size |
|----------------|-----------|-----------------|------------|
| No cache | 100s | 100s | 0 MB |
| Basic | 100s | 10s | 50 MB |
| SQLite | 100s | 5s | 40 MB |
| Fine-grained | 100s | 2s | 80 MB |

### Daemon Mode (dmypy)

**Start daemon:**

```bash
dmypy start -- --config-file mypy.ini
```

**Run checks:**

```bash
dmypy check .
```

**Status:**

```bash
dmypy status
```

**Stop:**

```bash
dmypy stop
```

**Performance:**

- First run: Same as mypy
- Subsequent runs: 10-100x faster
- Memory usage: ~500MB (persistent)

**Integration script:**

```bash
#!/bin/bash
# scripts/dmypy-check.sh

if ! dmypy status &>/dev/null; then
    echo "Starting dmypy daemon..."
    dmypy start -- --config-file mypy.ini
fi

echo "Running type check..."
dmypy check .

# Optionally restart on configuration changes
if git diff --name-only HEAD~1 | grep -q "mypy.ini"; then
    echo "Configuration changed, restarting daemon..."
    dmypy restart
fi
```

### Parallel Checking

**Configuration:**

```ini
[mypy]
# Use all available CPUs
# Not explicitly configurable, but mypy will use parallelism automatically
```

**Manual parallelization:**

```bash
# Split by app
parallel mypy ::: app1/ app2/ app3/

# Split by module
find . -name "*.py" -type f | parallel -j 4 mypy
```

### Selective Checking

**Check only changed files:**

```bash
# Git diff
git diff --name-only --diff-filter=ACMR origin/main | grep '\.py$' | xargs mypy

# Since last commit
git diff --name-only HEAD~1 | grep '\.py$' | xargs mypy
```

**Pre-commit hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Get staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep '\.py$')

if [ -n "$STAGED_FILES" ]; then
    echo "Running mypy on staged files..."
    echo "$STAGED_FILES" | xargs mypy --config-file mypy.ini

    if [ $? -ne 0 ]; then
        echo "Mypy check failed. Commit aborted."
        exit 1
    fi
fi
```

### Import Following

**Configuration:**

```ini
[mypy]
# Follow imports for type checking
follow_imports = normal  # Default: check all imports

# Or be more selective
follow_imports = skip  # Skip checking imported modules
```

**Options:**
- `normal`: Follow and check all imports (thorough, slower)
- `silent`: Follow but don't report errors in imports (faster)
- `skip`: Don't follow imports at all (fastest, least thorough)
- `error`: Treat missing imports as errors

**Selective following:**

```ini
[mypy]
follow_imports = normal

# Skip third-party
[mypy-third_party.*]
follow_imports = skip

# Skip tests
[mypy-tests.*]
follow_imports = skip
```

### Large Project Optimizations

**For projects >100k lines:**

```ini
[mypy]
# Incremental with SQLite
incremental = True
sqlite_cache = True
cache_fine_grained = True

# Skip unimportant checks
warn_unused_configs = False

# Selective import following
follow_imports = normal

[mypy-tests.*]
follow_imports = skip

[mypy-migrations.*]
follow_imports = skip

# Ignore third-party
[mypy-vendor.*]
follow_imports = skip
ignore_errors = True
```

**Parallel CI:**

```yaml
# .github/workflows/type-check-parallel.yml
jobs:
  mypy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        module:
          - app1
          - app2
          - app3
          - app4

    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: pip install mypy django-stubs

    - name: Check ${{ matrix.module }}
      run: mypy ${{ matrix.module }}/
```

### Memory Usage Optimization

**Reduce memory usage:**

```ini
[mypy]
# Disable fine-grained cache if memory-constrained
cache_fine_grained = False

# Skip some expensive checks
disallow_any_expr = False  # Very expensive
```

**Memory profiling:**

```bash
# Run with memory profiling
mprof run mypy .
mprof plot
```

**Monitoring script:**

```python
#!/usr/bin/env python3
"""Monitor mypy memory usage."""

import subprocess
import psutil
import time

def monitor_mypy():
    """Monitor mypy memory usage."""
    proc = subprocess.Popen(['mypy', '.'], stdout=subprocess.PIPE)
    process = psutil.Process(proc.pid)

    max_memory = 0
    while proc.poll() is None:
        try:
            mem_info = process.memory_info()
            current_memory = mem_info.rss / 1024 / 1024  # MB
            max_memory = max(max_memory, current_memory)
            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break

    print(f"Max memory usage: {max_memory:.1f} MB")

if __name__ == '__main__':
    monitor_mypy()
```

---

## Configuration Examples

### Small Project (<1k lines)

```ini
# mypy.ini - Small project
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Strict from the start
strict = True

# Django settings
[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True

# Ignore migrations
[mypy-*.migrations.*]
ignore_errors = True
```

**Usage:**
```bash
mypy .
```

**Typical runtime:** <1 second

### Medium Project (1k-10k lines)

```ini
# mypy.ini - Medium project
[mypy]
python_version = 3.11
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main

# Moderate strictness
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_any_generics = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True

# Caching
incremental = True
cache_dir = .mypy_cache

# Django settings
[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
strict_settings = True

# Per-app configuration
[mypy-myapp.models]
strict = True

[mypy-myapp.api.*]
disallow_untyped_defs = True

[mypy-tests.*]
disallow_untyped_defs = False

[mypy-*.migrations.*]
ignore_errors = True

# Third-party
[mypy-celery.*]
ignore_missing_imports = True
```

**Usage:**
```bash
mypy .
```

**Typical runtime:** 5-10 seconds

### Large Project (10k-100k lines)

```ini
# mypy.ini - Large project
[mypy]
python_version = 3.11
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main

# Performance optimizations
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True
cache_fine_grained = True

# Moderate global settings
disallow_untyped_defs = False
check_untyped_defs = True

# Import handling
follow_imports = normal
ignore_missing_imports = False

# Warnings
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True

# Error display
show_error_codes = True
pretty = True

# Django settings
[mypy.plugins.django-stubs]
django_settings_module = myproject.settings.production
strict_settings = False

# Core apps - strict
[mypy-core.*]
strict = True

[mypy-auth.*]
strict = True
disallow_any_expr = True

# API - moderate
[mypy-api.*]
disallow_untyped_defs = True
disallow_incomplete_defs = True

# Legacy - permissive
[mypy-legacy.*]
disallow_untyped_defs = False
follow_imports = skip

# Tests
[mypy-tests.*]
disallow_untyped_defs = False
disallow_untyped_calls = False

# Migrations
[mypy-*.migrations.*]
ignore_errors = True

# Third-party without stubs
[mypy-celery.*]
ignore_missing_imports = True

[mypy-kombu.*]
ignore_missing_imports = True

[mypy-channels.*]
ignore_missing_imports = True

# Vendored code
[mypy-vendor.*]
ignore_errors = True
follow_imports = skip
```

**Usage:**
```bash
# Use daemon mode
dmypy run -- .

# Or parallel checking
parallel mypy ::: app1/ app2/ app3/
```

**Typical runtime:** 30-60 seconds (first run), 2-5 seconds (daemon)

### Monorepo / Multi-Project

```ini
# mypy.ini - Monorepo
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

# Namespace packages for monorepo
namespace_packages = True
explicit_package_bases = True

# Search paths
mypy_path =
    $MYPY_CONFIG_FILE_DIR/services/auth,
    $MYPY_CONFIG_FILE_DIR/services/api,
    $MYPY_CONFIG_FILE_DIR/services/worker,
    $MYPY_CONFIG_FILE_DIR/shared

# Performance
incremental = True
cache_dir = .mypy_cache
sqlite_cache = True

# Global moderate settings
check_untyped_defs = True
warn_redundant_casts = True
warn_unused_ignores = True

# Service: Auth (strict)
[mypy-services.auth.*]
strict = True

[mypy.plugins.django-stubs.auth]
django_settings_module = services.auth.settings

# Service: API (strict)
[mypy-services.api.*]
strict = True

[mypy.plugins.django-stubs.api]
django_settings_module = services.api.settings

# Service: Worker (moderate)
[mypy-services.worker.*]
disallow_untyped_defs = True

# Shared libraries (very strict)
[mypy-shared.*]
strict = True
disallow_any_expr = True

# Tests across all services
[mypy-*.tests.*]
disallow_untyped_defs = False

# Migrations across all services
[mypy-*.migrations.*]
ignore_errors = True
```

**Directory structure:**
```
monorepo/
├── mypy.ini
├── services/
│   ├── auth/
│   │   ├── myapp/
│   │   └── settings.py
│   ├── api/
│   │   ├── myapp/
│   │   └── settings.py
│   └── worker/
│       └── tasks.py
└── shared/
    ├── utils/
    └── models/
```

**Usage:**
```bash
# Check all services
mypy services/

# Check specific service
mypy services/auth/

# Check shared libraries
mypy shared/
```

### Microservices

Each service has its own `mypy.ini`:

**services/auth/mypy.ini:**
```ini
[mypy]
python_version = 3.11
plugins = mypy_django_plugin.main

strict = True

[mypy.plugins.django-stubs]
django_settings_module = settings

[mypy-tests.*]
disallow_untyped_defs = False

[mypy-migrations.*]
ignore_errors = True
```

**services/api/mypy.ini:**
```ini
[mypy]
python_version = 3.11
plugins =
    mypy_django_plugin.main,
    mypy_drf_plugin.main

strict = True

[mypy.plugins.django-stubs]
django_settings_module = settings

[mypy-tests.*]
disallow_untyped_defs = False

[mypy-migrations.*]
ignore_errors = True
```

**Root mypy.ini (for CI):**
```ini
[mypy]
python_version = 3.11

# Check all services together
mypy_path =
    $MYPY_CONFIG_FILE_DIR/services/auth,
    $MYPY_CONFIG_FILE_DIR/services/api,
    $MYPY_CONFIG_FILE_DIR/services/worker

# Global settings
check_untyped_defs = True
```

---

## Troubleshooting

### Common Issues

#### Issue 1: "Cannot find implementation or library stub"

**Error:**
```
error: Cannot find implementation or library stub for module named "django"
```

**Solution:**
```bash
# Install django-stubs
pip install django-stubs

# Verify installation
pip show django-stubs

# Clear cache and retry
rm -rf .mypy_cache
mypy .
```

#### Issue 2: "Module has no attribute"

**Error:**
```
error: Module "django.db.models" has no attribute "CharField"
```

**Solution:**
```ini
# Ensure plugin is loaded
[mypy]
plugins = mypy_django_plugin.main

[mypy.plugins.django-stubs]
django_settings_module = myproject.settings
```

#### Issue 3: Settings module not found

**Error:**
```
Error: Django settings module "myproject.settings" not found
```

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
mypy .

# Or in mypy.ini
[mypy]
mypy_path = $MYPY_CONFIG_FILE_DIR
```

#### Issue 4: Slow performance

**Symptoms:** Mypy takes >1 minute to run

**Solutions:**
```ini
# Enable caching
[mypy]
incremental = True
sqlite_cache = True
cache_fine_grained = True

# Use daemon mode
dmypy start -- --config-file mypy.ini
dmypy check .

# Reduce follow_imports
[mypy-third_party.*]
follow_imports = skip
```

#### Issue 5: Cache corruption

**Error:**
```
error: Internal error: cache is corrupted
```

**Solution:**
```bash
# Clear cache
rm -rf .mypy_cache

# Disable cache temporarily
mypy --no-incremental .

# Re-enable cache
mypy .
```

#### Issue 6: Type stubs version mismatch

**Error:**
```
error: Incompatible types in assignment (expression has type "int", variable has type "str")
```

**Solution:**
```bash
# Check versions
pip list | grep -E "(mypy|django-stubs)"

# Update to compatible versions
pip install --upgrade mypy django-stubs

# Pin versions
pip install mypy==1.11.2 django-stubs==5.1.0
```

### Debug Mode

**Enable verbose output:**

```bash
# Verbose mode
mypy -v .

# Very verbose
mypy -vv .

# Show traceback
mypy --show-traceback .

# Debug cache
mypy --verbose --dump-graph .
```

### Plugin Debug

**Test plugin loading:**

```python
# test_plugin.py
from mypy_django_plugin.main import plugin

print(f"Plugin version: {plugin.__version__}")
print(f"Plugin loaded successfully")
```

```bash
python test_plugin.py
```

### Configuration Validation

**Validate mypy.ini:**

```bash
# Check for unused configs
mypy --warn-unused-configs .

# Show effective configuration
mypy --show-config .
```

---

## Best Practices

### 1. Start Small, Grow Strict

```ini
# Week 1: Permissive
[mypy]
check_untyped_defs = True

# Week 2-4: Moderate
[mypy]
disallow_untyped_defs = True

# Week 5+: Strict
[mypy]
strict = True
```

### 2. Use Per-Module Configuration

```ini
[mypy]
# Global permissive

[mypy-core.*]
# Critical code is strict
strict = True

[mypy-utils.*]
# Utils are moderate
disallow_untyped_defs = True

[mypy-legacy.*]
# Legacy stays permissive
disallow_untyped_defs = False
```

### 3. Ignore Generated Code

```ini
[mypy-*.migrations.*]
ignore_errors = True

[mypy-*.pb2]  # Protobuf
ignore_errors = True

[mypy-*_pb2_grpc]  # gRPC
ignore_errors = True
```

### 4. Use Type Comments for Python <3.6

```python
from typing import List, Optional

def get_users():
    # type: () -> List[str]
    return ["alice", "bob"]

user = None  # type: Optional[str]
```

### 5. Leverage reveal_type() for Debugging

```python
from django.contrib.auth.models import User

user = User.objects.get(id=1)
reveal_type(user)  # Revealed type is "User"
reveal_type(user.username)  # Revealed type is "str"
```

### 6. Use assert_type() for Tests

```python
from typing import assert_type
from django.db.models import QuerySet

users: QuerySet[User] = User.objects.all()
assert_type(users, QuerySet[User])
```

### 7. Document Type Ignores

```python
# Bad
result = some_function()  # type: ignore

# Good
result = some_function()  # type: ignore[attr-defined]  # Missing stub for library

# Better
result = some_function()  # type: ignore[attr-defined]  # TODO: Create stub for library (TICKET-123)
```

### 8. Use pyproject.toml for Modern Projects

```toml
[tool.mypy]
python_version = "3.11"
plugins = ["mypy_django_plugin.main"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = "*.migrations.*"
ignore_errors = true
```

### 9. Integrate with Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies:
          - django-stubs
        args: [--config-file=mypy.ini]
```

### 10. Monitor Type Coverage Over Time

```bash
# Generate coverage report
mypy --html-report reports/html .

# Track in CI
echo "TYPE_COVERAGE=$(grep -oP '\d+%' reports/html/index.html | head -1)" >> $GITHUB_ENV
```

### 11. Use Strict for New Code

```ini
# Global permissive
[mypy]
disallow_untyped_defs = False

# Strict for new feature
[mypy-new_feature.*]
strict = True
```

### 12. Create Custom Type Stubs

**stubs/untyped_library/__init__.pyi:**
```python
from typing import Any

class Client:
    def __init__(self, api_key: str) -> None: ...
    def get(self, path: str) -> dict[str, Any]: ...
```

**mypy.ini:**
```ini
[mypy]
mypy_path = $MYPY_CONFIG_FILE_DIR/stubs
```

---

## Additional Resources

### Official Documentation

- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Django-stubs GitHub](https://github.com/typeddjango/django-stubs)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 561 – Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)

### Community Resources

- [typeddjango/django-stubs](https://github.com/typeddjango/django-stubs) - Django type stubs
- [typeddjango/djangorestframework-stubs](https://github.com/typeddjango/djangorestframework-stubs) - DRF stubs
- [Mypy Playground](https://mypy-play.net/) - Interactive mypy testing

### Tools

- [monkeytype](https://github.com/Instagram/MonkeyType) - Generate type annotations from runtime types
- [pytype](https://google.github.io/pytype/) - Alternative type checker
- [pyre-check](https://pyre-check.org/) - Facebook's type checker

### Related Skills

- **Django Type Annotations Reference** - Comprehensive guide to typing Django code
- **Type Testing Patterns** - Testing strategies for typed Django code
- **Common Type Errors** - Solutions to frequent typing issues

---

## Changelog

**v1.0 (October 2025)**
- Initial comprehensive reference
- Coverage of mypy 1.11+ and django-stubs 5.1+
- Added CI/CD integration examples
- Performance optimization section
- Multiple project size configurations

---

## Contributing

This reference is maintained as part of the Django typing skills collection. For updates or corrections, please:

1. Test configurations with current versions
2. Provide real-world examples
3. Include performance benchmarks where relevant
4. Document version compatibility

---

**End of Reference Document**

*Total Lines: ~1,500*
*Last Updated: October 17, 2025*

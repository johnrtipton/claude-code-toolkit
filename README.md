# Claude Code Toolkit

Professional toolkit of Claude Code skills for Django development, multi-tenant architecture, and software engineering best practices.

> **Note:** This marketplace contains **plugins** (collections of related skills). When you install a plugin like `django-skills`, you get all the individual skills in that collection.

## Available Plugins

### django-skills

Collection of Django development skills including comprehensive best practices for multi-tenant architecture, security hardening, and type safety.

**Features:**
- Templates for creating tenant-aware models
- Admin interface patterns with query optimization
- Comprehensive test suites with tenant isolation
- Django migration best practices and patterns
- Migration helper script with validation
- OWASP Top 10 security patterns for Django
- Automated security auditor (settings, code, dependencies, multi-tenant)
- Production-ready security settings templates
- Custom security middleware examples
- Comprehensive security test templates
- Type safety with mypy and django-stubs
- Automated type checker with helpful error explanations
- Type hint generator for existing Django code
- Mypy configuration validator
- Comprehensive typing patterns for models, views, forms, DRF
- Advanced typing patterns (Protocols, Generics, TypedDict)
- Reference documentation for multi-tenant patterns, security, and typing
- Code generation scripts

**Use when:**
- Creating new Django models
- Building admin interfaces
- Writing tests for Django applications
- Creating or managing Django migrations
- Working with multi-tenant data isolation
- Optimizing Django queries
- Securing Django applications for production
- Auditing Django projects for security vulnerabilities
- Implementing OWASP Top 10 protections
- Managing secrets and sensitive configuration
- Adding type hints to Django code
- Configuring mypy for Django projects
- Debugging mypy errors in Django
- Implementing type-safe patterns with DRF
- Setting up pre-commit hooks for type checking

## Installation

### Add this marketplace to Claude Code:

```bash
/plugin marketplace add https://github.com/johnrtipton/claude-code-toolkit
```

### List available plugins:

```bash
/plugin marketplace list claude-code-toolkit
```

### Install the Django skills plugin:

```bash
/plugin install django-skills
```

This installs the Django skills collection, which includes:
- `django-best-practices` - Multi-tenant architecture patterns and templates
- `django-security` - Security best practices and automated security auditing
- `django-typing` - Type safety with mypy, django-stubs, and automated type checking

### Or install directly from local path:

```bash
# For development - install from local directory
cd ~/claude-code-toolkit
/plugin install .
```

## Updating

To get the latest updates and new features (like the recently added migration patterns):

```bash
# Update all plugins from all marketplaces
/plugin update

# Or update a specific plugin
/plugin update django-skills
```

After updating, the new features and improvements will be immediately available. Recent updates include:
- Django typing and mypy integration with automated tools
- Type hint generator for existing Django code
- Comprehensive typing patterns for DRF and multi-tenant architectures
- Django security best practices and OWASP Top 10 patterns
- Automated security auditor with multi-mode scanning
- Django migration best practices and patterns
- Migration helper script with validation
- Data migration templates and checklists

## Usage

Once installed, the skills will automatically activate when relevant. For example:

- "Create a new Django model for notifications"
- "Show me the admin interface pattern"
- "How do I test tenant isolation?"
- "Help me create a data migration"
- "Validate my migrations for multi-tenant best practices"
- "Audit my Django project for security vulnerabilities"
- "Show me how to secure my Django settings for production"
- "How do I protect against SQL injection in Django?"
- "Add type hints to my Django models"
- "Set up mypy for my Django project"
- "How do I type Django REST Framework serializers?"
- "Fix this mypy error in my Django view"
- "Generate type hints for my existing Django code"

## Development

### Adding New Skills

1. Create a new directory in `skills/`
2. Add a `SKILL.md` file with YAML frontmatter
3. Add any scripts, references, or assets
4. Update `.claude-plugin/marketplace.json` with the new skill
5. Push to GitHub

### Repository Structure

```
claude-code-toolkit/
├── .claude-plugin/
│   └── marketplace.json   # Marketplace metadata (required)
├── skills/
│   └── your-skill-name/
│       ├── SKILL.md       # Main skill file (required)
│       ├── scripts/       # Executable code (optional)
│       ├── references/    # Documentation (optional)
│       └── assets/        # Templates/files (optional)
└── README.md
```

## Plugins in This Marketplace

### django-skills (v1.0.0)

Collection of Django development skills for multi-tenant applications.

#### Included Skills:

**django-best-practices** - Django patterns and best practices for multi-tenant applications.

**Includes:**
- Multi-tenant architecture guide
- Model patterns and validation
- Admin interface optimization
- Django migration patterns and best practices
- Testing strategies
- Code generation scripts
- Migration helper with validation
- Copy-paste templates

**django-security** - Security hardening and vulnerability detection for Django applications.

**Includes:**
- OWASP Top 10 for Django guide (1,000+ lines)
- Automated security auditor (settings, code, dependencies, multi-tenant)
- Django security settings reference (900+ lines)
- Multi-tenant security patterns (900+ lines)
- Secrets management guide (800+ lines)
- Production-ready settings template
- Custom security middleware templates
- Comprehensive security test templates
- Pre-deployment security checklist

**django-typing** - Type safety and mypy best practices for Django applications.

**Includes:**
- Complete Django typing guide (2,400+ lines)
- Mypy configuration guide (1,500+ lines)
- DRF typing patterns (2,400+ lines)
- Advanced typing patterns (2,500+ lines) - Protocols, Generics, TypedDict
- Multi-tenant typing guide (3,000+ lines)
- Troubleshooting guide (3,300+ lines) - Common mypy errors and solutions
- Automated typing checker with Django-specific error explanations
- Type hint generator (auto-add hints to existing code)
- Configuration validator (validates mypy setup)
- Production-ready mypy.ini and pyproject.toml templates
- Pre-commit hook configuration
- Fully typed model, view, serializer, and manager templates

## Contributing

To add a skill to this marketplace:

1. Fork this repository
2. Create your skill in `skills/your-skill-name/`
3. Update `marketplace.json`
4. Submit a pull request

## License

[Your License Here]

# Claude Code Toolkit

Professional toolkit of Claude Code skills for Django development, multi-tenant architecture, and software engineering best practices.

> **Note:** This marketplace contains **plugins** (collections of related skills). When you install a plugin like `django-skills`, you get all the individual skills in that collection.

## Available Plugins

### django-skills

Collection of Django development skills including comprehensive best practices for multi-tenant architecture.

**Features:**
- Templates for creating tenant-aware models
- Admin interface patterns with query optimization
- Comprehensive test suites with tenant isolation
- Django migration best practices and patterns
- Migration helper script with validation
- Reference documentation for multi-tenant patterns
- Code generation scripts

**Use when:**
- Creating new Django models
- Building admin interfaces
- Writing tests for Django applications
- Creating or managing Django migrations
- Working with multi-tenant data isolation
- Optimizing Django queries

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

## Contributing

To add a skill to this marketplace:

1. Fork this repository
2. Create your skill in `skills/your-skill-name/`
3. Update `marketplace.json`
4. Submit a pull request

## License

[Your License Here]

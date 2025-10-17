# Claude Code Toolkit

Professional toolkit of Claude Code skills for Django development, multi-tenant architecture, and software engineering best practices.

## Available Skills

### django-best-practices

Comprehensive Django best practices skill for multi-tenant architecture.

**Features:**
- Templates for creating tenant-aware models
- Admin interface patterns with query optimization
- Comprehensive test suites with tenant isolation
- Reference documentation for multi-tenant patterns
- Code generation scripts

**Use when:**
- Creating new Django models
- Building admin interfaces
- Writing tests for Django applications
- Working with multi-tenant data isolation
- Optimizing Django queries

## Installation

### Add this marketplace to Claude Code:

```bash
/plugin marketplace add https://github.com/johnrtipton/claude-code-toolkit
```

### Install the skill:

```bash
/plugin install django-best-practices
```

### Or install directly from local path:

```bash
/plugin install /path/to/claude-code-toolkit/skills/django-best-practices
```

## Usage

Once installed, the skills will automatically activate when relevant. For example:

- "Create a new Django model for notifications"
- "Show me the admin interface pattern"
- "How do I test tenant isolation?"

## Development

### Adding New Skills

1. Create a new directory in `skills/`
2. Add a `SKILL.md` file with YAML frontmatter
3. Add any scripts, references, or assets
4. Update `marketplace.json` with the new skill
5. Push to GitHub

### Skill Structure

```
skills/
└── your-skill-name/
    ├── SKILL.md           # Main skill file (required)
    ├── scripts/           # Executable code (optional)
    ├── references/        # Documentation (optional)
    └── assets/            # Templates/files (optional)
```

## Skills in This Marketplace

### django-best-practices (v1.0.0)

Django patterns and best practices for multi-tenant applications.

**Includes:**
- Multi-tenant architecture guide
- Model patterns and validation
- Admin interface optimization
- Testing strategies
- Code generation scripts
- Copy-paste templates

## Contributing

To add a skill to this marketplace:

1. Fork this repository
2. Create your skill in `skills/your-skill-name/`
3. Update `marketplace.json`
4. Submit a pull request

## License

[Your License Here]

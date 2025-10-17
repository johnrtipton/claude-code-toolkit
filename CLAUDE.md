# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code plugin marketplace containing professional Django development skills. The repository follows the Claude Code plugin marketplace structure and distributes skills/plugins that can be installed by Claude Code users.

## Repository Structure

```
claude-code-toolkit/
├── .claude-plugin/
│   └── marketplace.json   # Marketplace metadata (defines plugins and skills)
├── skills/
│   └── django-best-practices/
│       ├── SKILL.md       # Main skill file with YAML frontmatter
│       ├── scripts/       # Code generation scripts (generate_model.py)
│       ├── references/    # Detailed documentation (multi-tenant, model, admin patterns)
│       └── assets/        # Templates (model_template.py, admin_template.py, test_template.py)
└── README.md
```

## Plugin Marketplace Structure

This repository is a **marketplace** that contains **plugins**, which in turn contain **skills**:

- **Marketplace**: `claude-code-toolkit` (this repo)
  - **Plugin**: `django-skills` (collection of Django-related skills)
    - **Skill**: `django-best-practices` (multi-tenant Django patterns)

The `.claude-plugin/marketplace.json` file defines all plugins and their associated skills.

## Key Files

### .claude-plugin/marketplace.json
- Defines marketplace metadata (name, owner, description, version)
- Lists all plugins available in this marketplace
- Each plugin specifies its skills (paths to SKILL.md files)
- Must match Claude Code's marketplace schema

### skills/*/SKILL.md
- Each skill requires a SKILL.md file with YAML frontmatter
- Frontmatter must include: `name` and `description`
- The description determines when Claude Code automatically activates the skill
- Body contains the full skill instructions/documentation

## Django Best Practices Skill

The main skill in this repo provides Django multi-tenant architecture patterns:

### Core Concepts
- All models inherit from `TenantBaseModel` or `TenantAwareModel`
- Multi-tenant data isolation enforced at database and application layers
- Tenant context set by middleware from authenticated user
- QuerySets automatically filtered by current tenant
- Indexes always put `tenant` field first in composite indexes
- Unique constraints include `tenant` field

### Quick Reference
- **Templates**: `skills/django-best-practices/assets/` - Copy-paste templates for models, admin, tests
- **References**: `skills/django-best-practices/references/` - Detailed pattern documentation
- **Generator**: `skills/django-best-practices/scripts/generate_model.py` - Boilerplate code generation

### Code Generation
```bash
python skills/django-best-practices/scripts/generate_model.py <app_name> <model_name> [--with-admin] [--with-tests]
```

## Adding New Skills

1. Create directory: `skills/your-skill-name/`
2. Create `SKILL.md` with YAML frontmatter (name and description required)
3. Add optional directories: `scripts/`, `references/`, `assets/`
4. Update `.claude-plugin/marketplace.json`:
   - Add to existing plugin's `skills` array, OR
   - Create new plugin entry with the skill

## Installation Commands (for users)

```bash
# Add marketplace
/plugin marketplace add https://github.com/johnrtipton/claude-code-toolkit

# List plugins
/plugin marketplace list claude-code-toolkit

# Install plugin
/plugin install django-skills
```

## Development Workflow

When making changes to skills:

1. Edit the SKILL.md file or add/update references
2. Test that YAML frontmatter is valid
3. Update marketplace.json if adding/removing skills
4. Update README.md to reflect changes
5. Commit with descriptive message
6. Push to GitHub (users pull updates when they sync)

## Important Notes

- No build/test commands - this is a documentation/template repository
- Skills are loaded directly by Claude Code when installed
- Changes pushed to GitHub are picked up when users run `/plugin update`
- The marketplace.json schema must match Claude Code's requirements
- Each skill's description should clearly indicate when it applies (Claude uses this for auto-activation)

# Django Migration Patterns

Comprehensive guide to Django migrations, covering schema changes, data migrations, multi-tenant patterns, and troubleshooting.

## Overview

Django migrations are version control for your database schema. They allow you to:
- Track schema changes over time
- Apply changes consistently across environments
- Reverse changes when needed
- Transform data safely during schema updates

**Key Principles:**
1. Always review generated migrations before committing
2. Test migrations in both directions (forward and backward)
3. Keep migrations small and focused
4. Never edit applied migrations
5. Use data migrations for complex transformations
6. Consider multi-tenant implications for every migration

## Migration Workflow

### Basic Workflow

```bash
# 1. Make model changes
# Edit your models.py

# 2. Generate migration
python manage.py makemigrations

# 3. Review the generated migration
# Check the migration file in app/migrations/

# 4. Test the migration
python manage.py migrate

# 5. Test reversibility
python manage.py migrate app_name previous_migration_name

# 6. Re-apply
python manage.py migrate
```

### Multi-App Workflow

```bash
# Generate migrations for specific app
python manage.py makemigrations app_name

# Generate migrations for all apps
python manage.py makemigrations

# Show what migrations would be created (dry run)
python manage.py makemigrations --dry-run --verbosity 3

# Create empty migration for custom operations
python manage.py makemigrations --empty app_name
```

## Schema Migrations

### Adding Fields

**Auto-generated migrations work well for most cases:**

```python
# models.py - Add new field
class MyModel(TenantAwareModel):
    name = models.CharField(max_length=200)
    email = models.EmailField()  # New field
```

**Review the generated migration:**

```python
# migrations/0002_add_email.py
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mymodel',
            name='email',
            field=models.EmailField(default=''),  # Check default!
            preserve_default=False,
        ),
    ]
```

**For fields with no default, provide one:**

```python
# Option 1: Provide default in model
class MyModel(TenantAwareModel):
    email = models.EmailField(default='noreply@example.com')

# Option 2: Allow null temporarily, then populate
class MyModel(TenantAwareModel):
    email = models.EmailField(null=True, blank=True)
```

### Removing Fields

**Two-step process for production safety:**

```python
# Step 1: Make field nullable and stop using it in code
class MyModel(TenantAwareModel):
    name = models.CharField(max_length=200)
    old_field = models.CharField(max_length=100, null=True)  # Added null=True
```

```bash
# Deploy this change, wait for all servers to update
python manage.py makemigrations
python manage.py migrate
```

```python
# Step 2: Remove field entirely (in next release)
class MyModel(TenantAwareModel):
    name = models.CharField(max_length=200)
    # old_field removed
```

```bash
# Deploy removal
python manage.py makemigrations
python manage.py migrate
```

### Renaming Fields

**Use RenameField operation:**

```bash
# Django can detect renames if you answer 'yes' to the prompt
python manage.py makemigrations
# Did you rename mymodel.old_name to mymodel.new_name? [y/N] y
```

**Generated migration:**

```python
class Migration(migrations.Migration):
    operations = [
        migrations.RenameField(
            model_name='mymodel',
            old_name='old_name',
            new_name='new_name',
        ),
    ]
```

**Manual creation if Django doesn't detect:**

```python
class Migration(migrations.Migration):
    operations = [
        migrations.RenameField(
            model_name='mymodel',
            old_name='old_field',
            new_name='new_field',
        ),
    ]
```

### Altering Fields

**Be careful with data loss:**

```python
# Changing field type - may lose data!
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name='mymodel',
            name='count',
            field=models.IntegerField(),  # Was CharField
        ),
    ]
```

**Safe approach for type changes:**

```python
# Step 1: Add new field
migrations.AddField(
    model_name='mymodel',
    name='count_int',
    field=models.IntegerField(null=True),
)

# Step 2: Data migration to populate new field (see Data Migrations section)

# Step 3: Remove old field
migrations.RemoveField(
    model_name='mymodel',
    name='count',
)

# Step 4: Rename new field
migrations.RenameField(
    model_name='mymodel',
    old_name='count_int',
    new_name='count',
)
```

### Adding Indexes

**Critical for multi-tenant: Always put tenant first!**

```python
# models.py
class MyModel(TenantAwareModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'user', '-created_at']),  # Tenant first!
            models.Index(fields=['tenant', 'status']),
        ]
```

**Generated migration:**

```python
class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='mymodel',
            index=models.Index(fields=['tenant', 'user', '-created_at'], name='myapp_mymodel_tenant_user_idx'),
        ),
    ]
```

**For large tables, use concurrent index creation (PostgreSQL):**

```python
from django.contrib.postgres.operations import AddIndexConcurrently

class Migration(migrations.Migration):
    atomic = False  # Required for concurrent operations

    operations = [
        AddIndexConcurrently(
            model_name='mymodel',
            index=models.Index(fields=['tenant', 'status'], name='myapp_mymodel_tenant_status_idx'),
        ),
    ]
```

### Adding Constraints

**Unique constraints with tenant:**

```python
# models.py
class MyModel(TenantAwareModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    slug = models.SlugField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'workspace', 'slug'],
                name='unique_mymodel_slug'
            ),
        ]
```

**Check constraints:**

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(start_date__lte=models.F('end_date')),
            name='check_date_range'
        ),
    ]
```

## Data Migrations

### Creating Data Migrations

**Create empty migration:**

```bash
python manage.py makemigrations --empty myapp --name populate_email_field
```

**Use RunPython for data transformations:**

```python
# migrations/0003_populate_email_field.py
from django.db import migrations

def populate_emails(apps, schema_editor):
    """Populate email field from username."""
    MyModel = apps.get_model('myapp', 'MyModel')
    db_alias = schema_editor.connection.alias

    # Update in batches for large datasets
    batch_size = 1000
    objects = MyModel.objects.using(db_alias).filter(email__isnull=True)

    for obj in objects.iterator(chunk_size=batch_size):
        obj.email = f"{obj.username}@example.com"
        obj.save(update_fields=['email'])

def reverse_populate_emails(apps, schema_editor):
    """Reverse operation - clear emails."""
    MyModel = apps.get_model('myapp', 'MyModel')
    db_alias = schema_editor.connection.alias
    MyModel.objects.using(db_alias).update(email='')

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0002_add_email'),
    ]

    operations = [
        migrations.RunPython(populate_emails, reverse_populate_emails),
    ]
```

### Data Migration Best Practices

**1. Always use apps.get_model():**

```python
# ✅ Good - uses historical model
def forward(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')
    for obj in MyModel.objects.all():
        obj.status = 'active'
        obj.save()

# ❌ Bad - imports current model
from myapp.models import MyModel  # Don't do this!
```

**2. Batch large updates:**

```python
def forward(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')

    # For very large datasets
    batch_size = 1000
    for obj in MyModel.objects.iterator(chunk_size=batch_size):
        obj.process()
        obj.save()

    # Or use bulk operations
    objects_to_update = []
    for obj in MyModel.objects.all():
        obj.status = 'active'
        objects_to_update.append(obj)

        if len(objects_to_update) >= batch_size:
            MyModel.objects.bulk_update(objects_to_update, ['status'])
            objects_to_update = []

    if objects_to_update:
        MyModel.objects.bulk_update(objects_to_update, ['status'])
```

**3. Make migrations reversible:**

```python
def forward(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')
    MyModel.objects.filter(status='old').update(status='new')

def reverse(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')
    MyModel.objects.filter(status='new').update(status='old')

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forward, reverse),
    ]
```

**4. Handle missing data gracefully:**

```python
def forward(apps, schema_editor):
    MyModel = apps.get_model('myapp', 'MyModel')

    for obj in MyModel.objects.all():
        if obj.old_field:  # Check before using
            obj.new_field = obj.old_field.upper()
            obj.save(update_fields=['new_field'])
```

### Using RunSQL

**For complex SQL operations:**

```python
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            # Forward SQL
            sql="""
                UPDATE myapp_mymodel
                SET status = 'active'
                WHERE created_at > NOW() - INTERVAL '30 days'
            """,
            # Reverse SQL
            reverse_sql="""
                UPDATE myapp_mymodel
                SET status = 'inactive'
                WHERE created_at > NOW() - INTERVAL '30 days'
            """,
        ),
    ]
```

**For database-specific operations:**

```python
operations = [
    migrations.RunSQL(
        sql="CREATE INDEX CONCURRENTLY idx_name ON myapp_mymodel (tenant_id, user_id);",
        reverse_sql="DROP INDEX CONCURRENTLY idx_name;",
    ),
]
```

## Multi-Tenant Migration Patterns

### Adding Tenant Support to Existing Models

**Pattern from multi-tenant-patterns.md - 4-step process:**

#### Step 1: Add Nullable Tenant FK

```python
class Migration(migrations.Migration):
    dependencies = [('myapp', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='mymodel',
            name='tenant',
            field=models.ForeignKey(
                'users.Tenant',
                on_delete=models.CASCADE,
                null=True,  # Nullable for migration
                blank=True
            ),
        ),
    ]
```

#### Step 2: Assign Default Tenant (Data Migration)

```python
def assign_default_tenant(apps, schema_editor):
    Tenant = apps.get_model('users', 'Tenant')
    MyModel = apps.get_model('myapp', 'MyModel')

    # Get or create default tenant
    default_tenant, _ = Tenant.objects.get_or_create(
        slug='default',
        defaults={'name': 'Default Organization'}
    )

    # Assign to all existing records
    MyModel.objects.filter(tenant__isnull=True).update(tenant=default_tenant)

class Migration(migrations.Migration):
    dependencies = [('myapp', '0002_add_tenant_field')]

    operations = [
        migrations.RunPython(assign_default_tenant, migrations.RunPython.noop),
    ]
```

#### Step 3: Make Tenant Required

```python
class Migration(migrations.Migration):
    dependencies = [('myapp', '0003_assign_default_tenant')]

    operations = [
        migrations.AlterField(
            model_name='mymodel',
            name='tenant',
            field=models.ForeignKey(
                'users.Tenant',
                on_delete=models.CASCADE,
                null=False  # Now required
            ),
        ),
    ]
```

#### Step 4: Add Tenant-First Indexes

```python
class Migration(migrations.Migration):
    dependencies = [('myapp', '0004_make_tenant_required')]

    operations = [
        # Add tenant-first indexes
        migrations.AddIndex(
            model_name='mymodel',
            index=models.Index(
                fields=['tenant', 'user', '-created_at'],
                name='myapp_mymodel_tenant_user_idx'
            ),
        ),
        # Update unique constraints to include tenant
        migrations.AddConstraint(
            model_name='mymodel',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'slug'],
                name='myapp_mymodel_unique_tenant_slug'
            ),
        ),
    ]
```

### Migrating Data Between Tenants

**Rarely needed, but when required:**

```python
def move_data_to_new_tenant(apps, schema_editor):
    """Move specific records to a new tenant."""
    Tenant = apps.get_model('users', 'Tenant')
    MyModel = apps.get_model('myapp', 'MyModel')

    old_tenant = Tenant.objects.get(slug='old-tenant')
    new_tenant = Tenant.objects.get(slug='new-tenant')

    # Move specific records
    MyModel.objects.filter(
        tenant=old_tenant,
        user__email__endswith='@newcompany.com'
    ).update(tenant=new_tenant)

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(
            move_data_to_new_tenant,
            migrations.RunPython.noop  # Usually not reversible
        ),
    ]
```

## Migration Dependencies and Ordering

### Specifying Dependencies

```python
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0003_previous_migration'),
        ('apping', '0002_required_migration'),  # Cross-app dependency
    ]

    operations = [...]
```

### Handling Circular Dependencies

**Problem: App A needs migration from App B, which needs migration from App A**

**Solution: Split into smaller migrations**

```python
# app_a/migrations/0002_step1.py
class Migration(migrations.Migration):
    dependencies = [
        ('app_a', '0001_initial'),
        # Don't depend on app_b yet
    ]
    operations = [
        # Part 1 of changes
    ]

# app_b/migrations/0002_step1.py
class Migration(migrations.Migration):
    dependencies = [
        ('app_b', '0001_initial'),
        ('app_a', '0002_step1'),  # Now we can depend on app_a
    ]
    operations = [
        # Part 1 of changes
    ]

# app_a/migrations/0003_step2.py
class Migration(migrations.Migration):
    dependencies = [
        ('app_a', '0002_step1'),
        ('app_b', '0002_step1'),  # Now we can depend on app_b
    ]
    operations = [
        # Part 2 of changes
    ]
```

### Run Before Dependencies

```python
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0002_previous'),
    ]

    run_before = [
        ('otherapp', '0003_needs_this_first'),
    ]

    operations = [...]
```

## Reversible Migrations

### Making Operations Reversible

**Most schema operations are automatically reversible:**

```python
# These are automatically reversible
migrations.AddField(...)      # Reverse: RemoveField
migrations.RemoveField(...)   # Reverse: AddField
migrations.AlterField(...)    # Reverse: AlterField (to original)
migrations.RenameField(...)   # Reverse: RenameField (swap names)
```

**Data migrations need explicit reverse:**

```python
class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(
            forward_func,
            reverse_func,  # Must provide
        ),
    ]
```

**Mark irreversible when appropriate:**

```python
operations = [
    migrations.RunPython(
        forward_func,
        reverse_code=migrations.RunPython.noop,  # Irreversible
    ),
]
```

### Testing Reversibility

```bash
# Apply migration
python manage.py migrate myapp 0005_my_migration

# Reverse it
python manage.py migrate myapp 0004_previous_migration

# Re-apply
python manage.py migrate myapp 0005_my_migration

# Check for errors at each step
```

## Testing Migrations

### Unit Testing Migrations

```python
# tests/test_migrations.py
from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

class TestMigration(TransactionTestCase):
    """Test data migration."""

    migrate_from = ('myapp', '0002_add_field')
    migrate_to = ('myapp', '0003_populate_field')

    def setUp(self):
        # Get migration executor
        self.executor = MigrationExecutor(connection)

        # Migrate to state before migration
        self.executor.migrate([self.migrate_from])

        # Get historical models
        apps = self.executor.loader.project_state(self.migrate_from).apps
        self.MyModel = apps.get_model('myapp', 'MyModel')

        # Create test data
        self.obj = self.MyModel.objects.create(name='Test')

    def test_migration(self):
        # Run the migration
        self.executor.migrate([self.migrate_to])

        # Get current model
        from myapp.models import MyModel

        # Verify data was transformed correctly
        obj = MyModel.objects.get(id=self.obj.id)
        self.assertEqual(obj.new_field, 'expected_value')
```

### Integration Testing

```python
def test_migration_preserves_tenant_isolation():
    """Test that migration maintains multi-tenant isolation."""
    # Create data for two tenants
    tenant1 = Tenant.objects.create(name='Tenant 1', slug='t1')
    tenant2 = Tenant.objects.create(name='Tenant 2', slug='t2')

    set_current_tenant(tenant1)
    obj1 = MyModel.objects.create(name='T1 Object')

    set_current_tenant(tenant2)
    obj2 = MyModel.objects.create(name='T2 Object')

    # Run migration (if needed, or just verify post-migration state)

    # Verify isolation maintained
    set_current_tenant(tenant1)
    assert MyModel.objects.count() == 1
    assert MyModel.objects.first().name == 'T1 Object'

    set_current_tenant(tenant2)
    assert MyModel.objects.count() == 1
    assert MyModel.objects.first().name == 'T2 Object'
```

## Squashing Migrations

### When to Squash

Squash when:
- Many small migrations accumulated
- Migration history is getting long
- Want to optimize migration performance
- Starting fresh in a new branch

**Don't squash if:**
- Migrations already deployed to production
- Other developers have unapplied migrations

### Squashing Process

```bash
# Squash migrations 0002 through 0010 into one
python manage.py squashmigrations myapp 0002 0010

# Creates a new migration file like:
# 0002_squashed_0010_auto_TIMESTAMP.py
```

**Review the squashed migration:**

```python
# migrations/0002_squashed_0010_auto_TIMESTAMP.py
class Migration(migrations.Migration):
    replaces = [
        ('myapp', '0002_auto'),
        ('myapp', '0003_auto'),
        # ... through 0010
    ]

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        # Optimized operations
    ]
```

**Test thoroughly:**

```bash
# Test on fresh database
python manage.py migrate

# Test on database with old migrations
# (Django will skip the replaced migrations)
```

**After deploying squashed migration:**

```bash
# Once deployed everywhere, remove old migration files
# and update the squashed migration:
# Remove the 'replaces = [...]' line
```

## Troubleshooting Migrations

### Common Issues

#### Issue: Unapplied migration detected

```bash
# Check migration status
python manage.py showmigrations

# Shows something like:
# [X] 0001_initial
# [ ] 0002_add_field  # Unapplied
# [X] 0003_add_index  # Applied but depends on unapplied!
```

**Solution:**

```bash
# Apply missing migrations
python manage.py migrate

# If migrations are out of order, may need to fake
python manage.py migrate --fake myapp 0002_add_field
```

#### Issue: Conflicting migrations

```bash
python manage.py migrate
# Error: Conflicting migrations detected; multiple leaf nodes in the migration graph

# Check for conflicts
python manage.py showmigrations --plan
```

**Solution: Merge migrations**

```bash
# Create merge migration
python manage.py makemigrations --merge

# Reviews both branches and creates merge migration
```

**Generated merge migration:**

```python
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0003_branch_a'),
        ('myapp', '0003_branch_b'),
    ]

    operations = [
        # Usually empty, just merges dependencies
    ]
```

#### Issue: Migration fails partway through

**For atomic migrations (default):**
- PostgreSQL: Automatically rolls back
- MySQL/SQLite: May be partially applied

**Solution:**

```bash
# Check what was applied
python manage.py showmigrations

# If partially applied, may need to manually fix database
# Then fake the migration
python manage.py migrate --fake myapp 0003_failed_migration

# Or roll back and fix
python manage.py migrate myapp 0002_previous_migration
# Fix the migration file
python manage.py migrate
```

#### Issue: Fake migration needed

**When to use --fake:**
- Applied changes manually in database
- Recovering from failed migration
- Syncing migration history

```bash
# Mark migration as applied without running it
python manage.py migrate --fake myapp 0003_manual_changes

# Fake all migrations (for syncing existing database)
python manage.py migrate --fake
```

#### Issue: Inconsistent migration history

```bash
# Reset migration history (DANGEROUS - only for development)
python manage.py migrate --fake myapp zero
python manage.py migrate --fake-initial
```

### Debugging Migrations

**Show migration plan:**

```bash
# See what will be applied
python manage.py migrate --plan

# See SQL that will be executed
python manage.py sqlmigrate myapp 0003_add_field
```

**Verbose output:**

```bash
# See detailed migration output
python manage.py migrate --verbosity 3
```

**Check migration state:**

```bash
# List all migrations and their status
python manage.py showmigrations

# List for specific app
python manage.py showmigrations myapp

# Show in plan order
python manage.py showmigrations --plan
```

## Migration Best Practices Summary

### Always Do

1. ✅ **Review generated migrations** before committing
2. ✅ **Test reversibility** by migrating backward then forward
3. ✅ **Use data migrations** for complex transformations
4. ✅ **Put tenant first** in all multi-tenant indexes
5. ✅ **Batch large data updates** to avoid memory issues
6. ✅ **Provide reverse operations** for RunPython
7. ✅ **Use apps.get_model()** in data migrations
8. ✅ **Test migrations** on production-like data
9. ✅ **Keep migrations small** and focused
10. ✅ **Document complex migrations** with comments

### Never Do

1. ❌ **Never edit applied migrations** (create new one instead)
2. ❌ **Never delete migration files** that are deployed
3. ❌ **Never import models directly** in migrations (use apps.get_model)
4. ❌ **Never assume atomicity** on MySQL/SQLite for DDL
5. ❌ **Never skip testing** migrations on staging
6. ❌ **Never forget tenant field** when adding indexes/constraints
7. ❌ **Never use --fake** without understanding the implications
8. ❌ **Never run migrations manually** (use manage.py)

### Production Deployment Checklist

- [ ] Review migration for data loss risks
- [ ] Test on production-sized dataset
- [ ] Test reversibility
- [ ] Check for blocking operations (add indexes concurrently)
- [ ] Verify multi-tenant isolation maintained
- [ ] Plan for downtime if needed
- [ ] Have rollback plan ready
- [ ] Monitor migration execution
- [ ] Verify data integrity after migration
- [ ] Test application functionality

## Advanced Patterns

### Conditional Migrations

```python
def conditional_operation(apps, schema_editor):
    """Only run if condition is met."""
    MyModel = apps.get_model('myapp', 'MyModel')

    if MyModel.objects.filter(needs_update=True).exists():
        # Perform migration
        pass
    else:
        # Skip
        pass

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(conditional_operation),
    ]
```

### Migrations with Custom Database Functions

```python
from django.contrib.postgres.operations import CreateExtension

class Migration(migrations.Migration):
    operations = [
        # Enable PostgreSQL extension
        CreateExtension('pg_trgm'),

        # Use it in an index
        migrations.AddIndex(
            model_name='mymodel',
            index=GinIndex(
                fields=['name'],
                name='mymodel_name_trgm_idx',
                opclasses=['gin_trgm_ops'],
            ),
        ),
    ]
```

### Migrations for Partitioned Tables

```python
class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE myapp_mymodel_2024_01 PARTITION OF myapp_mymodel
                FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
            """,
            reverse_sql="DROP TABLE myapp_mymodel_2024_01;",
        ),
    ]
```

## Resources

- Django Migrations Documentation: https://docs.djangoproject.com/en/stable/topics/migrations/
- Django Migration Operations Reference: https://docs.djangoproject.com/en/stable/ref/migration-operations/
- PostgreSQL Concurrent Index Creation: https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY

# Data Migration Template
#
# This template provides a complete example of a Django data migration
# using RunPython with proper error handling, batching, and reversibility.
#
# To use:
# 1. Create an empty migration:
#    python manage.py makemigrations --empty yourapp --name your_migration_name
#
# 2. Replace the contents with this template
# 3. Customize the forward and reverse functions
# 4. Test thoroughly before deploying

from django.db import migrations


def forward(apps, schema_editor):
    """
    Forward data migration.

    Args:
        apps: Django apps registry with historical models
        schema_editor: Database schema editor

    Best Practices:
    - Always use apps.get_model() - never import models directly
    - Process large datasets in batches
    - Handle missing/null data gracefully
    - Add progress logging for long-running migrations
    - Make idempotent if possible (safe to run multiple times)
    """
    # Get historical model (not current model!)
    MyModel = apps.get_model('yourapp', 'YourModel')
    db_alias = schema_editor.connection.alias

    # Example 1: Simple update
    # -------------------------
    # Update a single field based on condition
    MyModel.objects.using(db_alias).filter(
        old_status='pending'
    ).update(
        new_status='active'
    )

    # Example 2: Complex transformation with batching
    # ------------------------------------------------
    # For large datasets, process in batches to avoid memory issues
    batch_size = 1000
    queryset = MyModel.objects.using(db_alias).filter(
        needs_update=True
    ).iterator(chunk_size=batch_size)

    updated_count = 0
    for obj in queryset:
        # Complex logic here
        if obj.old_field:
            obj.new_field = obj.old_field.upper()
            obj.save(update_fields=['new_field'])
            updated_count += 1

        # Optional: Log progress for long migrations
        if updated_count % 1000 == 0:
            print(f"Processed {updated_count} records...")

    print(f"✅ Updated {updated_count} records")

    # Example 3: Bulk operations for better performance
    # --------------------------------------------------
    objects_to_update = []

    for obj in MyModel.objects.using(db_alias).filter(needs_update=True):
        # Prepare changes
        obj.new_field = obj.old_field.upper()
        objects_to_update.append(obj)

        # Bulk update in batches
        if len(objects_to_update) >= batch_size:
            MyModel.objects.bulk_update(
                objects_to_update,
                ['new_field'],
                batch_size=batch_size
            )
            objects_to_update = []

    # Update remaining objects
    if objects_to_update:
        MyModel.objects.bulk_update(
            objects_to_update,
            ['new_field'],
            batch_size=batch_size
        )

    # Example 4: Multi-tenant data migration
    # ---------------------------------------
    # When working with multi-tenant models
    Tenant = apps.get_model('users', 'Tenant')

    for tenant in Tenant.objects.using(db_alias).all():
        # Process data for each tenant
        tenant_objects = MyModel.objects.using(db_alias).filter(
            tenant=tenant,
            needs_update=True
        )

        for obj in tenant_objects:
            # Apply tenant-specific logic
            obj.new_field = f"{tenant.slug}_{obj.old_field}"
            obj.save(update_fields=['new_field'])

    # Example 5: Creating related objects
    # ------------------------------------
    # When you need to create new records
    objects_to_create = []

    for obj in MyModel.objects.using(db_alias).filter(needs_migration=True):
        # Create related object
        new_obj = RelatedModel(
            my_model=obj,
            tenant=obj.tenant,  # Don't forget tenant!
            value=obj.old_value
        )
        objects_to_create.append(new_obj)

        if len(objects_to_create) >= batch_size:
            RelatedModel.objects.bulk_create(objects_to_create)
            objects_to_create = []

    if objects_to_create:
        RelatedModel.objects.bulk_create(objects_to_create)


def reverse(apps, schema_editor):
    """
    Reverse data migration.

    Makes the migration reversible. Important for testing and
    potential rollbacks.

    If migration is truly irreversible (e.g., data transformation
    loses information), document why and use:
        migrations.RunPython.noop

    Args:
        apps: Django apps registry with historical models
        schema_editor: Database schema editor
    """
    # Get historical model
    MyModel = apps.get_model('yourapp', 'YourModel')
    db_alias = schema_editor.connection.alias

    # Example: Reverse the transformation
    MyModel.objects.using(db_alias).filter(
        new_status='active'
    ).update(
        old_status='pending'
    )

    # Or for complex transformations:
    batch_size = 1000
    for obj in MyModel.objects.using(db_alias).iterator(chunk_size=batch_size):
        if obj.new_field:
            obj.old_field = obj.new_field.lower()
            obj.save(update_fields=['old_field'])


# Alternative: Reverse function that cannot undo changes
def reverse_irreversible(apps, schema_editor):
    """
    This migration cannot be reversed because [explain why].

    Examples:
    - Data was deleted
    - Transformation loses information (e.g., hashing)
    - Aggregation from multiple sources
    """
    pass  # Explicitly do nothing


class Migration(migrations.Migration):
    """
    [Describe what this migration does]

    Example:
    Migrates user email addresses from old_email field to new_email field,
    converting all emails to lowercase and validating format.

    Related to: [ticket/issue number if applicable]
    """

    dependencies = [
        # List migrations this depends on
        ('yourapp', '0001_previous_migration'),
        # Cross-app dependencies if needed
        # ('otherapp', '0002_some_migration'),
    ]

    operations = [
        migrations.RunPython(
            forward,
            reverse,  # Or: reverse_irreversible or migrations.RunPython.noop
        ),
    ]

    # Optional: For migrations that modify large datasets
    # Set atomic = False to avoid wrapping in transaction
    # WARNING: Non-atomic migrations can't be automatically rolled back
    # atomic = False


# Advanced Examples
# -----------------

def forward_with_error_handling(apps, schema_editor):
    """Forward migration with comprehensive error handling."""
    MyModel = apps.get_model('yourapp', 'YourModel')
    db_alias = schema_editor.connection.alias

    errors = []
    success_count = 0

    for obj in MyModel.objects.using(db_alias).all():
        try:
            # Attempt transformation
            if obj.old_field:
                obj.new_field = obj.old_field.upper()
                obj.save(update_fields=['new_field'])
                success_count += 1
        except Exception as e:
            # Log error but continue
            errors.append(f"Error processing {obj.id}: {e}")

    print(f"✅ Successfully migrated {success_count} records")
    if errors:
        print(f"⚠️  {len(errors)} errors occurred:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   {error}")


def forward_conditional(apps, schema_editor):
    """Forward migration with conditional logic."""
    MyModel = apps.get_model('yourapp', 'YourModel')
    db_alias = schema_editor.connection.alias

    # Only run if data exists
    if not MyModel.objects.using(db_alias).filter(needs_update=True).exists():
        print("ℹ️  No records to update, skipping...")
        return

    # Run migration
    count = MyModel.objects.using(db_alias).filter(
        needs_update=True
    ).update(
        new_field='updated'
    )

    print(f"✅ Updated {count} records")


def forward_with_progress(apps, schema_editor):
    """Forward migration with progress reporting."""
    from datetime import datetime

    MyModel = apps.get_model('yourapp', 'YourModel')
    db_alias = schema_editor.connection.alias

    total = MyModel.objects.using(db_alias).count()
    processed = 0
    start_time = datetime.now()

    batch_size = 1000
    for obj in MyModel.objects.using(db_alias).iterator(chunk_size=batch_size):
        # Process object
        obj.new_field = obj.old_field.upper()
        obj.save(update_fields=['new_field'])

        processed += 1

        # Report progress every 10%
        if processed % (total // 10) == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (total - processed) / rate if rate > 0 else 0

            print(f"Progress: {processed}/{total} ({processed*100//total}%) "
                  f"- {rate:.1f} records/sec "
                  f"- Est. {remaining/60:.1f} min remaining")

    print(f"✅ Migration complete! Processed {processed} records "
          f"in {(datetime.now() - start_time).total_seconds():.1f} seconds")


# Testing Your Data Migration
# ----------------------------
#
# 1. Test on development data:
#    python manage.py migrate yourapp 0XXX_your_migration
#
# 2. Test reversibility:
#    python manage.py migrate yourapp 0XXX_previous_migration
#
# 3. Re-apply to verify idempotency:
#    python manage.py migrate yourapp 0XXX_your_migration
#
# 4. Test on production-sized dataset in staging
#
# 5. Monitor performance and adjust batch sizes
#
# 6. Verify data integrity after migration:
#    - Check row counts
#    - Spot-check transformed data
#    - Run validation queries

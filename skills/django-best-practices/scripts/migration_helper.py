#!/usr/bin/env python3
"""
Django Migration Helper

Wraps Django migration commands with validation and best practice checks.
Helps ensure migrations follow multi-tenant patterns and Django best practices.

Usage:
    # Check migration status
    python migration_helper.py status

    # Create new migration with validation
    python migration_helper.py create [app_name]

    # Show migration plan
    python migration_helper.py plan

    # Validate existing migrations
    python migration_helper.py validate [app_name]

    # Check for conflicts
    python migration_helper.py check-conflicts
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any


class MigrationHelper:
    """Helper for Django migrations with validation."""

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize migration helper.

        Args:
            project_root: Path to Django project root (default: current directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        self.manage_py = self.project_root / "manage.py"

        if not self.manage_py.exists():
            print(f"❌ Error: manage.py not found in {self.project_root}")
            print("   Run this script from your Django project root.")
            sys.exit(1)

    def run_django_command(self, command: List[str], capture: bool = False) -> Optional[str]:
        """
        Run Django management command.

        Args:
            command: Command parts (e.g., ['showmigrations', '--plan'])
            capture: Whether to capture and return output

        Returns:
            Command output if capture=True, None otherwise
        """
        cmd = ["python", str(self.manage_py)] + command

        try:
            if capture:
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout
            else:
                subprocess.run(cmd, cwd=self.project_root, check=True)
                return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running command: {' '.join(cmd)}")
            if capture and e.stderr:
                print(e.stderr)
            sys.exit(1)

    def show_status(self) -> None:
        """Show migration status for all apps."""
        print("📊 Migration Status\n")
        self.run_django_command(["showmigrations"])

    def show_plan(self) -> None:
        """Show migration execution plan."""
        print("📋 Migration Plan\n")
        output = self.run_django_command(["showmigrations", "--plan"], capture=True)
        print(output)

        # Check for unapplied migrations
        if output and "[ ]" in output:
            print("\n⚠️  There are unapplied migrations")
            print("   Run: python manage.py migrate")

    def check_conflicts(self) -> bool:
        """
        Check for migration conflicts.

        Returns:
            True if conflicts found, False otherwise
        """
        print("🔍 Checking for migration conflicts...\n")

        output = self.run_django_command(["showmigrations", "--plan"], capture=True)

        # Try to detect conflicts (Django shows error message)
        try:
            self.run_django_command(["makemigrations", "--dry-run"], capture=True)
            print("✅ No migration conflicts detected")
            return False
        except subprocess.CalledProcessError:
            print("❌ Migration conflicts detected!")
            print("\n   To resolve:")
            print("   1. Run: python manage.py makemigrations --merge")
            print("   2. Review and test the merge migration")
            print("   3. Apply: python manage.py migrate")
            return True

    def validate_migration_file(self, migration_path: Path) -> List[str]:
        """
        Validate a migration file for best practices.

        Args:
            migration_path: Path to migration file

        Returns:
            List of validation warnings
        """
        warnings = []

        try:
            with open(migration_path, 'r') as f:
                content = f.read()

            # Check for tenant-first indexes in multi-tenant projects
            # Look for Index definitions that don't start with 'tenant'
            index_pattern = r"models\.Index\(fields=\[([^\]]+)\]"
            for match in re.finditer(index_pattern, content):
                fields_str = match.group(1)
                # Parse field list
                fields = [f.strip().strip("'\"") for f in fields_str.split(",")]

                # Skip single-field indexes
                if len(fields) > 1:
                    first_field = fields[0].lstrip("-")  # Remove DESC prefix
                    if first_field != "tenant":
                        warnings.append(
                            f"⚠️  Multi-field index doesn't start with 'tenant': {fields}"
                        )

            # Check for unique constraints without tenant
            unique_pattern = r"models\.UniqueConstraint\(fields=\[([^\]]+)\]"
            for match in re.finditer(unique_pattern, content):
                fields_str = match.group(1)
                fields = [f.strip().strip("'\"") for f in fields_str.split(",")]

                if "tenant" not in fields and len(fields) > 1:
                    warnings.append(
                        f"⚠️  Unique constraint may need 'tenant' field: {fields}"
                    )

            # Check for direct model imports in RunPython
            if "from" in content and "import" in content and "RunPython" in content:
                # Check for model imports
                model_import_pattern = r"from\s+\w+\.models\s+import"
                if re.search(model_import_pattern, content):
                    warnings.append(
                        "⚠️  Direct model import detected - use apps.get_model() instead"
                    )

            # Check for RunPython without reverse
            runpython_pattern = r"migrations\.RunPython\(([^,\)]+)\)"
            for match in re.finditer(runpython_pattern, content):
                if "reverse" not in match.group(0):
                    warnings.append(
                        "⚠️  RunPython without reverse function - migration not reversible"
                    )

            # Check for AddField without default on non-nullable field
            addfield_pattern = r"migrations\.AddField\([^)]+\)"
            for match in re.finditer(addfield_pattern, content):
                field_def = match.group(0)
                if "null=True" not in field_def and "default=" not in field_def:
                    warnings.append(
                        "⚠️  AddField without default or null=True may cause issues"
                    )

        except Exception as e:
            warnings.append(f"❌ Error reading migration file: {e}")

        return warnings

    def validate_app_migrations(self, app_name: Optional[str] = None) -> None:
        """
        Validate migrations for an app (or all apps).

        Args:
            app_name: App name to validate, or None for all apps
        """
        print(f"🔍 Validating migrations{f' for {app_name}' if app_name else ''}...\n")

        # Find migration directories
        if app_name:
            migration_dirs = [self.project_root / app_name / "migrations"]
        else:
            migration_dirs = list(self.project_root.glob("*/migrations"))

        total_warnings = 0

        for migration_dir in migration_dirs:
            if not migration_dir.exists():
                continue

            app = migration_dir.parent.name

            # Find migration files (exclude __init__.py and __pycache__)
            migration_files = [
                f for f in migration_dir.glob("*.py")
                if f.name != "__init__.py" and not f.name.startswith(".")
            ]

            if not migration_files:
                continue

            print(f"\n📦 {app}")
            app_warnings = 0

            for migration_file in sorted(migration_files):
                warnings = self.validate_migration_file(migration_file)

                if warnings:
                    print(f"  📄 {migration_file.name}")
                    for warning in warnings:
                        print(f"     {warning}")
                        app_warnings += 1

            if app_warnings == 0:
                print(f"  ✅ All migrations look good")
            else:
                print(f"  ⚠️  {app_warnings} warning(s) found")

            total_warnings += app_warnings

        if total_warnings == 0:
            print("\n✅ All migrations validated successfully!")
        else:
            print(f"\n⚠️  Total: {total_warnings} warning(s) found")
            print("\n   Review warnings and fix if applicable.")
            print("   Some warnings may be false positives.")

    def create_migration(self, app_name: Optional[str] = None) -> None:
        """
        Create migration with validation.

        Args:
            app_name: App name to create migration for, or None for all apps
        """
        print("🔨 Creating migration...\n")

        # Run makemigrations
        cmd = ["makemigrations"]
        if app_name:
            cmd.append(app_name)

        # Show what will be created
        print("📋 Dry run:")
        dry_run_output = self.run_django_command(
            cmd + ["--dry-run", "--verbosity", "3"],
            capture=True
        )
        print(dry_run_output)

        # Ask for confirmation
        if dry_run_output and "No changes detected" not in dry_run_output:
            response = input("\n❓ Create this migration? [y/N]: ")
            if response.lower() != 'y':
                print("❌ Cancelled")
                return

            # Create the migration
            self.run_django_command(cmd)

            # Find the newly created migration
            if app_name:
                migrations_dir = self.project_root / app_name / "migrations"
                if migrations_dir.exists():
                    migration_files = sorted(migrations_dir.glob("*.py"))
                    if migration_files:
                        latest_migration = migration_files[-1]

                        # Validate it
                        print("\n🔍 Validating new migration...\n")
                        warnings = self.validate_migration_file(latest_migration)

                        if warnings:
                            print(f"📄 {latest_migration.name}")
                            for warning in warnings:
                                print(f"   {warning}")
                            print("\n⚠️  Please review the warnings above")
                        else:
                            print("✅ Migration looks good!")

            print("\n📝 Next steps:")
            print("   1. Review the migration file")
            print("   2. Test: python manage.py migrate")
            print("   3. Test reversibility: python manage.py migrate <app> <previous>")
            print("   4. Commit the migration file")
        else:
            print("ℹ️  No changes detected")

    def show_sql(self, app_name: str, migration_name: str) -> None:
        """
        Show SQL for a specific migration.

        Args:
            app_name: App name
            migration_name: Migration name (e.g., '0002_add_field')
        """
        print(f"📄 SQL for {app_name}.{migration_name}\n")
        self.run_django_command(["sqlmigrate", app_name, migration_name])


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Django Migration Helper - Validation and best practices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              Show migration status
  %(prog)s plan                Show migration plan
  %(prog)s create              Create migration for all apps
  %(prog)s create myapp        Create migration for specific app
  %(prog)s validate            Validate all migrations
  %(prog)s validate myapp      Validate migrations for specific app
  %(prog)s check-conflicts     Check for migration conflicts
  %(prog)s sql myapp 0002      Show SQL for specific migration
        """
    )

    parser.add_argument(
        "command",
        choices=["status", "plan", "create", "validate", "check-conflicts", "sql"],
        help="Command to run"
    )

    parser.add_argument(
        "app_name",
        nargs="?",
        help="App name (required for some commands)"
    )

    parser.add_argument(
        "migration_name",
        nargs="?",
        help="Migration name (for 'sql' command)"
    )

    parser.add_argument(
        "--project-root",
        help="Django project root directory (default: current directory)"
    )

    args = parser.parse_args()

    # Initialize helper
    helper = MigrationHelper(project_root=args.project_root)

    # Run command
    if args.command == "status":
        helper.show_status()
    elif args.command == "plan":
        helper.show_plan()
    elif args.command == "create":
        helper.create_migration(args.app_name)
    elif args.command == "validate":
        helper.validate_app_migrations(args.app_name)
    elif args.command == "check-conflicts":
        conflicts = helper.check_conflicts()
        sys.exit(1 if conflicts else 0)
    elif args.command == "sql":
        if not args.app_name or not args.migration_name:
            print("❌ Error: 'sql' command requires app_name and migration_name")
            sys.exit(1)
        helper.show_sql(args.app_name, args.migration_name)


if __name__ == "__main__":
    main()

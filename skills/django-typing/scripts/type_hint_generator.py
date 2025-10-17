#!/usr/bin/env python3
"""
Django Type Hint Generator

Automatically adds type hints to existing Django code (models, views, forms, serializers).

Usage:
    python type_hint_generator.py --target models --app myapp     # Add hints to models
    python type_hint_generator.py --target views --app myapp      # Add hints to views
    python type_hint_generator.py --all                           # Process all apps
    python type_hint_generator.py --dry-run                       # Preview changes
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


@dataclass
class TypeHint:
    """Represents a type hint to be added."""
    line_number: int
    original_line: str
    new_line: str
    hint_type: str  # 'field', 'method', 'parameter', 'return'


class DjangoTypeHintGenerator:
    """Generates type hints for Django code."""

    # Django field type mappings
    DJANGO_FIELD_TYPES = {
        'CharField': 'str',
        'TextField': 'str',
        'EmailField': 'str',
        'URLField': 'str',
        'SlugField': 'str',
        'IntegerField': 'int',
        'PositiveIntegerField': 'int',
        'SmallIntegerField': 'int',
        'BigIntegerField': 'int',
        'BooleanField': 'bool',
        'NullBooleanField': 'Optional[bool]',
        'FloatField': 'float',
        'DecimalField': 'Decimal',
        'DateField': 'date',
        'DateTimeField': 'datetime',
        'TimeField': 'time',
        'DurationField': 'timedelta',
        'JSONField': 'Dict[str, Any]',
        'BinaryField': 'bytes',
        'UUIDField': 'UUID',
        'FileField': 'str',  # Path to file
        'ImageField': 'str',  # Path to image
        'ForeignKey': 'ForeignKey["{model}"]',  # Will be filled in
        'OneToOneField': 'OneToOneField["{model}"]',
        'ManyToManyField': 'ManyToManyField["{model}", "{model}"]',
    }

    # Required imports for type hints
    TYPE_IMPORTS = {
        'typing': {'ClassVar', 'Optional', 'Dict', 'List', 'Any', 'Union'},
        'datetime': {'datetime', 'date', 'time', 'timedelta'},
        'decimal': {'Decimal'},
        'uuid': {'UUID'},
        'django.db': {'models'},
        'django.db.models': {'Manager', 'QuerySet', 'ForeignKey', 'OneToOneField', 'ManyToManyField'},
    }

    def __init__(self, project_root: str = ".", dry_run: bool = False):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.changes: Dict[str, List[TypeHint]] = {}

    def find_django_apps(self) -> List[Path]:
        """Find all Django apps in project."""
        apps = []
        for path in self.project_root.rglob("models.py"):
            # Exclude migrations and venv
            if 'migrations' not in path.parts and 'venv' not in path.parts:
                apps.append(path.parent)
        return apps

    def process_models_file(self, file_path: Path) -> List[TypeHint]:
        """Add type hints to models.py file."""
        hints: List[TypeHint] = []

        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # Parse AST
            tree = ast.parse(content)

            # Find model classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if self._is_django_model(node):
                        model_hints = self._process_model_class(node, lines)
                        hints.extend(model_hints)

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

        return hints

    def _is_django_model(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django model."""
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == 'Model':
                    return True
            elif isinstance(base, ast.Name):
                if 'Model' in base.id:
                    return True
        return False

    def _process_model_class(self, node: ast.ClassDef, lines: List[str]) -> List[TypeHint]:
        """Process Django model class and add type hints."""
        hints: List[TypeHint] = []

        for item in node.body:
            # Process field assignments
            if isinstance(item, ast.Assign):
                hint = self._process_field_assignment(item, lines)
                if hint:
                    hints.append(hint)

            # Process methods
            elif isinstance(item, ast.FunctionDef):
                method_hints = self._process_method(item, lines)
                hints.extend(method_hints)

        # Add manager type hint if not present
        manager_hint = self._add_manager_hint(node, lines)
        if manager_hint:
            hints.append(manager_hint)

        return hints

    def _process_field_assignment(self, node: ast.Assign, lines: List[str]) -> Optional[TypeHint]:
        """Process Django field assignment and add type hint."""
        if len(node.targets) != 1:
            return None

        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return None

        field_name = target.id

        # Check if it's a Django field
        if isinstance(node.value, ast.Call):
            field_type = self._get_field_type(node.value)
            if field_type:
                line_num = node.lineno - 1
                original_line = lines[line_num]

                # Check if already has type hint
                if ':' in original_line.split('=')[0]:
                    return None

                # Generate typed line
                indent = len(original_line) - len(original_line.lstrip())
                new_line = f"{' ' * indent}{field_name}: {field_type} = {original_line.split('=', 1)[1]}"

                return TypeHint(
                    line_number=line_num,
                    original_line=original_line,
                    new_line=new_line,
                    hint_type='field'
                )

        return None

    def _get_field_type(self, node: ast.Call) -> Optional[str]:
        """Get Python type for Django field."""
        field_class = None

        if isinstance(node.func, ast.Attribute):
            # models.CharField
            field_class = node.func.attr
        elif isinstance(node.func, ast.Name):
            # CharField (imported)
            field_class = node.func.id

        if field_class in self.DJANGO_FIELD_TYPES:
            type_hint = self.DJANGO_FIELD_TYPES[field_class]

            # Handle ForeignKey - extract model name
            if field_class in ('ForeignKey', 'OneToOneField'):
                # Try to find first argument (model)
                if node.args:
                    if isinstance(node.args[0], ast.Constant):
                        model_name = node.args[0].value
                        return f'{field_class}["{model_name}"]'
                    elif isinstance(node.args[0], ast.Name):
                        model_name = node.args[0].id
                        return f'{field_class}["{model_name}"]'

            return type_hint

        return None

    def _process_method(self, node: ast.FunctionDef, lines: List[str]) -> List[TypeHint]:
        """Add type hints to model methods."""
        hints: List[TypeHint] = []

        # Check if already has return type
        if node.returns:
            return hints

        # Common Django method return types
        return_types = {
            '__str__': 'str',
            '__repr__': 'str',
            'get_absolute_url': 'str',
            'save': 'None',
            'delete': 'None',
        }

        if node.name in return_types:
            line_num = node.lineno - 1
            original_line = lines[line_num]

            # Add return type
            if '->' not in original_line:
                new_line = original_line.rstrip(':') + f' -> {return_types[node.name]}:'

                hints.append(TypeHint(
                    line_number=line_num,
                    original_line=original_line,
                    new_line=new_line,
                    hint_type='return'
                ))

        return hints

    def _add_manager_hint(self, node: ast.ClassDef, lines: List[str]) -> Optional[TypeHint]:
        """Add type hint for default manager."""
        # Check if class already has 'objects' defined
        has_objects = False
        for item in node.body:
            if isinstance(item, ast.Assign):
                if len(item.targets) == 1:
                    target = item.targets[0]
                    if isinstance(target, ast.Name) and target.id == 'objects':
                        has_objects = True
                        break

        if not has_objects:
            # Add objects manager hint after last field
            last_field_line = None
            for item in node.body:
                if isinstance(item, ast.Assign):
                    last_field_line = item.lineno - 1

            if last_field_line is not None:
                original_line = lines[last_field_line]
                indent = len(original_line) - len(original_line.lstrip())

                new_line = f"{' ' * indent}objects: ClassVar[Manager['{node.name}']] = Manager()"

                return TypeHint(
                    line_number=last_field_line + 1,
                    original_line="",
                    new_line=new_line,
                    hint_type='field'
                )

        return None

    def process_views_file(self, file_path: Path) -> List[TypeHint]:
        """Add type hints to views.py file."""
        hints: List[TypeHint] = []

        try:
            content = file_path.read_text()
            lines = content.split('\n')
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Function-based views
                if isinstance(node, ast.FunctionDef):
                    view_hints = self._process_view_function(node, lines)
                    hints.extend(view_hints)

                # Class-based views
                elif isinstance(node, ast.ClassDef):
                    if self._is_django_view(node):
                        view_hints = self._process_view_class(node, lines)
                        hints.extend(view_hints)

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

        return hints

    def _is_django_view(self, node: ast.ClassDef) -> bool:
        """Check if class is a Django view."""
        view_bases = ['View', 'ListView', 'DetailView', 'CreateView', 'UpdateView',
                      'DeleteView', 'FormView', 'TemplateView', 'RedirectView',
                      'APIView', 'ViewSet', 'ModelViewSet']

        for base in node.bases:
            if isinstance(base, ast.Name):
                if base.id in view_bases:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in view_bases:
                    return True
            # Check for generic views like ListView[Model]
            elif isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name):
                    if base.value.id in view_bases:
                        return True

        return False

    def _process_view_function(self, node: ast.FunctionDef, lines: List[str]) -> List[TypeHint]:
        """Add type hints to function-based view."""
        hints: List[TypeHint] = []

        # Skip if already has type hints
        if node.returns or any(arg.annotation for arg in node.args.args):
            return hints

        # Assume first parameter is 'request'
        if node.args.args:
            first_arg = node.args.args[0]
            if first_arg.arg == 'request':
                line_num = node.lineno - 1
                original_line = lines[line_num]

                # Add HttpRequest and HttpResponse types
                new_line = original_line.replace(
                    'def ' + node.name + '(request',
                    'def ' + node.name + '(request: HttpRequest'
                )
                new_line = new_line.rstrip(':') + ' -> HttpResponse:'

                hints.append(TypeHint(
                    line_number=line_num,
                    original_line=original_line,
                    new_line=new_line,
                    hint_type='parameter'
                ))

        return hints

    def _process_view_class(self, node: ast.ClassDef, lines: List[str]) -> List[TypeHint]:
        """Add type hints to class-based view."""
        hints: List[TypeHint] = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                # Type common CBV methods
                if item.name in ['get', 'post', 'put', 'patch', 'delete']:
                    if not item.returns:
                        line_num = item.lineno - 1
                        original_line = lines[line_num]

                        if 'HttpResponse' not in original_line:
                            new_line = original_line.rstrip(':') + ' -> HttpResponse:'

                            hints.append(TypeHint(
                                line_number=line_num,
                                original_line=original_line,
                                new_line=new_line,
                                hint_type='return'
                            ))

                elif item.name == 'get_context_data':
                    if not item.returns:
                        line_num = item.lineno - 1
                        original_line = lines[line_num]

                        if '->' not in original_line:
                            new_line = original_line.rstrip(':') + ' -> Dict[str, Any]:'

                            hints.append(TypeHint(
                                line_number=line_num,
                                original_line=original_line,
                                new_line=new_line,
                                hint_type='return'
                            ))

        return hints

    def apply_hints(self, file_path: Path, hints: List[TypeHint]) -> None:
        """Apply type hints to file."""
        if not hints:
            return

        content = file_path.read_text()
        lines = content.split('\n')

        # Sort hints by line number (reverse order to maintain line numbers)
        hints.sort(key=lambda h: h.line_number, reverse=True)

        # Apply changes
        for hint in hints:
            if hint.original_line == "":
                # Insert new line
                lines.insert(hint.line_number, hint.new_line)
            else:
                # Replace line
                lines[hint.line_number] = hint.new_line

        # Write back
        new_content = '\n'.join(lines)

        if self.dry_run:
            print(f"\n📝 Would modify: {file_path}")
            for hint in reversed(hints):
                print(f"  Line {hint.line_number + 1} ({hint.hint_type}):")
                if hint.original_line:
                    print(f"    - {hint.original_line.strip()}")
                print(f"    + {hint.new_line.strip()}")
        else:
            file_path.write_text(new_content)
            print(f"✅ Updated: {file_path} ({len(hints)} hints added)")

    def add_missing_imports(self, file_path: Path, hints: List[TypeHint]) -> None:
        """Add missing type hint imports to file."""
        if not hints:
            return

        content = file_path.read_text()
        lines = content.split('\n')

        # Determine which imports are needed
        needed_imports: Set[str] = set()

        for hint in hints:
            hint_text = hint.new_line
            if 'ClassVar' in hint_text:
                needed_imports.add('ClassVar')
            if 'Optional[' in hint_text:
                needed_imports.add('Optional')
            if 'Dict[' in hint_text:
                needed_imports.add('Dict')
                needed_imports.add('Any')
            if 'List[' in hint_text:
                needed_imports.add('List')
            if 'Manager[' in hint_text:
                needed_imports.add('Manager')
            if 'HttpRequest' in hint_text:
                needed_imports.add('HttpRequest')
            if 'HttpResponse' in hint_text:
                needed_imports.add('HttpResponse')

        # Find import section
        import_line_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_line_idx = i

        # Add typing imports
        if 'ClassVar' in needed_imports or 'Dict' in needed_imports:
            typing_imports = ', '.join(sorted(needed_imports & {'ClassVar', 'Optional', 'Dict', 'List', 'Any'}))
            import_stmt = f"from typing import {typing_imports}"

            # Check if already exists
            has_typing_import = any('from typing import' in line for line in lines)

            if not has_typing_import:
                lines.insert(import_line_idx + 1, import_stmt)

        # Add Django imports
        if 'Manager' in needed_imports:
            manager_import = "from django.db.models import Manager"
            if not any(manager_import in line for line in lines):
                lines.insert(import_line_idx + 1, manager_import)

        if 'HttpRequest' in needed_imports or 'HttpResponse' in needed_imports:
            http_imports = ', '.join(sorted(needed_imports & {'HttpRequest', 'HttpResponse'}))
            http_import = f"from django.http import {http_imports}"
            if not any('from django.http import' in line for line in lines):
                lines.insert(import_line_idx + 1, http_import)

        # Write back
        new_content = '\n'.join(lines)
        file_path.write_text(new_content)


def main():
    parser = argparse.ArgumentParser(
        description="Add type hints to Django code"
    )

    parser.add_argument(
        '--target',
        choices=['models', 'views', 'forms', 'serializers', 'all'],
        default='all',
        help='Target files to process'
    )

    parser.add_argument(
        '--app',
        help='Specific Django app to process'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all Django apps in project'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )

    parser.add_argument(
        '--project-root',
        default='.',
        help='Django project root directory (default: current directory)'
    )

    args = parser.parse_args()

    generator = DjangoTypeHintGenerator(args.project_root, dry_run=args.dry_run)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")

    # Find apps to process
    if args.all:
        apps = generator.find_django_apps()
        print(f"Found {len(apps)} Django apps\n")
    elif args.app:
        app_path = Path(args.project_root) / args.app
        if not app_path.exists():
            print(f"❌ App not found: {args.app}")
            sys.exit(1)
        apps = [app_path]
    else:
        print("❌ Specify --app or --all")
        sys.exit(1)

    # Process each app
    total_hints = 0

    for app in apps:
        print(f"\n{'='*80}")
        print(f"Processing app: {app.name}")
        print(f"{'='*80}")

        # Process models
        if args.target in ('models', 'all'):
            models_file = app / 'models.py'
            if models_file.exists():
                hints = generator.process_models_file(models_file)
                if hints:
                    generator.add_missing_imports(models_file, hints)
                    generator.apply_hints(models_file, hints)
                    total_hints += len(hints)

        # Process views
        if args.target in ('views', 'all'):
            views_file = app / 'views.py'
            if views_file.exists():
                hints = generator.process_views_file(views_file)
                if hints:
                    generator.add_missing_imports(views_file, hints)
                    generator.apply_hints(views_file, hints)
                    total_hints += len(hints)

    print(f"\n{'='*80}")
    print(f"✅ Total type hints added: {total_hints}")
    print(f"{'='*80}")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == '__main__':
    main()

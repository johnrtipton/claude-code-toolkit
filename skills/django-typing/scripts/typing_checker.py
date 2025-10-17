#!/usr/bin/env python3
"""
Django Typing Checker

Automated mypy runner with Django-specific error explanations and helpful suggestions.

Usage:
    python typing_checker.py                    # Check entire project
    python typing_checker.py --app myapp        # Check specific app
    python typing_checker.py --strict           # Use strict mode
    python typing_checker.py --html-report      # Generate HTML report
    python typing_checker.py --fix-imports      # Auto-fix missing imports
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class ErrorCategory(Enum):
    """Categories of mypy errors."""
    MISSING_TYPE_HINT = "missing-type-hint"
    INCOMPATIBLE_TYPE = "incompatible-type"
    NO_ATTRIBUTE = "no-attribute"
    ARG_TYPE = "arg-type"
    RETURN_TYPE = "return-type"
    IMPORT_ERROR = "import-error"
    NAME_DEFINED = "name-defined"
    TYPE_VAR = "type-var"
    OTHER = "other"


@dataclass
class MypyError:
    """Represents a mypy error with context."""
    file_path: str
    line: int
    column: int
    severity: str  # "error", "note", "warning"
    message: str
    error_code: Optional[str] = None
    category: ErrorCategory = ErrorCategory.OTHER

    def __str__(self) -> str:
        location = f"{self.file_path}:{self.line}:{self.column}"
        code = f" [{self.error_code}]" if self.error_code else ""
        return f"{location}: {self.severity}: {self.message}{code}"


class DjangoTypingChecker:
    """Automated mypy checker with Django-specific helpers."""

    # Common Django-specific error explanations
    ERROR_EXPLANATIONS = {
        'Need type annotation for': 'Add type annotation to variable declaration.',
        'Incompatible types in assignment': 'Type mismatch between assigned value and variable type.',
        'Cannot determine type of': 'Django field needs explicit type annotation.',
        'has no attribute': 'Check if attribute exists or if imports are correct.',
        '"Manager" has no attribute': 'Use ClassVar[Manager["Model"]] for custom managers.',
        'Argument 1 has incompatible type': 'Check function argument types.',
        'Incompatible return value type': 'Return type doesn\'t match function signature.',
        'Name.*is not defined': 'Import missing or name not in scope.',
        'already defined': 'Duplicate definition or import.',
    }

    # Suggested fixes for common patterns
    SUGGESTED_FIXES = {
        'Need type annotation for.*list': 'items: List[MyModel] = []',
        'Need type annotation for.*dict': 'data: Dict[str, Any] = {}',
        'Cannot determine type.*CharField': 'field: str = models.CharField(...)',
        'Cannot determine type.*IntegerField': 'field: int = models.IntegerField(...)',
        'Cannot determine type.*BooleanField': 'field: bool = models.BooleanField(...)',
        'Cannot determine type.*ForeignKey': 'field: ForeignKey["Model"] = models.ForeignKey(...)',
        '"Manager" has no attribute': 'objects: ClassVar[Manager["MyModel"]] = Manager()',
    }

    def __init__(self, project_root: str = ".", strict: bool = False):
        self.project_root = Path(project_root)
        self.strict = strict
        self.errors: List[MypyError] = []
        self.error_counts: Dict[ErrorCategory, int] = defaultdict(int)

    def run_mypy(self, target: Optional[str] = None, html_report: bool = False) -> Tuple[int, str]:
        """
        Run mypy on target directory or file.

        Args:
            target: Specific path to check (default: entire project)
            html_report: Generate HTML report

        Returns:
            Tuple of (return_code, output)
        """
        target_path = target or "."

        cmd = ["mypy", target_path]

        # Add Django-specific configuration
        if (self.project_root / "mypy.ini").exists():
            cmd.extend(["--config-file", "mypy.ini"])
        elif (self.project_root / "pyproject.toml").exists():
            cmd.extend(["--config-file", "pyproject.toml"])

        if self.strict:
            cmd.extend([
                "--strict",
                "--disallow-untyped-defs",
                "--disallow-any-generics",
            ])

        if html_report:
            report_dir = self.project_root / "mypy-report"
            cmd.extend(["--html-report", str(report_dir)])

        # Always show error codes
        cmd.append("--show-error-codes")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            return result.returncode, result.stdout
        except FileNotFoundError:
            print("❌ Error: mypy not found. Install with: pip install mypy")
            sys.exit(1)

    def parse_mypy_output(self, output: str) -> List[MypyError]:
        """Parse mypy output into structured errors."""
        errors: List[MypyError] = []

        # Pattern: file.py:line:col: severity: message [error-code]
        pattern = r'^(.+?):(\d+):(\d+): (error|note|warning): (.+?)(?:\s+\[([^\]]+)\])?$'

        for line in output.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                file_path, line_num, col, severity, message, error_code = match.groups()

                # Categorize error
                category = self._categorize_error(message, error_code)

                error = MypyError(
                    file_path=file_path,
                    line=int(line_num),
                    column=int(col),
                    severity=severity,
                    message=message,
                    error_code=error_code,
                    category=category
                )

                errors.append(error)
                self.error_counts[category] += 1

        return errors

    def _categorize_error(self, message: str, error_code: Optional[str]) -> ErrorCategory:
        """Categorize error based on message and code."""
        if error_code == "var-annotated" or "Need type annotation" in message:
            return ErrorCategory.MISSING_TYPE_HINT
        elif error_code == "assignment" or "Incompatible types in assignment" in message:
            return ErrorCategory.INCOMPATIBLE_TYPE
        elif error_code == "attr-defined" or "has no attribute" in message:
            return ErrorCategory.NO_ATTRIBUTE
        elif error_code == "arg-type":
            return ErrorCategory.ARG_TYPE
        elif error_code == "return-value":
            return ErrorCategory.RETURN_TYPE
        elif error_code == "import" or "Cannot find" in message:
            return ErrorCategory.IMPORT_ERROR
        elif error_code == "name-defined":
            return ErrorCategory.NAME_DEFINED
        elif error_code == "type-var" or "TypeVar" in message:
            return ErrorCategory.TYPE_VAR
        else:
            return ErrorCategory.OTHER

    def get_explanation(self, error: MypyError) -> str:
        """Get helpful explanation for error."""
        for pattern, explanation in self.ERROR_EXPLANATIONS.items():
            if re.search(pattern, error.message):
                return explanation
        return "Check mypy documentation for this error."

    def get_suggested_fix(self, error: MypyError) -> Optional[str]:
        """Get suggested fix for error."""
        for pattern, fix in self.SUGGESTED_FIXES.items():
            if re.search(pattern, error.message):
                return fix
        return None

    def group_errors_by_file(self) -> Dict[str, List[MypyError]]:
        """Group errors by file."""
        grouped: Dict[str, List[MypyError]] = defaultdict(list)
        for error in self.errors:
            grouped[error.file_path].append(error)
        return grouped

    def generate_report(self, verbose: bool = True) -> str:
        """Generate human-readable report."""
        if not self.errors:
            return "✅ No type errors found! Your code is type-safe."

        report = []
        report.append("=" * 80)
        report.append("DJANGO TYPING CHECK REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append(f"Total Errors: {len(self.errors)}")
        report.append("")
        report.append("Errors by Category:")
        for category in ErrorCategory:
            count = self.error_counts.get(category, 0)
            if count > 0:
                report.append(f"  • {category.value}: {count}")
        report.append("")

        # Group by file
        grouped = self.group_errors_by_file()

        report.append("=" * 80)
        report.append("ERRORS BY FILE")
        report.append("=" * 80)
        report.append("")

        for file_path in sorted(grouped.keys()):
            file_errors = grouped[file_path]
            report.append(f"\n📄 {file_path} ({len(file_errors)} errors)")
            report.append("-" * 80)

            for error in file_errors:
                report.append(f"\nLine {error.line}, Column {error.column}:")
                report.append(f"  {error.message}")

                if error.error_code:
                    report.append(f"  Code: [{error.error_code}]")

                if verbose:
                    explanation = self.get_explanation(error)
                    report.append(f"  💡 {explanation}")

                    suggested_fix = self.get_suggested_fix(error)
                    if suggested_fix:
                        report.append(f"  ✅ Suggested fix: {suggested_fix}")

        # Common Django patterns section
        if verbose and self.error_counts:
            report.append("\n" + "=" * 80)
            report.append("COMMON DJANGO TYPING PATTERNS")
            report.append("=" * 80)
            report.append("")

            if self.error_counts.get(ErrorCategory.MISSING_TYPE_HINT, 0) > 0:
                report.append("For missing type hints:")
                report.append("  class MyModel(models.Model):")
                report.append("      title: str = models.CharField(max_length=200)")
                report.append("      objects: ClassVar[Manager['MyModel']] = Manager()")
                report.append("")

            if self.error_counts.get(ErrorCategory.INCOMPATIBLE_TYPE, 0) > 0:
                report.append("For incompatible types:")
                report.append("  # QuerySet returns Model | None")
                report.append("  obj = MyModel.objects.first()")
                report.append("  if obj is not None:")
                report.append("      # mypy knows obj is MyModel here")
                report.append("      print(obj.title)")
                report.append("")

            if self.error_counts.get(ErrorCategory.NO_ATTRIBUTE, 0) > 0:
                report.append("For custom managers:")
                report.append("  from typing import ClassVar")
                report.append("  class MyModel(models.Model):")
                report.append("      objects: ClassVar[CustomManager['MyModel']] = CustomManager()")
                report.append("")

        # Next steps
        report.append("=" * 80)
        report.append("NEXT STEPS")
        report.append("=" * 80)
        report.append("")
        report.append("1. Review errors grouped by file above")
        report.append("2. Use suggested fixes where provided")
        report.append("3. Check reference docs in references/django-typing-guide.md")
        report.append("4. Run with --html-report for detailed HTML output")
        report.append("5. Use type_hint_generator.py to auto-add hints")
        report.append("")

        return "\n".join(report)

    def check_django_stubs_installed(self) -> bool:
        """Check if django-stubs is installed."""
        try:
            import django_stubs_ext
            return True
        except ImportError:
            return False

    def check_mypy_config_exists(self) -> bool:
        """Check if mypy configuration exists."""
        return (self.project_root / "mypy.ini").exists() or \
               (self.project_root / "pyproject.toml").exists()


def main():
    parser = argparse.ArgumentParser(
        description="Django typing checker with helpful error explanations"
    )

    parser.add_argument(
        '--app',
        help='Specific Django app to check'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Use strict type checking'
    )

    parser.add_argument(
        '--html-report',
        action='store_true',
        help='Generate HTML report'
    )

    parser.add_argument(
        '--project-root',
        default='.',
        help='Django project root directory (default: current directory)'
    )

    parser.add_argument(
        '--fix-imports',
        action='store_true',
        help='Suggest missing imports (not implemented yet)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Show only summary, not detailed explanations'
    )

    args = parser.parse_args()

    # Initialize checker
    checker = DjangoTypingChecker(args.project_root, strict=args.strict)

    # Pre-flight checks
    if not checker.check_django_stubs_installed():
        print("⚠️  Warning: django-stubs not installed")
        print("   Install with: pip install django-stubs django-stubs-ext")
        print("")

    if not checker.check_mypy_config_exists():
        print("⚠️  Warning: No mypy configuration found")
        print("   Create mypy.ini or configure in pyproject.toml")
        print("   See assets/mypy.ini for template")
        print("")

    # Run mypy
    target = args.app if args.app else None

    print("🔍 Running mypy type checker...")
    if target:
        print(f"   Target: {target}")
    if args.strict:
        print("   Mode: STRICT")
    print("")

    return_code, output = checker.run_mypy(target, args.html_report)

    # Parse errors
    checker.errors = checker.parse_mypy_output(output)

    # Generate report
    verbose = not args.quiet
    report = checker.generate_report(verbose=verbose)
    print(report)

    if args.html_report:
        report_path = Path(args.project_root) / "mypy-report" / "index.html"
        if report_path.exists():
            print(f"\n📊 HTML report generated: {report_path}")

    # Exit with mypy's exit code
    sys.exit(return_code)


if __name__ == '__main__':
    main()

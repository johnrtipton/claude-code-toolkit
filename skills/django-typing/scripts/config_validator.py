#!/usr/bin/env python3
"""
Django mypy Configuration Validator

Validates mypy and django-stubs configuration, checks installation,
and suggests improvements.

Usage:
    python config_validator.py                 # Validate configuration
    python config_validator.py --check-stubs   # Check django-stubs setup
    python config_validator.py --suggest       # Suggest improvements
    python config_validator.py --fix           # Auto-fix common issues
"""

import argparse
import configparser
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Set
import tomli


class IssueLevel(Enum):
    """Severity level of configuration issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ConfigIssue:
    """Represents a configuration issue."""
    level: IssueLevel
    category: str
    message: str
    suggestion: Optional[str] = None
    fix_command: Optional[str] = None


class DjangoMypyConfigValidator:
    """Validates Django + mypy configuration."""

    # Recommended mypy settings for Django
    RECOMMENDED_SETTINGS = {
        'plugins': 'mypy_django_plugin.main',
        'show_error_codes': 'True',
        'warn_redundant_casts': 'True',
        'warn_unused_ignores': 'True',
        'warn_return_any': 'True',
        'check_untyped_defs': 'True',
    }

    # Required packages
    REQUIRED_PACKAGES = {
        'mypy': '1.0.0',
        'django-stubs': '1.0.0',
        'django-stubs-ext': '1.0.0',
    }

    # Optional but recommended packages
    OPTIONAL_PACKAGES = {
        'djangorestframework-stubs': 'For DRF projects',
        'types-requests': 'If using requests library',
        'types-PyYAML': 'If using PyYAML',
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues: List[ConfigIssue] = []

    def validate_installation(self) -> List[ConfigIssue]:
        """Check if required packages are installed."""
        issues: List[ConfigIssue] = []

        for package, min_version in self.REQUIRED_PACKAGES.items():
            if not self._is_package_installed(package):
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Installation",
                    message=f"{package} is not installed",
                    suggestion=f"Install with: pip install {package}",
                    fix_command=f"pip install {package}"
                ))

        # Check optional packages
        for package, description in self.OPTIONAL_PACKAGES.items():
            if not self._is_package_installed(package):
                issues.append(ConfigIssue(
                    level=IssueLevel.INFO,
                    category="Installation",
                    message=f"Optional: {package} not installed - {description}",
                    suggestion=f"Install with: pip install {package}"
                ))

        return issues

    def _is_package_installed(self, package: str) -> bool:
        """Check if Python package is installed."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def validate_config_file(self) -> List[ConfigIssue]:
        """Validate mypy configuration file."""
        issues: List[ConfigIssue] = []

        # Check if config file exists
        mypy_ini = self.project_root / "mypy.ini"
        pyproject_toml = self.project_root / "pyproject.toml"

        if not mypy_ini.exists() and not pyproject_toml.exists():
            issues.append(ConfigIssue(
                level=IssueLevel.ERROR,
                category="Configuration",
                message="No mypy configuration file found",
                suggestion="Create mypy.ini or add [tool.mypy] section to pyproject.toml",
                fix_command="cp assets/mypy.ini ."
            ))
            return issues

        # Validate mypy.ini
        if mypy_ini.exists():
            ini_issues = self._validate_mypy_ini(mypy_ini)
            issues.extend(ini_issues)

        # Validate pyproject.toml
        if pyproject_toml.exists():
            toml_issues = self._validate_pyproject_toml(pyproject_toml)
            issues.extend(toml_issues)

        return issues

    def _validate_mypy_ini(self, config_path: Path) -> List[ConfigIssue]:
        """Validate mypy.ini file."""
        issues: List[ConfigIssue] = []

        try:
            config = configparser.ConfigParser()
            config.read(config_path)

            # Check [mypy] section exists
            if 'mypy' not in config:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Configuration",
                    message="[mypy] section missing in mypy.ini"
                ))
                return issues

            mypy_config = config['mypy']

            # Check required settings
            if 'plugins' not in mypy_config:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Configuration",
                    message="django_stubs plugin not configured",
                    suggestion="Add: plugins = mypy_django_plugin.main"
                ))
            elif 'mypy_django_plugin' not in mypy_config['plugins']:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Configuration",
                    message="mypy_django_plugin not in plugins list",
                    suggestion="Add mypy_django_plugin.main to plugins"
                ))

            # Check [mypy.plugins.django-stubs] section
            if 'mypy.plugins.django-stubs' not in config:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Configuration",
                    message="[mypy.plugins.django-stubs] section missing",
                    suggestion="Add section with django_settings_module"
                ))
            else:
                django_config = config['mypy.plugins.django-stubs']
                if 'django_settings_module' not in django_config:
                    issues.append(ConfigIssue(
                        level=IssueLevel.ERROR,
                        category="Configuration",
                        message="django_settings_module not configured",
                        suggestion="Add: django_settings_module = yourproject.settings"
                    ))

            # Check recommended settings
            for setting, value in self.RECOMMENDED_SETTINGS.items():
                if setting not in mypy_config:
                    issues.append(ConfigIssue(
                        level=IssueLevel.WARNING,
                        category="Configuration",
                        message=f"Recommended setting missing: {setting}",
                        suggestion=f"Add: {setting} = {value}"
                    ))

            # Check migrations exclusion
            if not any('[mypy-*.migrations.*]' in section for section in config.sections()):
                issues.append(ConfigIssue(
                    level=IssueLevel.INFO,
                    category="Configuration",
                    message="Migrations not excluded from type checking",
                    suggestion="Add [mypy-*.migrations.*] section with ignore_errors = True"
                ))

        except Exception as e:
            issues.append(ConfigIssue(
                level=IssueLevel.ERROR,
                category="Configuration",
                message=f"Error parsing mypy.ini: {e}"
            ))

        return issues

    def _validate_pyproject_toml(self, config_path: Path) -> List[ConfigIssue]:
        """Validate pyproject.toml [tool.mypy] section."""
        issues: List[ConfigIssue] = []

        try:
            with open(config_path, 'rb') as f:
                try:
                    import tomli
                    config = tomli.load(f)
                except ImportError:
                    issues.append(ConfigIssue(
                        level=IssueLevel.WARNING,
                        category="Configuration",
                        message="tomli not installed, cannot validate pyproject.toml",
                        suggestion="Install with: pip install tomli"
                    ))
                    return issues

            # Check if [tool.mypy] section exists
            if 'tool' not in config or 'mypy' not in config.get('tool', {}):
                issues.append(ConfigIssue(
                    level=IssueLevel.INFO,
                    category="Configuration",
                    message="No [tool.mypy] section in pyproject.toml"
                ))
                return issues

            mypy_config = config['tool']['mypy']

            # Check django plugin
            if 'plugins' not in mypy_config:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Configuration",
                    message="No plugins configured in pyproject.toml",
                    suggestion="Add: plugins = ['mypy_django_plugin.main']"
                ))
            elif isinstance(mypy_config['plugins'], list):
                if 'mypy_django_plugin.main' not in mypy_config['plugins']:
                    issues.append(ConfigIssue(
                        level=IssueLevel.ERROR,
                        category="Configuration",
                        message="mypy_django_plugin not in plugins list"
                    ))

        except Exception as e:
            issues.append(ConfigIssue(
                level=IssueLevel.ERROR,
                category="Configuration",
                message=f"Error parsing pyproject.toml: {e}"
            ))

        return issues

    def check_django_settings_module(self) -> List[ConfigIssue]:
        """Check if DJANGO_SETTINGS_MODULE is accessible."""
        issues: List[ConfigIssue] = []

        # Try to find settings module from config
        settings_module = self._get_django_settings_module()

        if settings_module:
            # Try to import settings
            try:
                import importlib
                importlib.import_module(settings_module)
            except ImportError:
                issues.append(ConfigIssue(
                    level=IssueLevel.ERROR,
                    category="Django Setup",
                    message=f"Cannot import Django settings: {settings_module}",
                    suggestion="Check DJANGO_SETTINGS_MODULE path in mypy config"
                ))

        return issues

    def _get_django_settings_module(self) -> Optional[str]:
        """Extract Django settings module from mypy config."""
        mypy_ini = self.project_root / "mypy.ini"

        if mypy_ini.exists():
            config = configparser.ConfigParser()
            config.read(mypy_ini)
            if 'mypy.plugins.django-stubs' in config:
                return config['mypy.plugins.django-stubs'].get('django_settings_module')

        return None

    def suggest_improvements(self) -> List[ConfigIssue]:
        """Suggest configuration improvements."""
        suggestions: List[ConfigIssue] = []

        # Check if using strict mode
        suggestions.append(ConfigIssue(
            level=IssueLevel.INFO,
            category="Best Practices",
            message="Consider enabling strict mode gradually",
            suggestion="Add check_untyped_defs, then disallow_untyped_defs later"
        ))

        # Check pre-commit setup
        pre_commit_file = self.project_root / ".pre-commit-config.yaml"
        if not pre_commit_file.exists():
            suggestions.append(ConfigIssue(
                level=IssueLevel.INFO,
                category="CI/CD",
                message="pre-commit not configured",
                suggestion="Set up pre-commit hooks for automatic type checking",
                fix_command="cp assets/.pre-commit-config.yaml ."
            ))

        # Check if using mypy in CI
        github_workflows = self.project_root / ".github" / "workflows"
        if github_workflows.exists():
            has_mypy_workflow = any(
                'mypy' in f.read_text()
                for f in github_workflows.glob("*.yml")
                if f.is_file()
            )
            if not has_mypy_workflow:
                suggestions.append(ConfigIssue(
                    level=IssueLevel.INFO,
                    category="CI/CD",
                    message="mypy not configured in GitHub Actions",
                    suggestion="Add mypy check to CI pipeline"
                ))

        return suggestions

    def generate_report(self) -> str:
        """Generate validation report."""
        if not self.issues:
            return "✅ All checks passed! Your mypy + Django configuration is good."

        report = []
        report.append("=" * 80)
        report.append("DJANGO MYPY CONFIGURATION VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")

        # Group by level
        errors = [i for i in self.issues if i.level == IssueLevel.ERROR]
        warnings = [i for i in self.issues if i.level == IssueLevel.WARNING]
        info = [i for i in self.issues if i.level == IssueLevel.INFO]

        # Summary
        report.append(f"Total Issues: {len(self.issues)}")
        report.append(f"  🔴 Errors: {len(errors)}")
        report.append(f"  🟡 Warnings: {len(warnings)}")
        report.append(f"  ℹ️  Info: {len(info)}")
        report.append("")

        # Errors
        if errors:
            report.append("=" * 80)
            report.append("🔴 ERRORS (Must Fix)")
            report.append("=" * 80)
            report.append("")

            for issue in errors:
                report.append(f"[{issue.category}] {issue.message}")
                if issue.suggestion:
                    report.append(f"  💡 {issue.suggestion}")
                if issue.fix_command:
                    report.append(f"  ⚡ Fix: {issue.fix_command}")
                report.append("")

        # Warnings
        if warnings:
            report.append("=" * 80)
            report.append("🟡 WARNINGS (Should Fix)")
            report.append("=" * 80)
            report.append("")

            for issue in warnings:
                report.append(f"[{issue.category}] {issue.message}")
                if issue.suggestion:
                    report.append(f"  💡 {issue.suggestion}")
                report.append("")

        # Info
        if info:
            report.append("=" * 80)
            report.append("ℹ️  SUGGESTIONS (Nice to Have)")
            report.append("=" * 80)
            report.append("")

            for issue in info:
                report.append(f"[{issue.category}] {issue.message}")
                if issue.suggestion:
                    report.append(f"  💡 {issue.suggestion}")
                report.append("")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Django + mypy configuration"
    )

    parser.add_argument(
        '--check-stubs',
        action='store_true',
        help='Check django-stubs installation and setup'
    )

    parser.add_argument(
        '--suggest',
        action='store_true',
        help='Show improvement suggestions'
    )

    parser.add_argument(
        '--fix',
        action='store_true',
        help='Auto-fix common issues (not implemented yet)'
    )

    parser.add_argument(
        '--project-root',
        default='.',
        help='Django project root directory (default: current directory)'
    )

    args = parser.parse_args()

    validator = DjangoMypyConfigValidator(args.project_root)

    print("🔍 Validating Django + mypy configuration...\n")

    # Run validations
    validator.issues.extend(validator.validate_installation())
    validator.issues.extend(validator.validate_config_file())

    if args.check_stubs:
        validator.issues.extend(validator.check_django_settings_module())

    if args.suggest:
        validator.issues.extend(validator.suggest_improvements())

    # Generate and display report
    report = validator.generate_report()
    print(report)

    # Exit with error code if there are errors
    errors = [i for i in validator.issues if i.level == IssueLevel.ERROR]
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

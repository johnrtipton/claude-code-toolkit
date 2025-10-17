#!/usr/bin/env python3
"""
Django Security Auditor

Comprehensive security scanner for Django applications that checks:
- Django settings for security misconfigurations
- Code for security vulnerabilities (SQL injection, XSS, hardcoded secrets, etc.)
- Dependencies for known vulnerabilities
- Multi-tenant security patterns

Usage:
    python security_auditor.py                    # Full audit
    python security_auditor.py --scan settings    # Settings only
    python security_auditor.py --scan code        # Code only
    python security_auditor.py --scan dependencies # Dependencies only
    python security_auditor.py --scan multi-tenant # Multi-tenant only
    python security_auditor.py --report-only      # No auto-fix
    python security_auditor.py --auto-fix         # Auto-fix safe issues
    python security_auditor.py --format json      # JSON output
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import subprocess


class Severity(Enum):
    """Security issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    def __lt__(self, other):
        order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4
        }
        return order[self] < order[other]


@dataclass
class SecurityIssue:
    """Represents a security issue found during audit."""
    severity: Severity
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None
    cve: Optional[str] = None
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            'severity': self.severity.value,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'code_snippet': self.code_snippet,
            'recommendation': self.recommendation,
            'cve': self.cve,
            'auto_fixable': self.auto_fixable
        }


class SecurityAuditor:
    """Main security auditor class."""

    def __init__(self, project_root: str, auto_fix: bool = False):
        """
        Initialize security auditor.

        Args:
            project_root: Path to Django project root
            auto_fix: Whether to automatically fix issues
        """
        self.project_root = Path(project_root)
        self.auto_fix = auto_fix
        self.issues: List[SecurityIssue] = []

        # Secret patterns to detect
        self.secret_patterns = [
            (r'SECRET_KEY\s*=\s*["\']([^"\']+)["\']', 'SECRET_KEY'),
            (r'AWS_SECRET_ACCESS_KEY\s*=\s*["\']([^"\']+)["\']', 'AWS Secret'),
            (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', 'API Key'),
            (r'password\s*=\s*["\']([^"\']+)["\']', 'Password'),
            (r'(?:auth|token)[_-]?key\s*=\s*["\']([^"\']+)["\']', 'Auth Token'),
        ]

    def add_issue(self, issue: SecurityIssue) -> None:
        """Add a security issue to the list."""
        self.issues.append(issue)

    def scan_settings(self, settings_path: Optional[Path] = None) -> None:
        """
        Scan Django settings.py for security issues.

        Args:
            settings_path: Path to settings.py (auto-detect if None)
        """
        if settings_path is None:
            # Try to find settings.py
            settings_candidates = list(self.project_root.rglob("settings.py"))
            if not settings_candidates:
                print("❌ Could not find settings.py")
                return
            settings_path = settings_candidates[0]

        if not settings_path.exists():
            return

        with open(settings_path, 'r') as f:
            content = f.read()

        # Check DEBUG setting
        if re.search(r'\bDEBUG\s*=\s*True\b', content):
            self.add_issue(SecurityIssue(
                severity=Severity.CRITICAL,
                category="Settings",
                title="DEBUG enabled",
                description="DEBUG = True in settings - NEVER use in production",
                file_path=str(settings_path),
                recommendation="Set DEBUG = False for production. Use environment variable: DEBUG = os.environ.get('DEBUG', 'False') == 'True'",
                auto_fixable=True
            ))

        # Check SECRET_KEY
        if re.search(r'SECRET_KEY\s*=\s*["\'][^"\']+["\']', content):
            if 'os.environ' not in content and 'env(' not in content:
                self.add_issue(SecurityIssue(
                    severity=Severity.CRITICAL,
                    category="Settings",
                    title="Hardcoded SECRET_KEY",
                    description="SECRET_KEY is hardcoded in settings",
                    file_path=str(settings_path),
                    recommendation="Use environment variable: SECRET_KEY = os.environ['DJANGO_SECRET_KEY']",
                    auto_fixable=False
                ))

        # Check ALLOWED_HOSTS
        if re.search(r'ALLOWED_HOSTS\s*=\s*\[\s*\*\s*\]', content) or \
           re.search(r'ALLOWED_HOSTS\s*=\s*\[\s*["\']\\?\*["\']', content):
            self.add_issue(SecurityIssue(
                severity=Severity.HIGH,
                category="Settings",
                title="ALLOWED_HOSTS wildcard",
                description="ALLOWED_HOSTS = ['*'] allows any host header",
                file_path=str(settings_path),
                recommendation="Set specific hosts: ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']",
                auto_fixable=False
            ))

        # Check for missing security middleware
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]

        for mw in required_middleware:
            if mw not in content:
                self.add_issue(SecurityIssue(
                    severity=Severity.HIGH,
                    category="Settings",
                    title=f"Missing security middleware: {mw.split('.')[-1]}",
                    description=f"Required security middleware not found: {mw}",
                    file_path=str(settings_path),
                    recommendation=f"Add to MIDDLEWARE list: '{mw}'",
                    auto_fixable=True
                ))

        # Check HTTPS settings
        https_settings = {
            'SECURE_SSL_REDIRECT': ('True', Severity.HIGH),
            'SESSION_COOKIE_SECURE': ('True', Severity.HIGH),
            'CSRF_COOKIE_SECURE': ('True', Severity.HIGH),
            'SECURE_BROWSER_XSS_FILTER': ('True', Severity.MEDIUM),
            'SECURE_CONTENT_TYPE_NOSNIFF': ('True', Severity.MEDIUM),
        }

        for setting, (expected, severity) in https_settings.items():
            if setting not in content:
                self.add_issue(SecurityIssue(
                    severity=Severity.MEDIUM,
                    category="Settings",
                    title=f"Missing security setting: {setting}",
                    description=f"{setting} not configured",
                    file_path=str(settings_path),
                    recommendation=f"Add {setting} = {expected}",
                    auto_fixable=True
                ))
            elif re.search(f'{setting}\\s*=\\s*False', content):
                self.add_issue(SecurityIssue(
                    severity=Severity.HIGH,
                    category="Settings",
                    title=f"Insecure setting: {setting} = False",
                    description=f"{setting} is disabled",
                    file_path=str(settings_path),
                    recommendation=f"Set {setting} = True",
                    auto_fixable=True
                ))

        # Check for weak password validators
        if 'AUTH_PASSWORD_VALIDATORS' not in content:
            self.add_issue(SecurityIssue(
                severity=Severity.MEDIUM,
                category="Settings",
                title="Missing password validators",
                description="AUTH_PASSWORD_VALIDATORS not configured",
                file_path=str(settings_path),
                recommendation="Configure Django password validators",
                auto_fixable=True
            ))

        # Check for CSP report-only mode misconfiguration (django-csp 4.0+)
        if re.search(r'CONTENT_SECURITY_POLICY_REPORT_ONLY\s*=\s*(True|False|DEBUG)', content):
            self.add_issue(SecurityIssue(
                severity=Severity.HIGH,
                category="Settings",
                title="CSP report-only mode misconfigured",
                description="CONTENT_SECURITY_POLICY_REPORT_ONLY set to boolean (causes AttributeError in django-csp 4.0+)",
                file_path=str(settings_path),
                recommendation="Remove line or set to dict: CONTENT_SECURITY_POLICY_REPORT_ONLY = {'DIRECTIVES': {...}}",
                auto_fixable=False
            ))

    def scan_code(self, scan_dir: Optional[Path] = None) -> None:
        """
        Scan Python code for security vulnerabilities.

        Args:
            scan_dir: Directory to scan (defaults to project root)
        """
        if scan_dir is None:
            scan_dir = self.project_root

        # Find all Python files
        python_files = list(scan_dir.rglob("*.py"))

        for file_path in python_files:
            # Skip virtual environments and migrations
            if 'venv' in str(file_path) or 'migrations' in str(file_path):
                continue

            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.splitlines()

                self._scan_file_for_vulnerabilities(file_path, content, lines)

            except Exception as e:
                print(f"Error scanning {file_path}: {e}")

    def _scan_file_for_vulnerabilities(self, file_path: Path, content: str, lines: List[str]) -> None:
        """Scan a single file for security vulnerabilities."""

        # Check for SQL injection vulnerabilities
        sql_injection_patterns = [
            (r'\.raw\([^)]*["\'].*%s.*%.*["\']', 'String formatting in raw SQL'),
            (r'\.raw\([^)]*f["\']', 'F-string in raw SQL'),
            (r'\.execute\([^)]*["\'].*%s.*%.*["\']', 'String formatting in execute'),
            (r'\.execute\([^)]*f["\']', 'F-string in execute'),
        ]

        for pattern, desc in sql_injection_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.add_issue(SecurityIssue(
                        severity=Severity.CRITICAL,
                        category="SQL Injection",
                        title=f"Potential SQL injection: {desc}",
                        description="SQL query with string formatting detected",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Use parameterized queries: .raw('SELECT * FROM table WHERE id = %s', [value])",
                        auto_fixable=False
                    ))

        # Check for XSS vulnerabilities
        xss_patterns = [
            (r'mark_safe\(', 'mark_safe usage'),
            (r'\|\s*safe', '|safe filter'),
            (r'safestring\.SafeString', 'SafeString usage'),
        ]

        for pattern, desc in xss_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.add_issue(SecurityIssue(
                        severity=Severity.HIGH,
                        category="XSS",
                        title=f"Potential XSS: {desc}",
                        description="Unsafe HTML rendering detected",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Only use mark_safe with trusted, sanitized content. Consider using django.utils.html.escape()",
                        auto_fixable=False
                    ))

        # Check for hardcoded secrets
        for pattern, secret_type in self.secret_patterns:
            for i, line in enumerate(lines, 1):
                match = re.search(pattern, line, re.IGNORECASE)
                if match and 'os.environ' not in line and 'env(' not in line:
                    # Check if it looks like a real secret (not example/dummy)
                    value = match.group(1) if match.groups() else ''
                    if len(value) > 10 and value not in ['your-secret-key', 'changeme', 'dummy']:
                        self.add_issue(SecurityIssue(
                            severity=Severity.CRITICAL,
                            category="Secrets",
                            title=f"Hardcoded {secret_type}",
                            description=f"Hardcoded {secret_type} found in code",
                            file_path=str(file_path),
                            line_number=i,
                            code_snippet=line.strip()[:100],  # Truncate
                            recommendation=f"Use environment variables: {secret_type.upper()} = os.environ['{secret_type.upper()}']",
                            auto_fixable=False
                        ))

        # Check for dangerous functions
        dangerous_patterns = [
            (r'\beval\(', 'eval() usage', Severity.CRITICAL),
            (r'\bexec\(', 'exec() usage', Severity.CRITICAL),
            (r'pickle\.loads?\(', 'pickle deserialization', Severity.HIGH),
            (r'subprocess\.[^(]*\(.*shell\s*=\s*True', 'shell=True in subprocess', Severity.HIGH),
            (r'os\.system\(', 'os.system() usage', Severity.HIGH),
        ]

        for pattern, desc, severity in dangerous_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.add_issue(SecurityIssue(
                        severity=severity,
                        category="Dangerous Functions",
                        title=f"Dangerous function: {desc}",
                        description=f"{desc} can lead to code execution",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation=f"Avoid {desc}. Use safer alternatives.",
                        auto_fixable=False
                    ))

        # Check for path traversal vulnerabilities
        path_traversal_patterns = [
            r'open\([^)]*user|request',
            r'Path\([^)]*user|request',
            r'os\.path\.join\([^)]*user|request',
        ]

        for pattern in path_traversal_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    self.add_issue(SecurityIssue(
                        severity=Severity.HIGH,
                        category="Path Traversal",
                        title="Potential path traversal",
                        description="File path constructed with user input",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Validate and sanitize file paths. Use django.core.files.storage for uploads.",
                        auto_fixable=False
                    ))

    def scan_multi_tenant(self, scan_dir: Optional[Path] = None) -> None:
        """
        Scan for multi-tenant security issues.

        Args:
            scan_dir: Directory to scan (defaults to project root)
        """
        if scan_dir is None:
            scan_dir = self.project_root

        python_files = list(scan_dir.rglob("*.py"))

        for file_path in python_files:
            if 'venv' in str(file_path) or 'migrations' in str(file_path):
                continue

            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                self._scan_file_for_multi_tenant_issues(file_path, lines)

            except Exception as e:
                print(f"Error scanning {file_path}: {e}")

    def _scan_file_for_multi_tenant_issues(self, file_path: Path, lines: List[str]) -> None:
        """Scan file for multi-tenant security issues."""

        for i, line in enumerate(lines, 1):
            # Check for unfiltered .all() queries
            if re.search(r'\.objects\.all\(\)', line):
                # Check if not using unfiltered() explicitly
                if 'unfiltered' not in line and 'admin.py' not in str(file_path):
                    self.add_issue(SecurityIssue(
                        severity=Severity.MEDIUM,
                        category="Multi-Tenant",
                        title="Unfiltered query - potential tenant leak",
                        description=".all() query without tenant filter",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Ensure query filters by tenant: .filter(tenant=request.tenant)",
                        auto_fixable=False
                    ))

            # Check for .get() without tenant
            if re.search(r'\.objects\.get\([^)]*\)', line):
                if 'tenant' not in line and 'admin.py' not in str(file_path):
                    self.add_issue(SecurityIssue(
                        severity=Severity.MEDIUM,
                        category="Multi-Tenant",
                        title="Query without tenant filter",
                        description=".get() query may not filter by tenant",
                        file_path=str(file_path),
                        line_number=i,
                        code_snippet=line.strip(),
                        recommendation="Include tenant in query: .get(pk=pk, tenant=request.tenant)",
                        auto_fixable=False
                    ))

    def scan_dependencies(self) -> None:
        """Scan dependencies for known vulnerabilities."""
        requirements_files = [
            self.project_root / "requirements.txt",
            self.project_root / "pyproject.toml",
        ]

        requirements_file = None
        for req_file in requirements_files:
            if req_file.exists():
                requirements_file = req_file
                break

        if not requirements_file:
            print("ℹ️  No requirements.txt or pyproject.toml found")
            return

        # Try using pip-audit
        try:
            result = subprocess.run(
                ['pip-audit', '--format', 'json', '-r', str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Parse results
                try:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns.get('dependencies', []):
                        self.add_issue(SecurityIssue(
                            severity=Severity.HIGH,
                            category="Dependencies",
                            title=f"Vulnerable package: {vuln.get('name')}",
                            description=f"Version {vuln.get('version')} has known vulnerabilities",
                            recommendation=f"Update to version {vuln.get('fix_versions', ['latest'])[0]}",
                            cve=vuln.get('vulns', [{}])[0].get('id'),
                            auto_fixable=False
                        ))
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            # pip-audit not installed, try safety
            try:
                result = subprocess.run(
                    ['safety', 'check', '--json', '--file', str(requirements_file)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stdout:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns:
                        self.add_issue(SecurityIssue(
                            severity=Severity.HIGH,
                            category="Dependencies",
                            title=f"Vulnerable package: {vuln[0]}",
                            description=vuln[2],
                            recommendation=f"Update to safe version",
                            cve=vuln[1] if len(vuln) > 1 else None,
                            auto_fixable=False
                        ))

            except FileNotFoundError:
                self.add_issue(SecurityIssue(
                    severity=Severity.INFO,
                    category="Dependencies",
                    title="No dependency scanner available",
                    description="Install pip-audit or safety to scan dependencies",
                    recommendation="pip install pip-audit",
                    auto_fixable=False
                ))
            except Exception as e:
                print(f"⚠️  Error running safety: {e}")

        except Exception as e:
            print(f"⚠️  Error scanning dependencies: {e}")

    def generate_report(self, format: str = 'text') -> str:
        """
        Generate security audit report.

        Args:
            format: Output format ('text', 'json', 'html')

        Returns:
            Formatted report string
        """
        if format == 'json':
            return self._generate_json_report()
        elif format == 'html':
            return self._generate_html_report()
        else:
            return self._generate_text_report()

    def _generate_text_report(self) -> str:
        """Generate text format report."""
        # Group by severity
        by_severity = {}
        for issue in self.issues:
            if issue.severity not in by_severity:
                by_severity[issue.severity] = []
            by_severity[issue.severity].append(issue)

        # Icons for severity
        severity_icons = {
            Severity.CRITICAL: '🔴',
            Severity.HIGH: '🟠',
            Severity.MEDIUM: '🟡',
            Severity.LOW: '🔵',
            Severity.INFO: 'ℹ️ '
        }

        report = []
        report.append("=" * 80)
        report.append("DJANGO SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append("")

        # Summary
        report.append(f"Total Issues Found: {len(self.issues)}")
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = len(by_severity.get(severity, []))
            if count > 0:
                icon = severity_icons[severity]
                report.append(f"  {icon} {severity.value}: {count}")
        report.append("")

        # Detailed issues
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            issues = by_severity.get(severity, [])
            if not issues:
                continue

            report.append("-" * 80)
            report.append(f"{severity_icons[severity]} {severity.value} SEVERITY ({len(issues)} issues)")
            report.append("-" * 80)

            for issue in issues:
                report.append("")
                report.append(f"[{issue.category}] {issue.title}")
                report.append(f"Description: {issue.description}")

                if issue.file_path:
                    loc = f"Location: {issue.file_path}"
                    if issue.line_number:
                        loc += f":{issue.line_number}"
                    report.append(loc)

                if issue.code_snippet:
                    report.append(f"Code: {issue.code_snippet}")

                if issue.recommendation:
                    report.append(f"Recommendation: {issue.recommendation}")

                if issue.cve:
                    report.append(f"CVE: {issue.cve}")

                if issue.auto_fixable:
                    report.append("✅ Auto-fixable")

        report.append("")
        report.append("=" * 80)

        # Exit code recommendation
        critical_count = len(by_severity.get(Severity.CRITICAL, []))
        high_count = len(by_severity.get(Severity.HIGH, []))

        if critical_count > 0:
            report.append(f"🔴 CRITICAL: {critical_count} critical issues must be fixed immediately!")
        if high_count > 0:
            report.append(f"🟠 HIGH: {high_count} high severity issues should be addressed soon.")

        return "\n".join(report)

    def _generate_json_report(self) -> str:
        """Generate JSON format report."""
        report = {
            'total_issues': len(self.issues),
            'by_severity': {},
            'issues': [issue.to_dict() for issue in self.issues]
        }

        for severity in Severity:
            count = sum(1 for issue in self.issues if issue.severity == severity)
            report['by_severity'][severity.value] = count

        return json.dumps(report, indent=2)

    def _generate_html_report(self) -> str:
        """Generate HTML format report."""
        # Simple HTML report
        html = ["<html><head><title>Django Security Audit</title>"]
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append(".critical { color: #d32f2f; }")
        html.append(".high { color: #f57c00; }")
        html.append(".medium { color: #fbc02d; }")
        html.append(".low { color: #1976d2; }")
        html.append(".info { color: #0097a7; }")
        html.append("</style></head><body>")
        html.append("<h1>Django Security Audit Report</h1>")
        html.append(f"<p>Total Issues: {len(self.issues)}</p>")

        for issue in self.issues:
            severity_class = issue.severity.value.lower()
            html.append(f"<div class='{severity_class}'>")
            html.append(f"<h3>[{issue.severity.value}] {issue.title}</h3>")
            html.append(f"<p>{issue.description}</p>")
            if issue.file_path:
                html.append(f"<p><strong>File:</strong> {issue.file_path}:{issue.line_number or ''}</p>")
            if issue.recommendation:
                html.append(f"<p><strong>Fix:</strong> {issue.recommendation}</p>")
            html.append("</div><hr>")

        html.append("</body></html>")
        return "".join(html)

    def get_exit_code(self) -> int:
        """
        Get appropriate exit code based on findings.

        Returns:
            0 if no critical/high issues, 1 otherwise
        """
        for issue in self.issues:
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
                return 1
        return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Django Security Auditor - Comprehensive security scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           Full security audit
  %(prog)s --scan settings           Scan Django settings only
  %(prog)s --scan code               Scan code for vulnerabilities
  %(prog)s --scan dependencies       Check dependency vulnerabilities
  %(prog)s --scan multi-tenant       Check multi-tenant security
  %(prog)s --auto-fix                Auto-fix safe issues
  %(prog)s --format json             JSON output
  %(prog)s --fail-on high            Exit 1 if high+ severity found
        """
    )

    parser.add_argument(
        '--scan',
        choices=['settings', 'code', 'dependencies', 'multi-tenant', 'all'],
        default='all',
        help='Type of scan to perform (default: all)'
    )

    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically fix safe issues'
    )

    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Report only, no fixes'
    )

    parser.add_argument(
        '--format',
        choices=['text', 'json', 'html'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--project-root',
        default='.',
        help='Django project root directory (default: current directory)'
    )

    parser.add_argument(
        '--fail-on',
        choices=['critical', 'high', 'medium', 'low'],
        help='Exit with code 1 if issues at this severity or higher are found'
    )

    args = parser.parse_args()

    # Initialize auditor
    auto_fix = args.auto_fix and not args.report_only
    auditor = SecurityAuditor(args.project_root, auto_fix=auto_fix)

    # For structured formats (json, html), send diagnostic messages to stderr
    # so only clean output goes to stdout
    def log(msg):
        if args.format in ['json', 'html']:
            print(msg, file=sys.stderr)
        else:
            print(msg)

    # Run scans
    if args.scan in ['settings', 'all']:
        log("🔍 Scanning Django settings...")
        auditor.scan_settings()

    if args.scan in ['code', 'all']:
        log("🔍 Scanning code for vulnerabilities...")
        auditor.scan_code()

    if args.scan in ['dependencies', 'all']:
        log("🔍 Checking dependencies...")
        auditor.scan_dependencies()

    if args.scan in ['multi-tenant', 'all']:
        log("🔍 Checking multi-tenant security...")
        auditor.scan_multi_tenant()

    # Generate and display report
    report = auditor.generate_report(format=args.format)
    if args.format == 'json':
        # For JSON, print without extra newline to keep output clean
        print(report)
    else:
        print("\n" + report)

    # Determine exit code
    if args.fail_on:
        fail_severity = {
            'critical': Severity.CRITICAL,
            'high': Severity.HIGH,
            'medium': Severity.MEDIUM,
            'low': Severity.LOW
        }[args.fail_on]

        for issue in auditor.issues:
            if issue.severity.value <= fail_severity.value:
                sys.exit(1)

    sys.exit(auditor.get_exit_code())


if __name__ == '__main__':
    main()

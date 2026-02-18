"""
Config Access Migration Tool

Finds and reports all flat config access patterns that need migration
to the new nested structure. Supports dry-run and auto-fix modes.

Usage:
    python scripts/migrate_config_access.py                    # Dry run, report only
    python scripts/migrate_config_access.py --fix              # Auto-fix Python files
    python scripts/migrate_config_access.py --templates        # Include Jinja templates
    python scripts/migrate_config_access.py --json > report.json  # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

# Complete mapping of flat keys to canonical nested locations
MIGRATION_MAP: dict[str, str] = {
    # site.* (Site Metadata)
    "title": "site.title",
    "baseurl": "site.baseurl",
    "description": "site.description",
    "author": "site.author",
    "language": "site.language",
    # build.* (Build Settings)
    "output_dir": "build.output_dir",
    "content_dir": "build.content_dir",
    "assets_dir": "build.assets_dir",
    "templates_dir": "build.templates_dir",
    "parallel": "build.parallel",
    "incremental": "build.incremental",
    "max_workers": "build.max_workers",
    "pretty_urls": "build.pretty_urls",
    "minify_html": "build.minify_html",
    "strict_mode": "build.strict_mode",
    "debug": "build.debug",
    "validate_build": "build.validate_build",
    "validate_links": "build.validate_links",
    "transform_links": "build.transform_links",
    "fast_writes": "build.fast_writes",
    "fast_mode": "build.fast_mode",
    # dev.* (Development)
    "cache_templates": "dev.cache_templates",
    "watch_backend": "dev.watch_backend",
    "live_reload": "dev.live_reload",
    "port": "dev.port",
}

FLAT_KEYS = frozenset(MIGRATION_MAP.keys())

# Patterns that indicate nested access (not flat) - skip these
NESTED_ACCESS_SECTIONS = frozenset(
    {
        "site",
        "build",
        "dev",
        "theme",
        "search",
        "content",
        "assets",
        "output_formats",
        "features",
        "graph",
        "i18n",
        "markdown",
        "health_check",
        "pagination",
        "menu",
        "taxonomies",
    }
)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Issue:
    """A single flat access pattern found in code."""

    file: Path
    line: int
    column: int
    old_pattern: str
    new_pattern: str
    context: str  # The line of code for review
    pattern_type: str  # "dict_access" | "get_call" | "template"


@dataclass
class MigrationReport:
    """Aggregated migration report."""

    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0
    files_with_issues: int = 0

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_issues": len(self.issues),
                "files_scanned": self.files_scanned,
                "files_with_issues": self.files_with_issues,
                "by_type": self._count_by_type(),
                "by_key": self._count_by_key(),
            },
            "issues": [
                {
                    "file": str(i.file),
                    "line": i.line,
                    "column": i.column,
                    "old": i.old_pattern,
                    "new": i.new_pattern,
                    "type": i.pattern_type,
                }
                for i in self.issues
            ],
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.pattern_type] = counts.get(issue.pattern_type, 0) + 1
        return counts

    def _count_by_key(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            # Extract key from old_pattern
            if "[" in issue.old_pattern:
                key = issue.old_pattern.split("[")[1].split("]")[0].strip("\"'")
            elif "(" in issue.old_pattern:
                key = issue.old_pattern.split("(")[1].split(")")[0].split(",")[0].strip("\"'")
            else:
                key = issue.old_pattern.split(".")[-1]
            counts[key] = counts.get(key, 0) + 1
        return counts


# =============================================================================
# Pattern Matching
# =============================================================================


def find_python_issues(file: Path) -> list[Issue]:
    """Find flat config access patterns in Python files."""
    issues: list[Issue] = []

    try:
        content = file.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return issues

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        # Pattern 1: config["key"] or config['key']
        # Matches: config["title"], site.config["baseurl"], self.config["parallel"]
        for match in re.finditer(r'(\w*\.?config)\[(["\'])(\w+)\2\]', line):
            prefix = match.group(1)  # "config" or "site.config" etc.
            key = match.group(3)

            # Skip if accessing a known nested section
            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                section, attr = new_path.split(".")
                issues.append(
                    Issue(
                        file=file,
                        line=line_num,
                        column=match.start() + 1,
                        old_pattern=match.group(0),
                        new_pattern=f"{prefix}.{section}.{attr}",
                        context=line.strip(),
                        pattern_type="dict_access",
                    )
                )

        # Pattern 2: config.get("key") or config.get("key", default)
        # Handles: config.get("title"), config.get("parallel", True)
        for match in re.finditer(r'(\w*\.?config)\.get\((["\'])(\w+)\2(?:,\s*([^)]+))?\)', line):
            prefix = match.group(1)
            key = match.group(3)
            default = match.group(4)

            # Skip if accessing a known nested section
            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                section, attr = new_path.split(".")

                if default:
                    new_pattern = f'{prefix}.{section}.get("{attr}", {default})'
                else:
                    new_pattern = f'{prefix}.{section}.get("{attr}")'

                issues.append(
                    Issue(
                        file=file,
                        line=line_num,
                        column=match.start() + 1,
                        old_pattern=match.group(0),
                        new_pattern=new_pattern,
                        context=line.strip(),
                        pattern_type="get_call",
                    )
                )

    return issues


def find_template_issues(file: Path) -> list[Issue]:
    """Find flat config access patterns in Jinja templates."""
    issues: list[Issue] = []

    try:
        content = file.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return issues

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Pattern: {{ config.title }} or {{ config.baseurl }}
        for match in re.finditer(r"\{\{\s*config\.(\w+)\s*(\|[^}]+)?\}\}", line):
            key = match.group(1)
            filter_chain = match.group(2) or ""

            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                issues.append(
                    Issue(
                        file=file,
                        line=line_num,
                        column=match.start() + 1,
                        old_pattern=match.group(0),
                        new_pattern=f"{{{{ config.{new_path}{filter_chain} }}}}",
                        context=line.strip(),
                        pattern_type="template",
                    )
                )

        # Pattern: {% if config.debug %} or similar
        for match in re.finditer(r"\{%[^%]*config\.(\w+)[^%]*%\}", line):
            key = match.group(1)

            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                old_pattern = f"config.{key}"
                new_pattern = f"config.{new_path}"
                issues.append(
                    Issue(
                        file=file,
                        line=line_num,
                        column=match.start() + 1,
                        old_pattern=old_pattern,
                        new_pattern=new_pattern,
                        context=line.strip(),
                        pattern_type="template",
                    )
                )

    return issues


# =============================================================================
# Main
# =============================================================================


def scan_codebase(
    root: Path,
    include_templates: bool = False,
) -> MigrationReport:
    """Scan codebase for flat config access patterns."""
    report = MigrationReport()
    files_with_issues: set[Path] = set()

    # Scan Python files
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        report.files_scanned += 1
        issues = find_python_issues(py_file)
        if issues:
            files_with_issues.add(py_file)
            for issue in issues:
                report.add(issue)

    # Scan templates if requested
    if include_templates:
        for template_file in root.rglob("*.html"):
            report.files_scanned += 1
            issues = find_template_issues(template_file)
            if issues:
                files_with_issues.add(template_file)
                for issue in issues:
                    report.add(issue)

    report.files_with_issues = len(files_with_issues)
    return report


def print_report(report: MigrationReport) -> None:
    """Print human-readable migration report."""
    print(f"\n{'=' * 60}")
    print("Config Migration Report")
    print(f"{'=' * 60}\n")

    print(f"Files scanned:     {report.files_scanned}")
    print(f"Files with issues: {report.files_with_issues}")
    print(f"Total issues:      {len(report.issues)}\n")

    if not report.issues:
        print("✅ No flat config access patterns found!")
        return

    # Group by file
    by_file: dict[Path, list[Issue]] = {}
    for issue in report.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for file, issues in sorted(by_file.items()):
        print(f"\n📄 {file} ({len(issues)} issues)")
        print("-" * 40)
        for issue in issues:
            print(f"  L{issue.line}: {issue.old_pattern}")
            print(f"       → {issue.new_pattern}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Config access migration tool")
    parser.add_argument("--root", type=Path, default=Path("bengal"), help="Root directory to scan")
    parser.add_argument("--templates", action="store_true", help="Include Jinja templates in scan")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues (USE WITH CAUTION)")
    args = parser.parse_args()

    if args.fix:
        print("⚠️  --fix mode not implemented. Review issues manually.")
        return 1

    report = scan_codebase(args.root, include_templates=args.templates)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    return 0 if not report.issues else 1


if __name__ == "__main__":
    sys.exit(main())

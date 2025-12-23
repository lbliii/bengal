#!/usr/bin/env python3
"""
Architecture audit script for Bengal.

Checks model/orchestrator split, composition patterns, and file organization.

Usage:
    python audit_arch.py bengal/
    python audit_arch.py bengal/core/ --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArchViolation:
    """An architecture violation."""

    file: str
    line: int
    category: str
    message: str
    severity: str = "error"


@dataclass
class FileMetrics:
    """Metrics for a Python file."""

    path: str
    lines: int
    classes: int
    max_methods: int
    imports: int


@dataclass
class ArchAuditResult:
    """Result of architecture audit."""

    violations: list[ArchViolation] = field(default_factory=list)
    file_metrics: list[FileMetrics] = field(default_factory=list)
    patterns: dict[str, bool] = field(default_factory=dict)
    confidence: int = 0

    def to_dict(self) -> dict:
        return {
            "violations": [
                {
                    "file": v.file,
                    "line": v.line,
                    "category": v.category,
                    "message": v.message,
                    "severity": v.severity,
                }
                for v in self.violations
            ],
            "file_metrics": [
                {
                    "path": m.path,
                    "lines": m.lines,
                    "classes": m.classes,
                    "max_methods": m.max_methods,
                    "imports": m.imports,
                }
                for m in self.file_metrics
            ],
            "patterns": self.patterns,
            "confidence": self.confidence,
        }


# Patterns that indicate I/O or logging (not allowed in core)
IO_PATTERNS = [
    (r"logger\.\w+\(", "logging"),
    (r"logging\.\w+\(", "logging"),
    (r"get_logger\(", "logging"),
    (r"\.write\(", "file_write"),
    (r"\.write_text\(", "file_write"),
    (r"\.write_bytes\(", "file_write"),
    (r"open\([^)]+,\s*['\"]w", "file_write"),
    (r"requests\.\w+\(", "network"),
    (r"httpx\.\w+\(", "network"),
    (r"subprocess\.\w+\(", "subprocess"),
]


def check_model_purity(core_path: Path) -> list[ArchViolation]:
    """Check that bengal/core/ has no I/O or logging."""
    violations = []

    if not core_path.exists():
        return violations

    for py_file in core_path.rglob("*.py"):
        try:
            content = py_file.read_text()
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                for pattern, category in IO_PATTERNS:
                    if re.search(pattern, line):
                        violations.append(
                            ArchViolation(
                                file=str(py_file),
                                line=i,
                                category=f"model_{category}",
                                message=f"Found {category} in core model: {line.strip()[:60]}",
                            )
                        )
                        break

        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}", file=sys.stderr)

    return violations


def analyze_file_metrics(target: Path) -> list[FileMetrics]:
    """Analyze file metrics (lines, classes, methods, imports)."""
    metrics = []

    for py_file in target.rglob("*.py"):
        try:
            content = py_file.read_text()
            lines = len(content.splitlines())

            # Parse AST for class/method counts
            try:
                tree = ast.parse(content)

                classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                num_classes = len(classes)

                # Find max methods in any class
                max_methods = 0
                for cls in classes:
                    methods = [
                        node
                        for node in ast.walk(cls)
                        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                    ]
                    max_methods = max(max_methods, len(methods))

                # Count imports
                imports = len(
                    [
                        node
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Import | ast.ImportFrom)
                    ]
                )

            except SyntaxError:
                num_classes = 0
                max_methods = 0
                imports = 0

            metrics.append(
                FileMetrics(
                    path=str(py_file),
                    lines=lines,
                    classes=num_classes,
                    max_methods=max_methods,
                    imports=imports,
                )
            )

        except Exception as e:
            print(f"Warning: Could not analyze {py_file}: {e}", file=sys.stderr)

    return metrics


def check_file_sizes(metrics: list[FileMetrics], threshold: int = 400) -> list[ArchViolation]:
    """Check for files exceeding line threshold."""
    violations = []

    for m in metrics:
        if m.lines > threshold:
            # Check if it's a package (has __init__.py sibling)
            path = Path(m.path)
            is_package = path.name == "__init__.py"

            if not is_package:
                violations.append(
                    ArchViolation(
                        file=m.path,
                        line=1,
                        category="file_size",
                        message=f"File has {m.lines} lines (threshold: {threshold}). Consider converting to package.",
                        severity="warning",
                    )
                )

    return violations


def check_god_objects(metrics: list[FileMetrics]) -> list[ArchViolation]:
    """Check for potential God objects."""
    violations = []

    for m in metrics:
        # Too many methods
        if m.max_methods > 10:
            violations.append(
                ArchViolation(
                    file=m.path,
                    line=1,
                    category="god_object",
                    message=f"Class has {m.max_methods} methods (threshold: 10). Consider extracting mixins.",
                    severity="warning",
                )
            )

        # Too many imports
        if m.imports > 15:
            violations.append(
                ArchViolation(
                    file=m.path,
                    line=1,
                    category="coupling",
                    message=f"File has {m.imports} imports (threshold: 15). May indicate high coupling.",
                    severity="warning",
                )
            )

    return violations


def check_patterns(target: Path) -> dict[str, bool]:
    """Check for Bengal architecture patterns."""
    patterns = {
        "uses_mixins": False,
        "uses_delegation": False,
        "uses_dataclasses": False,
        "orchestrators_exist": False,
        "core_has_no_io": True,  # Assume true, violations mark false
    }

    for py_file in target.rglob("*.py"):
        try:
            content = py_file.read_text()

            if "Mixin)" in content or "Mixin," in content:
                patterns["uses_mixins"] = True

            if "Orchestrator.build(" in content or "Orchestrator.render(" in content:
                patterns["uses_delegation"] = True

            if "@dataclass" in content:
                patterns["uses_dataclasses"] = True

            if "orchestration" in str(py_file) and "Orchestrator" in content:
                patterns["orchestrators_exist"] = True

        except Exception:
            pass

    return patterns


def calculate_confidence(result: ArchAuditResult) -> int:
    """Calculate confidence score (0-100)."""
    score = 100

    # Deduct for violations
    for v in result.violations:
        if v.severity == "error":
            score -= 10
        else:
            score -= 5

    # Bonus for good patterns
    pattern_bonus = sum(5 for v in result.patterns.values() if v)
    score += pattern_bonus

    return max(0, min(100, score))


def main():
    parser = argparse.ArgumentParser(description="Audit Bengal architecture")
    parser.add_argument("target", type=Path, help="Target directory to audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.target.exists():
        print(f"Error: {args.target} does not exist", file=sys.stderr)
        sys.exit(1)

    result = ArchAuditResult()

    print(f"Auditing architecture in {args.target}...", file=sys.stderr)

    # Check model purity (only for core/)
    core_path = args.target / "core" if (args.target / "core").exists() else None
    if core_path:
        purity_violations = check_model_purity(core_path)
        result.violations.extend(purity_violations)
        if purity_violations:
            result.patterns["core_has_no_io"] = False

    # Analyze file metrics
    result.file_metrics = analyze_file_metrics(args.target)

    # Check file sizes
    result.violations.extend(check_file_sizes(result.file_metrics))

    # Check for God objects
    result.violations.extend(check_god_objects(result.file_metrics))

    # Check patterns
    result.patterns = check_patterns(args.target)

    # Calculate confidence
    result.confidence = calculate_confidence(result)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # Human-readable output
        print(f"\n{'=' * 60}")
        print(f"ARCHITECTURE AUDIT: {args.target}")
        print(f"{'=' * 60}\n")

        if result.violations:
            print(f"Violations: {len(result.violations)}")
            for v in result.violations:
                status = "❌" if v.severity == "error" else "⚠️"
                print(f"  {status} [{v.category}] {v.file}:{v.line}")
                print(f"     {v.message}")
        else:
            print("✅ No violations found")

        print(f"\nLarge files (>{400} lines):")
        large_files = [m for m in result.file_metrics if m.lines > 400]
        if large_files:
            for m in large_files:
                print(f"  ⚠️ {m.path}: {m.lines} lines")
        else:
            print("  ✅ All files within threshold")

        print("\nPatterns:")
        for pattern, found in result.patterns.items():
            status = "✅" if found else "❌"
            print(f"  {status} {pattern}")

        print(f"\nConfidence: {result.confidence}%")
        if result.confidence >= 90:
            print("  Status: 🟢 HIGH")
        elif result.confidence >= 70:
            print("  Status: 🟡 MODERATE")
        elif result.confidence >= 50:
            print("  Status: 🟠 LOW")
        else:
            print("  Status: 🔴 UNCERTAIN")


if __name__ == "__main__":
    main()

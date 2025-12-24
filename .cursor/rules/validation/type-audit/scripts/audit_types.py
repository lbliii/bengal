#!/usr/bin/env python3
"""
Type system audit script for Bengal.

Runs mypy and analyzes Any usage patterns.

Usage:
    python audit_types.py bengal/
    python audit_types.py bengal/core/ --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TypeIssue:
    """A type-related issue found during audit."""

    file: str
    line: int
    message: str
    code: str
    severity: str = "error"


@dataclass
class AnyUsage:
    """An occurrence of Any in the codebase."""

    file: str
    line: int
    context: str
    classification: str = "unknown"
    acceptable: bool = False


@dataclass
class TypeAuditResult:
    """Result of type system audit."""

    mypy_errors: list[TypeIssue] = field(default_factory=list)
    any_usages: list[AnyUsage] = field(default_factory=list)
    patterns: dict[str, bool] = field(default_factory=dict)
    confidence: int = 0

    def to_dict(self) -> dict:
        return {
            "mypy_errors": [
                {
                    "file": e.file,
                    "line": e.line,
                    "message": e.message,
                    "code": e.code,
                }
                for e in self.mypy_errors
            ],
            "any_usages": [
                {
                    "file": a.file,
                    "line": a.line,
                    "context": a.context,
                    "classification": a.classification,
                    "acceptable": a.acceptable,
                }
                for a in self.any_usages
            ],
            "patterns": self.patterns,
            "confidence": self.confidence,
        }


def run_mypy(target: Path) -> list[TypeIssue]:
    """Run mypy and parse output."""
    issues = []

    try:
        result = subprocess.run(
            ["mypy", str(target), "--show-error-codes", "--no-error-summary"],
            capture_output=True,
            text=True,
        )

        # Parse mypy output: file.py:line: error: message [code]
        pattern = re.compile(r"(.+):(\d+): (error|warning): (.+) \[(.+)\]")

        for line in result.stdout.splitlines():
            match = pattern.match(line)
            if match:
                issues.append(
                    TypeIssue(
                        file=match.group(1),
                        line=int(match.group(2)),
                        severity=match.group(3),
                        message=match.group(4),
                        code=match.group(5),
                    )
                )
    except FileNotFoundError:
        print("Warning: mypy not found, skipping mypy checks", file=sys.stderr)

    return issues


def find_any_usages(target: Path) -> list[AnyUsage]:
    """Find all usages of Any in Python files."""
    usages = []

    any_patterns = [
        re.compile(r":\s*Any\b"),
        re.compile(r"->\s*Any\b"),
        re.compile(r"dict\[.+,\s*Any\]"),
        re.compile(r"list\[Any\]"),
    ]

    # Acceptable patterns
    acceptable_patterns = [
        "extra: dict[str, Any]",  # User extension point
        "props: dict[str, Any]",  # PageCore props
        "**kwargs: Any",  # Kwargs
        "TYPE_CHECKING",  # In TYPE_CHECKING block
    ]

    for py_file in target.rglob("*.py"):
        try:
            content = py_file.read_text()
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                for pattern in any_patterns:
                    if pattern.search(line):
                        # Determine classification
                        classification = "lazy_typing"
                        acceptable = False

                        for acc_pattern in acceptable_patterns:
                            if acc_pattern in line:
                                classification = "escape_hatch"
                                acceptable = True
                                break

                        if (
                            "TYPE_CHECKING"
                            in content[max(0, content.find(line) - 200) : content.find(line)]
                        ):
                            classification = "type_checking_block"
                            acceptable = True

                        usages.append(
                            AnyUsage(
                                file=str(py_file),
                                line=i,
                                context=line.strip()[:80],
                                classification=classification,
                                acceptable=acceptable,
                            )
                        )
                        break  # Only count once per line

        except Exception as e:
            print(f"Warning: Could not read {py_file}: {e}", file=sys.stderr)

    return usages


def check_patterns(target: Path) -> dict[str, bool]:
    """Check for Bengal type patterns."""
    patterns = {
        "frozen_dataclasses": False,
        "type_checking_imports": False,
        "typed_dict_usage": False,
        "modern_union_syntax": False,
        "no_optional_import": True,  # Should NOT import Optional
    }

    for py_file in target.rglob("*.py"):
        try:
            content = py_file.read_text()

            if "@dataclass(frozen=True)" in content:
                patterns["frozen_dataclasses"] = True

            if "if TYPE_CHECKING:" in content:
                patterns["type_checking_imports"] = True

            if "TypedDict" in content:
                patterns["typed_dict_usage"] = True

            if " | None" in content or " | " in content:
                patterns["modern_union_syntax"] = True

            if "from typing import Optional" in content:
                patterns["no_optional_import"] = False

        except Exception:
            pass

    return patterns


def calculate_confidence(result: TypeAuditResult) -> int:
    """Calculate confidence score (0-100)."""
    score = 0

    # mypy clean: 40 points
    if len(result.mypy_errors) == 0:
        score += 40
    else:
        # Deduct based on error count
        score += max(0, 40 - len(result.mypy_errors) * 5)

    # Any acceptable: 30 points
    if result.any_usages:
        acceptable_ratio = sum(1 for a in result.any_usages if a.acceptable) / len(
            result.any_usages
        )
        score += int(30 * acceptable_ratio)
    else:
        score += 30

    # Patterns followed: 15 points
    pattern_score = sum(1 for v in result.patterns.values() if v)
    score += int(15 * pattern_score / len(result.patterns))

    # Tests typed: 15 points (simplified - assume typed if mypy passes)
    if len(result.mypy_errors) == 0:
        score += 15

    return min(100, score)


def main():
    parser = argparse.ArgumentParser(description="Audit Bengal type system")
    parser.add_argument("target", type=Path, help="Target directory to audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.target.exists():
        print(f"Error: {args.target} does not exist", file=sys.stderr)
        sys.exit(1)

    result = TypeAuditResult()

    print(f"Auditing types in {args.target}...", file=sys.stderr)

    # Run checks
    result.mypy_errors = run_mypy(args.target)
    result.any_usages = find_any_usages(args.target)
    result.patterns = check_patterns(args.target)
    result.confidence = calculate_confidence(result)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        # Human-readable output
        print(f"\n{'=' * 60}")
        print(f"TYPE AUDIT RESULTS: {args.target}")
        print(f"{'=' * 60}\n")

        print(f"mypy errors: {len(result.mypy_errors)}")
        for err in result.mypy_errors[:10]:  # Show first 10
            print(f"  {err.file}:{err.line}: {err.message} [{err.code}]")
        if len(result.mypy_errors) > 10:
            print(f"  ... and {len(result.mypy_errors) - 10} more")

        print(f"\nAny usages: {len(result.any_usages)}")
        acceptable = sum(1 for a in result.any_usages if a.acceptable)
        print(f"  Acceptable: {acceptable}")
        print(f"  Needs review: {len(result.any_usages) - acceptable}")

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

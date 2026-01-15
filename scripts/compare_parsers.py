#!/usr/bin/env python3
"""Compare mistune vs patitas parser output on real site content.

Usage:
    python scripts/compare_parsers.py [--verbose] [--limit N] [--diff]

This script:
1. Finds all markdown files in site/content/
2. Parses each file with both mistune and patitas
3. Compares the HTML output
4. Reports differences and timing statistics
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# Add bengal to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.parsing import create_markdown_parser


@dataclass
class ComparisonResult:
    """Result of comparing parser outputs."""

    file: Path
    mistune_html: str
    patitas_html: str
    mistune_time_ms: float
    patitas_time_ms: float
    is_identical: bool
    normalized_identical: bool
    diff_lines: list[str] = field(default_factory=list)


@dataclass
class ComparisonStats:
    """Aggregate statistics."""

    total_files: int = 0
    identical: int = 0
    normalized_identical: int = 0
    different: int = 0
    errors: int = 0
    mistune_total_ms: float = 0.0
    patitas_total_ms: float = 0.0
    total_chars: int = 0
    directive_counts: Counter = field(default_factory=Counter)


class HTMLNormalizer(HTMLParser):
    """Normalize HTML for comparison."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._in_pre = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Sort attributes for consistent comparison
        sorted_attrs = sorted(attrs, key=lambda x: x[0])
        attr_str = " ".join(f'{k}="{v}"' if v else k for k, v in sorted_attrs if v is not None)
        if attr_str:
            self.parts.append(f"<{tag} {attr_str}>")
        else:
            self.parts.append(f"<{tag}>")
        if tag == "pre":
            self._in_pre = True

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f"</{tag}>")
        if tag == "pre":
            self._in_pre = False

    def handle_data(self, data: str) -> None:
        if self._in_pre:
            self.parts.append(data)
        else:
            # Normalize whitespace outside <pre>
            normalized = " ".join(data.split())
            if normalized:
                self.parts.append(normalized)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def get_normalized(self) -> str:
        return "".join(self.parts)


def normalize_html(html: str) -> str:
    """Normalize HTML for comparison."""
    try:
        normalizer = HTMLNormalizer()
        normalizer.feed(html)
        return normalizer.get_normalized()
    except Exception:
        # Fallback: basic normalization
        html = re.sub(r"\s+", " ", html)
        html = re.sub(r">\s+<", "><", html)
        return html.strip()


def count_directives(content: str) -> Counter:
    """Count directive usage in markdown content."""
    pattern = r"^:::\{(\w+(?:-\w+)*)\}"
    matches = re.findall(pattern, content, re.MULTILINE)
    return Counter(matches)


def compare_file(
    file_path: Path,
    mistune_parser: Any,
    patitas_parser: Any,
) -> ComparisonResult:
    """Compare parser outputs for a single file."""
    content = file_path.read_text(encoding="utf-8")

    # Parse with mistune
    start = time.perf_counter()
    try:
        mistune_html = mistune_parser.parse(content, {})
    except Exception as e:
        mistune_html = f"<!-- MISTUNE ERROR: {e} -->"
    mistune_time = (time.perf_counter() - start) * 1000

    # Parse with patitas
    start = time.perf_counter()
    try:
        patitas_html = patitas_parser.parse(content, {})
    except Exception as e:
        patitas_html = f"<!-- PATITAS ERROR: {e} -->"
    patitas_time = (time.perf_counter() - start) * 1000

    # Compare
    is_identical = mistune_html == patitas_html

    # Normalized comparison
    norm_mistune = normalize_html(mistune_html)
    norm_patitas = normalize_html(patitas_html)
    normalized_identical = norm_mistune == norm_patitas

    # Generate diff if different
    diff_lines = []
    if not is_identical:
        differ = difflib.unified_diff(
            mistune_html.splitlines(keepends=True),
            patitas_html.splitlines(keepends=True),
            fromfile="mistune",
            tofile="patitas",
            lineterm="",
        )
        diff_lines = list(differ)[:100]  # Limit diff size

    return ComparisonResult(
        file=file_path,
        mistune_html=mistune_html,
        patitas_html=patitas_html,
        mistune_time_ms=mistune_time,
        patitas_time_ms=patitas_time,
        is_identical=is_identical,
        normalized_identical=normalized_identical,
        diff_lines=diff_lines,
    )


def run_comparison(
    content_dir: Path,
    verbose: bool = False,
    limit: int | None = None,
    show_diff: bool = False,
) -> ComparisonStats:
    """Run full comparison on site content."""
    # Create parsers
    print("🔧 Creating parsers...")
    mistune_parser = create_markdown_parser("mistune")
    patitas_parser = create_markdown_parser("patitas")

    # Find all markdown files
    md_files = sorted(content_dir.rglob("*.md"))
    if limit:
        md_files = md_files[:limit]

    print(f"📄 Found {len(md_files)} markdown files")
    print()

    stats = ComparisonStats()
    results: list[ComparisonResult] = []

    # Process each file
    for i, file_path in enumerate(md_files, 1):
        rel_path = file_path.relative_to(content_dir)

        # Count directives
        content = file_path.read_text(encoding="utf-8")
        stats.directive_counts.update(count_directives(content))
        stats.total_chars += len(content)

        # Compare
        result = compare_file(file_path, mistune_parser, patitas_parser)
        results.append(result)

        # Update stats
        stats.total_files += 1
        stats.mistune_total_ms += result.mistune_time_ms
        stats.patitas_total_ms += result.patitas_time_ms

        if result.is_identical:
            stats.identical += 1
            status = "✅"
        elif result.normalized_identical:
            stats.normalized_identical += 1
            status = "🟡"
        else:
            stats.different += 1
            status = "❌"

        # Progress
        if verbose or not result.is_identical:
            speedup = result.mistune_time_ms / max(result.patitas_time_ms, 0.01)
            print(
                f"{status} [{i:3d}/{len(md_files)}] {rel_path} "
                f"(mistune: {result.mistune_time_ms:.1f}ms, "
                f"patitas: {result.patitas_time_ms:.1f}ms, "
                f"speedup: {speedup:.2f}x)"
            )

            if show_diff and result.diff_lines and not result.is_identical:
                print("--- Diff (first 20 lines):")
                for line in result.diff_lines[:20]:
                    print(f"    {line.rstrip()}")
                print()

    return stats


def print_summary(stats: ComparisonStats) -> None:
    """Print summary statistics."""
    print()
    print("=" * 70)
    print("📊 COMPARISON SUMMARY")
    print("=" * 70)
    print()

    # Results
    total = stats.total_files
    pct_identical = (stats.identical / total * 100) if total else 0
    pct_norm = (stats.normalized_identical / total * 100) if total else 0
    pct_diff = (stats.different / total * 100) if total else 0

    print(f"{'Files processed:':<30} {total:>8}")
    print(f"{'Identical output:':<30} {stats.identical:>8} ({pct_identical:.1f}%)")
    print(f"{'Normalized identical:':<30} {stats.normalized_identical:>8} ({pct_norm:.1f}%)")
    print(f"{'Different output:':<30} {stats.different:>8} ({pct_diff:.1f}%)")
    print()

    # Timing
    avg_mistune = stats.mistune_total_ms / total if total else 0
    avg_patitas = stats.patitas_total_ms / total if total else 0
    speedup = stats.mistune_total_ms / max(stats.patitas_total_ms, 0.01)

    print("⏱️  TIMING")
    print("-" * 40)
    print(f"{'Mistune total:':<30} {stats.mistune_total_ms:>8.1f} ms")
    print(f"{'Patitas total:':<30} {stats.patitas_total_ms:>8.1f} ms")
    print(f"{'Mistune avg/file:':<30} {avg_mistune:>8.2f} ms")
    print(f"{'Patitas avg/file:':<30} {avg_patitas:>8.2f} ms")
    print(f"{'Speedup factor:':<30} {speedup:>8.2f}x")
    print()

    # Content stats
    kb_total = stats.total_chars / 1024
    print("📝 CONTENT")
    print("-" * 40)
    print(f"{'Total content:':<30} {kb_total:>8.1f} KB")
    print(f"{'Throughput (mistune):':<30} {kb_total / (stats.mistune_total_ms / 1000):>8.1f} KB/s")
    print(f"{'Throughput (patitas):':<30} {kb_total / (stats.patitas_total_ms / 1000):>8.1f} KB/s")
    print()

    # Directive usage
    if stats.directive_counts:
        print("📋 DIRECTIVE USAGE (top 15)")
        print("-" * 40)
        for directive, count in stats.directive_counts.most_common(15):
            print(f"  {directive:<25} {count:>5}")
        print(f"  {'--- Total ---':<25} {sum(stats.directive_counts.values()):>5}")
    print()

    # Final verdict
    print("=" * 70)
    if stats.different == 0:
        if stats.normalized_identical == 0:
            print("🎉 PERFECT MATCH: All files produce identical HTML output!")
        else:
            print(
                f"✅ MATCH: All files match (some whitespace differences in {stats.normalized_identical} files)"
            )
    else:
        print(f"⚠️  DIFFERENCES: {stats.different} files have different output")
        print("   Run with --diff to see detailed differences")
    print("=" * 70)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare mistune vs patitas parser output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all file results")
    parser.add_argument(
        "--limit", "-n", type=int, default=None, help="Limit number of files to process"
    )
    parser.add_argument("--diff", "-d", action="store_true", help="Show diff for different files")
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=Path(__file__).parent.parent / "site" / "content",
        help="Path to content directory",
    )
    args = parser.parse_args()

    if not args.content_dir.exists():
        print(f"❌ Content directory not found: {args.content_dir}")
        return 1

    print("🐾 Patitas vs Mistune Parser Comparison")
    print("=" * 70)
    print(f"Content directory: {args.content_dir}")
    print()

    stats = run_comparison(
        args.content_dir,
        verbose=args.verbose,
        limit=args.limit,
        show_diff=args.diff,
    )

    print_summary(stats)

    return 0 if stats.different == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

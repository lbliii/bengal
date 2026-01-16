#!/usr/bin/env python3
"""Check file sizes and enforce 400-line threshold for new files.

This script enforces a 400-line limit on new Python files to prevent
monolithic modules. Existing large files are allowed via a baseline.

Usage:
    python scripts/check_file_sizes.py
    python scripts/check_file_sizes.py --strict  # Fail on any file over limit

Exit codes:
    0: All files within limits (or only baseline files exceed)
    1: New files found exceeding limit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Maximum lines allowed for new files
MAX_LINES = 400

# Baseline: Existing large files that are allowed to exceed the limit.
# These should be refactored over time, but won't fail CI.
# Add file paths relative to repo root.
# Last updated: Sprint 6 (December 2024)
BASELINE_FILES = {
    # ==================== HIGH PRIORITY (>800 lines) ====================
    "bengal/orchestration/incremental.py",  # 1176 - refactor target
    "bengal/analysis/knowledge_graph.py",  # 982
    "bengal/core/section.py",  # 799
    "bengal/content/discovery/content_discovery.py",  # 799
    # ==================== MEDIUM PRIORITY (600-800 lines) ====================
    "bengal/rendering/pipeline/core.py",  # 773
    "bengal/orchestration/taxonomy.py",  # 703
    "bengal/cli/commands/theme.py",  # 680
    "bengal/cli/commands/debug.py",  # 679
    "bengal/health/report.py",  # 678
    "bengal/rendering/renderer.py",  # 672
    "bengal/health/autofix.py",  # 650
    "bengal/directives/embed.py",  # 619
    "bengal/orchestration/content.py",  # 618
    "bengal/autodoc/utils.py",  # 612
    "bengal/core/page/proxy.py",  # 607
    "bengal/utils/file_io.py",  # 606
    "bengal/server/dev_server.py",  # 602
    "bengal/directives/video.py",  # 598
    "bengal/orchestration/asset.py",  # 598
    "bengal/analysis/graph_visualizer.py",  # 596
    "bengal/orchestration/render.py",  # 585
    "bengal/server/request_handler.py",  # 585
    "bengal/autodoc/extractors/python/extractor.py",  # 579
    # ==================== LOWER PRIORITY (400-600 lines) ====================
    "bengal/debug/content_migrator.py",  # 567
    "bengal/debug/config_inspector.py",  # 565
    "bengal/autodoc/orchestration/orchestrator.py",  # 564
    "bengal/autodoc/extractors/cli.py",  # 553
    "bengal/core/asset/asset_core.py",  # 542
    "bengal/autodoc/docstring_parser.py",  # 537
    "bengal/health/health_check.py",  # 533
    "bengal/orchestration/build/__init__.py",  # 520
    "bengal/health/validators/directives/analysis.py",  # 517
    "bengal/analysis/path_analysis.py",  # 516
    "bengal/core/menu.py",  # 508
    "bengal/collections/validator.py",  # 506
    "bengal/debug/delta_analyzer.py",  # 505
    "bengal/cache/build_cache/core.py",  # 504
    "bengal/cli/commands/config.py",  # 497
    "bengal/rendering/errors.py",  # 497
    "bengal/cli/commands/build.py",  # 496
    "bengal/server/live_reload.py",  # 495
    "bengal/core/page/metadata.py",  # 490
    "bengal/cli/commands/version.py",  # 488
    "bengal/debug/explainer.py",  # 486
    "bengal/debug/incremental_debugger.py",  # 482
    "bengal/health/validators/links.py",  # 481
    "bengal/utils/logger.py",  # 480
    "bengal/debug/dependency_visualizer.py",  # 478
    "bengal/core/version.py",  # 471
    "bengal/server/build_trigger.py",  # 470
    "bengal/core/site/core.py",  # 467
    "bengal/directives/validator.py",  # 464
    "bengal/cli/progress.py",  # 460
    "bengal/core/page/__init__.py",  # 454
    "bengal/config/defaults.py",  # 451
    "bengal/parsing/backends/mistune/__init__.py",  # 447
    "bengal/rendering/template_functions/collections.py",  # 446
    "bengal/orchestration/build/initialization.py",  # 442
    "bengal/rendering/template_functions/strings.py",  # 426
    "bengal/analysis/performance_advisor.py",  # 411
    "bengal/directives/navigation.py",  # 411
    "bengal/cli/commands/project.py",  # 410
    "bengal/orchestration/menu.py",  # 409
    "bengal/analysis/graph_reporting.py",  # 404
    "bengal/cli/output/core.py",  # 402
    "bengal/output/core.py",  # 402
}


def count_lines(path: Path) -> int:
    """Count non-empty lines in a file."""
    try:
        return sum(1 for line in path.read_text().splitlines() if line.strip())
    except Exception:
        return 0


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files in the bengal package."""
    return sorted(root.rglob("*.py"))


def check_file_sizes(strict: bool = False) -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    """
    Check all Python files against the line limit.

    Args:
        strict: If True, baseline files also count as violations

    Returns:
        (violations, baseline_exceeds) - Lists of (path, line_count) tuples
    """
    repo_root = Path(__file__).parent.parent
    bengal_dir = repo_root / "bengal"

    if not bengal_dir.exists():
        print(f"Error: bengal directory not found at {bengal_dir}")
        sys.exit(1)

    violations: list[tuple[Path, int]] = []
    baseline_exceeds: list[tuple[Path, int]] = []

    for py_file in find_python_files(bengal_dir):
        line_count = count_lines(py_file)

        if line_count > MAX_LINES:
            rel_path = str(py_file.relative_to(repo_root))

            if rel_path in BASELINE_FILES and not strict:
                baseline_exceeds.append((py_file, line_count))
            else:
                violations.append((py_file, line_count))

    return violations, baseline_exceeds


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check Python file sizes")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on ALL files over limit, including baseline",
    )
    args = parser.parse_args()

    violations, baseline_exceeds = check_file_sizes(strict=args.strict)

    # Report baseline files (informational)
    if baseline_exceeds:
        print(f"\n📋 Baseline files exceeding {MAX_LINES} lines (allowed):")
        for path, count in sorted(baseline_exceeds, key=lambda x: -x[1]):
            print(f"   {count:4d} lines: {path.relative_to(Path.cwd())}")

    # Report violations
    if violations:
        print(f"\n❌ Files exceeding {MAX_LINES}-line limit:")
        for path, count in sorted(violations, key=lambda x: -x[1]):
            print(f"   {count:4d} lines: {path.relative_to(Path.cwd())}")

        print(f"\n💡 Refactor these files or add to BASELINE_FILES in {__file__}")
        return 1

    # Success
    if not baseline_exceeds:
        print(f"\n✅ All files within {MAX_LINES}-line limit")
    else:
        print(f"\n✅ No new files exceed {MAX_LINES}-line limit")

    return 0


if __name__ == "__main__":
    sys.exit(main())

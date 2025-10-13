#!/usr/bin/env python3
"""
Investigation script to count parser instances during a build.

Usage:
    python tests/performance/investigate_parser_instances.py

This will build the showcase site and report:
1. How many parser instances were created
2. Which threads created them
3. Why they were created (stack traces)
"""

import sys
import threading
from pathlib import Path

# Monkey-patch the parser creation to track instances
original_mistune_parser_init = None
parser_instances = []
parser_lock = threading.Lock()


def instrumented_init(self):
    """Instrumented __init__ that tracks parser creation."""
    original_mistune_parser_init(self)

    import traceback

    with parser_lock:
        parser_instances.append(
            {
                "id": id(self),
                "thread": threading.current_thread().name,
                "stack": traceback.format_stack(limit=8),
            }
        )
        print(
            f"[PARSER #{len(parser_instances)}] Created in thread '{threading.current_thread().name}' "
            f"(instance id: {id(self)})",
            file=sys.stderr,
        )


def main():
    """Run instrumented build."""
    # Apply monkey patch
    from bengal.rendering import parsers

    global original_mistune_parser_init
    original_mistune_parser_init = parsers.MistuneParser.__init__
    parsers.MistuneParser.__init__ = instrumented_init

    print("=" * 70)
    print("PARSER INSTANCE INVESTIGATION")
    print("=" * 70)
    print()

    # Run build
    from bengal.core.site import Site
    from bengal.orchestration.build import BuildOrchestrator

    site_path = Path(__file__).parent.parent.parent / "examples" / "showcase"
    print(f"Building: {site_path}")
    print()

    try:
        site = Site(root_path=site_path, config={})
        orchestrator = BuildOrchestrator(site)

        print("Starting build...")
        orchestrator.build()
        print()

    except Exception as e:
        print(f"Build failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    # Report results
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    with parser_lock:
        print(f"Total MistuneParser instances created: {len(parser_instances)}")
        print()

        # Count by thread
        by_thread = {}
        for p in parser_instances:
            thread = p["thread"]
            by_thread[thread] = by_thread.get(thread, 0) + 1

        print("By thread:")
        for thread, count in sorted(by_thread.items()):
            print(f"  {thread}: {count} parsers")
        print()

        # Show stack traces for first few
        print("Creation stack traces (first 3):")
        for i, p in enumerate(parser_instances[:3]):
            print(f"\n[PARSER #{i + 1}] Thread: {p['thread']}")
            print("".join(p["stack"][-5:]))  # Last 5 frames

        if len(parser_instances) > 3:
            print(f"\n... and {len(parser_instances) - 3} more")

    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()

    # Expected vs actual
    max_workers = 4  # Default
    expected_max = max_workers  # One per thread
    actual = len(parser_instances)

    print(f"Expected parsers (with perfect caching): {expected_max}")
    print(f"Actual parsers created: {actual}")

    if actual > expected_max * 2:
        print()
        print("⚠️  WARNING: Creating way more parsers than expected!")
        print("   This suggests thread-local caching isn't working properly.")
        overhead = (actual - expected_max) * 10  # Assume ~10ms per parser
        print(f"   Estimated wasted time: ~{overhead}ms")
    elif actual > expected_max:
        print()
        print("⚠️  Creating more parsers than threads.")
        print("   This might be intentional (e.g., different engines) or a caching issue.")
    else:
        print()
        print("✓  Parser creation looks optimal!")

    print()


if __name__ == "__main__":
    main()

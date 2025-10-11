#!/usr/bin/env python3
"""
Investigation script to count ALL parser instances during a build.

Tracks both MistuneParser and PythonMarkdownParser.
"""

import sys
import threading
from pathlib import Path

# Monkey-patch both parser types
mistune_instances = []
python_markdown_instances = []
parser_lock = threading.Lock()

original_mistune_init = None
original_python_markdown_init = None


def instrumented_mistune_init(self):
    """Instrumented MistuneParser.__init__."""
    original_mistune_init(self)
    with parser_lock:
        mistune_instances.append({
            'id': id(self),
            'thread': threading.current_thread().name,
        })
        print(f"[MISTUNE #{len(mistune_instances)}] Created in thread '{threading.current_thread().name}'",
              file=sys.stderr)


def instrumented_python_markdown_init(self):
    """Instrumented PythonMarkdownParser.__init__."""
    original_python_markdown_init(self)
    with parser_lock:
        python_markdown_instances.append({
            'id': id(self),
            'thread': threading.current_thread().name,
        })
        print(f"[PYTHON-MARKDOWN #{len(python_markdown_instances)}] Created in thread '{threading.current_thread().name}'",
              file=sys.stderr)


def main():
    """Run instrumented build."""
    # Apply monkey patches
    from bengal.rendering import parser

    global original_mistune_init, original_python_markdown_init
    original_mistune_init = parser.MistuneParser.__init__
    original_python_markdown_init = parser.PythonMarkdownParser.__init__

    parser.MistuneParser.__init__ = instrumented_mistune_init
    parser.PythonMarkdownParser.__init__ = instrumented_python_markdown_init

    print("=" * 70)
    print("PARSER INSTANCE INVESTIGATION (ALL TYPES)")
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
        orchestrator.build()

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
        total = len(mistune_instances) + len(python_markdown_instances)
        print(f"Total parser instances created: {total}")
        print(f"  - MistuneParser: {len(mistune_instances)}")
        print(f"  - PythonMarkdownParser: {len(python_markdown_instances)}")
        print()

        # Count by thread
        all_instances = [
            ('Mistune', p) for p in mistune_instances
        ] + [
            ('PythonMarkdown', p) for p in python_markdown_instances
        ]

        if all_instances:
            by_thread = {}
            for parser_type, p in all_instances:
                thread = p['thread']
                if thread not in by_thread:
                    by_thread[thread] = {'Mistune': 0, 'PythonMarkdown': 0}
                by_thread[thread][parser_type] += 1

            print("By thread:")
            for thread in sorted(by_thread.keys()):
                counts = by_thread[thread]
                print(f"  {thread}:")
                print(f"    Mistune: {counts['Mistune']}")
                print(f"    PythonMarkdown: {counts['PythonMarkdown']}")
            print()

    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()

    max_workers = 4
    expected_max = max_workers
    actual = len(mistune_instances) + len(python_markdown_instances)

    print(f"Expected parsers (with perfect caching): {expected_max}")
    print(f"Actual parsers created: {actual}")

    if actual > expected_max * 2:
        print()
        print("⚠️  WARNING: Creating way more parsers than expected!")
        overhead = (actual - expected_max) * 10
        print(f"   Estimated wasted time: ~{overhead}ms")
    elif actual > expected_max:
        print()
        print("⚠️  Creating more parsers than threads.")
    else:
        print()
        print("✓  Parser creation looks optimal!")


if __name__ == "__main__":
    main()

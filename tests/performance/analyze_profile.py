#!/usr/bin/env python
"""
Analyze performance profiling data from bengal build --perf-profile.

Usage:
    python analyze_profile.py profile.stats
    python analyze_profile.py profile.stats --top 50
    python analyze_profile.py profile.stats --sort time
"""

import argparse
import pstats
import sys
from pathlib import Path


def analyze_profile(profile_path: Path, top: int = 30, sort_by: str = 'cumulative'):
    """Analyze and display profiling data."""

    if not profile_path.exists():
        print(f"❌ Profile file not found: {profile_path}")
        sys.exit(1)

    print(f"📊 Analyzing profile: {profile_path}\n")

    # Load profiling data
    stats = pstats.Stats(str(profile_path))

    # Display different views
    print("=" * 80)
    print(f"Top {top} functions by CUMULATIVE time (total time including calls)")
    print("=" * 80)
    stats.sort_stats('cumulative')
    stats.print_stats(top)

    print("\n" + "=" * 80)
    print(f"Top {top} functions by TOTAL time (time spent in function itself)")
    print("=" * 80)
    stats.sort_stats('tottime')
    stats.print_stats(top)

    print("\n" + "=" * 80)
    print(f"Top {top} most called functions")
    print("=" * 80)
    stats.sort_stats('ncalls')
    stats.print_stats(top)

    # Callers analysis for top functions
    print("\n" + "=" * 80)
    print("Callers of top 10 time-consuming functions:")
    print("=" * 80)
    stats.sort_stats('tottime')
    stats.print_callers(10)

    # Extract key bottlenecks
    print("\n" + "=" * 80)
    print("🔥 KEY BOTTLENECKS (functions taking >1% of total time):")
    print("=" * 80)

    stats.sort_stats('tottime')

    # Get stats as a list
    stats_list = []
    for func, (_cc, nc, tt, ct, _callers) in stats.stats.items():
        filename, line, func_name = func
        # Filter out stdlib and external libraries
        if 'bengal' in filename or '<built-in' in filename:
            stats_list.append({
                'function': func_name,
                'file': filename,
                'line': line,
                'total_time': tt,
                'cum_time': ct,
                'ncalls': nc,
            })

    # Sort by total time and take top 20
    stats_list.sort(key=lambda x: x['total_time'], reverse=True)

    print(f"\n{'Function':<40} {'File':<50} {'Time (s)':<10} {'Cum Time':<10} {'Calls'}")
    print("-" * 120)

    total_time = sum(s['total_time'] for s in stats_list)

    for s in stats_list[:20]:
        file_short = Path(s['file']).name if 'bengal' in s['file'] else s['file']
        pct = (s['total_time'] / total_time * 100) if total_time > 0 else 0

        print(f"{s['function']:<40} {file_short:<50} {s['total_time']:>8.3f} ({pct:>4.1f}%)  "
              f"{s['cum_time']:>8.3f}  {s['ncalls']:>8}")

    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS:")
    print("=" * 80)

    # Analyze patterns
    recommendations = []

    # Check for regex compilation
    regex_time = sum(s['total_time'] for s in stats_list if 're.' in s['function'] or 'compile' in s['function'])
    if regex_time > 0.1:
        recommendations.append(f"• Consider caching compiled regex patterns ({regex_time:.2f}s in regex operations)")

    # Check for file I/O
    io_time = sum(s['total_time'] for s in stats_list if 'read' in s['function'] or 'write' in s['function'] or 'open' in s['function'])
    if io_time > 0.5:
        recommendations.append(f"• File I/O is significant ({io_time:.2f}s) - consider buffering or parallel I/O")

    # Check for Jinja2
    jinja_time = sum(s['total_time'] for s in stats_list if 'jinja2' in s['file'].lower())
    if jinja_time > 0.5:
        recommendations.append(f"• Template rendering is significant ({jinja_time:.2f}s) - check bytecode caching")

    # Check for markdown parsing
    markdown_time = sum(s['total_time'] for s in stats_list if 'mistune' in s['file'].lower() or 'markdown' in s['file'].lower())
    if markdown_time > 0.5:
        recommendations.append(f"• Markdown parsing is significant ({markdown_time:.2f}s) - consider content caching")

    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("• Profile looks good! No obvious bottlenecks detected.")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Bengal SSG performance profiling data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_profile.py profile.stats
  python analyze_profile.py profile.stats --top 50
  python analyze_profile.py profile.stats --sort time
        """
    )

    parser.add_argument('profile', type=Path, help='Path to profile data file (.stats)')
    parser.add_argument('--top', '-n', type=int, default=30, help='Number of top functions to show (default: 30)')
    parser.add_argument('--sort', '-s', choices=['cumulative', 'time', 'calls'], default='cumulative',
                       help='Sort by cumulative time, total time, or call count')

    args = parser.parse_args()

    analyze_profile(args.profile, args.top, args.sort)


if __name__ == '__main__':
    main()


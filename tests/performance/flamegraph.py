#!/usr/bin/env python
"""
Generate flame graphs from profiling data.

Supports multiple visualization tools:
- snakeviz (interactive HTML)
- flameprof (static SVG)
- gprof2dot (call graph)

Usage:
    python flamegraph.py profile.stats
    python flamegraph.py profile.stats --tool snakeviz
    python flamegraph.py profile.stats --tool gprof2dot --output graph.png
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_tool_installed(tool: str) -> bool:
    """Check if a visualization tool is installed."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False


def generate_snakeviz(profile_path: Path, output_dir: Path | None = None):
    """Generate interactive HTML flame graph with snakeviz."""
    if not check_tool_installed("snakeviz"):
        print("❌ snakeviz not installed. Install with: pip install snakeviz")
        return False

    print("🔥 Generating interactive flame graph with snakeviz...")
    print(f"   Profile: {profile_path}")

    # snakeviz opens a web browser automatically
    subprocess.run(["snakeviz", str(profile_path)])

    return True


def generate_flameprof(profile_path: Path, output_path: Path | None = None):
    """Generate static SVG flame graph with flameprof."""
    if not check_tool_installed("flameprof"):
        print("❌ flameprof not installed. Install with: pip install flameprof")
        return False

    if output_path is None:
        output_path = profile_path.with_suffix(".svg")

    print("🔥 Generating static flame graph with flameprof...")
    print(f"   Profile: {profile_path}")
    print(f"   Output:  {output_path}")

    try:
        result = subprocess.run(
            ["flameprof", str(profile_path)], capture_output=True, text=True, check=True
        )

        output_path.write_text(result.stdout)
        print(f"✓ Flame graph saved to: {output_path}")
        print(f"  Open with: open {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating flame graph: {e}")
        return False


def generate_gprof2dot(profile_path: Path, output_path: Path | None = None):
    """Generate call graph with gprof2dot."""
    if not check_tool_installed("gprof2dot"):
        print("❌ gprof2dot not installed. Install with: pip install gprof2dot")
        return False

    if not check_tool_installed("dot"):
        print("❌ graphviz not installed. Install with: brew install graphviz")
        return False

    if output_path is None:
        output_path = profile_path.with_suffix(".png")

    print("📊 Generating call graph with gprof2dot...")
    print(f"   Profile: {profile_path}")
    print(f"   Output:  {output_path}")

    try:
        # Convert profile to dot format
        dot_result = subprocess.run(
            ["gprof2dot", "-f", "pstats", str(profile_path)],
            capture_output=True,
            text=True,
            check=True,
        )

        # Convert dot to PNG
        subprocess.run(
            ["dot", "-Tpng", "-o", str(output_path)], input=dot_result.stdout, text=True, check=True
        )

        print(f"✓ Call graph saved to: {output_path}")
        print(f"  Open with: open {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating call graph: {e}")
        return False


def list_available_tools():
    """List available visualization tools."""
    print("\n📊 Available Visualization Tools:")
    print("-" * 60)

    tools = {
        "snakeviz": ("Interactive HTML flame graph", "pip install snakeviz"),
        "flameprof": ("Static SVG flame graph", "pip install flameprof"),
        "gprof2dot": (
            "Call graph (requires graphviz)",
            "pip install gprof2dot && brew install graphviz",
        ),
    }

    for tool, (desc, install) in tools.items():
        installed = check_tool_installed(tool)
        status = "✅ installed" if installed else "❌ not installed"
        print(f"\n{tool:15} {status}")
        print(f"  {desc}")
        if not installed:
            print(f"  Install: {install}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Generate flame graphs from profiling data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive HTML (opens browser)
  python flamegraph.py profile.stats --tool snakeviz

  # Static SVG
  python flamegraph.py profile.stats --tool flameprof --output flame.svg

  # Call graph
  python flamegraph.py profile.stats --tool gprof2dot --output graph.png

  # List available tools
  python flamegraph.py --list-tools
        """,
    )

    parser.add_argument("profile", type=Path, nargs="?", help="Path to profile data file (.stats)")

    parser.add_argument(
        "--tool",
        "-t",
        choices=["snakeviz", "flameprof", "gprof2dot"],
        default="snakeviz",
        help="Visualization tool to use (default: snakeviz)",
    )

    parser.add_argument("--output", "-o", type=Path, help="Output file path (for static outputs)")

    parser.add_argument(
        "--list-tools", action="store_true", help="List available visualization tools"
    )

    args = parser.parse_args()

    if args.list_tools:
        list_available_tools()
        return 0

    if not args.profile:
        parser.print_help()
        print("\n❌ Error: profile file required (or use --list-tools)")
        return 1

    if not args.profile.exists():
        print(f"❌ Profile file not found: {args.profile}")
        return 1

    # Generate visualization
    success = False

    if args.tool == "snakeviz":
        success = generate_snakeviz(args.profile, args.output)
    elif args.tool == "flameprof":
        success = generate_flameprof(args.profile, args.output)
    elif args.tool == "gprof2dot":
        success = generate_gprof2dot(args.profile, args.output)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

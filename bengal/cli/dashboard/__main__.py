"""
Dashboard Development Mode.

Run the dashboard directly for development and testing:
    python -m bengal.cli.dashboard

Options:
    --screen=build|serve|health  Start with specific screen (default: build)
    --demo                       Run with demo data (no site required)
    --css-watch                  Hot-reload CSS changes

Example:
    # Run build dashboard with demo data
    python -m bengal.cli.dashboard --demo

    # Run serve dashboard
    python -m bengal.cli.dashboard --screen=serve

    # Watch CSS for hot-reload
    python -m bengal.cli.dashboard --css-watch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bengal.cli.dashboard.app import BengalApp


def create_demo_site() -> None:
    """Create a minimal demo site for testing."""
    # Return None - dashboards handle missing site gracefully
    return None


def main() -> None:
    """Run dashboard in development mode."""
    parser = argparse.ArgumentParser(
        description="Bengal Dashboard Development Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--screen",
        choices=["build", "serve", "health"],
        default="build",
        help="Start with specific screen (default: build)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data (no site required)",
    )
    parser.add_argument(
        "--css-watch",
        action="store_true",
        help="Hot-reload CSS changes during development",
    )
    parser.add_argument(
        "--site",
        type=Path,
        default=None,
        help="Path to site config (default: current directory)",
    )

    args = parser.parse_args()

    # Load site if provided
    site = None
    if args.site and not args.demo:
        try:
            from bengal.config.site_loader import load_site

            site = load_site(args.site)
        except ImportError:
            print("Could not load site config. Running in demo mode.")
        except Exception as e:
            print(f"Error loading site: {e}. Running in demo mode.")

    if args.demo or site is None:
        site = create_demo_site()
        print("🐱 Running in demo mode (no site loaded)")

    # Create and run app
    app = BengalApp(
        site=site,
        start_screen=args.screen,
        watch_css=args.css_watch,
    )

    print(f"🐱 Starting Bengal Dashboard ({args.screen} screen)")
    print("   Press Ctrl+C to exit, ? for help")
    print()

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()

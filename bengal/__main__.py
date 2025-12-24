"""Allow running bengal as a module: python -m bengal"""

from __future__ import annotations

import sys


def run() -> None:
    """Entry point wrapper that gracefully handles KeyboardInterrupt."""
    try:
        from bengal.cli import main

        main()
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - no ugly traceback
        print("\n\033[2m Interrupted.\033[0m")
        sys.exit(130)  # Standard exit code for SIGINT


if __name__ == "__main__":
    run()

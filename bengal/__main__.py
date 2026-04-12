"""Allow running bengal as a module: python -m bengal"""

from __future__ import annotations

from bengal.cli.milo_app import run

if __name__ == "__main__":
    run()

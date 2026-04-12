"""
Allow running Bengal CLI as a module.

This module enables running the Bengal CLI via `python -m bengal.cli`,
providing an alternative entry point to the `bengal` console script.

Example:
    >>> python -m bengal.cli build
    >>> python -m bengal.cli serve --port 8080
"""

from __future__ import annotations

from bengal.cli.milo_app import run

if __name__ == "__main__":
    run()

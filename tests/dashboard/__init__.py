"""
Dashboard tests for Bengal's Textual-based terminal UI.

This package contains tests for interactive dashboards:
- Build dashboard (bengal build --dashboard)
- Serve dashboard (bengal serve --dashboard)
- Health dashboard (bengal health --dashboard)

Uses pytest-textual-snapshot for visual regression testing
and async fixtures for Textual app testing.
"""

from __future__ import annotations

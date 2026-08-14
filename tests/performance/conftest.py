"""Ensure performance tests carry the performance marker.

pytestmark in tests/performance/__init__.py does not apply to test modules in
this package, so @pytest.mark.slow tests here leaked into the weekly slow job.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    marker = pytest.mark.performance
    for item in items:
        item.add_marker(marker)

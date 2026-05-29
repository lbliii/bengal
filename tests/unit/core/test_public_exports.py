"""Guards for lazy public core re-exports."""

from __future__ import annotations

import subprocess
import sys


def _run_import_probe(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_top_level_page_export_is_lazy_but_importable() -> None:
    code = """
import sys
import bengal
print("loaded", "bengal.core.page" in sys.modules)
from bengal import Page
print(Page.__module__)
"""

    assert _run_import_probe(code).splitlines() == [
        "loaded False",
        "bengal.core.page",
    ]


def test_core_page_export_is_lazy_but_importable() -> None:
    code = """
import sys
import bengal.core
print("loaded", "bengal.core.page" in sys.modules)
from bengal.core import Page
print(Page.__module__)
"""

    assert _run_import_probe(code).splitlines() == [
        "loaded False",
        "bengal.core.page",
    ]

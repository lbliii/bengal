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


def test_top_level_exports_stay_lazy_without_page() -> None:
    code = """
import sys
import bengal
print("loaded", "bengal.core.page" in sys.modules)
from bengal import Section
print(Section.__module__)
print(hasattr(bengal, "Page"))
try:
    from bengal import Page
except ImportError:
    print("page import retired")
else:
    raise AssertionError(f"unexpected Page export: {Page!r}")
"""

    assert _run_import_probe(code).splitlines() == [
        "loaded False",
        "bengal.core.section",
        "False",
        "page import retired",
    ]


def test_core_exports_do_not_reexport_page() -> None:
    code = """
import sys
import bengal.core
print("loaded", "bengal.core.page" in sys.modules)
from bengal.core import Section
print(Section.__module__)
print(hasattr(bengal.core, "Page"))
try:
    from bengal.core import Page
except ImportError:
    print("core page import retired")
else:
    raise AssertionError(f"unexpected core Page export: {Page!r}")
"""

    assert _run_import_probe(code).splitlines() == [
        "loaded False",
        "bengal.core.section",
        "False",
        "core page import retired",
    ]

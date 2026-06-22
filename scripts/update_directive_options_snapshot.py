#!/usr/bin/env python3
"""Regenerate directive option tables from create_default_registry() (issue #626)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from tests._testing.directive_options_snapshot import (  # noqa: E402
    registry_option_tables,
    write_registry_options_doc,
    write_snapshot,
)


def main() -> int:
    payload = registry_option_tables()
    snapshot = write_snapshot()
    doc = write_registry_options_doc(payload=payload)
    print(f"Wrote {snapshot.relative_to(_REPO_ROOT)} ({len(payload)} handlers)")
    print(f"Wrote {doc.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

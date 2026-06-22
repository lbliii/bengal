#!/usr/bin/env python3
"""Regenerate committed CLI help snapshots for docs drift guards (issue #628).

Updates:
- tests/unit/docs/fixtures/cli_root_help_commands.txt
- site/content/docs/reference/architecture/tooling/cli.md (inventory + root help)
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from tests._testing.cli_help_snapshot import (  # noqa: E402
    update_cli_doc_inventory,
    update_cli_doc_root_help,
    write_snapshot,
)


def main() -> int:
    snapshot = write_snapshot()
    doc_inventory_changed = update_cli_doc_inventory()
    doc_help_changed = update_cli_doc_root_help()
    print(f"Wrote {snapshot.relative_to(_REPO_ROOT)}")
    if doc_inventory_changed:
        print("Updated cli.md command inventory")
    if doc_help_changed:
        print("Updated cli.md root help snapshot")
    if not doc_inventory_changed and not doc_help_changed:
        print("cli.md already matched live CLI output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Guards for direct writes in output and cache surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.check_output_writes import (
    APPROVED_DIRECT_WRITES,
    scan_direct_writes,
    scan_file,
    unapproved_direct_writes,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_output_write_audit_has_no_unapproved_current_writes() -> None:
    findings = scan_direct_writes()

    assert findings
    assert not unapproved_direct_writes(findings)


def test_output_write_audit_approval_keys_match_current_findings() -> None:
    findings = scan_direct_writes()
    approval_keys = {finding.approval_key for finding in findings}

    assert approval_keys == set(APPROVED_DIRECT_WRITES)


def test_output_write_audit_flags_new_direct_write(tmp_path: Path) -> None:
    source = tmp_path / "candidate.py"
    source.write_text(
        """
from pathlib import Path


def write(path: Path) -> None:
    path.write_text("unsafe")
""",
        encoding="utf-8",
    )

    findings = scan_file(source, root=tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "candidate.py"
    assert findings[0].function == "write"
    assert findings[0].method == "write_text"
    assert unapproved_direct_writes(findings) == findings

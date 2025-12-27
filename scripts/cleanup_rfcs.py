#!/usr/bin/env python3
"""Clean up completed RFCs from plan directory.

Identifies RFCs marked as "Implemented" and moves them to an archive directory.
Also identifies duplicates across directories.
"""

import argparse
import re
from pathlib import Path
from typing import NamedTuple

PLAN_DIR = Path(__file__).parent.parent / "plan"
ARCHIVE_DIR = PLAN_DIR / "archived"


class RFCStatus(NamedTuple):
    """RFC status information."""

    path: Path
    status: str
    is_implemented: bool
    is_duplicate: bool
    duplicate_of: Path | None = None


def parse_rfc_status(file_path: Path) -> str | None:
    """Extract status from RFC file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Try table format: | **Status** | Implemented |
    table_match = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*([^|]+)\s*\|", content, re.IGNORECASE)
    if table_match:
        return table_match.group(1).strip()

    # Try markdown format: **Status**: Implemented
    markdown_match = re.search(r"\*\*Status\*\*:\s*([^\n]+)", content, re.IGNORECASE)
    if markdown_match:
        return markdown_match.group(1).strip()

    # Try simple: Status: Implemented
    simple_match = re.search(r"^Status:\s*([^\n]+)", content, re.MULTILINE | re.IGNORECASE)
    if simple_match:
        return simple_match.group(1).strip()

    return None


def is_implemented_status(status: str | None) -> bool:
    """Check if status indicates implementation is complete."""
    if not status:
        return False

    status_lower = status.lower()

    # Exclude "in progress" or partial implementations
    if "in progress" in status_lower or "blocked" in status_lower:
        return False

    implemented_indicators = [
        "implemented",
        "implemented ✅",
        "✅ implemented",
        "complete",
        "completed",
        "done",
    ]

    return any(indicator in status_lower for indicator in implemented_indicators)


def find_duplicates(rfc_files: list[Path]) -> dict[str, list[Path]]:
    """Find duplicate RFCs by filename."""
    by_name: dict[str, list[Path]] = {}

    for rfc_file in rfc_files:
        name = rfc_file.name
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(rfc_file)

    return {name: paths for name, paths in by_name.items() if len(paths) > 1}


def analyze_rfcs() -> list[RFCStatus]:
    """Analyze all RFCs in plan directory."""
    rfc_files = [
        f for f in PLAN_DIR.rglob("*.md") if "archived" not in str(f.relative_to(PLAN_DIR))
    ]

    # Find duplicates
    duplicates = find_duplicates(rfc_files)

    results = []
    for rfc_file in rfc_files:
        status_text = parse_rfc_status(rfc_file)
        is_impl = is_implemented_status(status_text)

        # Check if duplicate
        is_dup = False
        dup_of = None
        if rfc_file.name in duplicates:
            dup_paths = duplicates[rfc_file.name]
            if len(dup_paths) > 1:
                is_dup = True
                # Prefer ready > evaluated > drafted
                priority = {"ready": 3, "evaluated": 2, "drafted": 1}
                dup_paths_sorted = sorted(
                    dup_paths, key=lambda p: priority.get(p.parent.name, 0), reverse=True
                )
                if rfc_file != dup_paths_sorted[0]:
                    dup_of = dup_paths_sorted[0]

        results.append(
            RFCStatus(
                path=rfc_file,
                status=status_text or "Unknown",
                is_implemented=is_impl,
                is_duplicate=is_dup,
                duplicate_of=dup_of,
            )
        )

    return results


def main():
    """Main cleanup script."""
    parser = argparse.ArgumentParser(description="Clean up completed RFCs")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt (non-interactive mode)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    args = parser.parse_args()

    print("🔍 Analyzing RFCs in plan directory...\n")

    results = analyze_rfcs()

    # Group by category
    implemented = [r for r in results if r.is_implemented]
    duplicates = [r for r in results if r.is_duplicate]

    print("📊 Summary:")
    print(f"  Total RFCs: {len(results)}")
    print(f"  Implemented: {len(implemented)}")
    print(f"  Duplicates: {len(duplicates)}\n")

    # Show implemented RFCs
    if implemented:
        print("✅ Implemented RFCs:")
        for rfc in sorted(implemented, key=lambda x: x.path):
            rel_path = rfc.path.relative_to(PLAN_DIR.parent)
            print(f"  - {rel_path} ({rfc.status})")
        print()

    # Show duplicates
    if duplicates:
        print("🔄 Duplicate RFCs:")
        seen_names = set()
        for rfc in sorted(duplicates, key=lambda x: x.path):
            if rfc.path.name not in seen_names:
                seen_names.add(rfc.path.name)
                rel_path = rfc.path.relative_to(PLAN_DIR.parent)
                dup_rel = (
                    rfc.duplicate_of.relative_to(PLAN_DIR.parent) if rfc.duplicate_of else None
                )
                print(f"  - {rel_path}")
                if dup_rel:
                    print(f"    → Keep: {dup_rel}")
        print()

    # Ask for confirmation
    if implemented or duplicates:
        print("📋 Actions:")
        if implemented:
            print(f"  - Archive {len(implemented)} implemented RFC(s)")
        if duplicates:
            print(f"  - Remove {len(duplicates)} duplicate RFC(s)")
        print()

        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            return

        if not args.yes:
            try:
                response = input("Proceed with cleanup? (yes/no): ").strip().lower()
                if response not in ("yes", "y"):
                    print("❌ Cleanup cancelled.")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Cleanup cancelled.")
                return

        # Create archive directory
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        # Archive implemented RFCs
        archived_count = 0
        for rfc in implemented:
            if not rfc.path.exists():
                continue  # Already archived/removed
            try:
                archive_path = ARCHIVE_DIR / rfc.path.name
                if archive_path.exists():
                    # Add parent directory name to avoid conflicts
                    archive_path = ARCHIVE_DIR / f"{rfc.path.parent.name}_{rfc.path.name}"

                rfc.path.rename(archive_path)
                archived_count += 1
                print(f"  ✅ Archived: {rfc.path.name}")
            except Exception as e:
                print(f"  ❌ Error archiving {rfc.path.name}: {e}")

        # Remove duplicates (keep the one in highest priority directory)
        removed_count = 0
        seen_names = set()
        for rfc in duplicates:
            if rfc.path.name not in seen_names and rfc.duplicate_of:
                seen_names.add(rfc.path.name)
                if not rfc.path.exists():
                    continue  # Already removed/archived
                try:
                    rfc.path.unlink()
                    removed_count += 1
                    print(f"  🗑️  Removed duplicate: {rfc.path.name}")
                except Exception as e:
                    print(f"  ❌ Error removing {rfc.path.name}: {e}")

        print("\n✨ Cleanup complete!")
        print(f"  Archived: {archived_count}")
        print(f"  Removed duplicates: {removed_count}")
    else:
        print("✨ No cleanup needed!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Remove null bytes from Python source files.

This script fixes files that were corrupted by null byte insertion,
which causes 'source code string cannot contain null bytes' errors.
"""

import sys
from pathlib import Path


def fix_null_bytes(directory: Path, dry_run: bool = False) -> tuple[int, int]:
    """Remove null bytes from all Python files in a directory.

    Args:
        directory: Root directory to scan
        dry_run: If True, only report affected files without modifying

    Returns:
        Tuple of (files_checked, files_fixed)
    """
    files_checked = 0
    files_fixed = 0

    for py_file in directory.rglob("*.py"):
        files_checked += 1

        try:
            # Read as binary to detect null bytes
            content = py_file.read_bytes()

            if b"\x00" in content:
                files_fixed += 1

                if dry_run:
                    # Count null bytes for reporting
                    null_count = content.count(b"\x00")
                    print(f"  [DRY RUN] {py_file}: {null_count} null byte(s)")
                else:
                    # Remove null bytes and write back
                    fixed_content = content.replace(b"\x00", b"")
                    py_file.write_bytes(fixed_content)
                    print(f"  ✅ Fixed: {py_file}")

        except (OSError, PermissionError) as e:
            print(f"  ❌ Error reading {py_file}: {e}", file=sys.stderr)

    return files_checked, files_fixed


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Remove null bytes from Python source files")
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Only report affected files, don't modify"
    )

    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: {args.directory} is not a directory", file=sys.stderr)
        return 1

    mode = "DRY RUN" if args.dry_run else "FIX"
    print(f"\n🔍 Scanning for null bytes ({mode}): {args.directory}\n")

    checked, fixed = fix_null_bytes(args.directory, dry_run=args.dry_run)

    print("\n📊 Summary:")
    print(f"   Files checked: {checked}")
    print(f"   Files {'affected' if args.dry_run else 'fixed'}: {fixed}")

    if args.dry_run and fixed > 0:
        print("\n💡 Run without --dry-run to fix these files")
    elif fixed > 0:
        print("\n✅ All null bytes removed!")
    else:
        print("\n✅ No null bytes found!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

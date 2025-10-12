#!/usr/bin/env python3
"""Fix trailing whitespace in files."""

from pathlib import Path

files_to_fix = [
    "bengal/cli/commands/init.py",
    "bengal/core/site.py",
    "tests/unit/test_cli_init.py",
]

for file_path in files_to_fix:
    path = Path(file_path)
    if not path.exists():
        print(f"Skipping {file_path} - not found")
        continue

    # Read file
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    # Remove trailing whitespace from each line
    fixed_lines = [line.rstrip() + "\n" if line.strip() else "\n" for line in lines]

    # Ensure file ends with newline
    if fixed_lines and not fixed_lines[-1].endswith("\n"):
        fixed_lines[-1] += "\n"

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)

    print(f"Fixed {file_path}")

print("\nDone! Now run: git add -A && git commit")

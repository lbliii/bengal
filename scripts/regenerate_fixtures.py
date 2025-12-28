#!/usr/bin/env python3
"""Fixture regeneration script for Rosettes test suite.

Regenerates token fixtures from source code files, allowing diff-based review
before approving changes.

Usage:
    # Regenerate fixtures for a specific lexer
    python scripts/regenerate_fixtures.py --lexer python --diff

    # Review diffs, approve intentional changes
    python scripts/regenerate_fixtures.py --lexer python --approve

    # Regenerate all fixtures
    python scripts/regenerate_fixtures.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path (must be before imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bengal.rendering.rosettes import get_lexer  # noqa: E402
from tests.unit.rendering.rosettes.conftest import FIXTURES_DIR, tokens_to_dict  # noqa: E402


def get_extension(language: str) -> str:
    """Get file extension for a language."""
    extensions = {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "rust": "rs",
        "go": "go",
        "kida": "kida",
        "html": "html",
        "css": "css",
        "yaml": "yml",
        "json": "json",
        "bash": "sh",
        "sql": "sql",
        "markdown": "md",
    }
    return extensions.get(language, "txt")


def regenerate_fixture(language: str, fixture_name: str, approve: bool = False) -> bool:
    """Regenerate a single fixture.

    Args:
        language: Language name.
        fixture_name: Fixture name without extension.
        approve: If True, write new tokens without prompting.

    Returns:
        True if fixture was regenerated, False if skipped.
    """
    lang_dir = FIXTURES_DIR / language
    lang_dir.mkdir(parents=True, exist_ok=True)

    ext = get_extension(language)
    input_file = lang_dir / f"{fixture_name}.{ext}"
    tokens_file = lang_dir / f"{fixture_name}.tokens"

    if not input_file.exists():
        print(f"⚠️  Input file not found: {input_file}")
        return False

    # Read input code
    input_code = input_file.read_text(encoding="utf-8")

    # Tokenize
    lexer = get_lexer(language)
    tokens = list(lexer.tokenize(input_code))
    new_tokens = tokens_to_dict(tokens)

    # Read existing tokens if they exist
    old_tokens = []
    if tokens_file.exists():
        old_tokens = json.loads(tokens_file.read_text(encoding="utf-8"))

    # Compare
    if old_tokens == new_tokens:
        print(f"✅ {language}/{fixture_name}: No changes")
        return False

    # Show diff
    print(f"\n📝 {language}/{fixture_name}: Changes detected")
    if old_tokens:
        print(f"   Old: {len(old_tokens)} tokens")
    print(f"   New: {len(new_tokens)} tokens")

    if not approve:
        print(f"   Run with --approve to update {tokens_file}")
        return False

    # Write new tokens
    tokens_file.write_text(
        json.dumps(new_tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"   ✅ Updated {tokens_file}")
    return True


def regenerate_all(language: str | None = None, approve: bool = False) -> None:
    """Regenerate all fixtures for a language or all languages.

    Args:
        language: Language name, or None for all languages.
        approve: If True, write without prompting.
    """
    if language:
        languages = [language]
    else:
        # Find all languages with fixture directories
        languages = [
            d.name for d in FIXTURES_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    total_regenerated = 0
    for lang in languages:
        lang_dir = FIXTURES_DIR / lang
        if not lang_dir.exists():
            continue

        # Find all input files
        ext = get_extension(lang)
        input_files = list(lang_dir.glob(f"*.{ext}"))

        for input_file in input_files:
            fixture_name = input_file.stem
            if regenerate_fixture(lang, fixture_name, approve=approve):
                total_regenerated += 1

    if total_regenerated > 0:
        print(f"\n✅ Regenerated {total_regenerated} fixture(s)")
    else:
        print("\n✅ No fixtures needed regeneration")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Regenerate Rosettes test fixtures")
    parser.add_argument(
        "--lexer",
        help="Language name (e.g., 'python', 'javascript')",
    )
    parser.add_argument(
        "--fixture",
        help="Fixture name without extension (e.g., 'keywords')",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Regenerate all fixtures",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve and write changes (default: show diff only)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff (same as default behavior)",
    )

    args = parser.parse_args()

    if args.all:
        regenerate_all(approve=args.approve)
    elif args.lexer:
        if args.fixture:
            regenerate_fixture(args.lexer, args.fixture, approve=args.approve)
        else:
            regenerate_all(language=args.lexer, approve=args.approve)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

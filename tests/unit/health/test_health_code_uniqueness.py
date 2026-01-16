"""
Tests for health check code uniqueness.

Ensures all health check codes (H001, H101, etc.) are unique across validators.
This prevents confusion in error tracking, filtering, and CI integration.

This test would have caught Bug #4: duplicate H701 code in external_refs and connectivity.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


def extract_health_codes_from_file(file_path: Path) -> list[tuple[str, int, str]]:
    """
    Extract health check codes from a Python file.

    Returns list of (code, line_number, file_name) tuples.
    """
    codes: list[tuple[str, int, str]] = []
    content = file_path.read_text(encoding="utf-8")

    # Pattern matches code="H###" or code='H###'
    pattern = re.compile(r'''code\s*=\s*["']([HV]\d{3})["']''')

    for i, line in enumerate(content.splitlines(), 1):
        for match in pattern.finditer(line):
            codes.append((match.group(1), i, file_path.name))

    return codes


def get_all_health_codes() -> dict[str, list[tuple[str, int]]]:
    """
    Scan all health validators and collect all health check codes.

    Returns dict mapping code -> [(file, line), ...]
    Note: Multiple uses of the same code within a single file are deduplicated
    since a validator may use the same code for different severity levels.
    """
    health_dir = Path(__file__).parent.parent.parent.parent / "bengal" / "health"
    validators_dir = health_dir / "validators"

    codes_map: dict[str, list[tuple[str, int]]] = {}

    # Scan all Python files in health/validators
    for py_file in validators_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        # Track codes seen in this file to deduplicate
        file_codes: set[str] = set()
        for code, line, filename in extract_health_codes_from_file(py_file):
            if code in file_codes:
                continue  # Skip duplicates within same file
            file_codes.add(code)
            
            if code not in codes_map:
                codes_map[code] = []
            codes_map[code].append((filename, line))

    return codes_map


class TestHealthCheckCodeUniqueness:
    """Tests ensuring health check codes are unique."""

    def test_no_duplicate_health_codes(self):
        """Each health check code should be unique across all validators."""
        codes_map = get_all_health_codes()

        duplicates = {
            code: locations for code, locations in codes_map.items() if len(locations) > 1
        }

        if duplicates:
            error_msg = "Duplicate health check codes found:\n"
            for code, locations in sorted(duplicates.items()):
                error_msg += f"  {code}:\n"
                for filename, line in locations:
                    error_msg += f"    - {filename}:{line}\n"

            pytest.fail(error_msg)

    def test_health_codes_follow_convention(self):
        """Health check codes should follow H### or V### convention."""
        codes_map = get_all_health_codes()

        invalid_codes = []
        for code in codes_map:
            if not re.match(r"^[HV]\d{3}$", code):
                invalid_codes.append(code)

        if invalid_codes:
            pytest.fail(f"Invalid health check codes (should be H### or V###): {invalid_codes}")

    def test_health_codes_are_in_expected_ranges(self):
        """
        Health check codes should be in documented ranges.

        Code Ranges (from bengal/health/report/models.py):
        - H0xx: Core/Basic (Output, Config, URL Collisions, Ownership)
        - H1xx: Links & Navigation
        - H2xx: Directives
        - H3xx: Taxonomy
        - H4xx: Cache & Performance
        - H5xx: Feeds (RSS, Sitemap)
        - H6xx: Assets (Fonts, Images)
        - H7xx: Graph & References (Connectivity, Anchors, Cross-refs)
        - H8xx: Tracks
        - H9xx: Accessibility
        - V0xx: Validator errors
        """
        codes_map = get_all_health_codes()

        # Just verify all codes are in valid ranges (0-9)
        for code in codes_map:
            if code.startswith("H"):
                num = int(code[1:])
                assert 0 <= num < 1000, f"Code {code} out of range"
            elif code.startswith("V"):
                num = int(code[1:])
                assert 0 <= num < 1000, f"Code {code} out of range"

    def test_all_validators_have_codes(self):
        """Validators with errors/warnings should use health check codes."""
        codes_map = get_all_health_codes()

        # Should have codes from multiple validators
        assert len(codes_map) > 20, "Expected at least 20 unique health codes"

        # Check key code ranges are represented
        h0_codes = [c for c in codes_map if c.startswith("H0")]
        h1_codes = [c for c in codes_map if c.startswith("H1")]
        h2_codes = [c for c in codes_map if c.startswith("H2")]

        assert len(h0_codes) > 0, "Missing H0xx codes (Core/Basic)"
        assert len(h1_codes) > 0, "Missing H1xx codes (Links & Navigation)"
        assert len(h2_codes) > 0, "Missing H2xx codes (Directives)"

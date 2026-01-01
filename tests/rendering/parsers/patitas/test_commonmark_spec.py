"""CommonMark 0.31.2 Specification Compliance Tests.

This module runs the official CommonMark spec tests against Patitas.
The spec.json contains 652 examples from the CommonMark specification.

Usage:
    # Run all spec tests
    pytest tests/rendering/parsers/patitas/test_commonmark_spec.py -v

    # Run specific section
    pytest tests/rendering/parsers/patitas/test_commonmark_spec.py -k "Emphasis"

    # Run single example
    pytest tests/rendering/parsers/patitas/test_commonmark_spec.py -k "example_42"

Baseline Tracking:
    The baseline pass rate is tracked in this file. Update after each sprint.
    Current baseline: TBD (run tests to establish)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bengal.rendering.parsers.patitas import parse

if TYPE_CHECKING:
    from typing import Any


# Load the CommonMark spec
SPEC_PATH = Path(__file__).parent / "commonmark_spec_0_31_2.json"
SPEC_TESTS: list[dict[str, Any]] = json.loads(SPEC_PATH.read_text())


def normalize_html(html_string: str) -> str:
    """Normalize HTML for comparison.

    CommonMark spec allows variation in:
    - Attribute ordering
    - Self-closing tag style (<br> vs <br />)
    - Whitespace handling
    - Entity encoding

    This normalizer makes comparisons more forgiving while still
    validating semantic correctness.

    Args:
        html_string: Raw HTML string to normalize

    Returns:
        Normalized HTML string for comparison
    """
    result = html_string.strip()

    # Normalize self-closing tags: <br /> -> <br>
    result = re.sub(r"<(br|hr|img)(\s[^>]*)?\s*/?>", r"<\1\2>", result)

    # Normalize empty self-closing: <tag /> -> <tag>
    result = re.sub(r"\s*/>", ">", result)

    # Normalize multiple spaces to single space
    result = re.sub(r" +", " ", result)

    # Normalize line endings
    result = result.replace("\r\n", "\n")

    # Normalize attribute quoting: unquoted -> double-quoted
    # This is a simplification; real parsers should handle this more carefully
    result = re.sub(r'=([^"\'\s>]+)(?=[\s>])', r'="\1"', result)

    # Sort attributes alphabetically for consistent comparison
    def sort_attrs(match: re.Match[str]) -> str:
        tag = match.group(1)
        attrs_str = match.group(2)
        if not attrs_str:
            return match.group(0)

        # Parse attributes
        attr_pattern = re.compile(r'(\w+)=("[^"]*"|\'[^\']*\'|[^\s>]+)')
        attrs = attr_pattern.findall(attrs_str)
        if not attrs:
            return match.group(0)

        # Sort by attribute name
        attrs.sort(key=lambda x: x[0])
        sorted_attrs = " ".join(f"{k}={v}" for k, v in attrs)
        return f"<{tag} {sorted_attrs}>"

    result = re.sub(r"<(\w+)(\s[^>]+)>", sort_attrs, result)

    return result


def normalize_for_comparison(expected: str, actual: str) -> tuple[str, str]:
    """Normalize both expected and actual HTML for comparison.

    This applies additional normalization rules that account for
    Patitas-specific rendering choices that are still spec-compliant.

    Args:
        expected: Expected HTML from spec
        actual: Actual HTML from Patitas

    Returns:
        Tuple of (normalized_expected, normalized_actual)
    """
    expected = normalize_html(expected)
    actual = normalize_html(actual)

    # Patitas uses <br /> with space, spec uses <br>
    # Both are valid HTML5
    actual = actual.replace("<br />", "<br>")
    actual = actual.replace("<hr />", "<hr>")

    return expected, actual


# Track which sections have known issues - skip entire sections
KNOWN_ISSUES: dict[str, str] = {
    # These are not yet implemented
    "Link reference definitions": "Not yet implemented - token exists, parser pending",
}

# Track specific examples that are expected to fail
XFAIL_EXAMPLES: dict[int, str] = {
    # Issue 1: Different markers should create separate lists (RFC Issue 1)
    # Issue 2: Deeply nested lists trigger code block detection (RFC Issue 2)
}


def pytest_generate_tests(metafunc: Any) -> None:
    """Generate test parameters from spec examples."""
    if "example" in metafunc.fixturenames:
        ids = [
            f"example_{ex['example']:03d}_{ex['section'].replace(' ', '_')}" for ex in SPEC_TESTS
        ]
        metafunc.parametrize("example", SPEC_TESTS, ids=ids)


class TestCommonMarkSpec:
    """Official CommonMark 0.31.2 specification tests."""

    def test_commonmark_example(self, example: dict[str, Any]) -> None:
        """Test a single CommonMark spec example.

        Args:
            example: Dict with 'markdown', 'html', 'example', 'section' keys
        """
        markdown = example["markdown"]
        expected_html = example["html"]
        example_num = example["example"]
        section = example["section"]

        # Check for known issues at section level
        if section in KNOWN_ISSUES:
            pytest.skip(f"Section '{section}': {KNOWN_ISSUES[section]}")

        # Check for specific xfail examples
        if example_num in XFAIL_EXAMPLES:
            pytest.xfail(XFAIL_EXAMPLES[example_num])

        # Parse and compare
        actual_html = parse(markdown)
        expected_norm, actual_norm = normalize_for_comparison(expected_html, actual_html)

        assert actual_norm == expected_norm, (
            f"\n\nExample {example_num} ({section}) failed:\n"
            f"\n--- Markdown ---\n{markdown!r}\n"
            f"\n--- Expected ---\n{expected_html!r}\n"
            f"\n--- Actual ---\n{actual_html!r}\n"
            f"\n--- Expected (normalized) ---\n{expected_norm!r}\n"
            f"\n--- Actual (normalized) ---\n{actual_norm!r}\n"
        )


class TestSpecSections:
    """Tests organized by CommonMark spec sections."""

    @pytest.fixture
    def section_examples(self) -> dict[str, list[dict[str, Any]]]:
        """Group examples by section."""
        sections: dict[str, list[dict[str, Any]]] = {}
        for ex in SPEC_TESTS:
            section = ex["section"]
            if section not in sections:
                sections[section] = []
            sections[section].append(ex)
        return sections

    def test_section_count(self, section_examples: dict[str, list[dict[str, Any]]]) -> None:
        """Verify we have all expected sections."""
        # Core sections from the spec
        core_sections = {
            "Tabs",
            "Thematic breaks",
            "ATX headings",
            "Setext headings",
            "Indented code blocks",
            "Fenced code blocks",
            "HTML blocks",
            "Link reference definitions",
            "Paragraphs",
            "Blank lines",
            "Block quotes",
            "List items",
            "Lists",
            "Backslash escapes",
            "Entity and numeric character references",
            "Code spans",
            "Emphasis and strong emphasis",
            "Links",
            "Images",
            "Autolinks",
            "Raw HTML",
            "Hard line breaks",
            "Soft line breaks",
            "Textual content",
        }
        actual_sections = set(section_examples.keys())
        missing = core_sections - actual_sections
        assert not missing, f"Missing sections: {missing}"


class TestBaseline:
    """Tests to establish and track baseline pass rate."""

    def test_total_examples(self) -> None:
        """Verify we have all 652 spec examples."""
        assert len(SPEC_TESTS) == 652, f"Expected 652 examples, got {len(SPEC_TESTS)}"

    def test_example_structure(self) -> None:
        """Verify example structure is correct."""
        for ex in SPEC_TESTS:
            assert "markdown" in ex
            assert "html" in ex
            assert "example" in ex
            assert "section" in ex


# =============================================================================
# Baseline Report Generator
# =============================================================================


def generate_baseline_report() -> str:
    """Generate a detailed baseline report.

    Run this function to get current pass/fail stats by section.
    """
    results: dict[str, dict[str, int]] = {}

    for example in SPEC_TESTS:
        section = example["section"]
        if section not in results:
            results[section] = {"passed": 0, "failed": 0, "skipped": 0}

        if section in KNOWN_ISSUES:
            results[section]["skipped"] += 1
            continue

        try:
            actual = parse(example["markdown"])
            expected_norm, actual_norm = normalize_for_comparison(example["html"], actual)
            if expected_norm == actual_norm:
                results[section]["passed"] += 1
            else:
                results[section]["failed"] += 1
        except Exception:
            results[section]["failed"] += 1

    # Generate report
    lines = [
        "# CommonMark Spec Baseline Report",
        "",
        "| Section | Passed | Failed | Skipped | Pass Rate |",
        "|---------|--------|--------|---------|-----------|",
    ]

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    for section, counts in sorted(results.items()):
        passed = counts["passed"]
        failed = counts["failed"]
        skipped = counts["skipped"]
        total = passed + failed
        rate = f"{(passed / total * 100):.0f}%" if total > 0 else "N/A"

        total_passed += passed
        total_failed += failed
        total_skipped += skipped

        lines.append(f"| {section} | {passed} | {failed} | {skipped} | {rate} |")

    total = total_passed + total_failed
    overall_rate = f"{(total_passed / total * 100):.1f}%" if total > 0 else "N/A"

    lines.extend(
        [
            "",
            f"**Total**: {total_passed}/{total} ({overall_rate})",
            f"**Skipped**: {total_skipped} (not yet implemented)",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    # Run directly to generate baseline report
    print(generate_baseline_report())

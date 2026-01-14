"""
Meta-tests that validate the quality of the test suite itself.

RFC: rfc-behavioral-test-hardening

These tests enforce coding standards for tests, preventing anti-patterns
that reduce test effectiveness:

- Weak assertions (assert True, assert result)
- Mock-only tests (no behavioral verification)
- Missing assertion helpers usage

Run with: pytest tests/meta/test_test_quality.py -v
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Path to tests directory
TESTS_DIR = Path(__file__).parent.parent


def _get_test_files() -> list[Path]:
    """Get all test files (excluding meta tests)."""
    test_files = []
    for f in TESTS_DIR.rglob("test_*.py"):
        # Exclude meta tests and __pycache__
        if "meta" not in f.parts and "__pycache__" not in f.parts:
            test_files.append(f)
    return test_files


def _parse_python_file(file_path: Path) -> ast.Module | None:
    """Parse a Python file into an AST, returning None on error."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except SyntaxError:
        return None


class TestNoWeakAssertions:
    """Tests that catch weak/useless assertions."""

    @pytest.mark.parametrize("pattern,description,threshold", [
        (r"^\s*assert\s+True\s*$", "assert True", 10),  # Start with baseline, reduce over time
        (r"^\s*assert\s+False\s*$", "assert False (always fails)", 0),
    ])
    def test_no_bare_assert_true_or_false(
        self,
        pattern: str,
        description: str,
        threshold: int,
    ) -> None:
        """Track usage of 'assert True' or 'assert False' as assertions."""
        violations = []

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line):
                    violations.append(f"{test_file.relative_to(TESTS_DIR)}:{i}")

        # Report violations for tracking
        if violations:
            print(f"\nFound '{description}' in {len(violations)} locations:")
            for v in violations[:10]:
                print(f"  - {v}")

        # Fail if above threshold
        assert len(violations) <= threshold, (
            f"Found '{description}' in {len(violations)} locations (threshold: {threshold}). "
            f"These assertions provide no value:\n"
            + "\n".join(f"  - {v}" for v in violations[:10])
            + (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
        )

    def test_limited_bare_assert_result(self) -> None:
        """
        Track usage of weak 'assert result' patterns.

        These assertions only check truthiness, not correctness.
        Goal: Reduce over time to 0.
        """
        pattern = re.compile(r"^\s*assert\s+result\s*$", re.MULTILINE)
        violations = []

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            matches = pattern.findall(content)
            if matches:
                violations.append((test_file.relative_to(TESTS_DIR), len(matches)))

        # Track count - should decrease over time
        total = sum(count for _, count in violations)

        # Soft limit - warn if above threshold
        THRESHOLD = 50  # Start tracking, reduce over time

        if total > THRESHOLD:
            pytest.skip(
                f"Found {total} 'assert result' patterns (threshold: {THRESHOLD}). "
                f"Files: {[str(f) for f, _ in violations[:5]]}"
            )


class TestMockUsagePatterns:
    """Tests that validate mock usage patterns."""

    def test_mock_density_per_file(self) -> None:
        """
        Track mock density (mocks per file).

        High mock density indicates tests may not be testing real behavior.
        Goal: Average < 5 mocks per test file.
        """
        mock_pattern = re.compile(r"\b(Mock|MagicMock|patch|mock\.)\b")

        densities = []
        high_density_files = []

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            mock_count = len(mock_pattern.findall(content))

            if mock_count > 0:
                densities.append(mock_count)
                if mock_count > 50:  # Flag very high density
                    high_density_files.append(
                        (test_file.relative_to(TESTS_DIR), mock_count)
                    )

        avg_density = sum(densities) / len(densities) if densities else 0

        # Report high-density files for prioritization
        if high_density_files:
            high_density_files.sort(key=lambda x: x[1], reverse=True)
            print(f"\nHigh mock density files (>50 mocks):")
            for f, count in high_density_files[:10]:
                print(f"  {count:3d} mocks: {f}")

        # Soft threshold - don't fail, just track
        TARGET_AVG = 10
        if avg_density > TARGET_AVG:
            pytest.skip(
                f"Average mock density {avg_density:.1f} exceeds target {TARGET_AVG}. "
                f"High-density files need refactoring."
            )

    def test_assert_called_patterns(self) -> None:
        """
        Track .assert_called() patterns.

        These verify implementation, not behavior.
        Goal: Reduce over time.
        """
        patterns = [
            r"\.assert_called\(",
            r"\.assert_called_once\(",
            r"\.assert_called_with\(",
            r"\.assert_called_once_with\(",
            r"\.assert_has_calls\(",
            r"\.assert_any_call\(",
        ]
        combined_pattern = re.compile("|".join(patterns))

        violations = []

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            matches = combined_pattern.findall(content)
            if matches:
                violations.append((test_file.relative_to(TESTS_DIR), len(matches)))

        total = sum(count for _, count in violations)

        # Track count - should decrease over time
        THRESHOLD = 200  # Start tracking, reduce over time

        print(f"\nTotal .assert_called* patterns: {total}")
        if total > 0:
            violations.sort(key=lambda x: x[1], reverse=True)
            print("Top files with mock verification:")
            for f, count in violations[:5]:
                print(f"  {count:3d} calls: {f}")

        if total > THRESHOLD:
            pytest.skip(
                f"Found {total} mock verification patterns (threshold: {THRESHOLD}). "
                f"Consider using behavioral assertions instead."
            )


class TestHardeningProgress:
    """Track progress on test hardening."""

    def test_needs_hardening_count(self) -> None:
        """
        Track tests marked @pytest.mark.needs_hardening.

        These are tests identified for refactoring.
        Goal: Reduce to 0.
        """
        pattern = re.compile(r"@pytest\.mark\.needs_hardening")
        count = 0

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            count += len(pattern.findall(content))

        print(f"\nTests marked @pytest.mark.needs_hardening: {count}")

        # This is informational, not a failure
        # Tests get marked as hardening is identified
        if count > 0:
            print(
                "Run: pytest --collect-only -m needs_hardening "
                "to see all tests needing hardening"
            )


class TestAssertionHelperUsage:
    """Track adoption of behavioral assertion helpers."""

    def test_assertion_helper_adoption(self) -> None:
        """
        Track usage of behavioral assertion helpers.

        Goal: Increase adoption over time.
        """
        helpers = [
            "assert_page_rendered",
            "assert_page_contains",
            "assert_output_files_exist",
            "assert_build_idempotent",
            "assert_incremental_equivalent",
            "assert_all_pages_have_urls",
            "assert_taxonomy_pages_complete",
            "assert_menu_structure",
            "assert_unchanged_files_not_rebuilt",
            "assert_changed_file_rebuilt",
            "assert_no_broken_internal_links",
            "assert_pages_have_required_metadata",
        ]

        helper_pattern = re.compile("|".join(rf"\b{h}\b" for h in helpers))
        usages = 0
        files_using = 0

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            matches = helper_pattern.findall(content)
            if matches:
                usages += len(matches)
                files_using += 1

        print(f"\nBehavioral assertion helper usage:")
        print(f"  Total usages: {usages}")
        print(f"  Files using helpers: {files_using}")

        # Informational - track growth
        TARGET_USAGES = 50
        if usages < TARGET_USAGES:
            print(
                f"  Target: {TARGET_USAGES}+ usages. "
                f"Consider using helpers from tests._testing.assertions"
            )


class TestGoldenFileScenarios:
    """Validate golden file test infrastructure."""

    def test_golden_scenarios_exist(self) -> None:
        """At least one golden scenario exists."""
        golden_dir = TESTS_DIR / "golden"

        if not golden_dir.exists():
            pytest.skip("Golden directory not yet created")

        scenarios = [
            d.name
            for d in golden_dir.iterdir()
            if d.is_dir() and (d / "input").exists()
        ]

        assert len(scenarios) >= 1, (
            "No golden scenarios found. "
            "Create tests/golden/*/input/ directories."
        )

        print(f"\nGolden scenarios: {scenarios}")

    def test_golden_scenarios_have_content(self) -> None:
        """Golden scenarios have valid input content."""
        golden_dir = TESTS_DIR / "golden"

        if not golden_dir.exists():
            pytest.skip("Golden directory not yet created")

        for scenario_dir in golden_dir.iterdir():
            if not scenario_dir.is_dir():
                continue

            input_dir = scenario_dir / "input"
            if not input_dir.exists():
                continue

            # Check for config
            config_file = input_dir / "bengal.toml"
            assert config_file.exists(), (
                f"Golden scenario '{scenario_dir.name}' missing bengal.toml"
            )

            # Check for content
            content_dir = input_dir / "content"
            assert content_dir.exists(), (
                f"Golden scenario '{scenario_dir.name}' missing content directory"
            )

            # Check for at least one content file
            content_files = list(content_dir.rglob("*.md"))
            assert len(content_files) >= 1, (
                f"Golden scenario '{scenario_dir.name}' has no .md files"
            )


class TestPropertyTestCoverage:
    """Validate property test coverage."""

    def test_hypothesis_tests_exist(self) -> None:
        """Property tests using Hypothesis exist."""
        given_pattern = re.compile(r"@given\(")
        count = 0

        for test_file in _get_test_files():
            content = test_file.read_text(encoding="utf-8")
            count += len(given_pattern.findall(content))

        print(f"\n@given() property tests: {count}")

        # Target from RFC: 300+
        TARGET = 100  # Start with lower target
        assert count >= TARGET, (
            f"Only {count} property tests found (target: {TARGET}). "
            f"Add more property tests for core invariants."
        )

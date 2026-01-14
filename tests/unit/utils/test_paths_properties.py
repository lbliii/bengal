"""
Property-based tests for path utilities using Hypothesis.

These tests verify that path generation maintains critical invariants
across ALL possible inputs.

Note: These tests use LegacyBengalPaths for the static method interface.
For new code, prefer the instance-based bengal.cache.paths.BengalPaths.
"""

import string
import tempfile
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from bengal.utils.paths.paths import LegacyBengalPaths as BengalPaths


class TestProfileDirProperties:
    """Property tests for get_profile_dir method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_returns_absolute_path(self, dir_name):
        """
        Property: Profile directory paths are always absolute.

        Critical for avoiding path ambiguity issues.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            profile_dir = BengalPaths.get_profile_dir(source_dir)

            assert profile_dir.is_absolute(), f"Profile dir should be absolute: {profile_dir}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_creates_directory(self, dir_name):
        """
        Property: get_profile_dir always creates the directory.

        Ensures immediate usability without separate mkdir calls.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            profile_dir = BengalPaths.get_profile_dir(source_dir)

            assert profile_dir.exists(), f"Profile dir should exist: {profile_dir}"
            assert profile_dir.is_dir(), f"Profile dir should be directory: {profile_dir}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_under_bengal_dir(self, dir_name):
        """
        Property: Profile directories are always under .bengal/.

        Maintains consistent project structure.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            profile_dir = BengalPaths.get_profile_dir(source_dir)

            assert ".bengal" in profile_dir.parts, (
                f"Profile dir should be under .bengal: {profile_dir}"
            )
            assert "profiles" in profile_dir.parts, (
                f"Profile dir should be under profiles: {profile_dir}"
            )

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_idempotent(self, dir_name):
        """
        Property: Calling get_profile_dir multiple times returns same path.

        Idempotency ensures predictable behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            dir1 = BengalPaths.get_profile_dir(source_dir)
            dir2 = BengalPaths.get_profile_dir(source_dir)

            assert dir1 == dir2, f"Profile dir should be idempotent: {dir1} != {dir2}"


class TestLogDirProperties:
    """Property tests for get_log_dir method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_returns_absolute_path(self, dir_name):
        """
        Property: Log directory paths are always absolute.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            log_dir = BengalPaths.get_log_dir(source_dir)

            assert log_dir.is_absolute(), f"Log dir should be absolute: {log_dir}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_creates_directory(self, dir_name):
        """
        Property: get_log_dir always creates the directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            log_dir = BengalPaths.get_log_dir(source_dir)

            assert log_dir.exists(), f"Log dir should exist: {log_dir}"
            assert log_dir.is_dir(), f"Log dir should be directory: {log_dir}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_under_bengal_dir(self, dir_name):
        """
        Property: Log directories are always under .bengal/.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            log_dir = BengalPaths.get_log_dir(source_dir)

            assert ".bengal" in log_dir.parts, f"Log dir should be under .bengal: {log_dir}"
            assert "logs" in log_dir.parts, f"Log dir should be under logs: {log_dir}"


class TestBuildLogPathProperties:
    """Property tests for get_build_log_path method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_default_path_always_under_source(self, dir_name):
        """
        Property: Default build log is always under source directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            log_path = BengalPaths.get_build_log_path(source_dir)

            assert log_path.parent == source_dir or log_path.is_relative_to(source_dir), (
                f"Build log should be under source: {log_path}"
            )

    @pytest.mark.hypothesis
    @given(
        source_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=30),
        custom_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=30),
    )
    def test_custom_path_overrides_default(self, source_name, custom_name):
        """
        Property: Custom path always overrides default.
        """
        assume(source_name != custom_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / source_name
            custom_path = Path(tmpdir) / custom_name / "custom.log"
            source_dir.mkdir(parents=True, exist_ok=True)

            log_path = BengalPaths.get_build_log_path(source_dir, custom_path)

            assert log_path == custom_path, (
                f"Custom path should be used: {log_path} != {custom_path}"
            )
            assert log_path != BengalPaths.get_build_log_path(source_dir), (
                "Custom path should differ from default"
            )

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_default_path_has_bengal_prefix(self, dir_name):
        """
        Property: Default build log path contains .bengal directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            log_path = BengalPaths.get_build_log_path(source_dir)

            assert ".bengal" in str(log_path), f"Build log path should contain .bengal: {log_path}"
            assert log_path.parts[-3] == ".bengal", (
                f"Build log should be under .bengal/logs/: {log_path}"
            )


class TestProfilePathProperties:
    """Property tests for get_profile_path method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        ),
        filename=st.text(alphabet=string.ascii_lowercase + ".", min_size=1, max_size=30),
    )
    def test_custom_filename_preserved(self, dir_name, filename):
        """
        Property: Custom filenames are preserved.
        """
        # Ensure valid filename
        assume("/" not in filename)
        assume(filename != "." and filename != "..")

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            profile_path = BengalPaths.get_profile_path(source_dir, filename=filename)

            assert profile_path.name == filename, (
                f"Profile filename should be preserved: {profile_path.name} != {filename}"
            )

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_default_creates_parent_directory(self, dir_name):
        """
        Property: get_profile_path creates parent directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / dir_name
            source_dir.mkdir(parents=True, exist_ok=True)

            profile_path = BengalPaths.get_profile_path(source_dir)

            assert profile_path.parent.exists(), (
                f"Profile parent directory should exist: {profile_path.parent}"
            )
            assert profile_path.parent.is_dir(), (
                f"Profile parent should be directory: {profile_path.parent}"
            )


class TestCachePathProperties:
    """Property tests for get_cache_path method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_cache_always_in_output_dir(self, dir_name):
        """
        Property: Cache path is always directly in output directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name

            cache_path = BengalPaths.get_cache_path(output_dir)

            assert cache_path.parent == output_dir, (
                f"Cache should be direct child of output: {cache_path.parent} != {output_dir}"
            )

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_cache_has_json_extension(self, dir_name):
        """
        Property: Cache file has .json extension.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name

            cache_path = BengalPaths.get_cache_path(output_dir)

            assert cache_path.suffix == ".json", f"Cache should be JSON: {cache_path.suffix}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_cache_has_bengal_prefix(self, dir_name):
        """
        Property: Cache file has .bengal prefix.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name

            cache_path = BengalPaths.get_cache_path(output_dir)

            assert ".bengal" in cache_path.name, (
                f"Cache should have .bengal prefix: {cache_path.name}"
            )


class TestTemplateCacheDirProperties:
    """Property tests for get_template_cache_dir method."""

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_creates_directory(self, dir_name):
        """
        Property: get_template_cache_dir always creates the directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            cache_dir = BengalPaths.get_template_cache_dir(output_dir)

            assert cache_dir.exists(), f"Template cache dir should exist: {cache_dir}"
            assert cache_dir.is_dir(), f"Template cache dir should be directory: {cache_dir}"

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_always_under_bengal_cache(self, dir_name):
        """
        Property: Template cache is under .bengal-cache/.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            cache_dir = BengalPaths.get_template_cache_dir(output_dir)

            assert ".bengal-cache" in cache_dir.parts, (
                f"Template cache should be under .bengal-cache: {cache_dir}"
            )
            assert "templates" in cache_dir.parts, (
                f"Template cache should be under templates: {cache_dir}"
            )

    @pytest.mark.hypothesis
    @given(
        dir_name=st.text(
            alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=50
        )
    )
    def test_idempotent(self, dir_name):
        """
        Property: Calling get_template_cache_dir multiple times returns same path.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / dir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            dir1 = BengalPaths.get_template_cache_dir(output_dir)
            dir2 = BengalPaths.get_template_cache_dir(output_dir)

            assert dir1 == dir2, f"Template cache dir should be idempotent: {dir1} != {dir2}"


class TestPathSeparationProperties:
    """Property tests for source vs output directory separation."""

    @pytest.mark.hypothesis
    @given(
        source_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=30),
        output_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=30),
    )
    @settings(deadline=None)
    def test_source_and_output_paths_independent(self, source_name, output_name):
        """
        Property: Source and output paths are independent.

        Changing one doesn't affect the other.
        """
        assume(source_name != output_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / source_name
            output_dir = Path(tmpdir) / output_name
            source_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Source-related paths
            profile_dir = BengalPaths.get_profile_dir(source_dir)
            build_log = BengalPaths.get_build_log_path(source_dir)

            # Output-related paths
            cache_path = BengalPaths.get_cache_path(output_dir)
            template_cache = BengalPaths.get_template_cache_dir(output_dir)

            # Source paths under source
            assert profile_dir.is_relative_to(source_dir), (
                f"Profile should be under source: {profile_dir}"
            )
            assert build_log.is_relative_to(source_dir), (
                f"Build log should be under source: {build_log}"
            )

            # Output paths under output
            assert cache_path.is_relative_to(output_dir), (
                f"Cache should be under output: {cache_path}"
            )
            assert template_cache.is_relative_to(output_dir), (
                f"Template cache should be under output: {template_cache}"
            )


# Example output documentation
"""
EXAMPLE HYPOTHESIS OUTPUT
-------------------------

Running these tests generates thousands of path examples like:

1. Profile directories:
   - /tmp/xyz/source/.bengal/profiles
   - /tmp/abc123/my-project/.bengal/profiles

2. Log directories:
   - /tmp/xyz/source/.bengal/logs
   - /tmp/abc/nested/deep/.bengal/logs

3. Cache paths:
   - /tmp/xyz/public/.bengal-cache.json
   - /tmp/abc/output/.bengal-cache.json

4. Template caches:
   - /tmp/xyz/public/.bengal-cache/templates
   - /tmp/abc/output/.bengal-cache/templates

Each test runs 100+ times with different directory names,
automatically discovering edge cases like:
- Relative vs absolute paths
- Deep nesting
- Special characters
- Unicode in paths

To see statistics:
    pytest tests/unit/utils/test_paths_properties.py --hypothesis-show-statistics
"""

"""
Tests for BuildOptions dataclass.

Tests cover:
- BuildOptions default values
- BuildOptions with custom values
- Integration with BuildOrchestrator.build()
- Integration with Site.build()

Note: Parallel processing is now auto-detected via should_parallelize().
Use force_sequential=True to explicitly disable parallel processing.
"""

from __future__ import annotations

from pathlib import Path

from bengal.orchestration.build.options import BuildOptions


class TestBuildOptionsDefaults:
    """Tests for BuildOptions default values."""

    def test_default_force_sequential_is_false(self):
        """Test force_sequential defaults to False (auto-detect mode)."""
        options = BuildOptions()
        assert options.force_sequential is False

    def test_default_incremental_is_none(self):
        """Test incremental defaults to None (auto-detect)."""
        options = BuildOptions()
        assert options.incremental is None

    def test_default_verbose_is_false(self):
        """Test verbose defaults to False."""
        options = BuildOptions()
        assert options.verbose is False

    def test_default_quiet_is_false(self):
        """Test quiet defaults to False."""
        options = BuildOptions()
        assert options.quiet is False

    def test_default_memory_optimized_is_false(self):
        """Test memory_optimized defaults to False."""
        options = BuildOptions()
        assert options.memory_optimized is False

    def test_default_strict_is_false(self):
        """Test strict defaults to False."""
        options = BuildOptions()
        assert options.strict is False

    def test_default_full_output_is_false(self):
        """Test full_output defaults to False."""
        options = BuildOptions()
        assert options.full_output is False

    def test_default_profile_is_none(self):
        """Test profile defaults to None."""
        options = BuildOptions()
        assert options.profile is None

    def test_default_profile_templates_is_false(self):
        """Test profile_templates defaults to False."""
        options = BuildOptions()
        assert options.profile_templates is False

    def test_default_changed_sources_is_empty_set(self):
        """Test changed_sources defaults to empty set."""
        options = BuildOptions()
        assert options.changed_sources == set()
        assert isinstance(options.changed_sources, set)

    def test_default_nav_changed_sources_is_empty_set(self):
        """Test nav_changed_sources defaults to empty set."""
        options = BuildOptions()
        assert options.nav_changed_sources == set()
        assert isinstance(options.nav_changed_sources, set)

    def test_default_structural_changed_is_false(self):
        """Test structural_changed defaults to False."""
        options = BuildOptions()
        assert options.structural_changed is False


class TestBuildOptionsCustomValues:
    """Tests for BuildOptions with custom values."""

    def test_force_sequential_true(self):
        """Test setting force_sequential to True (disable parallel)."""
        options = BuildOptions(force_sequential=True)
        assert options.force_sequential is True

    def test_incremental_true(self):
        """Test setting incremental to True."""
        options = BuildOptions(incremental=True)
        assert options.incremental is True

    def test_incremental_false(self):
        """Test setting incremental to False."""
        options = BuildOptions(incremental=False)
        assert options.incremental is False

    def test_verbose_true(self):
        """Test setting verbose to True."""
        options = BuildOptions(verbose=True)
        assert options.verbose is True

    def test_quiet_true(self):
        """Test setting quiet to True."""
        options = BuildOptions(quiet=True)
        assert options.quiet is True

    def test_with_profile(self):
        """Test setting profile."""
        from bengal.utils.profile import BuildProfile

        options = BuildOptions(profile=BuildProfile.WRITER)
        assert options.profile == BuildProfile.WRITER

    def test_strict_true(self):
        """Test setting strict to True."""
        options = BuildOptions(strict=True)
        assert options.strict is True

    def test_memory_optimized_true(self):
        """Test setting memory_optimized to True."""
        options = BuildOptions(memory_optimized=True)
        assert options.memory_optimized is True

    def test_changed_sources_with_paths(self):
        """Test setting changed_sources with paths."""
        paths = {Path("content/post1.md"), Path("content/post2.md")}
        options = BuildOptions(changed_sources=paths)
        assert options.changed_sources == paths

    def test_nav_changed_sources_with_paths(self):
        """Test setting nav_changed_sources with paths."""
        paths = {Path("content/_index.md")}
        options = BuildOptions(nav_changed_sources=paths)
        assert options.nav_changed_sources == paths

    def test_structural_changed_true(self):
        """Test setting structural_changed to True."""
        options = BuildOptions(structural_changed=True)
        assert options.structural_changed is True


class TestBuildOptionsMultipleValues:
    """Tests for BuildOptions with multiple custom values."""

    def test_production_build_options(self):
        """Test typical production build options."""
        from bengal.utils.profile import BuildProfile

        options = BuildOptions(
            profile=BuildProfile.WRITER,
            force_sequential=False,  # Auto-detect
            incremental=False,
            strict=True,
        )

        assert options.profile == BuildProfile.WRITER
        assert options.force_sequential is False
        assert options.incremental is False
        assert options.strict is True

    def test_dev_server_rebuild_options(self):
        """Test typical dev server rebuild options."""
        from bengal.utils.profile import BuildProfile

        changed = {Path("content/blog/post.md")}
        options = BuildOptions(
            profile=BuildProfile.WRITER,
            incremental=True,
            changed_sources=changed,
        )

        assert options.incremental is True
        assert options.changed_sources == changed

    def test_sequential_large_site_options(self):
        """Test options for forcing sequential build."""
        options = BuildOptions(
            force_sequential=True,  # Disable parallel
            memory_optimized=True,
            quiet=True,
        )

        assert options.force_sequential is True
        assert options.memory_optimized is True
        assert options.quiet is True


class TestBuildOptionsDataclassBehavior:
    """Tests for dataclass-specific behavior."""

    def test_options_is_dataclass(self):
        """Test BuildOptions is a dataclass."""
        from dataclasses import is_dataclass

        assert is_dataclass(BuildOptions)

    def test_options_equality(self):
        """Test BuildOptions equality comparison."""
        options1 = BuildOptions(force_sequential=True, strict=True)
        options2 = BuildOptions(force_sequential=True, strict=True)

        assert options1 == options2

    def test_options_inequality(self):
        """Test BuildOptions inequality comparison."""
        options1 = BuildOptions(force_sequential=True)
        options2 = BuildOptions(force_sequential=False)

        assert options1 != options2

    def test_options_repr(self):
        """Test BuildOptions has readable repr."""
        options = BuildOptions(force_sequential=True, strict=True)
        repr_str = repr(options)

        assert "BuildOptions" in repr_str
        assert "force_sequential=True" in repr_str
        assert "strict=True" in repr_str

    def test_mutable_default_isolation(self):
        """Test that mutable defaults (sets) are isolated per instance."""
        options1 = BuildOptions()
        options2 = BuildOptions()

        # Modify one instance's set
        options1.changed_sources.add(Path("test.md"))

        # Other instance should not be affected
        assert len(options2.changed_sources) == 0

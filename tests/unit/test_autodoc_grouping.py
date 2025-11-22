"""Unit tests for autodoc URL grouping functionality."""

from __future__ import annotations

from bengal.autodoc.utils import apply_grouping, auto_detect_prefix_map


class TestAutoDetectPrefixMap:
    """Tests for auto_detect_prefix_map function."""

    def test_simple_package(self, tmp_path):
        """Auto-detect finds simple package structure."""
        # Create: mypackage/core/__init__.py
        core_dir = tmp_path / "mypackage" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "__init__.py").touch()

        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"])

        assert "core" in prefix_map
        assert prefix_map["core"] == "core"

    def test_nested_packages(self, tmp_path):
        """Auto-detect finds nested packages."""
        # Create: mypackage/cli/__init__.py
        #         mypackage/cli/templates/__init__.py
        cli_dir = tmp_path / "mypackage" / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "__init__.py").touch()

        templates_dir = cli_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "__init__.py").touch()

        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"])

        assert "cli" in prefix_map
        assert "cli.templates" in prefix_map
        assert prefix_map["cli"] == "cli"
        assert prefix_map["cli.templates"] == "cli/templates"

    def test_with_strip_prefix(self, tmp_path):
        """Auto-detect strips configured prefix."""
        # Create: mypackage/core/__init__.py
        core_dir = tmp_path / "mypackage" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "__init__.py").touch()

        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"], strip_prefix="mypackage.")

        # Should have "core", not "mypackage.core"
        assert "core" in prefix_map
        assert "mypackage.core" not in prefix_map
        assert prefix_map["core"] == "core"

    def test_ignores_non_packages(self, tmp_path):
        """Auto-detect skips directories without __init__.py."""
        # Create: mypackage/utils/ (no __init__.py)
        #         mypackage/utils/helper.py
        utils_dir = tmp_path / "mypackage" / "utils"
        utils_dir.mkdir(parents=True)
        (utils_dir / "helper.py").write_text("def helper(): pass")

        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"])

        # utils should not be in prefix_map (no __init__.py)
        assert "utils" not in prefix_map

    def test_multiple_source_dirs(self, tmp_path):
        """Auto-detect works across multiple source directories."""
        # Create: src1/package1/core/__init__.py
        #         src2/package2/utils/__init__.py
        src1_dir = tmp_path / "src1" / "package1" / "core"
        src1_dir.mkdir(parents=True)
        (src1_dir / "__init__.py").touch()

        src2_dir = tmp_path / "src2" / "package2" / "utils"
        src2_dir.mkdir(parents=True)
        (src2_dir / "__init__.py").touch()

        prefix_map = auto_detect_prefix_map(
            [tmp_path / "src1" / "package1", tmp_path / "src2" / "package2"]
        )

        assert "core" in prefix_map
        assert "utils" in prefix_map

    def test_root_init_skipped(self, tmp_path):
        """Auto-detect skips root __init__.py."""
        # Create: mypackage/__init__.py (root)
        package_dir = tmp_path / "mypackage"
        package_dir.mkdir()
        (package_dir / "__init__.py").touch()

        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"])

        # Root package should not be in map (empty module_parts)
        assert prefix_map == {}

    def test_nonexistent_directory(self, tmp_path):
        """Auto-detect handles nonexistent directories gracefully."""
        prefix_map = auto_detect_prefix_map([tmp_path / "nonexistent"])

        assert prefix_map == {}

    def test_empty_after_strip_prefix(self, tmp_path):
        """Auto-detect skips modules that are empty after stripping prefix."""
        # Create: mypackage/__init__.py
        package_dir = tmp_path / "mypackage"
        package_dir.mkdir()
        (package_dir / "__init__.py").touch()

        # This would create empty module name after stripping
        prefix_map = auto_detect_prefix_map([tmp_path], strip_prefix="mypackage")

        # Should be empty (module name becomes empty after strip)
        assert "mypackage" not in prefix_map or prefix_map == {}


class TestApplyGrouping:
    """Tests for apply_grouping function."""

    def test_off_mode_returns_no_grouping(self):
        """Mode 'off' returns no grouping."""
        config = {"mode": "off", "prefix_map": {"core": "core"}}

        group, remaining = apply_grouping("mypackage.core.site", config)

        assert group is None
        assert remaining == "mypackage.core.site"

    def test_longest_prefix_wins(self):
        """Longest matching prefix takes priority."""
        config = {
            "mode": "auto",
            "prefix_map": {
                "cli": "cli",
                "cli.templates": "cli/templates",
            },
        }

        group, remaining = apply_grouping("cli.templates.blog", config)

        # Should match "cli.templates", not "cli"
        assert group == "cli/templates"
        assert remaining == "blog"

    def test_exact_match(self):
        """Exact prefix match works."""
        config = {
            "mode": "auto",
            "prefix_map": {"core": "core"},
        }

        group, remaining = apply_grouping("core", config)

        assert group == "core"
        assert remaining == ""

    def test_no_match_returns_ungrouped(self):
        """No matching prefix returns ungrouped."""
        config = {
            "mode": "auto",
            "prefix_map": {"core": "core"},
        }

        group, remaining = apply_grouping("utils.helper", config)

        assert group is None
        assert remaining == "utils.helper"

    def test_partial_word_match_rejected(self):
        """Partial word matches don't count."""
        config = {
            "mode": "auto",
            "prefix_map": {"core": "core"},
        }

        # "core_utils" should not match "core" prefix
        group, remaining = apply_grouping("core_utils.helper", config)

        assert group is None
        assert remaining == "core_utils.helper"

    def test_nested_module_under_prefix(self):
        """Nested modules under prefix get grouped correctly."""
        config = {
            "mode": "auto",
            "prefix_map": {"cli.templates": "cli/templates"},
        }

        group, remaining = apply_grouping("cli.templates.blog.template", config)

        assert group == "cli/templates"
        assert remaining == "blog.template"

    def test_empty_prefix_map_returns_ungrouped(self):
        """Empty prefix_map returns no grouping."""
        config = {"mode": "auto", "prefix_map": {}}

        group, remaining = apply_grouping("mypackage.core.site", config)

        assert group is None
        assert remaining == "mypackage.core.site"

    def test_missing_mode_defaults_to_off(self):
        """Missing mode defaults to 'off'."""
        config = {"prefix_map": {"core": "core"}}

        group, remaining = apply_grouping("core.site", config)

        # Default mode="off" means no grouping
        assert group is None
        assert remaining == "core.site"

    def test_explicit_mode_works(self):
        """Explicit mode works same as auto."""
        config = {
            "mode": "explicit",
            "prefix_map": {
                "cli.templates": "template-reference",
            },
        }

        group, remaining = apply_grouping("cli.templates.blog", config)

        assert group == "template-reference"
        assert remaining == "blog"

    def test_multiple_prefixes_longest_wins(self):
        """With multiple matching prefixes, longest wins."""
        config = {
            "mode": "auto",
            "prefix_map": {
                "a": "a",
                "a.b": "b",
                "a.b.c": "c",
            },
        }

        group, remaining = apply_grouping("a.b.c.d", config)

        # Should match "a.b.c" (longest)
        assert group == "c"
        assert remaining == "d"

    def test_dot_separated_boundary_required(self):
        """Prefix must match at dot-separated boundaries."""
        config = {
            "mode": "auto",
            "prefix_map": {"core": "core"},
        }

        # "coremain" should not match "core"
        group, remaining = apply_grouping("coremain.module", config)

        assert group is None
        assert remaining == "coremain.module"


class TestGroupingIntegration:
    """Integration tests combining auto-detection and grouping."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: detect → apply."""
        # Create structure:
        # mypackage/
        #   cli/
        #     __init__.py
        #     templates/
        #       __init__.py
        #       blog/
        #         template.py (no __init__.py)
        cli_dir = tmp_path / "mypackage" / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "__init__.py").touch()

        templates_dir = cli_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "__init__.py").touch()

        blog_dir = templates_dir / "blog"
        blog_dir.mkdir()
        (blog_dir / "template.py").write_text("# template")

        # Auto-detect
        prefix_map = auto_detect_prefix_map([tmp_path / "mypackage"], strip_prefix="mypackage.")

        # Apply grouping
        config = {"mode": "auto", "prefix_map": prefix_map}
        group, remaining = apply_grouping("cli.templates.blog.template", config)

        assert group == "cli/templates"
        assert remaining == "blog.template"

    def test_real_world_bengal_structure(self, tmp_path):
        """Test with structure similar to Bengal's own codebase."""
        # Create: bengal/core/__init__.py
        #         bengal/cli/__init__.py
        #         bengal/cli/templates/__init__.py
        #         bengal/rendering/__init__.py
        bengal_dir = tmp_path / "bengal"

        for subdir in ["core", "rendering"]:
            dir_path = bengal_dir / subdir
            dir_path.mkdir(parents=True)
            (dir_path / "__init__.py").touch()

        cli_dir = bengal_dir / "cli"
        cli_dir.mkdir(parents=True)
        (cli_dir / "__init__.py").touch()

        templates_dir = cli_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "__init__.py").touch()

        # Auto-detect
        prefix_map = auto_detect_prefix_map([tmp_path / "bengal"], strip_prefix="bengal.")

        # Verify structure
        assert "core" in prefix_map
        assert "cli" in prefix_map
        assert "cli.templates" in prefix_map
        assert "rendering" in prefix_map

        # Test grouping
        config = {"mode": "auto", "prefix_map": prefix_map}

        group1, remaining1 = apply_grouping("cli.templates.blog", config)
        assert group1 == "cli/templates"
        assert remaining1 == "blog"

        group2, remaining2 = apply_grouping("core.site", config)
        assert group2 == "core"
        assert remaining2 == "site"

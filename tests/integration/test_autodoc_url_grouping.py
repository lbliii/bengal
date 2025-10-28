"""Integration tests for autodoc URL grouping with output validation."""

from __future__ import annotations

from pathlib import Path

from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.generator import DocumentationGenerator


class TestAutodocGroupingIntegration:
    """Integration tests for URL grouping across all modes."""

    def test_mode_off_default_behavior(self, tmp_path):
        """Test mode='off' produces default URL structure."""
        # Get test root
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Configure extractor with mode='off' (default)
        # Extract from source_dir (not mypackage/) to get full mypackage.* names
        config = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "grouping": {"mode": "off"},
        }
        extractor = PythonExtractor(config=config)

        # Extract elements
        elements = extractor.extract(source_dir)

        # Generate docs
        output_dir = tmp_path / "api-off"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # Verify structure: mypackage/core/_index.md, mypackage/cli/templates/_index.md
        assert (output_dir / "mypackage" / "_index.md").exists()
        assert (output_dir / "mypackage" / "core" / "_index.md").exists()
        assert (output_dir / "mypackage" / "core" / "site.md").exists()
        assert (output_dir / "mypackage" / "cli" / "_index.md").exists()
        assert (output_dir / "mypackage" / "cli" / "templates" / "_index.md").exists()
        assert (output_dir / "mypackage" / "cli" / "templates" / "base.md").exists()
        assert (output_dir / "mypackage" / "cli" / "templates" / "blog.md").exists()

    def test_mode_auto_groups_by_package(self, tmp_path):
        """Test mode='auto' groups modules by package hierarchy."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Configure with auto mode and strip_prefix
        # Extract from source_dir (not mypackage/) to get full mypackage.* names
        config = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "auto"},
        }
        extractor = PythonExtractor(config=config)

        # Extract and generate
        elements = extractor.extract(source_dir)
        output_dir = tmp_path / "api-auto"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # Verify grouped structure
        # core package → core/_index.md
        assert (output_dir / "core" / "_index.md").exists()
        assert (output_dir / "core" / "site.md").exists()

        # cli package → cli/_index.md (with nested templates)
        assert (output_dir / "cli" / "_index.md").exists()
        assert (output_dir / "cli" / "templates" / "_index.md").exists()
        assert (output_dir / "cli" / "templates" / "base.md").exists()
        assert (output_dir / "cli" / "templates" / "blog.md").exists()

        # utils package → utils/_index.md
        assert (output_dir / "utils" / "_index.md").exists()

        # Verify mypackage/ doesn't exist at root (stripped)
        assert not (output_dir / "mypackage").exists()

    def test_mode_explicit_custom_group_names(self, tmp_path):
        """Test mode='explicit' allows custom group names."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Configure with explicit mode and custom names
        # Extract from source_dir (not mypackage/) to get full mypackage.* names
        config = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "strip_prefix": "mypackage.",
            "grouping": {
                "mode": "explicit",
                "prefix_map": {
                    "core": "core-api",
                    "cli.templates": "template-system",
                    "cli": "command-line",
                    "utils": "utilities",
                },
            },
        }
        extractor = PythonExtractor(config=config)

        # Extract and generate
        elements = extractor.extract(source_dir)
        output_dir = tmp_path / "api-explicit"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # Verify custom group names
        assert (output_dir / "core-api" / "_index.md").exists()
        assert (output_dir / "core-api" / "site.md").exists()
        assert (output_dir / "template-system" / "_index.md").exists()
        assert (output_dir / "template-system" / "base.md").exists()
        assert (output_dir / "template-system" / "blog.md").exists()
        assert (output_dir / "utilities" / "_index.md").exists()

        # Verify original names don't exist
        assert not (output_dir / "core").exists()
        assert not (output_dir / "templates").exists()

    def test_longest_prefix_wins(self, tmp_path):
        """Test that longest matching prefix takes priority."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Configure with overlapping prefixes
        # Extract from source_dir (not mypackage/) to get full mypackage.* names
        config = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "strip_prefix": "mypackage.",
            "grouping": {
                "mode": "explicit",
                "prefix_map": {
                    "cli": "cli",  # Shorter
                    "cli.templates": "templates",  # Longer, should win
                },
            },
        }
        extractor = PythonExtractor(config=config)

        # Extract and generate (extract from source_dir to get full names)
        elements = extractor.extract(source_dir)
        # Filter to only cli.templates elements for focused test
        elements = [e for e in elements if "cli.templates" in e.qualified_name]

        output_dir = tmp_path / "api-longest"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # Should be grouped under 'templates' (longer prefix)
        assert (output_dir / "templates" / "_index.md").exists()
        assert (output_dir / "templates" / "base.md").exists()

        # Not under 'cli/templates'
        assert not (output_dir / "cli" / "templates").exists()

    def test_package_index_files_preserved(self, tmp_path):
        """Test that packages generate _index.md in all modes."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        for mode in ["off", "auto"]:
            # Extract from source_dir to get full mypackage.* names
            config = {
                "source_dirs": [str(source_dir)],
                "exclude_patterns": [],  # Don't exclude test roots
                "strip_prefix": "mypackage." if mode == "auto" else "",
                "grouping": {"mode": mode},
            }
            extractor = PythonExtractor(config=config)
            elements = extractor.extract(source_dir)
            # Filter to core package only
            elements = [e for e in elements if e.qualified_name.startswith("mypackage.core")]

            output_dir = tmp_path / f"api-{mode}"
            generator = DocumentationGenerator(extractor, {"python": config})
            generator.generate_all(elements, output_dir, parallel=False)

            # Packages should always get _index.md
            if mode == "off":
                assert (output_dir / "mypackage" / "core" / "_index.md").exists()
            else:  # auto mode with strip_prefix
                assert (output_dir / "core" / "_index.md").exists()

    def test_strip_prefix_removes_leading_components(self, tmp_path):
        """Test that strip_prefix correctly removes leading module components."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Without strip_prefix - extract from source_dir to get full names
        config_no_strip = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "grouping": {"mode": "off"},
        }
        extractor_no_strip = PythonExtractor(config=config_no_strip)
        elements_no_strip = extractor_no_strip.extract(source_dir)
        # Filter to core only
        elements_no_strip = [
            e for e in elements_no_strip if e.qualified_name.startswith("mypackage.core")
        ]

        output_no_strip = tmp_path / "api-no-strip"
        generator_no_strip = DocumentationGenerator(extractor_no_strip, {"python": config_no_strip})
        generator_no_strip.generate_all(elements_no_strip, output_no_strip, parallel=False)

        # Should have mypackage/ prefix
        assert (output_no_strip / "mypackage" / "core" / "_index.md").exists()

        # With strip_prefix - extract from source_dir to get full names
        config_with_strip = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "off"},
        }
        extractor_with_strip = PythonExtractor(config=config_with_strip)
        elements_with_strip = extractor_with_strip.extract(source_dir)
        # Filter to core only
        elements_with_strip = [
            e for e in elements_with_strip if e.qualified_name.startswith("mypackage.core")
        ]

        output_with_strip = tmp_path / "api-with-strip"
        generator_with_strip = DocumentationGenerator(
            extractor_with_strip, {"python": config_with_strip}
        )
        generator_with_strip.generate_all(elements_with_strip, output_with_strip, parallel=False)

        # Should NOT have mypackage/ prefix
        assert (output_with_strip / "core" / "_index.md").exists()
        assert not (output_with_strip / "mypackage").exists()

    def test_cross_module_consistency(self, tmp_path):
        """Test that grouping is consistent across different modules."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Extract from source_dir (not mypackage/) to get full mypackage.* names
        config = {
            "source_dirs": [str(source_dir)],
            "exclude_patterns": [],  # Don't exclude test roots
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "auto"},
        }
        extractor = PythonExtractor(config=config)

        # Extract from different entry points
        elements = extractor.extract(source_dir)
        output_dir = tmp_path / "api-consistent"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # All modules should respect the same grouping
        assert (output_dir / "core" / "_index.md").exists()
        assert (output_dir / "cli" / "_index.md").exists()
        assert (output_dir / "cli" / "templates" / "_index.md").exists()
        assert (output_dir / "utils" / "_index.md").exists()

        # mypackage root should NOT exist (stripped prefix)
        assert not (output_dir / "mypackage").exists()

        # No ungrouped top-level modules
        top_level_md = [f for f in output_dir.glob("*.md")]
        assert len(top_level_md) == 0, f"Found ungrouped modules at root: {top_level_md}"

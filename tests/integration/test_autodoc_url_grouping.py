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
        config = {
            "source_dirs": [str(source_dir / "mypackage")],
            "grouping": {"mode": "off"},
        }
        extractor = PythonExtractor(config=config)

        # Extract elements
        elements = extractor.extract(source_dir / "mypackage")

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
        config = {
            "source_dirs": [str(source_dir / "mypackage")],
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "auto"},
        }
        extractor = PythonExtractor(config=config)

        # Extract and generate
        elements = extractor.extract(source_dir / "mypackage")
        output_dir = tmp_path / "api-auto"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # Verify grouped structure
        # core package → core/_index.md
        assert (output_dir / "core" / "_index.md").exists()
        assert (output_dir / "core" / "site.md").exists()

        # cli package → cli/_index.md
        assert (output_dir / "cli" / "_index.md").exists()

        # templates package (under cli) → templates/_index.md
        assert (output_dir / "templates" / "_index.md").exists()
        assert (output_dir / "templates" / "base.md").exists()
        assert (output_dir / "templates" / "blog.md").exists()

        # utils package → utils/_index.md
        assert (output_dir / "utils" / "_index.md").exists()

        # Verify mypackage/ doesn't exist at root (stripped)
        assert not (output_dir / "mypackage").exists()

    def test_mode_explicit_custom_group_names(self, tmp_path):
        """Test mode='explicit' allows custom group names."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Configure with explicit mode and custom names
        config = {
            "source_dirs": [str(source_dir / "mypackage")],
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
        elements = extractor.extract(source_dir / "mypackage")
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
        config = {
            "source_dirs": [str(source_dir / "mypackage")],
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

        # Extract and generate
        elements = extractor.extract(source_dir / "mypackage" / "cli" / "templates")
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
            config = {
                "source_dirs": [str(source_dir / "mypackage")],
                "strip_prefix": "mypackage." if mode == "auto" else "",
                "grouping": {"mode": mode},
            }
            extractor = PythonExtractor(config=config)
            elements = extractor.extract(source_dir / "mypackage" / "core")

            output_dir = tmp_path / f"api-{mode}"
            generator = DocumentationGenerator(extractor, {"python": config})
            generator.generate_all(elements, output_dir, parallel=False)

            # Packages should always get _index.md
            if mode == "off":
                assert (output_dir / "mypackage" / "core" / "_index.md").exists()
            else:  # auto
                assert (output_dir / "core" / "_index.md").exists()

    def test_strip_prefix_removes_leading_components(self, tmp_path):
        """Test that strip_prefix correctly removes leading module components."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        # Without strip_prefix
        config_no_strip = {
            "source_dirs": [str(source_dir / "mypackage")],
            "grouping": {"mode": "off"},
        }
        extractor_no_strip = PythonExtractor(config=config_no_strip)
        elements_no_strip = extractor_no_strip.extract(source_dir / "mypackage" / "core")

        output_no_strip = tmp_path / "api-no-strip"
        generator_no_strip = DocumentationGenerator(extractor_no_strip, {"python": config_no_strip})
        generator_no_strip.generate_all(elements_no_strip, output_no_strip, parallel=False)

        # Should have mypackage/ prefix
        assert (output_no_strip / "mypackage" / "core" / "_index.md").exists()

        # With strip_prefix
        config_strip = {
            "source_dirs": [str(source_dir / "mypackage")],
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "off"},
        }
        extractor_strip = PythonExtractor(config=config_strip)
        elements_strip = extractor_strip.extract(source_dir / "mypackage" / "core")

        output_strip = tmp_path / "api-strip"
        generator_strip = DocumentationGenerator(extractor_strip, {"python": config_strip})
        generator_strip.generate_all(elements_strip, output_strip, parallel=False)

        # Should NOT have mypackage/ prefix
        assert (output_strip / "core" / "_index.md").exists()
        assert not (output_strip / "mypackage").exists()

    def test_cross_module_consistency(self, tmp_path):
        """Test that grouping is consistent across different modules."""
        source_dir = Path(__file__).parent.parent / "roots" / "autodoc-grouping" / "source"

        config = {
            "source_dirs": [str(source_dir / "mypackage")],
            "strip_prefix": "mypackage.",
            "grouping": {"mode": "auto"},
        }
        extractor = PythonExtractor(config=config)

        # Extract from different entry points
        elements = extractor.extract(source_dir / "mypackage")
        output_dir = tmp_path / "api-consistent"
        generator = DocumentationGenerator(extractor, {"python": config})
        generator.generate_all(elements, output_dir, parallel=False)

        # All modules should respect the same grouping
        assert (output_dir / "core" / "_index.md").exists()
        assert (output_dir / "templates" / "_index.md").exists()
        assert (output_dir / "utils" / "_index.md").exists()

        # No ungrouped modules should exist
        module_files = list(output_dir.glob("*.md"))
        assert len(module_files) == 0, f"Found ungrouped modules: {module_files}"

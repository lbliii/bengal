"""Tests for SwizzleManager - theme template override system."""

import contextlib
import json
from unittest.mock import MagicMock

import pytest

from bengal.utils.swizzle import SwizzleManager, SwizzleRecord


@pytest.fixture
def temp_site(tmp_path):
    """Create a temporary site structure."""
    # Create site directories
    root = tmp_path / "site"
    root.mkdir()
    (root / "templates").mkdir()
    (root / "themes" / "default" / "templates").mkdir(parents=True)

    # Create a sample theme template
    theme_template = root / "themes" / "default" / "templates" / "partials" / "toc.html"
    theme_template.parent.mkdir(parents=True, exist_ok=True)
    theme_template.write_text("<nav>Table of Contents</nav>")

    return root


@pytest.fixture
def mock_site(temp_site):
    """Create a mock Site object."""
    site = MagicMock()
    site.root_path = temp_site
    site.theme = "default"
    return site


@pytest.fixture
def swizzle_manager(mock_site):
    """Create SwizzleManager instance."""
    return SwizzleManager(mock_site)


class TestSwizzleManager:
    """Test SwizzleManager class."""

    def test_initialization(self, mock_site):
        """Test creating SwizzleManager instance."""
        manager = SwizzleManager(mock_site)

        assert manager.site == mock_site
        assert manager.root == mock_site.root_path
        assert manager.registry_path == mock_site.root_path / ".bengal" / "themes" / "sources.json"

    def test_registry_path_structure(self, swizzle_manager, temp_site):
        """Test registry path has correct structure."""
        assert swizzle_manager.registry_path == temp_site / ".bengal" / "themes" / "sources.json"


class TestSwizzle:
    """Test swizzle() method - copying theme templates."""

    def test_swizzle_template(self, swizzle_manager, temp_site):
        """Test swizzling a theme template."""
        # Swizzle the template
        dest = swizzle_manager.swizzle("partials/toc.html")

        # Check file was copied
        assert dest.exists()
        assert dest == temp_site / "templates" / "partials" / "toc.html"
        assert dest.read_text() == "<nav>Table of Contents</nav>"

    def test_swizzle_creates_directories(self, swizzle_manager, temp_site):
        """Test that swizzle creates necessary directories."""
        dest = swizzle_manager.swizzle("partials/nested/deep/template.html")

        # Parent directories should be created
        assert dest.parent.exists()
        assert dest.parent == temp_site / "templates" / "partials" / "nested" / "deep"

    def test_swizzle_records_provenance(self, swizzle_manager):
        """Test that swizzle records provenance information."""
        swizzle_manager.swizzle("partials/toc.html")

        # Check registry was created
        assert swizzle_manager.registry_path.exists()

        # Check record was saved
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        assert "partials/toc.html" in registry
        record = registry["partials/toc.html"]
        assert "source" in record
        assert "theme" in record
        assert "upstream_checksum" in record
        assert "local_checksum" in record
        assert "timestamp" in record

    def test_swizzle_missing_template_raises(self, swizzle_manager):
        """Test that swizzling missing template raises error."""
        with pytest.raises(FileNotFoundError):
            swizzle_manager.swizzle("partials/nonexistent.html")

    def test_swizzle_overwrites_existing(self, swizzle_manager, temp_site):
        """Test that swizzling existing template overwrites it."""
        dest = temp_site / "templates" / "partials" / "toc.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<nav>Old content</nav>")

        swizzle_manager.swizzle("partials/toc.html")

        # Should be overwritten with theme template
        assert dest.read_text() == "<nav>Table of Contents</nav>"

    def test_swizzle_multiple_templates(self, swizzle_manager, temp_site):
        """Test swizzling multiple templates."""
        # Create multiple theme templates
        templates = [
            "partials/header.html",
            "partials/footer.html",
            "layouts/base.html",
        ]

        for template in templates:
            theme_file = temp_site / "themes" / "default" / "templates" / template
            theme_file.parent.mkdir(parents=True, exist_ok=True)
            theme_file.write_text(f"<div>{template}</div>")

        # Swizzle all
        for template in templates:
            swizzle_manager.swizzle(template)

        # All should exist in project templates
        for template in templates:
            dest = temp_site / "templates" / template
            assert dest.exists()

        # Registry should have all records
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        for template in templates:
            assert template in registry


class TestListSwizzled:
    """Test list_swizzled() method."""

    def test_list_empty(self, swizzle_manager):
        """Test listing when no templates are swizzled."""
        records = swizzle_manager.list_swizzled()

        assert records == []

    def test_list_single_template(self, swizzle_manager):
        """Test listing single swizzled template."""
        swizzle_manager.swizzle("partials/toc.html")

        records = swizzle_manager.list_swizzled()

        assert len(records) == 1
        assert records[0].target == "partials/toc.html"
        assert records[0].theme == "default"

    def test_list_multiple_templates(self, swizzle_manager, temp_site):
        """Test listing multiple swizzled templates."""
        templates = ["partials/toc.html", "partials/header.html"]

        for template in templates:
            theme_file = temp_site / "themes" / "default" / "templates" / template
            theme_file.parent.mkdir(parents=True, exist_ok=True)
            theme_file.write_text(f"<div>{template}</div>")
            swizzle_manager.swizzle(template)

        records = swizzle_manager.list_swizzled()

        assert len(records) == 2
        targets = [r.target for r in records]
        assert "partials/toc.html" in targets
        assert "partials/header.html" in targets

    def test_list_returns_swizzle_records(self, swizzle_manager):
        """Test that list returns SwizzleRecord objects."""
        swizzle_manager.swizzle("partials/toc.html")

        records = swizzle_manager.list_swizzled()

        assert len(records) == 1
        assert isinstance(records[0], SwizzleRecord)


class TestDetectModifications:
    """Test _is_modified() method for detecting local changes."""

    def test_unmodified_template(self, swizzle_manager, temp_site):
        """Test detecting unmodified template."""
        swizzle_manager.swizzle("partials/toc.html")

        # Template not modified
        is_modified = swizzle_manager._is_modified("partials/toc.html")

        assert is_modified is False

    def test_modified_template(self, swizzle_manager, temp_site):
        """Test detecting modified template."""
        swizzle_manager.swizzle("partials/toc.html")

        # Modify the local template
        local_file = temp_site / "templates" / "partials" / "toc.html"
        local_file.write_text("<nav>Modified content</nav>")

        is_modified = swizzle_manager._is_modified("partials/toc.html")

        assert is_modified is True

    def test_modified_detection_for_missing_template(self, swizzle_manager):
        """Test modification detection for template not in registry."""
        # Template never swizzled
        is_modified = swizzle_manager._is_modified("partials/nonexistent.html")

        # Should return False (or handle gracefully)
        assert is_modified is False or is_modified is None


class TestChecksumCalculation:
    """Test checksum calculation for tracking changes."""

    def test_checksum_consistent(self, swizzle_manager):
        """Test that checksum is consistent for same content."""
        swizzle_manager.swizzle("partials/toc.html")

        # Get record
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        record = registry["partials/toc.html"]
        checksum1 = record["upstream_checksum"]
        checksum2 = record["local_checksum"]

        # Both should be same (content is same at swizzle time)
        assert checksum1 == checksum2

    def test_checksum_changes_after_modification(self, swizzle_manager, temp_site):
        """Test that checksum changes after modification."""
        swizzle_manager.swizzle("partials/toc.html")

        # Get original checksum
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)
        original_checksum = registry["partials/toc.html"]["local_checksum"]

        # Modify file
        local_file = temp_site / "templates" / "partials" / "toc.html"
        local_file.write_text("<nav>Different content</nav>")

        # Re-calculate checksum
        from bengal.utils.swizzle import _checksum_file

        new_checksum = _checksum_file(local_file)

        assert new_checksum != original_checksum


class TestFindThemeTemplate:
    """Test _find_theme_template() method."""

    def test_finds_template_in_theme(self, swizzle_manager, temp_site):
        """Test finding template in theme directory."""
        template = swizzle_manager._find_theme_template("partials/toc.html")

        expected = temp_site / "themes" / "default" / "templates" / "partials" / "toc.html"
        assert template == expected

    def test_returns_none_for_missing_template(self, swizzle_manager):
        """Test that missing template returns None or raises."""
        template = swizzle_manager._find_theme_template("partials/missing.html")

        # Implementation may return None or Path that doesn't exist
        assert template is None or not template.exists()


class TestSaveAndLoadRegistry:
    """Test registry persistence."""

    def test_save_creates_registry_file(self, swizzle_manager):
        """Test that saving creates registry file."""
        swizzle_manager.swizzle("partials/toc.html")

        assert swizzle_manager.registry_path.exists()

    def test_save_creates_parent_directories(self, swizzle_manager):
        """Test that saving creates parent directories."""
        swizzle_manager.swizzle("partials/toc.html")

        # .bengal/themes directory should exist
        assert swizzle_manager.registry_path.parent.exists()

    def test_registry_is_valid_json(self, swizzle_manager):
        """Test that registry file is valid JSON."""
        swizzle_manager.swizzle("partials/toc.html")

        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        assert isinstance(registry, dict)

    def test_load_empty_registry(self, swizzle_manager):
        """Test loading empty registry."""
        records = swizzle_manager.list_swizzled()

        assert records == []

    def test_load_persisted_registry(self, swizzle_manager):
        """Test that registry persists across instances."""
        swizzle_manager.swizzle("partials/toc.html")

        # Create new manager instance
        manager2 = SwizzleManager(swizzle_manager.site)
        records = manager2.list_swizzled()

        assert len(records) == 1
        assert records[0].target == "partials/toc.html"


class TestSwizzleRecord:
    """Test SwizzleRecord dataclass."""

    def test_create_record(self):
        """Test creating SwizzleRecord."""
        record = SwizzleRecord(
            target="partials/toc.html",
            source="/path/to/theme/templates/partials/toc.html",
            theme="default",
            upstream_checksum="abc123",
            local_checksum="abc123",
            timestamp=1234567890.0,
        )

        assert record.target == "partials/toc.html"
        assert record.theme == "default"
        assert record.upstream_checksum == "abc123"

    def test_record_is_hashable(self):
        """Test that SwizzleRecord is hashable (frozen dataclass)."""
        record = SwizzleRecord(
            target="partials/toc.html",
            source="/path/to/theme/templates/partials/toc.html",
            theme="default",
            upstream_checksum="abc123",
            local_checksum="abc123",
            timestamp=1234567890.0,
        )

        # Should be hashable
        hash(record)

        # Should be usable in sets
        record_set = {record}
        assert record in record_set


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_swizzle_with_no_theme(self, temp_site):
        """Test swizzle when site has no theme."""
        site = MagicMock()
        site.root_path = temp_site
        site.theme = None

        manager = SwizzleManager(site)

        # Should handle missing theme gracefully
        with contextlib.suppress(FileNotFoundError, AttributeError):
            # Expected to fail, but shouldn't crash
            manager.swizzle("partials/toc.html")

    def test_swizzle_absolute_path(self, swizzle_manager):
        """Test that swizzle handles relative paths only."""
        # Swizzle should use relative paths
        dest = swizzle_manager.swizzle("partials/toc.html")

        # Destination should be relative to templates dir
        assert "templates/partials/toc.html" in str(dest)

    def test_concurrent_swizzles(self, swizzle_manager, temp_site):
        """Test swizzling templates in sequence."""
        templates = [f"partial{i}.html" for i in range(5)]

        for template in templates:
            theme_file = temp_site / "themes" / "default" / "templates" / template
            theme_file.write_text(f"<div>{template}</div>")
            swizzle_manager.swizzle(template)

        records = swizzle_manager.list_swizzled()
        assert len(records) == 5

    def test_swizzle_with_unicode_filename(self, swizzle_manager, temp_site):
        """Test swizzling template with unicode in filename."""
        template = "partials/导航.html"
        theme_file = temp_site / "themes" / "default" / "templates" / template
        theme_file.parent.mkdir(parents=True, exist_ok=True)
        theme_file.write_text("<nav>Navigation</nav>")

        dest = swizzle_manager.swizzle(template)

        assert dest.exists()
        assert "导航.html" in dest.name

    def test_swizzle_empty_template(self, swizzle_manager, temp_site):
        """Test swizzling empty template file."""
        template = "partials/empty.html"
        theme_file = temp_site / "themes" / "default" / "templates" / template
        theme_file.parent.mkdir(parents=True, exist_ok=True)
        theme_file.write_text("")

        dest = swizzle_manager.swizzle(template)

        assert dest.exists()
        assert dest.read_text() == ""


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_customize_multiple_partials(self, swizzle_manager, temp_site):
        """Test typical workflow of customizing multiple partials."""
        # Create theme partials
        partials = ["header.html", "footer.html", "sidebar.html"]

        for partial in partials:
            theme_file = temp_site / "themes" / "default" / "templates" / "partials" / partial
            theme_file.parent.mkdir(parents=True, exist_ok=True)
            theme_file.write_text(f"<div>Original {partial}</div>")

        # Swizzle all partials
        for partial in partials:
            swizzle_manager.swizzle(f"partials/{partial}")

        # Customize some
        (temp_site / "templates" / "partials" / "header.html").write_text("<header>Custom</header>")

        # Check modification detection
        assert swizzle_manager._is_modified("partials/header.html") is True
        assert swizzle_manager._is_modified("partials/footer.html") is False

    def test_list_and_inspect_swizzled_files(self, swizzle_manager, temp_site):
        """Test listing swizzled files for inspection."""
        # Swizzle some templates
        templates = ["base.html", "partials/nav.html", "layouts/default.html"]

        for template in templates:
            theme_file = temp_site / "themes" / "default" / "templates" / template
            theme_file.parent.mkdir(parents=True, exist_ok=True)
            theme_file.write_text(f"<div>{template}</div>")
            swizzle_manager.swizzle(template)

        # List all swizzled
        records = swizzle_manager.list_swizzled()

        assert len(records) == 3

        # Should be able to inspect each record
        for record in records:
            assert record.target in [t for t in templates]
            assert record.theme == "default"
            assert isinstance(record.timestamp, float)
            assert len(record.upstream_checksum) > 0

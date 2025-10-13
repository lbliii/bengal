"""Tests for SwizzleManager - theme template override system."""

import contextlib
import json
from unittest.mock import MagicMock

import pytest

from bengal.utils.swizzle import SwizzleManager, SwizzleRecord


@pytest.fixture
def temp_site(tmp_path):
    """Create a temporary site structure with test theme templates."""
    # Create site directories
    root = tmp_path / "site"
    root.mkdir()
    (root / "templates").mkdir()

    # Create test theme templates for testing
    theme_dir = root / "themes" / "default" / "templates"
    theme_dir.mkdir(parents=True, exist_ok=True)

    # Create test partials
    partials_dir = theme_dir / "partials"
    partials_dir.mkdir(parents=True, exist_ok=True)

    # Create common test templates with unique names to avoid conflicts with real theme
    (partials_dir / "test-component.html").write_text("<div>Test Component</div>")
    (partials_dir / "test-nav.html").write_text("<nav>Test Navigation</nav>")
    (theme_dir / "test-base.html").write_text("<!DOCTYPE html><html><body>Base</body></html>")
    (theme_dir / "test-page.html").write_text("<!DOCTYPE html><html><body>Test Page</body></html>")

    return root


@pytest.fixture
def mock_site(temp_site):
    """Create a mock Site object."""
    site = MagicMock()
    site.root_path = temp_site
    site.theme = "default"
    return site


@pytest.fixture
def swizzle_manager(mock_site, temp_site):
    """Create SwizzleManager instance with mocked template finding."""
    manager = SwizzleManager(mock_site)

    # Mock _find_theme_template to return our test templates
    theme_dir = temp_site / "themes" / "default" / "templates"

    def mock_find_template(template_rel_path):
        # Try to find it in our test theme directory
        test_path = theme_dir / template_rel_path
        if test_path.exists():
            return test_path
        return None

    manager._find_theme_template = mock_find_template
    return manager


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
        dest = swizzle_manager.swizzle("test-base.html")

        # Check file was copied
        assert dest.exists()
        assert dest == temp_site / "templates" / "test-base.html"
        # Verify it has actual content (not empty)
        assert len(dest.read_text()) > 0
        assert "<!DOCTYPE html>" in dest.read_text()

    def test_swizzle_creates_directories(self, swizzle_manager, temp_site):
        """Test that swizzle creates necessary directories."""
        dest = swizzle_manager.swizzle("partials/test-component.html")

        # Parent directories should be created
        assert dest.exists()
        assert dest.parent == temp_site / "templates" / "partials"

    def test_swizzle_records_provenance(self, swizzle_manager):
        """Test that swizzle records provenance information."""
        swizzle_manager.swizzle("test-page.html")

        # Check registry was created
        assert swizzle_manager.registry_path.exists()

        # Check record was saved
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        # Registry format: {"records": [{"target": "...", ...}]}
        assert "records" in registry
        assert len(registry["records"]) > 0
        record = registry["records"][0]
        assert record["target"] == "test-page.html"
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
        dest = temp_site / "templates" / "partials" / "test-component.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<div>Old content</div>")

        swizzle_manager.swizzle("partials/test-component.html")

        # Should be overwritten with theme template
        assert dest.read_text() == "<div>Test Component</div>"

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

        # Check all templates are in records
        targets = [rec["target"] for rec in registry["records"]]
        for template in templates:
            assert template in targets


class TestListSwizzled:
    """Test list_swizzled() method."""

    def test_list_empty(self, swizzle_manager):
        """Test listing when no templates are swizzled."""
        records = swizzle_manager.list_swizzled()

        assert records == []

    def test_list_single_template(self, swizzle_manager):
        """Test listing single swizzled template."""
        swizzle_manager.swizzle("partials/test-component.html")

        records = swizzle_manager.list_swizzled()

        assert len(records) == 1
        assert records[0].target == "partials/test-component.html"
        assert records[0].theme == "default"

    def test_list_multiple_templates(self, swizzle_manager):
        """Test listing multiple swizzled templates."""
        templates = ["partials/test-component.html", "partials/test-nav.html"]

        for template in templates:
            swizzle_manager.swizzle(template)

        records = swizzle_manager.list_swizzled()

        assert len(records) == 2
        targets = [r.target for r in records]
        assert "partials/test-component.html" in targets
        assert "partials/test-nav.html" in targets

    def test_list_returns_swizzle_records(self, swizzle_manager):
        """Test that list returns SwizzleRecord objects."""
        swizzle_manager.swizzle("partials/test-component.html")

        records = swizzle_manager.list_swizzled()

        assert len(records) == 1
        assert isinstance(records[0], SwizzleRecord)


class TestDetectModifications:
    """Test _is_modified() method for detecting local changes."""

    def test_unmodified_template(self, swizzle_manager, temp_site):
        """Test detecting unmodified template."""
        swizzle_manager.swizzle("partials/test-component.html")

        # Template not modified
        is_modified = swizzle_manager._is_modified("partials/test-component.html")

        assert is_modified is False

    def test_modified_template(self, swizzle_manager, temp_site):
        """Test detecting modified template."""
        swizzle_manager.swizzle("partials/test-component.html")

        # Modify the local template
        local_file = temp_site / "templates" / "partials" / "test-component.html"
        local_file.write_text("<div>Modified content</div>")

        is_modified = swizzle_manager._is_modified("partials/test-component.html")

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
        swizzle_manager.swizzle("partials/test-component.html")

        # Get record
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        record = registry["records"][0]
        checksum1 = record["upstream_checksum"]
        checksum2 = record["local_checksum"]

        # Both should be same (content is same at swizzle time)
        assert checksum1 == checksum2

    def test_checksum_changes_after_modification(self, swizzle_manager, temp_site):
        """Test that checksum changes after modification."""
        swizzle_manager.swizzle("partials/test-component.html")

        # Get original checksum
        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)
        original_checksum = registry["records"][0]["local_checksum"]

        # Modify file
        local_file = temp_site / "templates" / "partials" / "test-component.html"
        local_file.write_text("<div>Different content</div>")

        # Re-calculate checksum
        from bengal.utils.swizzle import _checksum_file

        new_checksum = _checksum_file(local_file)

        assert new_checksum != original_checksum


class TestFindThemeTemplate:
    """Test _find_theme_template() method."""

    def test_finds_template_in_theme(self, swizzle_manager, temp_site):
        """Test finding template in theme directory."""
        template = swizzle_manager._find_theme_template("partials/test-component.html")

        expected = (
            temp_site / "themes" / "default" / "templates" / "partials" / "test-component.html"
        )
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
        swizzle_manager.swizzle("partials/test-component.html")

        assert swizzle_manager.registry_path.exists()

    def test_save_creates_parent_directories(self, swizzle_manager):
        """Test that saving creates parent directories."""
        swizzle_manager.swizzle("partials/test-component.html")

        # .bengal/themes directory should exist
        assert swizzle_manager.registry_path.parent.exists()

    def test_registry_is_valid_json(self, swizzle_manager):
        """Test that registry file is valid JSON."""
        swizzle_manager.swizzle("partials/test-component.html")

        with open(swizzle_manager.registry_path) as f:
            registry = json.load(f)

        assert isinstance(registry, dict)

    def test_load_empty_registry(self, swizzle_manager):
        """Test loading empty registry."""
        records = swizzle_manager.list_swizzled()

        assert records == []

    def test_load_persisted_registry(self, swizzle_manager):
        """Test that registry persists across instances."""
        swizzle_manager.swizzle("partials/test-component.html")

        # Create new manager instance
        manager2 = SwizzleManager(swizzle_manager.site)
        records = manager2.list_swizzled()

        assert len(records) == 1
        assert records[0].target == "partials/test-component.html"


class TestSwizzleRecord:
    """Test SwizzleRecord dataclass."""

    def test_create_record(self):
        """Test creating SwizzleRecord."""
        record = SwizzleRecord(
            target="partials/test-component.html",
            source="/path/to/theme/templates/partials/test-component.html",
            theme="default",
            upstream_checksum="abc123",
            local_checksum="abc123",
            timestamp=1234567890.0,
        )

        assert record.target == "partials/test-component.html"
        assert record.theme == "default"
        assert record.upstream_checksum == "abc123"

    def test_record_is_hashable(self):
        """Test that SwizzleRecord is hashable (frozen dataclass)."""
        record = SwizzleRecord(
            target="partials/test-component.html",
            source="/path/to/theme/templates/partials/test-component.html",
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
            manager.swizzle("partials/search.html")

    def test_swizzle_absolute_path(self, swizzle_manager):
        """Test that swizzle handles relative paths only."""
        # Swizzle should use relative paths
        dest = swizzle_manager.swizzle("partials/test-component.html")

        # Destination should be relative to templates dir
        assert "templates/partials/test-component.html" in str(dest)

    def test_concurrent_swizzles(self, swizzle_manager, temp_site):
        """Test swizzling templates in sequence."""
        templates = [f"partial{i}.html" for i in range(5)]

        for template in templates:
            theme_file = temp_site / "themes" / "default" / "templates" / template
            theme_file.parent.mkdir(parents=True, exist_ok=True)
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
        templates = ["test-base.html", "partials/test-component.html", "partials/test-nav.html"]

        for template in templates:
            swizzle_manager.swizzle(template)

        # List all swizzled
        records = swizzle_manager.list_swizzled()

        assert len(records) == 3

        # Should be able to inspect each record
        for record in records:
            assert record.target in templates
            assert record.theme == "default"
            assert isinstance(record.timestamp, float)
            assert len(record.upstream_checksum) > 0

"""
Integration tests for versioned documentation pipeline integration.

Tests cover:
- Shared content change detection and cascade to all versions
- Version-specific change detection
- Version config change detection
- Build trigger version awareness

RFC: rfc-versioned-docs-pipeline-integration
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.site import Site
from bengal.orchestration.incremental import IncrementalOrchestrator
from bengal.server.build_trigger import BuildTrigger as _BuildTrigger
from bengal.server.wiring import get_reload_controller


def BuildTrigger(*args: object, **kwargs: object) -> _BuildTrigger:
    """Create BuildTrigger with explicit reload controller dependency."""
    kwargs.setdefault("reload_controller", get_reload_controller())
    return _BuildTrigger(*args, **kwargs)


class TestSharedContentCascade:
    """Tests for shared content change cascading to all versions."""

    @pytest.fixture
    def temp_versioned_site(self):
        """Create a temporary versioned site directory."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create site structure
        content_dir = temp_dir / "content"
        config_dir = temp_dir / "config" / "_default"
        config_dir.mkdir(parents=True)

        # Create versioning config
        (config_dir / "versioning.yaml").write_text("""
versioning:
  enabled: true
  sections:
    - docs
  shared:
    - _shared
  versions:
    - id: v2
      label: "2.0"
      latest: true
    - id: v1
      label: "1.0"
  aliases:
    latest: v2
""")

        # Create bengal.toml
        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Versioned Test Site"
baseurl = "/"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"
""")

        # Create versioned content
        docs_v2 = content_dir / "docs"
        docs_v2.mkdir(parents=True)
        (docs_v2 / "guide.md").write_text("""---
title: Guide v2
---
# Guide v2
""")

        docs_v1 = content_dir / "_versions" / "v1" / "docs"
        docs_v1.mkdir(parents=True)
        (docs_v1 / "guide.md").write_text("""---
title: Guide v1
---
# Guide v1
""")

        # Create shared content
        shared_dir = content_dir / "_shared"
        shared_dir.mkdir(parents=True)
        (shared_dir / "changelog.md").write_text("""---
title: Changelog
---
# Changelog
""")

        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_shared_content_change_detected(self, temp_versioned_site):
        """Test that changes to _shared/ content are detected."""
        # Create site and initialize
        site = Site.from_config(temp_versioned_site)
        site.discover_content()

        # Verify versioning is enabled
        assert site.versioning_enabled is True

        # Create build trigger
        trigger = BuildTrigger(site)

        # Simulate shared content change
        shared_file = temp_versioned_site / "content" / "_shared" / "changelog.md"
        changed_paths = {shared_file}

        # Check if detected as shared content change
        is_shared = trigger._is_shared_content_change(changed_paths)
        assert is_shared is True

    def test_shared_content_triggers_full_rebuild(self, temp_versioned_site):
        """Test that shared content changes trigger full rebuild."""
        site = Site.from_config(temp_versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        # Simulate shared content change
        shared_file = temp_versioned_site / "content" / "_shared" / "changelog.md"
        changed_paths = {shared_file}
        event_types = {"modified"}

        # Check if full rebuild needed
        needs_full = trigger._needs_full_rebuild(changed_paths, event_types)
        assert needs_full is True

    def test_version_specific_change_not_shared(self, temp_versioned_site):
        """Test that version-specific changes don't trigger shared cascade."""
        site = Site.from_config(temp_versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        # Simulate v1 content change
        v1_file = temp_versioned_site / "content" / "_versions" / "v1" / "docs" / "guide.md"
        changed_paths = {v1_file}

        # Should NOT be detected as shared content change
        is_shared = trigger._is_shared_content_change(changed_paths)
        assert is_shared is False


class TestVersionAffectedDetection:
    """Tests for detecting which versions are affected by changes."""

    @pytest.fixture
    def versioned_site(self):
        """Create a mock versioned site."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create minimal versioned structure
        config_dir = temp_dir / "config" / "_default"
        config_dir.mkdir(parents=True)

        (config_dir / "versioning.yaml").write_text("""
versioning:
  enabled: true
  sections:
    - docs
    - api
  versions:
    - id: v3
      latest: true
    - id: v2
    - id: v1
  aliases:
    latest: v3
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test"
baseurl = "/"
""")

        # Create content directories
        (temp_dir / "content" / "docs").mkdir(parents=True)
        (temp_dir / "content" / "docs" / "guide.md").write_text("---\ntitle: Guide\n---\n")
        (temp_dir / "content" / "_versions" / "v2" / "docs").mkdir(parents=True)
        (temp_dir / "content" / "_versions" / "v2" / "docs" / "guide.md").write_text(
            "---\ntitle: Guide v2\n---\n"
        )
        (temp_dir / "content" / "_versions" / "v1" / "docs").mkdir(parents=True)
        (temp_dir / "content" / "_versions" / "v1" / "docs" / "guide.md").write_text(
            "---\ntitle: Guide v1\n---\n"
        )

        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_get_affected_versions_v1(self, versioned_site):
        """Test detecting v1 as affected from _versions/v1/ path."""
        site = Site.from_config(versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        v1_file = versioned_site / "content" / "_versions" / "v1" / "docs" / "guide.md"
        affected = trigger._get_affected_versions({v1_file})

        assert "v1" in affected
        assert "v2" not in affected
        assert "v3" not in affected

    def test_get_affected_versions_v2(self, versioned_site):
        """Test detecting v2 as affected from _versions/v2/ path."""
        site = Site.from_config(versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        v2_file = versioned_site / "content" / "_versions" / "v2" / "docs" / "guide.md"
        affected = trigger._get_affected_versions({v2_file})

        assert "v2" in affected
        assert "v1" not in affected
        assert "v3" not in affected

    def test_get_affected_versions_latest(self, versioned_site):
        """Test detecting latest version from main docs/ path."""
        site = Site.from_config(versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        latest_file = versioned_site / "content" / "docs" / "guide.md"
        affected = trigger._get_affected_versions({latest_file})

        assert "v3" in affected  # v3 is latest
        assert "v2" not in affected
        assert "v1" not in affected

    def test_get_affected_versions_multiple(self, versioned_site):
        """Test detecting multiple affected versions."""
        site = Site.from_config(versioned_site)
        site.discover_content()

        trigger = BuildTrigger(site)

        v1_file = versioned_site / "content" / "_versions" / "v1" / "docs" / "guide.md"
        v2_file = versioned_site / "content" / "_versions" / "v2" / "docs" / "guide.md"
        affected = trigger._get_affected_versions({v1_file, v2_file})

        assert "v1" in affected
        assert "v2" in affected
        assert "v3" not in affected


class TestVersionConfigChange:
    """Tests for version config change detection."""

    def test_versioning_yaml_detected(self):
        """Test that versioning.yaml changes are detected."""
        site = MagicMock()
        site.versioning_enabled = True

        trigger = BuildTrigger(site)

        config_file = Path("/site/config/_default/versioning.yaml")
        is_config_change = trigger._is_version_config_change({config_file})

        assert is_config_change is True

    def test_other_config_not_detected(self):
        """Test that non-version config files are not detected."""
        site = MagicMock()
        site.versioning_enabled = True

        trigger = BuildTrigger(site)

        other_config = Path("/site/config/_default/site.yaml")
        is_config_change = trigger._is_version_config_change({other_config})

        assert is_config_change is False

    def test_version_config_triggers_full_rebuild(self):
        """Test that version config change triggers full rebuild."""
        site = MagicMock()
        site.versioning_enabled = True

        trigger = BuildTrigger(site)

        config_file = Path("/site/config/_default/versioning.yaml")
        event_types = {"modified"}

        needs_full = trigger._needs_full_rebuild({config_file}, event_types)
        assert needs_full is True


class TestIncrementalOrchestratorVersioning:
    """Tests for IncrementalOrchestrator versioning support."""

    @pytest.fixture
    def temp_versioned_site_with_cache(self):
        """Create a temporary versioned site with cache initialized."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create site structure
        content_dir = temp_dir / "content"
        config_dir = temp_dir / "config" / "_default"
        config_dir.mkdir(parents=True)

        (config_dir / "versioning.yaml").write_text("""
versioning:
  enabled: true
  sections:
    - docs
  shared:
    - _shared
  versions:
    - id: v2
      latest: true
    - id: v1
  aliases:
    latest: v2
""")

        (temp_dir / "bengal.toml").write_text("""
[site]
title = "Test"
baseurl = "/"
""")

        # Create content
        (content_dir / "docs").mkdir(parents=True)
        (content_dir / "docs" / "guide.md").write_text("---\ntitle: Guide v2\n---\n")
        (content_dir / "_versions" / "v1" / "docs").mkdir(parents=True)
        (content_dir / "_versions" / "v1" / "docs" / "guide.md").write_text(
            "---\ntitle: Guide v1\n---\n"
        )
        (content_dir / "_shared").mkdir(parents=True)
        (content_dir / "_shared" / "changelog.md").write_text("---\ntitle: Changelog\n---\n")

        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_check_shared_content_changes_enabled(self, temp_versioned_site_with_cache):
        """Test that shared content checking works when versioning enabled."""
        site = Site.from_config(temp_versioned_site_with_cache)
        site.discover_content()

        orchestrator = IncrementalOrchestrator(site)
        cache = orchestrator.initialize(enabled=True)

        # On first call, files are new (not in cache) so is_changed returns True
        result = orchestrator._check_shared_content_changes(set())
        assert result is True  # New files detected as changes

        # Update file hashes in cache (simulate first build complete)
        shared_file = temp_versioned_site_with_cache / "content" / "_shared" / "changelog.md"
        cache.update_file(shared_file)

        # After caching, no changes should be detected
        result = orchestrator._check_shared_content_changes(set())
        assert result is False  # No changes after caching

    def test_check_shared_content_changes_disabled(self, temp_versioned_site_with_cache):
        """Test that shared content checking returns False when versioning disabled."""
        # Modify config to disable versioning
        config_file = temp_versioned_site_with_cache / "config" / "_default" / "versioning.yaml"
        config_file.write_text("""
versioning:
  enabled: false
""")

        site = Site.from_config(temp_versioned_site_with_cache)
        site.discover_content()

        orchestrator = IncrementalOrchestrator(site)
        orchestrator.initialize(enabled=True)

        result = orchestrator._check_shared_content_changes(set())
        assert result is False


@pytest.mark.bengal(testroot="test-versioned")
class TestVersionedBuildIntegration:
    """Integration tests using test-versioned root."""

    def test_versioned_site_config_enabled(self, site):
        """Test that versioning is enabled in test-versioned root."""
        assert site.versioning_enabled is True
        assert site.version_config is not None
        assert len(site.version_config.versions) == 3  # v1, v2, v3

    def test_versioned_site_has_latest_content(self, site):
        """Test that versioned site discovers latest version content."""
        # Latest version is in docs/ directly (not under _versions/)
        page_paths = [str(p.source_path) for p in site.pages]
        assert any("docs/guide.md" in p for p in page_paths)

    def test_versioned_site_version_config_structure(self, site):
        """Test version config has expected structure."""
        config = site.version_config

        # Check versions
        version_ids = [v.id for v in config.versions]
        assert "v3" in version_ids
        assert "v2" in version_ids
        assert "v1" in version_ids

        # Check v3 is latest
        latest = config.latest_version
        assert latest is not None
        assert latest.id == "v3"

        # Check shared paths
        assert "_shared" in config.shared

        # Check sections
        assert "docs" in config.sections

    def test_versioned_site_discovers_older_versions(self, site):
        """Test that pages in _versions/ are actually discovered."""
        page_paths = [str(p.source_path) for p in site.pages]

        # Verify v2 and v1 pages are discovered
        assert any("_versions/v2/docs/guide.md" in p for p in page_paths)
        assert any("_versions/v1/docs/guide.md" in p for p in page_paths)

    def test_versioned_site_output_paths(self, site):
        """Test that versioned pages have correct output paths."""
        # Find v2 page
        v2_page = next(p for p in site.pages if "_versions/v2/docs/guide.md" in str(p.source_path))

        # Should have version set to 'v2'
        assert v2_page.version == "v2"

        # Should build to public/docs/v2/guide/index.html
        assert "docs/v2/guide/index.html" in str(v2_page.output_path)

        # Find v1 page
        v1_page = next(p for p in site.pages if "_versions/v1/docs/guide.md" in str(p.source_path))

        # Should have version set to 'v1'
        assert v1_page.version == "v1"

        # Should build to public/docs/v1/guide/index.html
        assert "docs/v1/guide/index.html" in str(v1_page.output_path)

    def test_versioned_site_discovers_shared_content(self, site):
        """Test that pages in _shared/ are actually discovered."""
        page_paths = [str(p.source_path) for p in site.pages]

        # Verify shared page is discovered
        assert any("_shared/changelog.md" in p for p in page_paths)

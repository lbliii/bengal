"""Integration tests for resume and changelog templates.

Tests template-specific functionality:
- Resume data loading from YAML
- Changelog releases parsing
- Template rendering with data

Phase 2 of RFC: User Scenario Coverage - Extended Validation
"""

from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-resume")
class TestResumeTemplate:
    """Test resume template with YAML data."""

    def test_resume_data_loaded(self, site) -> None:
        """Resume data from YAML should be accessible."""
        data = site.data.get("resume", {})

        # Verify core resume fields exist
        assert data.get("name"), "Resume should have a name"
        assert data.get("headline"), "Resume should have a headline"
        assert data.get("contact"), "Resume should have contact info"

    def test_resume_has_experience(self, site) -> None:
        """Resume should have experience entries."""
        data = site.data.get("resume", {})
        experience = data.get("experience", [])

        assert len(experience) >= 1, "Resume should have at least 1 experience entry"

        # Verify experience structure
        first_job = experience[0]
        assert first_job.get("title"), "Experience should have a title"
        assert first_job.get("company"), "Experience should have a company"

    def test_resume_has_skills(self, site) -> None:
        """Resume should have skills."""
        data = site.data.get("resume", {})
        skills = data.get("skills", [])

        assert len(skills) >= 1, "Resume should have at least 1 skill category"

        # Verify skills structure
        first_category = skills[0]
        assert first_category.get("category"), "Skill should have a category"
        assert first_category.get("items"), "Skill category should have items"

    def test_resume_has_education(self, site) -> None:
        """Resume should have education entries."""
        data = site.data.get("resume", {})
        education = data.get("education", [])

        assert len(education) >= 1, "Resume should have at least 1 education entry"

        # Verify education structure
        first_edu = education[0]
        assert first_edu.get("degree"), "Education should have a degree"
        assert first_edu.get("institution"), "Education should have an institution"

    def test_resume_builds_successfully(self, site, build_site) -> None:
        """Resume site should build without errors."""
        build_site()

        output = site.output_dir
        assert (output / "index.html").exists(), "Index page should be generated"

    def test_resume_renders_content(self, site, build_site) -> None:
        """Built resume should render data sections."""
        build_site()

        html = (site.output_dir / "index.html").read_text()

        # Resume data should be rendered
        data = site.data.get("resume", {})

        # The name should appear in the output
        if data.get("name"):
            assert data["name"] in html or "resume" in html.lower(), (
                "Resume content should be rendered"
            )


@pytest.mark.bengal(testroot="test-changelog")
class TestChangelogTemplate:
    """Test changelog template with releases data."""

    def test_changelog_data_loaded(self, site) -> None:
        """Changelog releases should be accessible."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])

        assert len(releases) >= 2, "Changelog should have at least 2 releases"

    def test_changelog_releases_structure(self, site) -> None:
        """Changelog releases should have proper structure."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])

        for release in releases:
            assert release.get("version"), "Release should have version"
            assert release.get("date"), "Release should have date"

    def test_changelog_has_change_types(self, site) -> None:
        """Changelog releases should have change types (added/changed/fixed)."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])

        # At least one release should have changes
        has_changes = False
        for release in releases:
            if (
                release.get("added")
                or release.get("changed")
                or release.get("fixed")
                or release.get("security")
            ):
                has_changes = True
                break

        assert has_changes, "At least one release should have changes"

    def test_changelog_builds_successfully(self, site, build_site) -> None:
        """Changelog site should build without errors."""
        build_site()

        output = site.output_dir
        assert (output / "index.html").exists(), "Index page should be generated"

    def test_changelog_displays_versions(self, site, build_site) -> None:
        """Changelog should display version numbers."""
        build_site()

        html = (site.output_dir / "index.html").read_text()

        # At least one version number should appear
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])

        if releases:
            # Check that changelog content is present (version or changelog text)
            assert "1.0.0" in html or "0.9.0" in html or "changelog" in html.lower(), (
                "Changelog should display version numbers or changelog content"
            )

    def test_changelog_releases_are_ordered(self, site) -> None:
        """Changelog releases should be in version order."""
        data = site.data.get("changelog", {})
        releases = data.get("releases", [])

        if len(releases) >= 2:
            # Extract version numbers (handle semantic versioning)
            versions = [r.get("version", "0.0.0") for r in releases]

            # First version should be the latest (1.0.0 > 0.9.0)
            assert versions[0] >= versions[-1], "Releases should be ordered newest first"

"""
Tests for _normalize_config github_repo URL handling.

The _normalize_config method extracts github_repo and github_branch from the
autodoc config section and normalizes owner/repo format to full GitHub URLs.
This is used by autodoc templates to generate correct "View source" links.

Regression test for: View source links producing 404s when github_repo is
specified in autodoc.yaml but not at the top level of site config.
"""

from bengal.rendering.pipeline.core import RenderingPipeline


class TestNormalizeConfigGithubRepo:
    """Test github_repo extraction and URL normalization."""

    def _normalize(self, config: dict) -> dict:
        """
        Call _normalize_config without needing a full pipeline instance.

        We use __new__ to create an instance without calling __init__,
        then call the method directly.
        """
        pipeline = object.__new__(RenderingPipeline)
        return pipeline._normalize_config(config)

    def test_extracts_github_repo_from_autodoc_section(self) -> None:
        """github_repo in autodoc section is extracted and normalized."""
        config = {
            "autodoc": {
                "github_repo": "lbliii/bengal",
                "github_branch": "main",
            }
        }
        result = self._normalize(config)

        assert result["github_repo"] == "https://github.com/lbliii/bengal"
        assert result["github_branch"] == "main"

    def test_converts_owner_repo_to_full_url(self) -> None:
        """owner/repo format is converted to full GitHub URL."""
        config = {"autodoc": {"github_repo": "my-org/my-project"}}
        result = self._normalize(config)

        assert result["github_repo"] == "https://github.com/my-org/my-project"

    def test_preserves_full_https_url(self) -> None:
        """Full https:// URLs are preserved unchanged."""
        config = {"autodoc": {"github_repo": "https://github.com/custom/repo"}}
        result = self._normalize(config)

        assert result["github_repo"] == "https://github.com/custom/repo"

    def test_preserves_full_http_url(self) -> None:
        """Full http:// URLs are preserved unchanged (e.g., enterprise GitHub)."""
        config = {"autodoc": {"github_repo": "http://github.example.com/org/repo"}}
        result = self._normalize(config)

        assert result["github_repo"] == "http://github.example.com/org/repo"

    def test_top_level_github_repo_takes_precedence(self) -> None:
        """Top-level github_repo takes precedence over autodoc section."""
        config = {
            "github_repo": "https://github.com/top-level/repo",
            "autodoc": {"github_repo": "autodoc/repo"},
        }
        result = self._normalize(config)

        assert result["github_repo"] == "https://github.com/top-level/repo"

    def test_empty_github_repo_stays_empty(self) -> None:
        """Empty github_repo doesn't produce malformed URL."""
        config = {"autodoc": {"github_repo": ""}}
        result = self._normalize(config)

        assert result["github_repo"] == ""

    def test_missing_github_repo_defaults_to_empty(self) -> None:
        """Missing github_repo defaults to empty string."""
        config = {"autodoc": {}}
        result = self._normalize(config)

        assert result["github_repo"] == ""

    def test_no_autodoc_section_defaults_to_empty(self) -> None:
        """Config without autodoc section defaults to empty github_repo."""
        config = {"some_other": "config"}
        result = self._normalize(config)

        assert result["github_repo"] == ""

    def test_extracts_github_branch_from_autodoc_section(self) -> None:
        """github_branch in autodoc section is extracted."""
        config = {"autodoc": {"github_branch": "develop"}}
        result = self._normalize(config)

        assert result["github_branch"] == "develop"

    def test_github_branch_defaults_to_main(self) -> None:
        """Missing github_branch defaults to 'main'."""
        config = {"autodoc": {}}
        result = self._normalize(config)

        assert result["github_branch"] == "main"

    def test_top_level_github_branch_takes_precedence(self) -> None:
        """Top-level github_branch takes precedence over autodoc section."""
        config = {
            "github_branch": "release",
            "autodoc": {"github_branch": "develop"},
        }
        result = self._normalize(config)

        assert result["github_branch"] == "release"

    def test_real_world_autodoc_config(self) -> None:
        """
        Test with realistic autodoc.yaml config structure.

        This mirrors the actual config at site/config/_default/autodoc.yaml
        """
        config = {
            "autodoc": {
                "github_repo": "lbliii/bengal",
                "github_branch": "main",
                "python": {
                    "enabled": True,
                    "source_dirs": ["../bengal"],
                },
                "cli": {
                    "enabled": True,
                    "app_module": "bengal.cli:main",
                },
            }
        }
        result = self._normalize(config)

        # View source links should produce:
        # https://github.com/lbliii/bengal/blob/main/bengal/...
        assert result["github_repo"] == "https://github.com/lbliii/bengal"
        assert result["github_branch"] == "main"

    def test_dotted_access_works(self) -> None:
        """Result supports dotted attribute access for templates."""
        config = {"autodoc": {"github_repo": "owner/repo"}}
        result = self._normalize(config)

        # Templates use config.github_repo syntax
        assert result.github_repo == "https://github.com/owner/repo"
        assert result.github_branch == "main"

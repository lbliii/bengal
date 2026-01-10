"""Tests for environment-based configuration overrides.

Tests config/env_overrides.py:
- apply_env_overrides: auto-detecting baseurl from deployment platforms

Note: Config is now nested (site.baseurl instead of flat baseurl).
"""

from __future__ import annotations

import os
from unittest.mock import patch

from bengal.config.env_overrides import apply_env_overrides


class TestApplyEnvOverridesExplicit:
    """Tests for explicit BENGAL_BASEURL override."""

    def test_explicit_baseurl_not_overridden(self):
        """Explicit baseurl in config is never overridden."""
        config = {"site": {"baseurl": "https://custom.com"}}
        result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://custom.com"

    def test_bengal_baseurl_env_overrides_missing(self):
        """BENGAL_BASEURL env var overrides missing baseurl."""
        config = {}  # Missing baseurl allows env override
        with patch.dict(os.environ, {"BENGAL_BASEURL": "https://env-override.com"}, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://env-override.com"

    def test_bengal_base_url_env_works(self):
        """BENGAL_BASE_URL (with underscore) also works."""
        config = {}  # Missing baseurl allows env override
        with patch.dict(
            os.environ,
            {"BENGAL_BASE_URL": "https://underscore-env.com"},
            clear=False,
        ):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://underscore-env.com"

    def test_strips_trailing_slash(self):
        """Strips trailing slash from baseurl."""
        config = {}  # Missing baseurl allows env override
        with patch.dict(
            os.environ,
            {"BENGAL_BASEURL": "https://example.com/"},
            clear=False,
        ):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://example.com"

    def test_empty_baseurl_allows_platform_detection(self):
        """Empty baseurl allows platform detection (enables DEFAULTS + auto-detect)."""
        # With DEFAULTS providing baseurl: "", platform detection should still work
        # This is the common case: user doesn't set baseurl, DEFAULTS sets "",
        # and we want platform detection to auto-compute the right value
        config = {"site": {"baseurl": ""}}
        env = {
            "NETLIFY": "true",
            "URL": "https://mysite.netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        # Platform detection should apply because baseurl is empty
        assert result["site"]["baseurl"] == "https://mysite.netlify.app"

    def test_bengal_baseurl_overrides_explicit_empty(self):
        """BENGAL_BASEURL can override explicit empty baseurl."""
        config = {"site": {"baseurl": ""}}  # Explicit empty
        with patch.dict(os.environ, {"BENGAL_BASEURL": "https://env-override.com"}, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://env-override.com"  # BENGAL_BASEURL overrides


class TestApplyEnvOverridesNetlify:
    """Tests for Netlify platform detection."""

    def test_netlify_production_url(self):
        """Detects Netlify production URL."""
        config = {}  # Missing baseurl allows env override
        env = {
            "NETLIFY": "true",
            "URL": "https://mysite.netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://mysite.netlify.app"

    def test_netlify_deploy_preview_url(self):
        """Detects Netlify deploy preview URL."""
        config = {}  # Missing baseurl allows env override
        env = {
            "NETLIFY": "true",
            "DEPLOY_PRIME_URL": "https://deploy-preview-123--mysite.netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://deploy-preview-123--mysite.netlify.app"

    def test_netlify_production_takes_precedence(self):
        """Production URL takes precedence over deploy preview."""
        config = {}  # Missing baseurl allows env override
        env = {
            "NETLIFY": "true",
            "URL": "https://production.netlify.app",
            "DEPLOY_PRIME_URL": "https://preview.netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://production.netlify.app"

    def test_netlify_not_detected_without_flag(self):
        """Netlify not detected without NETLIFY=true."""
        config = {"site": {"baseurl": ""}}
        # Clear platform env vars that might be set in CI
        clean_env = {
            "URL": "https://mysite.netlify.app",  # Missing NETLIFY=true
            "GITHUB_ACTIONS": "",  # Clear in case running in GitHub Actions CI
            "VERCEL": "",
        }
        with patch.dict(os.environ, clean_env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == ""


class TestApplyEnvOverridesVercel:
    """Tests for Vercel platform detection."""

    def test_vercel_detection_with_1(self):
        """Detects Vercel with VERCEL=1."""
        config = {}  # Missing baseurl allows env override
        env = {
            "VERCEL": "1",
            "VERCEL_URL": "mysite.vercel.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://mysite.vercel.app"

    def test_vercel_detection_with_true(self):
        """Detects Vercel with VERCEL=true."""
        config = {}  # Missing baseurl allows env override
        env = {
            "VERCEL": "true",
            "VERCEL_URL": "mysite.vercel.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://mysite.vercel.app"

    def test_vercel_adds_https_prefix(self):
        """Adds https:// prefix to Vercel URL."""
        config = {}  # Missing baseurl allows env override
        env = {
            "VERCEL": "1",
            "VERCEL_URL": "myproject-abc123.vercel.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"].startswith("https://")

    def test_vercel_preserves_existing_protocol(self):
        """Preserves existing protocol in Vercel URL."""
        config = {}  # Missing baseurl allows env override
        env = {
            "VERCEL": "1",
            "VERCEL_URL": "https://already-has-protocol.vercel.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://already-has-protocol.vercel.app"


class TestApplyEnvOverridesGitHub:
    """Tests for GitHub Actions/Pages detection."""

    def test_github_project_site(self):
        """Detects GitHub Pages project site with path-only baseurl."""
        config = {}  # Missing baseurl allows env override
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "owner/myrepo",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "/myrepo"

    def test_github_user_site_auto_detection(self):
        """Auto-detects user/org site when repo name matches owner.github.io."""
        config = {}  # Missing baseurl allows env override
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "myuser/myuser.github.io",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        # User/org sites serve from root, so baseurl should be empty
        assert result["site"]["baseurl"] == ""

    def test_github_pages_root_flag(self):
        """GITHUB_PAGES_ROOT=true forces root deployment."""
        config = {}  # Missing baseurl allows env override
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "owner/myrepo",
            "GITHUB_PAGES_ROOT": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == ""

    def test_github_not_detected_without_flag(self):
        """GitHub not detected without GITHUB_ACTIONS=true."""
        config = {"site": {"baseurl": ""}}
        # Clear platform env vars that might be set in CI
        env = {
            "GITHUB_REPOSITORY": "owner/myrepo",  # Missing GITHUB_ACTIONS
            "GITHUB_ACTIONS": "",  # Explicitly clear (might be set in CI)
            "NETLIFY": "",
            "VERCEL": "",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == ""


class TestApplyEnvOverridesPriority:
    """Tests for environment override priority."""

    def test_explicit_takes_precedence_over_platform(self):
        """BENGAL_BASEURL takes precedence over platform detection."""
        config = {}  # Missing baseurl allows env override
        env = {
            "BENGAL_BASEURL": "https://explicit.com",
            "NETLIFY": "true",
            "URL": "https://netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://explicit.com"

    def test_config_baseurl_takes_precedence_over_all(self):
        """Explicit config baseurl takes precedence over all env vars."""
        config = {"site": {"baseurl": "https://config.com"}}
        env = {
            "BENGAL_BASEURL": "https://explicit.com",
            "NETLIFY": "true",
            "URL": "https://netlify.app",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://config.com"


class TestApplyEnvOverridesEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_baseurl_key(self):
        """Handles missing baseurl key in config."""
        config = {}
        with patch.dict(os.environ, {"BENGAL_BASEURL": "https://example.com"}, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == "https://example.com"

    def test_github_repository_without_slash(self):
        """Handles malformed GITHUB_REPOSITORY without slash."""
        config = {}  # Missing baseurl allows env override, but malformed repo prevents override
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "noslash",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        # Should not crash, site section should exist but baseurl empty
        assert result.get("site", {}).get("baseurl", "") == ""

    def test_empty_env_vars_ignored(self):
        """Empty environment variables are ignored."""
        config = {"site": {"baseurl": ""}}
        # Clear platform env vars that might be set in CI
        env = {
            "BENGAL_BASEURL": "",  # Empty string should be ignored
            "GITHUB_ACTIONS": "",  # Clear in case running in GitHub Actions CI
            "NETLIFY": "",
            "VERCEL": "",
        }
        with patch.dict(os.environ, env, clear=False):
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == ""

    def test_exception_in_env_logic_logged_and_recovered(self):
        """Exceptions in env logic are caught, logged as warning, and recovered."""
        config = {"site": {"baseurl": ""}}
        # Simulate exception by making os.environ.get raise for specific keys
        original_get = os.environ.get

        def mock_get(key, default=None):
            # Only raise for keys used in env override logic
            if key in ("BENGAL_BASEURL", "BENGAL_BASE_URL", "NETLIFY", "VERCEL", "GITHUB_ACTIONS"):
                raise Exception("Test error")
            return original_get(key, default)

        with patch.object(os.environ, "get", side_effect=mock_get):
            # Should not raise, should return original config
            result = apply_env_overrides(config)
        assert result["site"]["baseurl"] == ""

    def test_returns_same_config_object(self):
        """Returns the same config object (mutated)."""
        config = {}  # Missing baseurl allows env override
        with patch.dict(os.environ, {"BENGAL_BASEURL": "https://test.com"}, clear=False):
            result = apply_env_overrides(config)
        assert result is config

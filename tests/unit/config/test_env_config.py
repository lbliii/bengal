"""Tests for BENGAL_ prefix environment variable overrides (Hugo-style)."""

from __future__ import annotations

import os
from unittest.mock import patch

from bengal.config.env_config import apply_bengal_overrides


class TestApplyBengalOverrides:
    """Tests for apply_bengal_overrides."""

    def test_bengal_params_repo_url_with_x_delimiter(self):
        """BENGALxPARAMSxREPO_URL sets params.repo_url."""
        config = {}
        env = {"BENGALxPARAMSxREPO_URL": "https://github.com/owner/repo"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result.get("params", {}).get("repo_url") == "https://github.com/owner/repo"

    def test_bengal_params_colab_branch_with_x_delimiter(self):
        """BENGALxPARAMSxCOLAB_BRANCH sets params.colab_branch."""
        config = {}
        env = {"BENGALxPARAMSxCOLAB_BRANCH": "develop"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result.get("params", {}).get("colab_branch") == "develop"

    def test_bengal_params_nested_with_underscore(self):
        """BENGAL_PARAMS_FOO_BAR sets params.foo.bar (underscore = nesting)."""
        config = {}
        env = {"BENGAL_PARAMS_FOO_BAR": "baz"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result.get("params", {}).get("foo", {}).get("bar") == "baz"

    def test_bengal_params_api_key_with_x_delimiter(self):
        """BENGALxPARAMSxAPI_KEY sets params.api_key (key contains underscore)."""
        config = {}
        env = {"BENGALxPARAMSxAPI_KEY": "secret123"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result.get("params", {}).get("api_key") == "secret123"

    def test_empty_value_ignored(self):
        """Empty BENGAL_ env var is ignored."""
        config = {}
        env = {"BENGALxPARAMSxREPO_URL": ""}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result.get("params", {}).get("repo_url") is None

    def test_non_bengal_prefix_ignored(self):
        """Env vars not starting with BENGAL_ are ignored."""
        config = {}
        env = {"OTHER_VAR": "value", "BENGAL_": ""}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert "params" not in result or result.get("params") == {}

    def test_overrides_config_value(self):
        """BENGAL_ overrides existing config value."""
        config = {"params": {"repo_url": "https://github.com/old/repo"}}
        env = {"BENGALxPARAMSxREPO_URL": "https://github.com/new/repo"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result["params"]["repo_url"] == "https://github.com/new/repo"

    def test_returns_same_config_object(self):
        """Returns the same config object (mutated)."""
        config = {}
        env = {"BENGALxPARAMSxREPO_URL": "https://github.com/owner/repo"}
        with patch.dict(os.environ, env, clear=False):
            result = apply_bengal_overrides(config)
        assert result is config

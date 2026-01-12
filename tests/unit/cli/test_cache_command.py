"""
Tests for bengal cache commands (inputs and hash).

Tests the CLI commands for generating cache keys for CI systems,
as specified in plan/rfc-ci-cache-inputs.md.
"""

from __future__ import annotations

import json

from click.testing import CliRunner

from bengal.cli.commands.cache import cache_cli, get_input_globs


class TestCacheInputs:
    """Test bengal cache inputs command."""

    def test_cache_inputs_includes_content_and_config(self, tmp_path):
        """Always includes content/** and config/**."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "content/**" in result.output
        assert "config/**" in result.output

    def test_cache_inputs_includes_templates_if_exists(self, tmp_path):
        """Includes templates/** if templates directory exists."""
        self._create_test_site(tmp_path)
        (tmp_path / "templates").mkdir()

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "templates/**" in result.output

    def test_cache_inputs_excludes_templates_if_not_exists(self, tmp_path):
        """Excludes templates/** if templates directory doesn't exist."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "templates/**" not in result.output

    def test_cache_inputs_includes_static_if_exists(self, tmp_path):
        """Includes static/** if static directory exists."""
        self._create_test_site(tmp_path)
        (tmp_path / "static").mkdir()

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "static/**" in result.output

    def test_cache_inputs_includes_autodoc_sources(self, tmp_path):
        """Includes Python source dirs when autodoc enabled."""
        self._create_test_site_with_autodoc(
            tmp_path,
            autodoc_config={"python": {"enabled": True, "source_dirs": ["../src"]}},
        )

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "../src/**/*.py" in result.output

    def test_cache_inputs_includes_autodoc_cli(self, tmp_path):
        """Includes CLI package when autodoc CLI enabled."""
        self._create_test_site_with_autodoc(
            tmp_path,
            autodoc_config={"cli": {"enabled": True, "app_module": "myapp.cli:main"}},
        )

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "../myapp/**/*.py" in result.output

    def test_cache_inputs_includes_autodoc_openapi(self, tmp_path):
        """Includes OpenAPI spec when autodoc OpenAPI enabled."""
        self._create_test_site_with_autodoc(
            tmp_path,
            autodoc_config={"openapi": {"enabled": True, "spec_file": "api/openapi.yaml"}},
        )

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", str(tmp_path)])

        assert result.exit_code == 0
        assert "api/openapi.yaml" in result.output

    def test_cache_inputs_verbose_shows_sources(self, tmp_path):
        """--verbose shows source of each pattern."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", "--verbose", str(tmp_path)])

        assert result.exit_code == 0
        assert "# built-in" in result.output

    def test_cache_inputs_json_format(self, tmp_path):
        """--format json outputs valid JSON."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["inputs", "--format", "json", str(tmp_path)])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert "content/**" in data

    def test_cache_inputs_json_verbose_format(self, tmp_path):
        """--format json --verbose outputs detailed JSON."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cache_cli, ["inputs", "--format", "json", "--verbose", str(tmp_path)]
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert any(item.get("pattern") == "content/**" for item in data)
        assert any(item.get("source") == "built-in" for item in data)

    def _create_test_site(self, tmp_path, autodoc_config=None):
        """Helper to create test site structure."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "site.yaml").write_text("title: Test Site\n")

        if autodoc_config:
            import yaml

            (config_dir / "autodoc.yaml").write_text(yaml.dump(autodoc_config))

    def _create_test_site_with_autodoc(self, tmp_path, autodoc_config):
        """Helper to create test site with autodoc config in bengal.toml."""
        import tomli_w

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Use bengal.toml for reliable autodoc config loading
        config = {
            "site": {"title": "Test Site"},
            "build": {"output_dir": "public"},
            "autodoc": autodoc_config,
        }

        with open(tmp_path / "bengal.toml", "wb") as f:
            tomli_w.dump(config, f)


class TestCacheHash:
    """Test bengal cache hash command."""

    def test_cache_hash_deterministic(self, tmp_path):
        """Same inputs produce same hash across runs."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result1 = runner.invoke(cache_cli, ["hash", str(tmp_path)])
        result2 = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result1.output.strip() == result2.output.strip()

    def test_cache_hash_changes_on_file_change(self, tmp_path):
        """Hash changes when any input file changes."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result1 = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        # Modify a content file
        (tmp_path / "content" / "index.md").write_text("changed content")
        result2 = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result1.output.strip() != result2.output.strip()

    def test_cache_hash_includes_version(self, tmp_path, monkeypatch):
        """Hash includes Bengal version by default."""
        self._create_test_site(tmp_path)

        runner = CliRunner()

        # Temporarily change version
        import bengal

        original_version = bengal.__version__

        monkeypatch.setattr(bengal, "__version__", "0.1.0")
        result1 = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        monkeypatch.setattr(bengal, "__version__", "0.2.0")
        result2 = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        # Restore version
        monkeypatch.setattr(bengal, "__version__", original_version)

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result1.output.strip() != result2.output.strip()

    def test_cache_hash_no_version_flag(self, tmp_path, monkeypatch):
        """--no-include-version excludes version from hash."""
        self._create_test_site(tmp_path)

        runner = CliRunner()

        import bengal

        original_version = bengal.__version__

        monkeypatch.setattr(bengal, "__version__", "0.1.0")
        result1 = runner.invoke(cache_cli, ["hash", "--no-include-version", str(tmp_path)])

        monkeypatch.setattr(bengal, "__version__", "0.2.0")
        result2 = runner.invoke(cache_cli, ["hash", "--no-include-version", str(tmp_path)])

        monkeypatch.setattr(bengal, "__version__", original_version)

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result1.output.strip() == result2.output.strip()

    def test_cache_hash_empty_glob_graceful(self, tmp_path):
        """Hash handles non-matching globs gracefully."""
        self._create_test_site_with_autodoc(
            tmp_path,
            autodoc_config={"python": {"enabled": True, "source_dirs": ["../nonexistent"]}},
        )

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        assert result.exit_code == 0

    def test_cache_hash_outputs_16_chars(self, tmp_path):
        """Hash output is 16 characters (truncated SHA-256)."""
        self._create_test_site(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cache_cli, ["hash", str(tmp_path)])

        assert result.exit_code == 0
        hash_output = result.output.strip()
        assert len(hash_output) == 16
        assert all(c in "0123456789abcdef" for c in hash_output)

    def _create_test_site(self, tmp_path, autodoc_config=None):
        """Helper to create test site structure."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "site.yaml").write_text("title: Test Site\n")

        if autodoc_config:
            import yaml

            (config_dir / "autodoc.yaml").write_text(yaml.dump(autodoc_config))

    def _create_test_site_with_autodoc(self, tmp_path, autodoc_config):
        """Helper to create test site with autodoc config in bengal.toml."""
        import tomli_w

        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "index.md").write_text("---\ntitle: Home\n---\n# Home")

        # Use bengal.toml for reliable autodoc config loading
        config = {
            "site": {"title": "Test Site"},
            "build": {"output_dir": "public"},
            "autodoc": autodoc_config,
        }

        with open(tmp_path / "bengal.toml", "wb") as f:
            tomli_w.dump(config, f)


class TestGetInputGlobs:
    """Test get_input_globs helper function directly."""

    def test_handles_parent_paths_for_cli(self, site_builder):
        """Correctly handles ../ patterns for CLI autodoc."""
        site = site_builder(
            config={
                "autodoc": {
                    "cli": {"enabled": True, "app_module": "bengal.cli:main"},
                },
            },
            content={"_index.md": "---\ntitle: Test\n---\nTest"},
        )

        globs = get_input_globs(site.site)
        patterns = [p for p, _ in globs]

        assert "../bengal/**/*.py" in patterns

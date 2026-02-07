"""
Tests for the bengal upgrade command.

Covers:
- PyPI version checking with caching
- Installer detection (uv, pip, pipx, conda)
- CLI command behavior (dry-run, force, yes flags)
- Environment variable controls
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from bengal import __version__
from bengal.cli.commands.upgrade.check import (
    UpgradeInfo,
    check_for_upgrade,
    fetch_latest_version,
    get_cache_path,
    load_cache,
    save_cache,
    should_check,
)
from bengal.cli.commands.upgrade.command import upgrade
from bengal.cli.commands.upgrade.installers import (
    InstallerInfo,
    _is_pipx_install,
    _is_uv_project,
    detect_installer,
)


class TestUpgradeInfo:
    """Tests for UpgradeInfo namedtuple."""

    def test_is_outdated_true_when_older(self):
        """Test is_outdated returns True when current < latest."""
        info = UpgradeInfo(current="0.1.0", latest="0.2.0")
        assert info.is_outdated is True

    def test_is_outdated_false_when_same(self):
        """Test is_outdated returns False when versions match."""
        info = UpgradeInfo(current="0.1.0", latest="0.1.0")
        assert info.is_outdated is False

    def test_is_outdated_false_when_newer(self):
        """Test is_outdated returns False when current > latest."""
        info = UpgradeInfo(current="0.2.0", latest="0.1.0")
        assert info.is_outdated is False

    def test_is_outdated_handles_prerelease(self):
        """Test is_outdated handles prerelease versions correctly."""
        info = UpgradeInfo(current="0.1.0a1", latest="0.1.0")
        assert info.is_outdated is True

    def test_is_outdated_handles_invalid_version(self):
        """Test is_outdated handles invalid version strings gracefully."""
        info = UpgradeInfo(current="invalid", latest="0.1.0")
        # Should fall back to string comparison
        assert info.is_outdated is True  # "invalid" != "0.1.0"


class TestShouldCheck:
    """Tests for should_check function."""

    def test_returns_false_in_ci_environment(self, monkeypatch):
        """Test upgrade checks are disabled in CI."""
        monkeypatch.setenv("CI", "1")
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        assert should_check() is False

    def test_returns_false_in_github_actions(self, monkeypatch):
        """Test upgrade checks are disabled in GitHub Actions."""
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        assert should_check() is False

    def test_returns_false_when_disabled_via_env(self, monkeypatch):
        """Test upgrade checks can be disabled via environment variable."""
        monkeypatch.setenv("BENGAL_NO_UPDATE_CHECK", "1")
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        assert should_check() is False

    def test_returns_false_when_disabled_via_env_true(self, monkeypatch):
        """Test upgrade checks disabled with BENGAL_NO_UPDATE_CHECK=true."""
        monkeypatch.setenv("BENGAL_NO_UPDATE_CHECK", "true")
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        assert should_check() is False

    def test_returns_false_when_not_tty(self, monkeypatch):
        """Test upgrade checks are skipped for non-interactive terminals."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("BENGAL_NO_UPDATE_CHECK", raising=False)
        monkeypatch.setattr("sys.stderr.isatty", lambda: False)
        assert should_check() is False

    def test_returns_true_in_interactive_terminal(self, monkeypatch):
        """Test upgrade checks run in interactive terminals."""
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        monkeypatch.delenv("GITLAB_CI", raising=False)
        monkeypatch.delenv("JENKINS_URL", raising=False)
        monkeypatch.delenv("TRAVIS", raising=False)
        monkeypatch.delenv("CIRCLECI", raising=False)
        monkeypatch.delenv("BENGAL_NO_UPDATE_CHECK", raising=False)
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        assert should_check() is True


class TestCachePath:
    """Tests for cache path resolution."""

    def test_uses_xdg_config_home_on_linux(self, monkeypatch):
        """Test cache uses XDG_CONFIG_HOME when set."""
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setenv("XDG_CONFIG_HOME", "/home/user/.config")
        path = get_cache_path()
        assert str(path) == "/home/user/.config/bengal/upgrade_check.json"

    def test_uses_appdata_on_windows(self, monkeypatch):
        """Test cache uses APPDATA on Windows."""
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setenv("APPDATA", "C:\\Users\\user\\AppData\\Roaming")
        path = get_cache_path()
        assert "bengal" in str(path)
        assert "upgrade_check.json" in str(path)


class TestCacheOperations:
    """Tests for cache load/save operations."""

    def test_load_cache_returns_none_when_missing(self, tmp_path, monkeypatch):
        """Test load_cache returns None when cache file doesn't exist."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: tmp_path / "nonexistent" / "cache.json",
        )
        assert load_cache() is None

    def test_load_cache_returns_none_when_expired(self, tmp_path, monkeypatch):
        """Test load_cache returns None when cache is expired."""
        cache_path = tmp_path / "upgrade_check.json"
        old_time = datetime.now(UTC) - timedelta(hours=25)  # Older than CACHE_TTL
        cache_data = {
            "latest_version": "0.2.0",
            "current_version": "0.1.0",
            "checked_at": old_time.isoformat(),
        }
        cache_path.write_text(json.dumps(cache_data))

        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: cache_path,
        )
        assert load_cache() is None

    def test_load_cache_returns_data_when_fresh(self, tmp_path, monkeypatch):
        """Test load_cache returns data when cache is fresh."""
        cache_path = tmp_path / "upgrade_check.json"
        fresh_time = datetime.now(UTC) - timedelta(hours=1)  # Within CACHE_TTL
        cache_data = {
            "latest_version": "0.2.0",
            "current_version": "0.1.0",
            "checked_at": fresh_time.isoformat(),
        }
        cache_path.write_text(json.dumps(cache_data))

        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: cache_path,
        )
        result = load_cache()
        assert result is not None
        assert result["latest_version"] == "0.2.0"

    def test_save_cache_creates_parent_directories(self, tmp_path, monkeypatch):
        """Test save_cache creates parent directories if needed."""
        cache_path = tmp_path / "subdir" / "bengal" / "upgrade_check.json"
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: cache_path,
        )
        save_cache("0.2.0")
        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert data["latest_version"] == "0.2.0"

    def test_save_cache_handles_permission_errors(self, tmp_path, monkeypatch):
        """Test save_cache fails silently on permission errors."""
        # Mock a path that will fail
        cache_path = Path("/root/bengal/upgrade_check.json")
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: cache_path,
        )
        # Should not raise
        save_cache("0.2.0")


class TestFetchLatestVersion:
    """Tests for PyPI version fetching."""

    def test_fetch_returns_version_on_success(self, monkeypatch):
        """Test fetch_latest_version returns version on successful response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.2.0"}}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            result = fetch_latest_version()
            assert result == "0.2.0"

    def test_fetch_returns_none_on_network_error(self, monkeypatch):
        """Test fetch_latest_version returns None on network error."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Network error")

        with patch("httpx.Client", return_value=mock_client):
            result = fetch_latest_version()
            assert result is None


class TestCheckForUpgrade:
    """Tests for the main check_for_upgrade function."""

    def test_returns_none_when_should_not_check(self, monkeypatch):
        """Test check_for_upgrade returns None when checks are disabled."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.should_check",
            lambda: False,
        )
        assert check_for_upgrade() is None

    def test_uses_cache_when_fresh(self, monkeypatch, tmp_path):
        """Test check_for_upgrade uses cached result when fresh."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.should_check",
            lambda: True,
        )

        # Create fresh cache
        cache_path = tmp_path / "upgrade_check.json"
        fresh_time = datetime.now(UTC) - timedelta(hours=1)
        cache_data = {
            "latest_version": "999.0.0",  # Much newer than current
            "current_version": __version__,
            "checked_at": fresh_time.isoformat(),
        }
        cache_path.write_text(json.dumps(cache_data))

        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.get_cache_path",
            lambda: cache_path,
        )

        # Mock fetch to ensure it's not called
        fetch_mock = MagicMock(return_value="999.0.0")
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.fetch_latest_version",
            fetch_mock,
        )

        result = check_for_upgrade()
        assert result is not None
        assert result.latest == "999.0.0"
        fetch_mock.assert_not_called()  # Should use cache, not fetch

    def test_returns_none_when_up_to_date(self, monkeypatch):
        """Test check_for_upgrade returns None when already on latest."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.should_check",
            lambda: True,
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.check.load_cache",
            lambda: {"latest_version": __version__},
        )

        result = check_for_upgrade()
        assert result is None


class TestInstallerDetection:
    """Tests for installer detection."""

    def test_detects_uv_from_lock_file(self, tmp_path, monkeypatch):
        """Test detect_installer returns uv when uv.lock exists."""
        (tmp_path / "uv.lock").touch()
        monkeypatch.chdir(tmp_path)

        installer = detect_installer()
        assert installer.name == "uv"
        assert "uv pip install" in installer.display_command

    def test_detects_uv_from_env_var(self, tmp_path, monkeypatch):
        """Test detect_installer returns uv when UV_CACHE_DIR is set."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("UV_CACHE_DIR", "/some/path")

        installer = detect_installer()
        assert installer.name == "uv"

    def test_detects_conda_from_prefix(self, tmp_path, monkeypatch):
        """Test detect_installer returns conda when CONDA_PREFIX is set."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CONDA_PREFIX", "/opt/conda/envs/myenv")

        # Clear UV env vars
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.delenv("UV_PYTHON", raising=False)

        # Mock pipx check to return False
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.installers._is_pipx_install",
            lambda: False,
        )

        installer = detect_installer()
        assert installer.name == "conda"
        assert "conda update" in installer.display_command

    def test_detects_venv(self, tmp_path, monkeypatch):
        """Test detect_installer returns pip (venv) when in virtual environment."""
        monkeypatch.chdir(tmp_path)

        # Clear other detection signals
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)

        # Mock virtual environment
        import sys

        monkeypatch.setattr(sys, "prefix", "/path/to/venv")
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.installers._is_pipx_install",
            lambda: False,
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.installers._is_uv_project",
            lambda: False,
        )

        installer = detect_installer()
        assert installer.name == "pip (venv)"
        assert "pip install --upgrade bengal" in installer.display_command

    def test_fallback_to_pip_user(self, tmp_path, monkeypatch):
        """Test detect_installer falls back to pip --user."""
        monkeypatch.chdir(tmp_path)

        # Clear all detection signals
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.delenv("UV_PYTHON", raising=False)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)

        # Mock: not in venv
        import sys

        monkeypatch.setattr(sys, "prefix", "/usr")
        monkeypatch.setattr(sys, "base_prefix", "/usr")

        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.installers._is_pipx_install",
            lambda: False,
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.installers._is_uv_project",
            lambda: False,
        )

        installer = detect_installer()
        assert installer.name == "pip"
        assert "--user" in installer.display_command


class TestUpgradeCommand:
    """Tests for the bengal upgrade CLI command."""

    def test_upgrade_dry_run_shows_command(self, monkeypatch):
        """Test --dry-run shows what would be done without executing."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: "999.0.0",
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.detect_installer",
            lambda: InstallerInfo(
                name="uv",
                command=["uv", "pip", "install", "--upgrade", "bengal"],
                display_command="uv pip install --upgrade bengal",
            ),
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, ["--dry-run"])

        assert result.exit_code == 0
        assert "Would run:" in result.output
        assert "uv pip install --upgrade bengal" in result.output

    def test_upgrade_already_latest(self, monkeypatch):
        """Test upgrade shows success when already on latest."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: __version__,
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.detect_installer",
            lambda: InstallerInfo(
                name="pip",
                command=["pip", "install", "--upgrade", "bengal"],
                display_command="pip install --upgrade bengal",
            ),
        )

        runner = CliRunner()
        result = runner.invoke(upgrade)

        assert result.exit_code == 0
        assert "Already on latest" in result.output

    def test_upgrade_network_error(self, monkeypatch):
        """Test upgrade handles network errors gracefully."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: None,
        )

        runner = CliRunner()
        result = runner.invoke(upgrade)

        assert result.exit_code == 1
        assert "Failed to check PyPI" in result.output

    def test_upgrade_with_yes_flag_skips_prompt(self, monkeypatch):
        """Test --yes flag skips confirmation prompt."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: "999.0.0",
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.detect_installer",
            lambda: InstallerInfo(
                name="pip",
                command=["pip", "install", "--upgrade", "bengal"],
                display_command="pip install --upgrade bengal",
            ),
        )

        # Mock subprocess to avoid actual upgrade
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        monkeypatch.setattr("subprocess.run", mock_run)

        runner = CliRunner()
        result = runner.invoke(upgrade, ["--yes"])

        # Should have attempted upgrade without prompt
        mock_run.assert_called_once()

    def test_upgrade_force_when_on_latest(self, monkeypatch):
        """Test --force flag runs upgrade even when on latest."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: __version__,
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.detect_installer",
            lambda: InstallerInfo(
                name="pip",
                command=["pip", "install", "--upgrade", "bengal"],
                display_command="pip install --upgrade bengal",
            ),
        )

        runner = CliRunner()
        result = runner.invoke(upgrade, ["--force", "--dry-run"])

        assert result.exit_code == 0
        assert "Would run:" in result.output

    def test_upgrade_cancelled_by_user(self, monkeypatch):
        """Test upgrade can be cancelled by user."""
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.fetch_latest_version",
            lambda: "999.0.0",
        )
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.detect_installer",
            lambda: InstallerInfo(
                name="pip",
                command=["pip", "install", "--upgrade", "bengal"],
                display_command="pip install --upgrade bengal",
            ),
        )

        # Mock questionary to return False (user cancelled)
        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False
        monkeypatch.setattr(
            "bengal.cli.commands.upgrade.command.questionary.confirm",
            lambda *args, **kwargs: mock_confirm,
        )

        runner = CliRunner()
        result = runner.invoke(upgrade)

        assert "cancelled" in result.output.lower()


class TestIsUvProject:
    """Tests for _is_uv_project helper."""

    def test_returns_true_when_uv_lock_exists(self, tmp_path, monkeypatch):
        """Test returns True when uv.lock exists in current directory."""
        (tmp_path / "uv.lock").touch()
        monkeypatch.chdir(tmp_path)
        assert _is_uv_project() is True

    def test_returns_true_when_uv_lock_in_parent(self, tmp_path, monkeypatch):
        """Test returns True when uv.lock exists in parent directory."""
        (tmp_path / "uv.lock").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        assert _is_uv_project() is True

    def test_returns_false_when_no_uv_signals(self, tmp_path, monkeypatch):
        """Test returns False when no uv indicators present."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("UV_CACHE_DIR", raising=False)
        monkeypatch.delenv("UV_PYTHON", raising=False)
        assert _is_uv_project() is False


class TestIsPipxInstall:
    """Tests for _is_pipx_install helper."""

    def test_returns_false_when_pipx_not_installed(self, monkeypatch):
        """Test returns False when pipx is not available."""
        monkeypatch.setattr("shutil.which", lambda x: None)
        assert _is_pipx_install() is False

    def test_returns_true_when_bengal_in_pipx_list(self, monkeypatch):
        """Test returns True when bengal appears in pipx list."""
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/pipx" if x == "pipx" else None)

        mock_result = MagicMock()
        mock_result.stdout = "bengal 0.1.8\nsome-other-tool 1.0.0\n"

        with patch("subprocess.run", return_value=mock_result):
            assert _is_pipx_install() is True

    def test_returns_false_when_bengal_not_in_pipx_list(self, monkeypatch):
        """Test returns False when bengal is not in pipx list."""
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/pipx" if x == "pipx" else None)

        mock_result = MagicMock()
        mock_result.stdout = "some-other-tool 1.0.0\nanother-tool 2.0.0\n"

        with patch("subprocess.run", return_value=mock_result):
            assert _is_pipx_install() is False


class TestInstallerInfo:
    """Tests for InstallerInfo dataclass."""

    def test_is_available_true_when_in_path(self, monkeypatch):
        """Test is_available returns True when command is in PATH."""
        monkeypatch.setattr("shutil.which", lambda x: f"/usr/bin/{x}")
        info = InstallerInfo(
            name="pip",
            command=["pip", "install", "--upgrade", "bengal"],
            display_command="pip install --upgrade bengal",
        )
        assert info.is_available is True

    def test_is_available_false_when_not_in_path(self, monkeypatch):
        """Test is_available returns False when command is not in PATH."""
        monkeypatch.setattr("shutil.which", lambda x: None)
        info = InstallerInfo(
            name="fictional-installer",
            command=["fictional", "upgrade", "bengal"],
            display_command="fictional upgrade bengal",
        )
        assert info.is_available is False

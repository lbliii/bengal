"""Tests for bengal.utils.dx.detection module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from bengal.utils.dx.detection import (
    is_ci,
    is_docker,
    is_kubernetes,
    is_wsl,
    is_wsl_windows_drive,
)


class TestIsDocker:
    """Tests for is_docker()."""

    def test_dockerenv_exists(self) -> None:
        """/.dockerenv exists indicates Docker."""
        with patch("bengal.utils.dx.detection.Path") as mock_path_cls:
            mock_p = mock_path_cls.return_value
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = False
            assert is_docker() is True

    def test_cgroup_contains_docker(self) -> None:
        """Cgroup file with docker indicates Docker."""
        with patch("bengal.utils.dx.detection.Path") as mock_path_cls:
            mock_p = mock_path_cls.return_value
            mock_p.exists.return_value = False
            mock_p.is_file.return_value = True
            mock_p.read_text.return_value = "0::/docker/abc123"
            assert is_docker() is True

    def test_not_docker(self) -> None:
        """No dockerenv and no docker in cgroup means not Docker."""
        with patch("bengal.utils.dx.detection.Path") as mock_path_cls:
            mock_p = mock_path_cls.return_value
            mock_p.exists.return_value = False
            mock_p.is_file.return_value = True
            mock_p.read_text.return_value = "0::/user.slice"
            assert is_docker() is False


class TestIsKubernetes:
    """Tests for is_kubernetes()."""

    def test_k8s_service_host_set(self) -> None:
        """KUBERNETES_SERVICE_HOST set indicates Kubernetes."""
        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}, clear=False):
            assert is_kubernetes() is True

    def test_k8s_service_host_unset(self) -> None:
        """KUBERNETES_SERVICE_HOST unset means not Kubernetes."""
        with patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": ""}, clear=True):
            # clear=True might remove it; use del or set to ""
            env = os.environ.copy()
            env.pop("KUBERNETES_SERVICE_HOST", None)
            with patch.dict(os.environ, env, clear=False):
                # Restore if it was there
                pass
        # Without the env var, is_kubernetes returns False
        with patch.dict(os.environ, {}, clear=False):
            orig = os.environ.get("KUBERNETES_SERVICE_HOST")
            try:
                if "KUBERNETES_SERVICE_HOST" in os.environ:
                    del os.environ["KUBERNETES_SERVICE_HOST"]
                assert is_kubernetes() is False
            finally:
                if orig is not None:
                    os.environ["KUBERNETES_SERVICE_HOST"] = orig


class TestIsWsl:
    """Tests for is_wsl()."""

    def test_microsoft_standard_in_release(self) -> None:
        """microsoft-standard in release indicates WSL."""
        with patch("bengal.utils.dx.detection.platform") as mock_platform:
            mock_platform.uname.return_value.release = "5.10.102.1-microsoft-standard-WSL2"
            assert is_wsl() is True

    def test_linux_standard_release(self) -> None:
        """Standard Linux release means not WSL."""
        with patch("bengal.utils.dx.detection.platform") as mock_platform:
            mock_platform.uname.return_value.release = "5.15.0-91-generic"
            assert is_wsl() is False


class TestIsWslWindowsDrive:
    """Tests for is_wsl_windows_drive()."""

    def test_wsl_plus_mnt_path(self) -> None:
        """WSL + path under /mnt/c returns True."""
        with patch("bengal.utils.dx.detection.is_wsl", return_value=True):
            assert is_wsl_windows_drive("/mnt/c/Users/foo") is True
            assert is_wsl_windows_drive(Path("/mnt/d/projects")) is True

    def test_wsl_plus_home_path(self) -> None:
        """WSL + path under /home returns False."""
        with patch("bengal.utils.dx.detection.is_wsl", return_value=True):
            assert is_wsl_windows_drive("/home/user/project") is False

    def test_not_wsl(self) -> None:
        """Not WSL means False even for /mnt/c."""
        with patch("bengal.utils.dx.detection.is_wsl", return_value=False):
            assert is_wsl_windows_drive("/mnt/c/Users/foo") is False


class TestIsCi:
    """Tests for is_ci()."""

    def test_ci_true(self) -> None:
        """CI=true indicates CI."""
        with patch.dict(os.environ, {"CI": "true"}, clear=False):
            assert is_ci() is True

    def test_github_actions_true(self) -> None:
        """GITHUB_ACTIONS=true indicates CI."""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            assert is_ci() is True

    def test_neither_set(self) -> None:
        """Neither set means not CI."""
        with patch.dict(
            os.environ,
            {"CI": "", "GITHUB_ACTIONS": ""},
            clear=False,
        ):
            # Clear them if we're in CI
            orig_ci = os.environ.get("CI")
            orig_gh = os.environ.get("GITHUB_ACTIONS")
            try:
                os.environ.pop("CI", None)
                os.environ.pop("GITHUB_ACTIONS", None)
                assert is_ci() is False
            finally:
                if orig_ci is not None:
                    os.environ["CI"] = orig_ci
                if orig_gh is not None:
                    os.environ["GITHUB_ACTIONS"] = orig_gh

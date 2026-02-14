"""Tests for bengal.utils.dx.hints module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from bengal.utils.dx.hints import Hint, collect_hints


class TestCollectHints:
    """Tests for collect_hints()."""

    def test_returns_list(self) -> None:
        """collect_hints returns a list."""
        result = collect_hints("build")
        assert isinstance(result, list)

    def test_respects_max_hints(self) -> None:
        """collect_hints returns at most max_hints items."""
        result = collect_hints("serve", host="localhost", max_hints=2)
        assert len(result) <= 2

    def test_quiet_suppresses_hints(self) -> None:
        """quiet=True returns empty list."""
        result = collect_hints("build", quiet=True)
        assert result == []

    def test_bengal_hints_zero_disables(self) -> None:
        """BENGAL_HINTS=0 disables all hints."""
        with patch.dict(os.environ, {"BENGAL_HINTS": "0"}, clear=False):
            result = collect_hints("serve", host="localhost")
        assert result == []

    def test_bengal_no_hints_disables(self) -> None:
        """BENGAL_NO_HINTS=1 disables all hints."""
        with patch.dict(os.environ, {"BENGAL_NO_HINTS": "1"}, clear=False):
            result = collect_hints("serve", host="localhost")
        assert result == []

    def test_docker_baseurl_hint_when_docker_and_empty_baseurl(self) -> None:
        """Docker + empty baseurl yields docker_baseurl hint."""
        with patch("bengal.utils.dx.hints.is_docker", return_value=True):
            with patch("bengal.utils.dx.hints.is_kubernetes", return_value=False):
                result = collect_hints("config", baseurl="", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "docker_baseurl" in hint_ids

    def test_kubernetes_baseurl_hint_when_k8s_and_empty_baseurl(self) -> None:
        """Kubernetes + empty baseurl yields kubernetes_baseurl hint."""
        with patch("bengal.utils.dx.hints.is_docker", return_value=False):
            with patch("bengal.utils.dx.hints.is_kubernetes", return_value=True):
                result = collect_hints("config", baseurl="", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "kubernetes_baseurl" in hint_ids

    def test_no_baseurl_hint_when_baseurl_set(self) -> None:
        """Non-empty baseurl suppresses docker/k8s baseurl hints."""
        with patch("bengal.utils.dx.hints.is_docker", return_value=True):
            result = collect_hints("config", baseurl="https://example.com", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "docker_baseurl" not in hint_ids
        assert "kubernetes_baseurl" not in hint_ids

    def test_wsl_hint_in_serve_context(self) -> None:
        """WSL + serve context yields wsl_watchfiles hint."""
        with patch("bengal.utils.dx.hints.is_wsl", return_value=True):
            with patch("bengal.utils.dx.hints.is_docker", return_value=False):
                result = collect_hints("serve", host="localhost", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "wsl_watchfiles" in hint_ids

    def test_dev_server_container_hint_when_docker_and_localhost(self) -> None:
        """Docker + host=localhost + serve yields dev_server_container hint."""
        with patch("bengal.utils.dx.hints.is_docker", return_value=True):
            with patch("bengal.utils.dx.hints.is_kubernetes", return_value=False):
                result = collect_hints("serve", host="localhost", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "dev_server_container" in hint_ids

    def test_per_hint_opt_out(self) -> None:
        """BENGAL_HINT_DOCKER_BASEURL=0 disables that hint."""
        with patch("bengal.utils.dx.hints.is_docker", return_value=True):
            with patch("bengal.utils.dx.hints.is_kubernetes", return_value=False):
                with patch.dict(os.environ, {"BENGAL_HINT_DOCKER_BASEURL": "0"}, clear=False):
                    result = collect_hints("config", baseurl="", max_hints=3)
        hint_ids = [h.id for h in result]
        assert "docker_baseurl" not in hint_ids


class TestHint:
    """Tests for Hint dataclass."""

    def test_hint_has_required_fields(self) -> None:
        """Hint has id, message, priority, context."""
        hint = Hint(
            id="test",
            message="Test message",
            priority=10,
            context=frozenset({"build"}),
        )
        assert hint.id == "test"
        assert hint.message == "Test message"
        assert hint.priority == 10
        assert "build" in hint.context

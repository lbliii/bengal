"""
Tests for ResourceManager cleanup and lifecycle management.

BUG FIX: Signal handler exception safety - cleanup exceptions should not
prevent sys.exit() from being called.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bengal.server.resource_manager import ResourceManager


class TestResourceManagerBasics:
    """Basic tests for ResourceManager functionality."""

    def test_init_creates_empty_resources(self):
        """Test that ResourceManager initializes with empty resource list."""
        rm = ResourceManager()
        assert rm._resources == []
        assert rm._cleanup_done is False

    def test_register_adds_resource(self):
        """Test that register adds a resource to the list."""
        rm = ResourceManager()
        resource = object()
        cleanup_fn = MagicMock()

        result = rm.register("Test Resource", resource, cleanup_fn)

        assert result is resource
        assert len(rm._resources) == 1
        assert rm._resources[0] == ("Test Resource", resource, cleanup_fn)

    def test_register_returns_resource_for_chaining(self):
        """Test that register returns the resource for chaining."""
        rm = ResourceManager()
        resource = {"key": "value"}

        result = rm.register("Dict", resource, lambda x: None)

        assert result is resource

    def test_cleanup_calls_cleanup_functions(self):
        """Test that cleanup calls all registered cleanup functions."""
        rm = ResourceManager()

        cleanup1 = MagicMock()
        cleanup2 = MagicMock()
        resource1 = object()
        resource2 = object()

        rm.register("Resource 1", resource1, cleanup1)
        rm.register("Resource 2", resource2, cleanup2)

        rm.cleanup()

        cleanup1.assert_called_once_with(resource1)
        cleanup2.assert_called_once_with(resource2)

    def test_cleanup_is_idempotent(self):
        """Test that cleanup can be called multiple times safely."""
        rm = ResourceManager()
        cleanup = MagicMock()
        rm.register("Resource", object(), cleanup)

        rm.cleanup()
        rm.cleanup()
        rm.cleanup()

        # Should only be called once
        cleanup.assert_called_once()

    def test_cleanup_reverse_order(self):
        """Test that cleanup happens in LIFO order."""
        rm = ResourceManager()
        call_order = []

        def cleanup1(r):
            call_order.append(1)

        def cleanup2(r):
            call_order.append(2)

        def cleanup3(r):
            call_order.append(3)

        rm.register("First", object(), cleanup1)
        rm.register("Second", object(), cleanup2)
        rm.register("Third", object(), cleanup3)

        rm.cleanup()

        # Should be called in reverse order (LIFO)
        assert call_order == [3, 2, 1]


class TestResourceManagerContextManager:
    """Tests for ResourceManager as context manager."""

    def test_context_manager_calls_cleanup_on_exit(self):
        """Test that __exit__ calls cleanup."""
        cleanup = MagicMock()

        with ResourceManager() as rm:
            rm.register("Resource", object(), cleanup)

        cleanup.assert_called_once()

    def test_context_manager_returns_self(self):
        """Test that __enter__ returns the ResourceManager."""
        rm = ResourceManager()
        with rm as returned:
            assert returned is rm


class TestResourceManagerSignalHandler:
    """
    Tests for ResourceManager signal handling.
    
    BUG FIX: Signal handler should call sys.exit() even if cleanup raises.
    """

    def test_signal_handler_calls_cleanup_and_exits(self):
        """Test that signal handler calls cleanup and exits."""
        rm = ResourceManager()
        cleanup = MagicMock()
        rm.register("Resource", object(), cleanup)

        with patch.object(sys, "exit") as mock_exit:
            rm._signal_handler(signal.SIGINT, None)

        cleanup.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_signal_handler_exits_even_if_cleanup_raises(self):
        """
        Test that sys.exit is called even if cleanup raises an exception.
        
        BUG FIX: Previously, if cleanup() raised an exception, sys.exit()
        would never be called, leaving the process in an undefined state.
        """
        rm = ResourceManager()

        def failing_cleanup(r):
            raise RuntimeError("Cleanup failed!")

        rm.register("Failing Resource", object(), failing_cleanup)

        with patch.object(sys, "exit") as mock_exit:
            # Should not raise, and should call exit
            rm._signal_handler(signal.SIGINT, None)

        # Exit should still be called even though cleanup raised
        mock_exit.assert_called_once_with(0)

    def test_second_signal_forces_exit(self):
        """Test that second signal forces immediate exit."""
        rm = ResourceManager()
        rm._cleanup_done = True  # Simulate first cleanup already done

        with patch.object(sys, "exit") as mock_exit:
            rm._signal_handler(signal.SIGINT, None)

        # Should exit with code 1 (force exit)
        mock_exit.assert_called_once_with(1)


class TestResourceManagerSpecificRegisters:
    """Tests for specific resource registration methods."""

    def test_register_server(self):
        """Test that register_server registers HTTP server correctly."""
        rm = ResourceManager()
        server = MagicMock()

        result = rm.register_server(server)

        assert result is server
        assert len(rm._resources) == 1
        assert rm._resources[0][0] == "HTTP Server"

    def test_register_watcher_runner(self):
        """Test that register_watcher_runner registers correctly."""
        rm = ResourceManager()
        runner = MagicMock()

        result = rm.register_watcher_runner(runner)

        assert result is runner
        assert len(rm._resources) == 1
        assert rm._resources[0][0] == "Watcher Runner"

    def test_register_build_trigger(self):
        """Test that register_build_trigger registers correctly."""
        rm = ResourceManager()
        trigger = MagicMock()

        result = rm.register_build_trigger(trigger)

        assert result is trigger
        assert len(rm._resources) == 1
        assert rm._resources[0][0] == "Build Trigger"

    def test_register_pidfile(self, tmp_path: Path):
        """Test that register_pidfile registers and cleans up PID files."""
        rm = ResourceManager()
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("12345")

        result = rm.register_pidfile(pid_file)

        assert result == pid_file
        assert len(rm._resources) == 1

        # Cleanup should delete the file
        rm.cleanup()
        assert not pid_file.exists()

    def test_register_sse_shutdown(self):
        """Test that register_sse_shutdown is registered."""
        rm = ResourceManager()

        with patch("bengal.server.live_reload.reset_sse_shutdown"):
            rm.register_sse_shutdown()

        assert len(rm._resources) == 1
        assert rm._resources[0][0] == "SSE Clients"


class TestResourceManagerCleanupContinuesOnError:
    """Tests for cleanup continuation when individual cleanups fail."""

    def test_cleanup_continues_after_one_failure(self):
        """Test that cleanup continues even if one resource fails."""
        rm = ResourceManager()

        cleanup1 = MagicMock()
        failing_cleanup = MagicMock(side_effect=RuntimeError("Oops"))
        cleanup3 = MagicMock()

        rm.register("Resource 1", object(), cleanup1)
        rm.register("Failing", object(), failing_cleanup)
        rm.register("Resource 3", object(), cleanup3)

        # Should not raise
        rm.cleanup()

        # All cleanups should have been called
        cleanup1.assert_called_once()
        failing_cleanup.assert_called_once()
        cleanup3.assert_called_once()

    def test_cleanup_logs_errors(self):
        """Test that cleanup errors are logged (via print)."""
        rm = ResourceManager()

        def failing_cleanup(r):
            raise RuntimeError("Test error")

        rm.register("Failing", object(), failing_cleanup)

        with patch("builtins.print") as mock_print:
            rm.cleanup()

        # Should have printed error message
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("Error cleaning up" in str(call) for call in calls)

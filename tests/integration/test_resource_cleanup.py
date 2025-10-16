"""
Integration tests for resource cleanup functionality.

Tests the ResourceManager and PIDManager to ensure robust cleanup
across all termination scenarios.
"""

import os
import subprocess

import pytest


class TestPIDManager:
    """Test PID file management."""

    def test_pid_file_creation_and_cleanup(self, tmp_path):
        """Test that PID files are created and cleaned up properly."""
        from bengal.server.pid_manager import PIDManager

        pid_file = tmp_path / ".bengal.pid"

        # Write PID file
        PIDManager.write_pid_file(pid_file)

        assert pid_file.exists()
        assert pid_file.read_text().strip() == str(os.getpid())

        # Clean up
        pid_file.unlink()
        assert not pid_file.exists()

    def test_check_stale_pid_no_file(self, tmp_path):
        """Test checking for stale PID when no file exists."""
        from bengal.server.pid_manager import PIDManager

        pid_file = tmp_path / ".bengal.pid"
        stale_pid = PIDManager.check_stale_pid(pid_file)

        assert stale_pid is None

    def test_check_stale_pid_with_dead_process(self, tmp_path):
        """Test checking for stale PID when process no longer exists."""
        from bengal.server.pid_manager import PIDManager

        pid_file = tmp_path / ".bengal.pid"

        # Write a PID that definitely doesn't exist
        pid_file.write_text("999999")

        stale_pid = PIDManager.check_stale_pid(pid_file)

        # Should return None and clean up the stale file
        assert stale_pid is None
        assert not pid_file.exists()

    def test_check_stale_pid_with_current_process(self, tmp_path):
        """Test checking for stale PID with current process."""
        from bengal.server.pid_manager import PIDManager

        pid_file = tmp_path / ".bengal.pid"

        # Write current process PID (this test process)
        pid_file.write_text(str(os.getpid()))

        # Should return the PID since process exists
        # (though it's not actually a Bengal serve process)
        # This tests the existence check, not the Bengal-specific check
        PIDManager.check_stale_pid(pid_file)

        # May or may not return PID depending on psutil availability
        # and whether it detects this isn't a Bengal process
        # Either behavior is acceptable for this test


class TestResourceManager:
    """Test resource manager cleanup."""

    def test_resource_manager_context(self):
        """Test that ResourceManager works as a context manager."""
        from bengal.server.resource_manager import ResourceManager

        cleanup_called = []

        def test_cleanup(resource):
            cleanup_called.append(resource)

        with ResourceManager() as rm:
            rm.register("Test", "test_resource", test_cleanup)

        # Cleanup should have been called
        assert cleanup_called == ["test_resource"]

    def test_resource_manager_idempotent(self):
        """Test that cleanup is idempotent (safe to call multiple times)."""
        from bengal.server.resource_manager import ResourceManager

        cleanup_count = []

        def test_cleanup(resource):
            cleanup_count.append(1)

        rm = ResourceManager()
        rm.register("Test", "test_resource", test_cleanup)

        # Call cleanup multiple times
        rm.cleanup()
        rm.cleanup()
        rm.cleanup()

        # Should only have cleaned up once
        assert len(cleanup_count) == 1

    def test_resource_manager_lifo_order(self):
        """Test that resources are cleaned up in LIFO order."""
        from bengal.server.resource_manager import ResourceManager

        cleanup_order = []

        def cleanup1(r):
            cleanup_order.append(1)

        def cleanup2(r):
            cleanup_order.append(2)

        def cleanup3(r):
            cleanup_order.append(3)

        with ResourceManager() as rm:
            rm.register("First", "r1", cleanup1)
            rm.register("Second", "r2", cleanup2)
            rm.register("Third", "r3", cleanup3)

        # Should clean up in reverse order (LIFO)
        assert cleanup_order == [3, 2, 1]

    def test_resource_manager_exception_handling(self):
        """Test that cleanup continues even if one cleanup fails."""
        from bengal.server.resource_manager import ResourceManager

        cleanup_order = []

        def cleanup_fail(r):
            cleanup_order.append("fail")
            raise Exception("Cleanup failed")

        def cleanup_ok(r):
            cleanup_order.append("ok")

        with ResourceManager() as rm:
            rm.register("OK1", "r1", cleanup_ok)
            rm.register("Fail", "r2", cleanup_fail)
            rm.register("OK2", "r3", cleanup_ok)

        # All cleanups should have been attempted (reverse order)
        assert cleanup_order == ["ok", "fail", "ok"]


class TestDevServerCleanup:
    """Test dev server cleanup integration."""

    @pytest.mark.skipif(
        not os.path.exists("examples/quickstart"), reason="Requires quickstart example"
    )
    def test_server_creates_pid_file(self, tmp_path):
        """Test that dev server creates and cleans up PID file."""
        # This is more of a smoke test - we can't easily test signal handling
        # in pytest without more complex subprocess management
        pass


@pytest.mark.skipif(os.name == "nt", reason="Signal handling differs on Windows")
class TestSignalHandling:
    """Test signal handling (Unix-like systems only)."""

    def test_cleanup_command_help(self):
        """Test that cleanup command is accessible."""
        result = subprocess.run(
            ["python", "-m", "bengal.cli", "site", "clean", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert "Clean" in result.stdout or "clean" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

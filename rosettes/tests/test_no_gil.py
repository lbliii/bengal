"""Tests for free-threading (GIL) safety.

These tests verify that Rosettes doesn't re-enable the GIL
when running on free-threaded Python (3.14t+).
"""

import concurrent.futures
import subprocess
import sys

import pytest

from rosettes import highlight, tokenize


class TestNoGilReenablement:
    """Tests that verify no GIL re-enablement."""

    @pytest.mark.skipif(
        not hasattr(sys, "_is_gil_enabled"),
        reason="Requires Python 3.14t+ with free-threading support",
    )
    def test_gil_declaration(self) -> None:
        """Verify module declares free-threading safety."""
        import rosettes

        # The module should have __getattr__ that returns 0 for _Py_mod_gil
        assert rosettes.__getattr__("_Py_mod_gil") == 0

    def test_no_gil_warning_in_subprocess(self) -> None:
        """Verify importing rosettes doesn't trigger GIL warning.

        This test runs in a subprocess with PYTHON_GIL=0 to verify
        that importing and using rosettes doesn't cause the GIL to
        be re-enabled.
        """
        import os

        env = os.environ.copy()
        env["PYTHON_GIL"] = "0"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import rosettes
result = rosettes.highlight('def foo(): pass', 'python')
print('OK')
""",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        # Check that it ran successfully
        assert "OK" in result.stdout, f"stdout: {result.stdout}"

        # Check no GIL warning in stderr
        assert "GIL has been enabled" not in result.stderr, f"stderr: {result.stderr}"


class TestConcurrentHighlighting:
    """Tests for concurrent highlighting operations."""

    def test_concurrent_different_languages(self) -> None:
        """Concurrent highlighting of different languages."""
        codes = {
            "python": "def foo(): pass",
            "javascript": "const x = 1 + 2;",
        }

        def highlight_code(lang: str, code: str) -> str:
            return highlight(code, lang)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(highlight_code, lang, code)
                for lang, code in codes.items()
                for _ in range(10)
            ]
            results = [f.result() for f in futures]

        # All results should be valid HTML
        assert all("<span" in r for r in results)

    def test_high_concurrency_stress(self) -> None:
        """Stress test with high concurrency."""
        code = """
class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
"""

        def highlight_many(_: int) -> list[str]:
            results = []
            for _ in range(50):
                results.append(highlight(code, "python"))
            return results

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(highlight_many, i) for i in range(16)]
            all_results = [f.result() for f in futures]

        # Verify all results are consistent
        first_result = all_results[0][0]
        for batch in all_results:
            for result in batch:
                assert result == first_result, "Inconsistent results under concurrency"

    def test_tokenize_thread_isolation(self) -> None:
        """Verify tokenization state is isolated per thread."""
        import threading

        results: dict[int, list[tuple[str, int]]] = {}
        lock = threading.Lock()

        def tokenize_with_id(thread_id: int, code: str) -> None:
            tokens = tokenize(code, "python")
            with lock:
                results[thread_id] = [(t.value, t.line) for t in tokens]

        threads = []
        codes = [
            ("x = 1", 1),
            ("y = 2", 2),
            ("z = 3", 3),
            ("w = 4", 4),
        ]

        for i, (code, _) in enumerate(codes):
            t = threading.Thread(target=tokenize_with_id, args=(i, code))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have its own distinct tokenization
        assert len(results) == 4
        # Check each got the right variable name
        for i, (code, _) in enumerate(codes):
            var_name = code.split()[0]
            thread_results = results[i]
            var_tokens = [v for v, _ in thread_results if v in "xyzw"]
            assert var_name in var_tokens

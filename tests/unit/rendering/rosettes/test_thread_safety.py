"""Thread safety tests for concurrent tokenization."""

from __future__ import annotations

import concurrent.futures

from bengal.rendering.rosettes import get_lexer, highlight_many, tokenize_many


class TestConcurrentTokenization:
    """Test concurrent tokenization safety."""

    def test_concurrent_tokenization(self) -> None:
        """Multiple threads tokenizing simultaneously should not interfere."""
        lexer = get_lexer("python")

        codes = [f"x{i} = {i}" for i in range(100)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda c: list(lexer.tokenize(c)), codes))

        # Verify each result is correct
        for i, tokens in enumerate(results):
            assert len(tokens) > 0
            # Check that value is in tokens
            all_values = "".join(t.value for t in tokens)
            assert str(i) in all_values

    def test_concurrent_different_lexers(self) -> None:
        """Different lexers in parallel should not interfere."""
        languages = ["python", "javascript", "rust", "go"]
        codes = [f"x = {i}" for i in range(20)]

        def tokenize_with_lang(args):
            code, lang = args
            lexer = get_lexer(lang)
            return list(lexer.tokenize(code))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            items = [(code, languages[i % len(languages)]) for i, code in enumerate(codes)]
            results = list(executor.map(tokenize_with_lang, items))

        assert len(results) == 20
        for tokens in results:
            assert len(tokens) > 0

    def test_concurrent_registry_access(self) -> None:
        """Concurrent get_lexer() calls should be safe."""
        languages = ["python", "javascript", "rust", "go", "kida"]

        def get_lexer_safe(lang):
            return get_lexer(lang)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(get_lexer_safe, languages * 10))

        assert len(results) == 50
        # All should be valid lexers
        for lexer in results:
            assert lexer is not None
            assert hasattr(lexer, "tokenize")


class TestParallelAPICorrectness:
    """Test parallel API correctness under concurrency."""

    def test_highlight_many_concurrent(self) -> None:
        """highlight_many() should work correctly with concurrent access."""
        items = [(f"def foo{i}(): pass", "python") for i in range(50)]

        results = highlight_many(items)

        assert len(results) == 50
        for i, result in enumerate(results):
            assert f"foo{i}" in result

    def test_tokenize_many_concurrent(self) -> None:
        """tokenize_many() should work correctly with concurrent access."""
        items = [(f"x{i} = {i}", "python") for i in range(50)]

        results = tokenize_many(items)

        assert len(results) == 50
        for i, tokens in enumerate(results):
            assert len(tokens) > 0
            all_values = "".join(t.value for t in tokens)
            assert str(i) in all_values


class TestRaceConditionDetection:
    """Test for race conditions using barriers."""

    def test_barrier_synchronization(self) -> None:
        """Use barrier to maximize contention."""
        import threading

        lexer = get_lexer("python")
        barrier = threading.Barrier(8)
        results = []

        def tokenize_with_barrier(code):
            barrier.wait()  # Synchronize all threads
            return list(lexer.tokenize(code))

        codes = [f"x{i} = {i}" for i in range(8)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(tokenize_with_barrier, codes))

        assert len(results) == 8
        for tokens in results:
            assert len(tokens) > 0

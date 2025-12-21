"""
Tests for bengal.utils.retry module.

Verifies retry utilities with exponential backoff for both sync and async.
"""

from __future__ import annotations

import time

import pytest

from bengal.utils.retry import (
    async_retry_with_backoff,
    calculate_backoff,
    retry_with_backoff,
)


class TestCalculateBackoff:
    """Tests for calculate_backoff function."""

    def test_exponential_growth(self) -> None:
        """Test backoff grows exponentially."""
        # Without jitter for predictable testing
        delay0 = calculate_backoff(0, base=1.0, jitter=False)
        delay1 = calculate_backoff(1, base=1.0, jitter=False)
        delay2 = calculate_backoff(2, base=1.0, jitter=False)

        assert delay0 == pytest.approx(1.0)
        assert delay1 == pytest.approx(2.0)
        assert delay2 == pytest.approx(4.0)

    def test_respects_max_delay(self) -> None:
        """Test backoff is capped at max_delay."""
        delay = calculate_backoff(10, base=1.0, max_delay=5.0, jitter=False)
        assert delay == pytest.approx(5.0)

    def test_minimum_delay(self) -> None:
        """Test minimum delay of 0.1 seconds."""
        # Even with tiny base, should be at least 0.1
        delay = calculate_backoff(0, base=0.01, jitter=False)
        assert delay >= 0.1

    def test_jitter_range(self) -> None:
        """Test jitter adds ±25% variation."""
        base = 1.0
        delays = [calculate_backoff(1, base=base, jitter=True) for _ in range(100)]

        # Expected delay is 2.0 (base * 2^1), jitter is ±25%
        # So range should be 1.5 to 2.5
        assert all(1.4 <= d <= 2.6 for d in delays)

        # With jitter, values should vary
        assert len(set(delays)) > 1

    def test_custom_base(self) -> None:
        """Test custom base delay."""
        delay = calculate_backoff(0, base=0.5, jitter=False)
        assert delay == pytest.approx(0.5)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    def test_success_on_first_try(self) -> None:
        """Test function that succeeds immediately."""
        result = retry_with_backoff(lambda: 42, retries=3)
        assert result == 42

    def test_success_after_retries(self) -> None:
        """Test function that succeeds after retries."""
        call_count = 0

        def flaky_function() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet!")
            return 42

        result = retry_with_backoff(
            flaky_function,
            retries=5,
            base_delay=0.01,  # Fast for testing
            exceptions=(ValueError,),
        )

        assert result == 42
        assert call_count == 3

    def test_exhausted_retries_raises(self) -> None:
        """Test that exhausted retries raises the last exception."""

        def always_fails() -> None:
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            retry_with_backoff(
                always_fails,
                retries=2,
                base_delay=0.01,
                exceptions=(ValueError,),
            )

    def test_only_catches_specified_exceptions(self) -> None:
        """Test that only specified exceptions are caught."""

        def raises_type_error() -> None:
            raise TypeError("Wrong type")

        # Should not retry on TypeError when only ValueError specified
        with pytest.raises(TypeError):
            retry_with_backoff(
                raises_type_error,
                retries=3,
                base_delay=0.01,
                exceptions=(ValueError,),
            )

    def test_on_retry_callback(self) -> None:
        """Test on_retry callback is called."""
        callback_calls: list[tuple[int, Exception]] = []
        call_count = 0

        def callback(attempt: int, error: Exception) -> None:
            callback_calls.append((attempt, error))

        def flaky_function() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return 42

        retry_with_backoff(
            flaky_function,
            retries=5,
            base_delay=0.01,
            exceptions=(ValueError,),
            on_retry=callback,
        )

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 0
        assert callback_calls[1][0] == 1

    def test_respects_delay(self) -> None:
        """Test that delays are actually applied."""
        call_count = 0
        call_times: list[float] = []

        def flaky_function() -> int:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 2:
                raise ValueError("Retry!")
            return 42

        retry_with_backoff(
            flaky_function,
            retries=3,
            base_delay=0.1,
            jitter=False,
            exceptions=(ValueError,),
        )

        # Should have at least 0.1s between calls
        assert call_times[1] - call_times[0] >= 0.09  # Allow small timing variation


class TestAsyncRetryWithBackoff:
    """Tests for async_retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        """Test async function that succeeds immediately."""

        async def async_func() -> int:
            return 42

        result = await async_retry_with_backoff(async_func, retries=3)
        assert result == 42

    @pytest.mark.asyncio
    async def test_success_after_retries(self) -> None:
        """Test async function that succeeds after retries."""
        call_count = 0

        async def flaky_async() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet!")
            return 42

        result = await async_retry_with_backoff(
            flaky_async,
            retries=5,
            base_delay=0.01,
            exceptions=(ValueError,),
        )

        assert result == 42
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        """Test that exhausted retries raises the last exception."""

        async def always_fails() -> None:
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await async_retry_with_backoff(
                always_fails,
                retries=2,
                base_delay=0.01,
                exceptions=(ValueError,),
            )

    @pytest.mark.asyncio
    async def test_on_retry_callback(self) -> None:
        """Test on_retry callback is called for async."""
        callback_calls: list[tuple[int, Exception]] = []
        call_count = 0

        def callback(attempt: int, error: Exception) -> None:
            callback_calls.append((attempt, error))

        async def flaky_async() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return 42

        await async_retry_with_backoff(
            flaky_async,
            retries=5,
            base_delay=0.01,
            exceptions=(ValueError,),
            on_retry=callback,
        )

        assert len(callback_calls) == 2

    @pytest.mark.asyncio
    async def test_respects_async_delay(self) -> None:
        """Test that async delays are actually applied."""
        call_count = 0
        call_times: list[float] = []

        async def flaky_async() -> int:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 2:
                raise ValueError("Retry!")
            return 42

        await async_retry_with_backoff(
            flaky_async,
            retries=3,
            base_delay=0.1,
            jitter=False,
            exceptions=(ValueError,),
        )

        # Should have at least 0.1s between calls
        assert call_times[1] - call_times[0] >= 0.09



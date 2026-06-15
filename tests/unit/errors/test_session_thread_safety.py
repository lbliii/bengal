"""Free-threading data-race coverage for :class:`ErrorSession` (issue #439).

The session docstring claims thread-safety, but only ``record()`` and
``clear()`` hold ``self._lock``; the read methods iterate the shared
``_patterns`` / ``_errors_by_*`` dicts unlocked. Under free-threaded CPython
(``python3.14t``, GIL disabled) a reader iterating a dict while ``record()``
mutates it raises ``RuntimeError: dictionary changed size during iteration``.

These tests are **discriminating**: on the unfixed code they reproduce that
race (the assertions fail), and they pass only once every reader holds the
lock. They are no-ops on a GIL build (the GIL serialises access), which is
why the #439 milestone requires verifying under ``python3.14t``.
"""

from __future__ import annotations

import threading

import pytest

from bengal.errors.session import ErrorSession

pytestmark = pytest.mark.parallel_unsafe

# High write pressure with *distinct* signatures so ``_patterns`` keeps growing
# (and therefore resizes) *during* a reader's iteration — a gentle driver with
# few patterns is vacuously green because the dicts never change size mid-read.
_WRITERS = 6
_READERS = 6
_RECORDS_PER_WRITER = 4000


def _unique_error(writer: int, index: int) -> ValueError:
    # The signature is derived from the (normalised) message, so a unique
    # message per call yields a unique pattern -> the pattern dict grows.
    return ValueError(f"boom w{writer} n{index}")


def test_error_session_readers_are_race_free_under_free_threading() -> None:
    """Concurrent record() + read methods must never tear or raise.

    Drives ``record()`` from many threads while other threads hammer every
    reader (``get_summary`` / ``get_investigation_hints`` /
    ``get_systemic_issues`` / ``get_most_common_errors`` / the per-key
    getters). Asserts no exception escaped any thread and the final totals
    are internally consistent.
    """
    session = ErrorSession()
    errors: list[BaseException] = []
    errors_lock = threading.Lock()
    stop = threading.Event()
    start = threading.Barrier(_WRITERS + _READERS)

    def writer(writer_id: int) -> None:
        start.wait()
        try:
            for index in range(_RECORDS_PER_WRITER):
                session.record(
                    _unique_error(writer_id, index),
                    file_path=f"content/w{writer_id}/post{index % 50}.md",
                    build_phase=("render", "parse", "postprocess")[index % 3],
                )
        except BaseException as exc:
            with errors_lock:
                errors.append(exc)
        finally:
            stop.set()

    def reader() -> None:
        start.wait()
        try:
            while not stop.is_set():
                session.get_summary()
                session.get_investigation_hints()
                session.get_systemic_issues()
                session.get_most_common_errors()
                session.get_errors_for_file("content/w0/post0.md")
                session.get_errors_by_code("X")
        except BaseException as exc:
            with errors_lock:
                errors.append(exc)

    threads = [threading.Thread(target=writer, args=(w,)) for w in range(_WRITERS)]
    threads += [threading.Thread(target=reader) for _ in range(_READERS)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, (
        f"ErrorSession raced under free-threading: {len(errors)} thread(s) failed, "
        f"first = {type(errors[0]).__name__}: {errors[0]}"
    )

    summary = session.get_summary()
    assert summary["total_errors"] == _WRITERS * _RECORDS_PER_WRITER
    # Every record had a unique message -> a unique pattern.
    assert summary["unique_patterns"] == _WRITERS * _RECORDS_PER_WRITER


def test_get_summary_does_not_deadlock_when_readers_are_locked() -> None:
    """``get_summary`` calls two other readers, so a plain ``Lock`` self-deadlocks.

    This guards the reentrancy trap: the fix must use a re-entrant lock (or a
    snapshot-then-release strategy). A plain ``Lock`` wrapping every reader
    would hang here; the test asserts the call returns promptly.
    """
    session = ErrorSession()
    for index in range(200):
        session.record(_unique_error(0, index), file_path=f"f{index % 5}.md")

    done = threading.Event()
    result: dict[str, object] = {}

    def call_summary() -> None:
        result["summary"] = session.get_summary()
        result["hints"] = session.get_investigation_hints()
        done.set()

    thread = threading.Thread(target=call_summary)
    thread.start()
    thread.join(timeout=10.0)

    assert done.is_set(), (
        "get_summary()/get_investigation_hints() deadlocked (reentrant reader calls)"
    )
    assert result["summary"]["total_errors"] == 200  # type: ignore[index]

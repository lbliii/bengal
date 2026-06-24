"""Tests for free-threading detection and CLI gate."""

from __future__ import annotations

import pytest

from bengal.cli.utils.free_threading import (
    ensure_free_threading_or_confirm,
    free_threading_bypassed,
)
from bengal.utils.concurrency.gil import (
    FreeThreadingState,
    FreeThreadingStatus,
    get_free_threading_status,
    has_free_threading_support,
    is_free_threading_build,
)


class TestFreeThreadingDetection:
    def test_active_when_gil_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.sys.version",
            "3.14.2 free-threading build",
        )
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.is_gil_disabled",
            lambda: True,
        )

        status = get_free_threading_status()
        assert status.state is FreeThreadingState.ACTIVE
        assert has_free_threading_support() is True
        assert is_free_threading_build() is True

    def test_gil_enabled_on_free_threading_build(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.sys.version",
            "3.14.2 free-threading build",
        )
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.is_gil_disabled",
            lambda: False,
        )

        status = get_free_threading_status()
        assert status.state is FreeThreadingState.GIL_ENABLED
        assert "GIL is still on" in status.headline
        assert any("PYTHON_GIL=0" in line for line in status.fix_lines)

    def test_standard_python_is_unsupported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.sys.version",
            "3.14.3 (main) [Clang]",
        )
        monkeypatch.setattr(
            "bengal.utils.concurrency.gil.is_gil_disabled",
            lambda: False,
        )

        status = get_free_threading_status()
        assert status.state is FreeThreadingState.UNSUPPORTED
        assert has_free_threading_support() is False
        assert is_free_threading_build() is False
        assert any("python3.14t" in line for line in status.fix_lines)


class TestFreeThreadingGate:
    def test_bypass_with_yes_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("BENGAL_ALLOW_GIL", raising=False)
        assert free_threading_bypassed(yes=True) is True

    def test_bypass_with_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BENGAL_ALLOW_GIL", "1")
        assert free_threading_bypassed(yes=False) is True

    def test_no_op_when_free_threading_active(self) -> None:
        class _CLI:
            def confirm(self, *_args: object, **_kwargs: object) -> bool:
                raise AssertionError("confirm should not run")

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "bengal.cli.utils.free_threading.get_free_threading_status",
                lambda: FreeThreadingStatus(
                    state=FreeThreadingState.ACTIVE,
                    python_version="3.14.2 free-threading build",
                    headline="active",
                    body_lines=(),
                    fix_lines=(),
                ),
            )
            ensure_free_threading_or_confirm(_CLI(), command="serve", yes=False)

    def test_aborts_when_user_declines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bengal.cli.utils.free_threading.get_free_threading_status",
            lambda: FreeThreadingStatus(
                state=FreeThreadingState.UNSUPPORTED,
                python_version="3.14.3",
                headline="not free-threaded",
                body_lines=("slow",),
                fix_lines=("install python3.14t",),
            ),
        )
        monkeypatch.setattr("bengal.cli.utils.free_threading.sys.stdin.isatty", lambda: True)

        class _CLI:
            def blank(self) -> None:
                return None

            def warning(self, *_args: object, **_kwargs: object) -> None:
                return None

            def detail(self, *_args: object, **_kwargs: object) -> None:
                return None

            def confirm(self, *_args: object, **_kwargs: object) -> bool:
                return False

            def error(self, *_args: object, **_kwargs: object) -> None:
                return None

            def tip(self, *_args: object, **_kwargs: object) -> None:
                return None

        with pytest.raises(SystemExit) as exc:
            ensure_free_threading_or_confirm(_CLI(), command="build", yes=False)
        assert exc.value.code == 130

    def test_non_interactive_requires_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bengal.cli.utils.free_threading.get_free_threading_status",
            lambda: FreeThreadingStatus(
                state=FreeThreadingState.UNSUPPORTED,
                python_version="3.14.3",
                headline="not free-threaded",
                body_lines=("slow",),
                fix_lines=("install python3.14t",),
            ),
        )
        monkeypatch.setattr("bengal.cli.utils.free_threading.sys.stdin.isatty", lambda: False)

        class _CLI:
            def blank(self) -> None:
                return None

            def warning(self, *_args: object, **_kwargs: object) -> None:
                return None

            def detail(self, *_args: object, **_kwargs: object) -> None:
                return None

            def error(self, *_args: object, **_kwargs: object) -> None:
                return None

            def tip(self, *_args: object, **_kwargs: object) -> None:
                return None

            def confirm(self, *_args: object, **_kwargs: object) -> bool:
                raise AssertionError("confirm should not run")

        with pytest.raises(SystemExit) as exc:
            ensure_free_threading_or_confirm(_CLI(), command="serve", yes=False)
        assert exc.value.code == 2

"""Regression tests for KidaTemplateEngine error-code classification (#391).

``KidaTemplateEngine.render_template`` used to inline-classify TypeErrors with
its own string heuristics, emitting ``R008`` (``template_context_error``) for the
NoneType-not-callable case while the canonical :class:`ErrorClassifier` returns
``R015`` (``template_callable_error``). These tests pin the live render path to
the classifier so the two cannot drift again.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from bengal.errors import BengalRenderingError
from bengal.errors.codes import ErrorCode
from bengal.rendering.engines.kida import KidaTemplateEngine
from bengal.rendering.errors.classifier import ErrorClassifier


class _FakeTemplate:
    """A compiled-template stand-in whose render raises a chosen exception."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def render(self, _ctx: Any) -> str:
        raise self._exc


class _FakeEnv:
    """Minimal environment exposing ``get_template`` and ``globals``."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.globals: dict[str, Any] = {}

    def get_template(self, _name: str) -> _FakeTemplate:
        return _FakeTemplate(self._exc)


class _FakeSite:
    config: ClassVar[dict[str, Any]] = {}


class _StubKidaEngine(KidaTemplateEngine):
    """KidaTemplateEngine wired to raise a controlled exception at render time.

    Bypasses ``__init__`` (no real Site/templates) and no-ops the dependency
    bookkeeping that runs before the ``try`` block, so the real
    ``except TypeError`` handler in ``render_template`` is exercised verbatim.
    """

    def __init__(self, exc: BaseException) -> None:
        self._env = _FakeEnv(exc)
        self.site = _FakeSite()
        self._profiler = None

    def get_template_path(self, name: str) -> None:  # type: ignore[override]
        return None

    def _track_referenced_templates(self, template_name: str) -> None:  # type: ignore[override]
        return None


def _render_error(exc: BaseException) -> BengalRenderingError:
    engine = _StubKidaEngine(exc)
    with pytest.raises(BengalRenderingError) as excinfo:
        engine.render_template("page.html", {})
    return excinfo.value


class TestRenderTemplateErrorCodes:
    def test_nonetype_not_callable_maps_to_r015_not_r008(self) -> None:
        exc = TypeError("'NoneType' object is not callable")
        err = _render_error(exc)
        assert err.code == ErrorCode.R015
        assert err.code != ErrorCode.R008

    def test_undefined_macro_call_maps_to_r006(self) -> None:
        exc = TypeError("'_Undefined' object is not callable")
        err = _render_error(exc)
        assert err.code == ErrorCode.R006

    def test_generic_typeerror_maps_to_r010(self) -> None:
        exc = TypeError("unsupported operand type(s)")
        err = _render_error(exc)
        assert err.code == ErrorCode.R010

    @pytest.mark.parametrize(
        "exc",
        [
            TypeError("'NoneType' object is not callable"),
            TypeError("'_Undefined' object is not callable"),
            TypeError("something entirely different"),
        ],
    )
    def test_no_drift_engine_matches_classifier(self, exc: TypeError) -> None:
        # The TypeError branch derives every classifiable code from the
        # classifier. The generic fallback is R010, which is also the
        # classifier's fallback, so the codes match for all three cases.
        err = _render_error(exc)
        assert err.code == ErrorClassifier().classify(exc)

    def test_nonetype_message_is_byte_stable(self) -> None:
        # The user-facing message for the NoneType case must not change; only
        # the code flips R008 -> R015.
        exc = TypeError("'NoneType' object is not callable")
        err = _render_error(exc)
        assert "A function or filter is None (not callable)." in str(err)

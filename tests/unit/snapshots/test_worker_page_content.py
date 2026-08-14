"""Tests for the render-plan worker page-content registry lock."""

from __future__ import annotations

import dataclasses
import inspect
import threading
from datetime import datetime
from pathlib import Path

import pytest

from bengal.snapshots import render_plan
from bengal.snapshots.render_plan import (
    _WORKER_PAGE_CONTENT_LOCK,
    PageView,
    clear_worker_page_content,
    set_worker_page_content,
)


def _mk_pv(source_path: Path) -> PageView:
    """Minimal PageView for registry lookups (no fixture build)."""
    return PageView(
        title=source_path.name,
        href=f"/{source_path}",
        site_path=f"/{source_path}",
        source_path=source_path,
        output_path=source_path,
        slug=source_path.stem,
        ref_id=None,
        template_name="page.html",
        date=datetime(2024, 1, 1),
        weight=0.0,
        tags=(),
        categories=(),
        excerpt="",
        meta_description="",
        reading_time=0,
        word_count=0,
        toc_items=(),
        content_hash="",
        metadata={},
        section_path=None,
        version=None,
        is_generated=False,
    )


@pytest.fixture(autouse=True)
def _reset_worker_page_content() -> None:
    clear_worker_page_content()
    yield
    clear_worker_page_content()


class TestWorkerPageContentLock:
    """Module-level content registry is locked on every read and write."""

    def test_registry_lock_is_threading_lock(self) -> None:
        assert type(_WORKER_PAGE_CONTENT_LOCK) is type(threading.Lock())

    def test_public_signatures_unchanged(self) -> None:
        set_params = inspect.signature(set_worker_page_content).parameters
        assert list(set_params) == ["content_by_path"]

        clear_sig = inspect.signature(clear_worker_page_content)
        assert list(clear_sig.parameters) == []
        assert clear_sig.return_annotation in {None, "None"}

    def test_set_rebinds_module_mapping(self) -> None:
        mapping = {Path("a.md"): "<p>a</p>"}
        set_worker_page_content(mapping)
        with _WORKER_PAGE_CONTENT_LOCK:
            assert render_plan._WORKER_PAGE_CONTENT is mapping

    def test_clear_rebinds_to_empty_dict(self) -> None:
        mapping = {Path("a.md"): "<p>a</p>"}
        set_worker_page_content(mapping)
        clear_worker_page_content()
        with _WORKER_PAGE_CONTENT_LOCK:
            assert render_plan._WORKER_PAGE_CONTENT == {}
            assert render_plan._WORKER_PAGE_CONTENT is not mapping

    def test_page_view_content_reads_registry(self) -> None:
        path = Path("post.md")
        view = _mk_pv(path)
        set_worker_page_content({path: "<p>hello</p>"})
        assert view.content == "<p>hello</p>"
        assert "content" not in {field.name for field in dataclasses.fields(PageView)}

    def test_page_view_content_empty_outside_worker(self) -> None:
        view = _mk_pv(Path("post.md"))
        assert view.content == ""

    @pytest.mark.parallel_unsafe
    def test_concurrent_set_get_and_clear(self) -> None:
        paths = [Path(f"page-{i}.md") for i in range(16)]
        views = [_mk_pv(path) for path in paths]
        errors: list[BaseException] = []

        def _set(path: Path) -> None:
            try:
                set_worker_page_content({path: f"<p>{path.name}</p>"})
            except Exception as exc:
                errors.append(exc)

        def _get_loop() -> None:
            try:
                for view in views:
                    body = view.content
                    assert isinstance(body, str)
            except Exception as exc:
                errors.append(exc)

        def _clear_loop() -> None:
            try:
                for _ in range(20):
                    clear_worker_page_content()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_set, args=(path,)) for path in paths]
        threads.extend(threading.Thread(target=_get_loop) for _ in range(4))
        threads.extend(threading.Thread(target=_clear_loop) for _ in range(4))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        mapping = {paths[0]: "<p>final</p>"}
        set_worker_page_content(mapping)
        assert views[0].content == "<p>final</p>"
        clear_worker_page_content()
        assert views[0].content == ""

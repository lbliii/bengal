"""Tests for build-time static markup enhancements (#538)."""

from __future__ import annotations

from bengal.postprocess.static_markup import (
    enhance_theme_markup,
    inject_code_copy_chrome,
    mark_external_links,
)


def test_mark_external_links_adds_attributes() -> None:
    html = '<p><a href="https://example.com/docs">Docs</a></p>'
    out = mark_external_links(html, base_url="https://mysite.test")
    assert 'data-external="true"' in out
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out


def test_mark_external_links_skips_internal_paths() -> None:
    html = '<a href="/guide/">Guide</a>'
    out = mark_external_links(html, base_url="https://mysite.test")
    assert "data-external" not in out


def test_inject_code_copy_chrome_wraps_pre_code() -> None:
    html = '<pre><code class="language-python">print("hi")</code></pre>'
    out = inject_code_copy_chrome(html)
    assert 'class="code-block-wrapper"' in out
    assert 'class="code-copy-button' in out
    assert 'class="code-language">PYTHON' in out


def test_enhance_theme_markup_is_idempotent_on_wrapped_code() -> None:
    html = "<pre><code>one</code></pre>"
    once = enhance_theme_markup(html, base_url="https://mysite.test")
    twice = enhance_theme_markup(once, base_url="https://mysite.test")
    assert once.count("code-block-wrapper") == 1
    assert twice.count("code-block-wrapper") == 1

"""Tests for build-time static markup enhancements (#538, #542)."""

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


def test_inject_code_copy_chrome_uses_rosettes_data_language() -> None:
    html = (
        '<div class="rosettes" data-language="python"><pre><code>'
        '<span class="syntax-name">x</span></code></pre></div>'
    )
    out = inject_code_copy_chrome(html)
    assert 'class="code-language">PYTHON' in out
    assert out.count("code-block-wrapper") == 1


def test_inject_code_copy_chrome_adds_linenos_gutter() -> None:
    html = (
        '<div class="rosettes" data-language="python" data-linenos="true">'
        "<pre><code>line1\nline2\nline3\n</code></pre></div>"
    )
    out = inject_code_copy_chrome(html)
    assert 'class="code-block-with-linenos"' in out
    assert 'class="code-linenos"' in out
    assert "1\n2\n3" in out


def test_inject_code_copy_chrome_adds_terminal_frame() -> None:
    html = (
        '<div class="rosettes" data-language="bash" data-frame="terminal">'
        "<pre><code>echo hi</code></pre></div>"
    )
    out = inject_code_copy_chrome(html)
    assert "code-block-frame--terminal" in out
    assert "code-block-frame-header--terminal" in out


def test_inject_code_copy_chrome_adds_editor_frame_for_titled_blocks() -> None:
    html = (
        '<div class="code-block-titled"><div class="code-block-title">app.py</div>'
        '<div class="rosettes" data-language="python"><pre><code>x=1</code></pre></div></div>'
    )
    out = inject_code_copy_chrome(html)
    assert "code-block-frame--editor" in out


def test_inject_code_copy_chrome_adds_annotations() -> None:
    html = (
        '<div class="rosettes" data-language="python" data-annotate="2:Run this step">'
        "<pre><code>setup\nrun\n</code></pre></div>"
    )
    out = inject_code_copy_chrome(html)
    assert 'class="code-line-annotation"' in out
    assert "Run this step" in out


def test_inject_code_copy_chrome_wraps_collapsible_blocks() -> None:
    html = (
        '<div class="rosettes" data-language="python" data-collapsible="closed">'
        "<pre><code>x=1</code></pre></div>"
    )
    out = inject_code_copy_chrome(html)
    assert "<details" in out
    assert 'class="code-block-collapsible"' in out
    assert "data-collapsible" not in out or "<details" in out


def test_enhance_theme_markup_is_idempotent_on_wrapped_code() -> None:
    html = "<pre><code>one</code></pre>"
    once = enhance_theme_markup(html, base_url="https://mysite.test")
    twice = enhance_theme_markup(once, base_url="https://mysite.test")
    assert once.count("code-block-wrapper") == 1
    assert twice.count("code-block-wrapper") == 1


def test_parser_fence_metadata_reaches_premium_chrome() -> None:
    from bengal.parsing import PatitasParser

    parser = PatitasParser(enable_highlighting=True)
    raw = parser.parse('```python linenos annotate="2:Run" collapse\na=1\nb=2\n```', {})
    out = enhance_theme_markup(raw)
    assert 'data-linenos="true"' in raw
    assert 'class="code-linenos"' in out
    assert 'class="code-line-annotation"' in out
    assert "<details" in out

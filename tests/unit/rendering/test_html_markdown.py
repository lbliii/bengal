"""Tests for rendered HTML to Markdown mirror helpers."""

from __future__ import annotations

from bengal.rendering.html_markdown import (
    extract_primary_content_html,
    html_fragment_to_markdown,
    rendered_html_to_markdown,
)


def test_extracts_article_before_surrounding_navigation() -> None:
    html = """
    <html><body>
      <main id="main-content">
        <aside class="docs-sidebar">Navigation noise</aside>
        <article class="prose">
          <h2>Install</h2>
          <p>Run <code>pip install bengal</code>.</p>
        </article>
      </main>
    </body></html>
    """

    result = extract_primary_content_html(html)

    assert "Install" in result
    assert "Navigation noise" not in result


def test_converts_common_content_markup_to_markdown() -> None:
    html = """
    <article class="prose">
      <h2>Steps</h2>
      <p>Install <a href="/docs/install/">Bengal</a>.</p>
      <ul><li>Create a site</li><li>Run the server</li></ul>
      <pre><code>bengal serve</code></pre>
    </article>
    """

    result = html_fragment_to_markdown(html)

    assert "## Steps" in result
    assert "Install Bengal (/docs/install/)." in result
    assert "- Create a site" in result
    assert "```\nbengal serve\n```" in result


def test_rendered_html_to_markdown_ignores_sidebar_when_main_is_fallback() -> None:
    html = """
    <main id="main-content">
      <section>
        <h1>Overview</h1>
        <p>Generated page summary.</p>
      </section>
      <aside>Sidebar links</aside>
    </main>
    """

    result = rendered_html_to_markdown(html)

    assert "# Overview" in result
    assert "Generated page summary." in result
    assert "Sidebar links" not in result

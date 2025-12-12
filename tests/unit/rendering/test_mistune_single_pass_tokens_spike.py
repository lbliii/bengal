from __future__ import annotations

from types import SimpleNamespace

from bengal.rendering.parsers.mistune import MistuneParser


def test_parse_with_context_and_tokens_matches_html_and_captures_directive_tokens():
    parser = MistuneParser(enable_highlighting=False)

    page = SimpleNamespace(
        title="Spike",
        metadata={},
        source_path="/docs/spike.md",
    )
    ctx = {"page": page, "site": SimpleNamespace(config={}), "config": {}}

    content = """
:::{note} Note title
This is **bold** and a variable: {{ page.title }}.
:::

:::{dropdown} More
Hidden *content*.
:::
""".strip()

    html_expected = parser.parse_with_context(content, {}, ctx)
    html, tokens = parser.parse_with_context_and_tokens(content, {}, ctx)

    assert html == html_expected
    assert isinstance(tokens, list)
    assert any(isinstance(t, dict) and t.get("type") in {"admonition", "dropdown"} for t in tokens)


def test_parse_with_toc_and_context_and_tokens_matches_html_and_toc():
    parser = MistuneParser(enable_highlighting=False)

    page = SimpleNamespace(title="Spike", metadata={}, source_path="/docs/spike.md")
    ctx = {"page": page, "site": SimpleNamespace(config={}), "config": {}}

    content = """
## Heading A

:::{note}
Body
:::

## Heading B
""".strip()

    html_expected, toc_expected = parser.parse_with_toc_and_context(content, {}, ctx)
    html, toc, tokens = parser.parse_with_toc_and_context_and_tokens(content, {}, ctx)

    assert html == html_expected
    assert toc == toc_expected
    assert any(isinstance(t, dict) and t.get("type") in {"heading", "admonition"} for t in tokens)

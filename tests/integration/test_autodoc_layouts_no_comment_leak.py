from __future__ import annotations

import pytest


@pytest.mark.bengal(testroot="test-autodoc-layouts")
def test_autodoc_layout_does_not_leak_template_comment_closers(site, build_site) -> None:
    """
    Ensure API/CLI reference layouts do not leak template doc-comment fragments.

    Regression test for a real-world failure mode where a Jinja doc comment
    contained nested `{# ... #}` examples, causing `#}` and stray `</div>` to
    be emitted into output HTML and breaking `.docs-main` layout containment.
    """
    build_site()

    api_python_index = site.output_dir / "api" / "python" / "index.html"
    assert api_python_index.exists(), f"Expected output missing: {api_python_index}"

    html = api_python_index.read_text(encoding="utf-8")

    # The exact broken fragment observed in public output.
    assert "</div>  #}" not in html

    docs_main_open = html.find('<div class="docs-main">')
    assert docs_main_open != -1, "Expected .docs-main wrapper"

    # `.page-hero` must be inside `.docs-main` (layout contract for docs grid).
    within_main = html[docs_main_open : docs_main_open + 2000]
    assert 'class="page-hero' in within_main

"""Guard: per-page navigation active-state must never become stale chrome (#348).

Issue #348 ("render the invariant chrome once and reuse") is tempting because
the site nav/header/footer *look* byte-identical across pages. They are NOT:
the default theme renders the active-nav highlight server-side, per page
(`base.html`: ``is_active = (item?.active ?? false) or (_page_url == _item_href)``).
Hoisting the nav once and splicing it into every page would therefore show a
stale active item on every page except the one it happened to be pre-rendered
for.

This test locks that invariant. It builds a multi-section site and asserts that
each section's page marks ITS OWN nav entry active while a different section's
page marks a DIFFERENT entry — so any regression that hoists the nav fails here.

Concrete regression this guards against: the ``BlockCache``
(``bengal/rendering/block_cache.py``) currently caches **0** blocks for the
default theme (``warm_site_blocks`` → ``render_block`` throws on base.html's
module-level ``{% let %}`` scaffold), so no stale chrome ships today. Its block
introspection nonetheless labels ``nav_items`` / ``mobile_nav_items`` as
``scope='site'``, which is unsafe — those blocks read the per-page ``_page_url``.
If that warming path is ever repaired without fixing the scope classification,
the page-scoped nav block would be cached as if site-scoped and this test would
fail. See ``benchmarks/348-chrome-memoization-findings.md``.
"""

from __future__ import annotations

import re

import pytest

# Match an <a> whose attributes carry an active marker (class "active" or
# aria-current="page"); capture its inner text. The default theme renders both
# on the current section's top-level nav entry, in the desktop and mobile navs.
_ACTIVE_LINK = re.compile(
    r'<a[^>]*?(?:class="[^"]*\bactive\b[^"]*"|aria-current="page")[^>]*>(.*?)</a>',
    re.S,
)


def _active_nav_labels(html: str) -> set[str]:
    """Visible text of every nav link marked active in the rendered page."""
    return {re.sub(r"<[^>]+>", "", t).strip() for t in _ACTIVE_LINK.findall(html)}


@pytest.mark.bengal(testroot="test-navigation")
def test_nav_active_state_is_per_page_not_hoisted(site, build_site):
    """Each page marks its own section's nav entry active — never a stale hoist."""
    build_site()

    docs_html = (site.output_dir / "docs" / "index.html").read_text(encoding="utf-8")
    blog_html = (site.output_dir / "blog" / "index.html").read_text(encoding="utf-8")

    docs_active = _active_nav_labels(docs_html)
    blog_active = _active_nav_labels(blog_html)

    # Each section page marks its OWN nav entry active...
    assert "Documentation" in docs_active, (
        f"/docs/ page should mark its own nav entry active; got {docs_active!r}"
    )
    assert "Blog" in blog_active, (
        f"/blog/ page should mark its own nav entry active; got {blog_active!r}"
    )

    # ...and NOT the other section's. This is the stale-chrome failure mode: if
    # the nav were rendered once and spliced into every page, both pages would
    # carry the same active set.
    assert "Blog" not in docs_active, (
        f"/docs/ page wrongly marks 'Blog' active — stale hoisted nav? {docs_active!r}"
    )
    assert "Documentation" not in blog_active, (
        f"/blog/ page wrongly marks 'Documentation' active — stale hoisted nav? {blog_active!r}"
    )

    # The active set genuinely differs per page: the nav is rendered per page,
    # never reused as page-invariant chrome.
    assert docs_active != blog_active, (
        "nav active-state is identical across two different section pages — the "
        "nav appears to have been hoisted/spliced (stale chrome). #348 must not "
        f"hoist the nav block. docs={docs_active!r} blog={blog_active!r}"
    )

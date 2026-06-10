"""
Tests for the autodoc SymbolResolver and xref template helpers (#327).

These lock the deterministic, ambiguity-safe, page-aware resolution contract and
the type/docstring cross-reference rendering. Assertions discriminate: each fails
if the guarded behavior breaks (an ambiguous name MUST NOT resolve; an inline
symbol MUST anchor onto its module page, not its own non-existent page URL).
"""

from __future__ import annotations

from bengal.autodoc.base import DocElement
from bengal.autodoc.symbol_resolver import SymbolResolver
from bengal.rendering.template_functions.autodoc import (
    xref_docstring_html,
    xref_type_html,
)


def _el(name: str, qualified: str, href: str | None, element_type: str = "class") -> DocElement:
    el = DocElement(
        name=name,
        qualified_name=qualified,
        description="",
        element_type=element_type,
    )
    el.href = href
    return el


def _two_module_tree() -> list[DocElement]:
    # Mirrors the Python autodoc shape: only the MODULE owns a page; the class and
    # its methods render inline as cards on the module page. compute_element_urls
    # still sets a (non-page) href on every element; the resolver must ignore those
    # and anchor inline symbols onto the module page so links are never broken.
    site = _el("Site", "pkg.core.site.Site", "/api/pkg/core/site/Site/")
    method = _el("build", "pkg.core.site.Site.build", "/api/pkg/core/site/Site/build/", "method")
    site.children = [method]
    mod = _el("site", "pkg.core.site", "/api/pkg/core/site/", "module")
    mod.children = [site]
    return [mod]


def test_module_resolves_to_its_own_page():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    assert resolver.resolve("pkg.core.site") == "/api/pkg/core/site/"


def test_inline_class_resolves_to_module_page_anchor():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    # The class renders on the module page; link points at the module page + card.
    assert resolver.resolve("pkg.core.site.Site") == "/api/pkg/core/site/#Site"


def test_resolves_unique_simple_name_to_anchor():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    assert resolver.resolve("Site") == "/api/pkg/core/site/#Site"


def test_method_resolves_to_top_level_card_anchor():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    # A method anchors onto its CLASS card (unique on the page), not a #build
    # fragment that could collide with a module-level function named "build".
    assert resolver.resolve("pkg.core.site.Site.build") == "/api/pkg/core/site/#Site"


def test_strips_tilde_and_backticks_and_call_suffix():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    assert resolver.resolve("~pkg.core.site.Site") == "/api/pkg/core/site/#Site"
    assert resolver.resolve("`Site`") == "/api/pkg/core/site/#Site"


def test_unknown_name_returns_none():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    # Stdlib / undocumented names MUST NOT resolve (no broken links).
    assert resolver.resolve("dict") is None
    assert resolver.resolve("collections.OrderedDict") is None
    assert resolver.resolve("") is None
    assert resolver.resolve(None) is None


def test_ambiguous_simple_name_degrades_to_none():
    # Two documented classes share the simple name "Config".
    a = _el("Config", "pkg.a.Config", "/api/pkg/a/Config/")
    b = _el("Config", "pkg.b.Config", "/api/pkg/b/Config/")
    mod_a = _el("a", "pkg.a", "/api/pkg/a/", "module")
    mod_a.children = [a]
    mod_b = _el("b", "pkg.b", "/api/pkg/b/", "module")
    mod_b.children = [b]
    resolver = SymbolResolver.from_elements([mod_a, mod_b])

    # Ambiguous simple name MUST be None (a wrong link is worse than no link).
    assert resolver.resolve("Config") is None
    # But qualified names still disambiguate (to module page + card anchor).
    assert resolver.resolve("pkg.a.Config") == "/api/pkg/a/#Config"
    assert resolver.resolve("pkg.b.Config") == "/api/pkg/b/#Config"


def test_orphan_without_page_owner_is_not_indexed():
    # A top-level non-module element with no page-owning ancestor is unresolvable.
    orphan = _el("Hidden", "Hidden", "/whatever/", "class")
    resolver = SymbolResolver.from_elements([orphan])
    assert resolver.resolve("Hidden") is None


def test_inline_element_without_module_href_is_not_indexed():
    no_href_mod = _el("pkg", "pkg", None, "module")
    cls = _el("Inline", "pkg.Inline", "/api/pkg/Inline/", "class")
    no_href_mod.children = [cls]
    resolver = SymbolResolver.from_elements([no_href_mod])
    # Module owns the page but has no href -> nothing under it can be linked.
    assert resolver.resolve("pkg.Inline") is None
    assert resolver.resolve("Inline") is None


def test_build_is_deterministic_across_runs():
    r1 = SymbolResolver.from_elements(_two_module_tree())
    r2 = SymbolResolver.from_elements(_two_module_tree())
    # Same inputs -> identical resolution (byte-stable xref output depends on this).
    for name in ("Site", "pkg.core.site.Site", "pkg.core.site", "build", "dict"):
        assert r1.resolve(name) == r2.resolve(name)


def test_xref_type_links_resolvable_compound_components():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    html = str(xref_type_html("dict[str, Site | None]", resolver))
    # The resolvable component is linked to the module page + card anchor...
    assert '<a href="/api/pkg/core/site/#Site">Site</a>' in html
    # ...the structure and unresolved tokens are preserved as plain text.
    assert "dict[str, " in html
    assert " | None]" in html
    # 'str' and 'None' must NOT be linked (no documented symbol).
    assert ">str</a>" not in html
    assert ">None</a>" not in html


def test_xref_type_without_resolver_is_escaped_plaintext():
    html = str(xref_type_html("Site & <bad>", None))
    assert "<a " not in html  # No links without a resolver.
    assert "&lt;bad&gt;" in html  # HTML is escaped, not raw.


def test_xref_type_escapes_href_and_text():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    html = str(xref_type_html("Site", resolver))
    assert html == '<a href="/api/pkg/core/site/#Site">Site</a>'


def test_xref_docstring_links_known_code_spans_only():
    resolver = SymbolResolver.from_elements(_two_module_tree())
    rendered = "See the <code>Site</code> object, not <code>os.path</code>."
    html = str(xref_docstring_html(rendered, resolver))
    # Known symbol is wrapped in a link...
    assert '<a href="/api/pkg/core/site/#Site" class="autodoc-xref"><code>Site</code></a>' in html
    # ...unknown code span is left exactly as-is (no broken link).
    assert "<code>os.path</code>" in html
    assert html.count("autodoc-xref") == 1


def test_xref_docstring_without_resolver_is_passthrough():
    rendered = "Plain <code>Site</code> text."
    html = str(xref_docstring_html(rendered, None))
    assert html == rendered

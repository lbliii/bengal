"""
Tests for compute_element_urls anchor hrefs on non-page members (#401).

Members that never get their own page (Python classes/functions/methods, CLI
options) must receive an on-page anchor href (``{parent_page}#{card}``) rather
than a dangling ``/api/<module>/<member>/`` page URL, so templates following the
documented ``{{ child.href }}`` contract never emit broken internal links.

Assertions discriminate: each fails if a member's href regresses to a
standalone page path, or if a method anchors onto the module page instead of
its top-level CLASS card.
"""

from __future__ import annotations

from types import SimpleNamespace

from bengal.autodoc.base import DocElement
from bengal.autodoc.orchestration.page_builders import compute_element_urls


def _el(name: str, qualified: str, element_type: str) -> DocElement:
    return DocElement(
        name=name,
        qualified_name=qualified,
        description="",
        element_type=element_type,
    )


# Prefix resolution mirrors the orchestrator: python -> "api/pkg", cli -> "cli",
# openapi -> "api". The site has no baseurl so href == _path.
_PREFIX = {"python": "api/pkg", "cli": "cli", "openapi": "api"}


def _resolve_prefix(doc_type: str) -> str:
    return _PREFIX[doc_type]


_SITE = SimpleNamespace(baseurl="")


def test_python_module_owns_its_page() -> None:
    mod = _el("site", "pkg.core.site", "module")
    compute_element_urls(mod, _SITE, "python", _resolve_prefix)
    assert mod._path == "/api/pkg/pkg/core/site/"
    assert mod.href == "/api/pkg/pkg/core/site/"


def test_python_class_anchors_onto_module_page() -> None:
    mod = _el("site", "pkg.core.site", "module")
    cls = _el("Site", "pkg.core.site.Site", "class")
    mod.children = [cls]
    compute_element_urls(mod, _SITE, "python", _resolve_prefix)
    # The class renders inline as a card on the module page -> anchor, not a
    # dangling /api/pkg/pkg/core/site/Site/ page.
    assert cls._path == "/api/pkg/pkg/core/site/#Site"
    assert cls.href == "/api/pkg/pkg/core/site/#Site"


def test_python_method_anchors_onto_class_card_not_module() -> None:
    mod = _el("site", "pkg.core.site", "module")
    cls = _el("Site", "pkg.core.site.Site", "class")
    method = _el("build", "pkg.core.site.Site.build", "method")
    cls.children = [method]
    mod.children = [cls]
    compute_element_urls(mod, _SITE, "python", _resolve_prefix)
    # Mirrors test_symbol_resolver.test_method_resolves_to_top_level_card_anchor:
    # the method anchors onto its CLASS card (highest inline ancestor), not a
    # #build fragment and not the bare module page.
    assert method._path == "/api/pkg/pkg/core/site/#Site"
    assert method.href == "/api/pkg/pkg/core/site/#Site"


def test_python_module_level_function_anchors_with_own_name() -> None:
    mod = _el("site", "pkg.core.site", "module")
    func = _el("build_site", "pkg.core.site.build_site", "function")
    mod.children = [func]
    compute_element_urls(mod, _SITE, "python", _resolve_prefix)
    # A top-level function card uses its own simple name as the anchor.
    assert func._path == "/api/pkg/pkg/core/site/#build_site"


def test_cli_command_owns_page_options_anchor() -> None:
    group = _el("assets", "bengal.assets", "command-group")
    command = _el("build", "bengal.assets.build", "command")
    option = _el("--force", "bengal.assets.build.force", "option")
    command.children = [option]
    group.children = [command]
    compute_element_urls(group, _SITE, "cli", _resolve_prefix)
    # Commands and groups each own a page; the option anchors onto the command.
    assert command._path == "/cli/assets/build/"
    assert command.href == "/cli/assets/build/"
    assert option._path == "/cli/assets/build/#--force"


def test_openapi_endpoint_and_schema_own_pages() -> None:
    schema = _el("User", "User", "openapi_schema")
    compute_element_urls(schema, _SITE, "openapi", _resolve_prefix)
    assert schema._path == "/api/schemas/User/"
    assert "#" not in (schema._path or "")


def test_baseurl_is_applied_to_anchor_hrefs() -> None:
    site = SimpleNamespace(baseurl="/docs")
    mod = _el("site", "pkg.core.site", "module")
    cls = _el("Site", "pkg.core.site.Site", "class")
    mod.children = [cls]
    compute_element_urls(mod, site, "python", _resolve_prefix)
    # baseurl prefixes the path while preserving the fragment.
    assert cls.href == "/docs/api/pkg/pkg/core/site/#Site"
    assert cls._path == "/api/pkg/pkg/core/site/#Site"

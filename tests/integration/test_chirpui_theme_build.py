from __future__ import annotations

import asyncio
import re
import shutil
import sys
from pathlib import Path
from textwrap import dedent
from urllib.parse import urlparse

from bengal.assets.manifest import AssetManifest
from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.server.asgi_app import create_bengal_dev_app

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CSS_JS_RE = re.compile(r"""(?:href|src)=["']([^"']+\.(?:css|js)(?:\?[^"']*)?)["']""")


def _write_text(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")


def _write_fake_chirp_ui(package_root) -> None:
    pkg = package_root / "chirp_ui"
    templates = pkg / "templates"
    components = templates / "chirpui"

    _write_text(
        pkg / "__init__.py",
        """
        from pathlib import Path
        from kida import PackageLoader

        def static_path():
            return Path(__file__).parent / "templates"

        def get_library_contract():
            root = static_path()
            return {
                "asset_root": root,
                "assets": [
                    {"path": "chirpui.css", "mode": "bundle", "type": "css"},
                    {
                        "path": "chirpui-transitions.css",
                        "mode": "bundle",
                        "type": "css",
                        "output": "chirpui.css",
                    },
                    {"path": "chirpui.js", "mode": "link", "type": "javascript"},
                    {"path": "unused.css", "mode": "none", "type": "css"},
                ],
                "runtime": ["chirpui"],
            }

        def get_loader():
            return PackageLoader("chirp_ui", "templates")

        def register_filters(app):
            return None
        """,
    )
    _write_text(templates / "chirpui.css", ".chirpui-navbar{}.chirpui-rendered-content{}")
    _write_text(templates / "chirpui-transitions.css", ".chirpui-transition{}")
    _write_text(templates / "chirpui.js", "window.__chirpui_test__=true;")
    _write_text(templates / "unused.css", ".unused{}")
    _write_text(
        components / "navbar.html",
        """
        {% def navbar(brand=none, brand_url="/", cls="", use_slots=false, brand_slot=false, current_path="") %}
        <nav class="chirpui-navbar {{ cls }}"><a class="chirpui-navbar__brand" href="{{ brand_url }}">{{ brand }}</a><div class="chirpui-navbar__links">{% slot %}</div><div class="chirpui-navbar__links chirpui-navbar__links--end">{% slot end %}</div></nav>
        {% end %}
        {% def navbar_link(href, label, active=false, match="", cls="") %}<a class="chirpui-navbar__link{{ ' chirpui-navbar__link--active' if active else '' }}" href="{{ href }}">{{ label }}</a>{% end %}
        {% def navbar_dropdown(label, active=false, match="", href="", cls="") %}<details class="chirpui-navbar-dropdown"><summary>{{ label }}</summary>{% slot %}</details>{% end %}
    """,
    )
    _write_text(
        components / "button.html",
        """
        {% def btn(label, variant="", size=none, loading=false, type="submit", href=none, icon=none, cls="", attrs="", attrs_map=none, disabled=false, data_action=none, aria_label=none) %}
        {% if href %}<a class="chirpui-btn chirpui-btn--{{ variant }} chirpui-btn--{{ size }}" href="{{ href }}">{% if icon %}<span class="chirpui-btn__icon">{{ icon }}</span>{% end %}<span class="chirpui-btn__label">{{ label }}</span></a>{% else %}<button class="chirpui-btn" type="{{ type }}"{% if attrs_map %}{% if attrs_map.get("data-chirpui-drawer-open") %} data-chirpui-drawer-open="{{ attrs_map.get("data-chirpui-drawer-open") }}"{% end %}{% if attrs_map.get("aria-controls") %} aria-controls="{{ attrs_map.get("aria-controls") }}"{% end %}{% end %}>{% if icon %}<span class="chirpui-btn__icon">{{ icon }}</span>{% end %}<span class="chirpui-btn__label">{{ label }}</span></button>{% end %}
        {% end %}
    """,
    )
    _write_text(
        components / "layout.html",
        """
        {% def container(max_width="72rem", padding=true, cls="") %}<div class="chirpui-container {{ cls }}" style="--chirpui-container-max: {{ max_width }}">{% slot %}</div>{% end %}
        {% def grid(cols=none, gap=none, cls="") %}<div class="chirpui-grid chirpui-grid--cols-{{ cols }} chirpui-grid--gap-{{ gap }} {{ cls }}">{% slot %}</div>{% end %}
        {% def stack(gap=none, cls="") %}<div class="chirpui-stack chirpui-stack--{{ gap }} {{ cls }}">{% slot %}</div>{% end %}
        {% def cluster(gap=none, cls="") %}<div class="chirpui-cluster chirpui-cluster--{{ gap }} {{ cls }}">{% slot %}</div>{% end %}
        {% def block(span=1, cls="") %}<div class="chirpui-block {{ cls }}">{% slot %}</div>{% end %}
    """,
    )
    _write_text(
        components / "hero.html",
        """
        {% def hero(title=none, subtitle=none, background="solid", cls="") %}<section class="chirpui-hero chirpui-hero--{{ background }}"><h1 class="chirpui-hero__title">{{ title }}</h1>{% if subtitle %}<p class="chirpui-hero__subtitle">{{ subtitle }}</p>{% end %}<div class="chirpui-hero__content">{% slot %}</div><div class="chirpui-hero__action">{% slot action %}</div></section>{% end %}
        {% def page_hero(title=none, subtitle=none, variant="editorial", background="solid", cls="") %}<section class="chirpui-hero chirpui-hero--page chirpui-hero--page-{{ variant }} chirpui-hero--{{ background }}"><div class="chirpui-hero__eyebrow">{% slot eyebrow %}</div><h1 class="chirpui-hero__title">{{ title }}</h1>{% if subtitle %}<p class="chirpui-hero__subtitle">{{ subtitle }}</p>{% end %}<div class="chirpui-hero__metadata">{% slot metadata %}</div><div class="chirpui-hero__content">{% slot %}</div><div class="chirpui-hero__actions">{% slot actions %}</div><div class="chirpui-hero__footer">{% slot footer %}</div></section>{% end %}
    """,
    )
    _write_text(
        components / "card.html",
        """
        {% def card(title=none, subtitle=none, footer=none, collapsible=false, open=false, variant="", icon=none, border_variant="", header_variant="", cls="") %}<article class="chirpui-card {{ cls }}">{% if title %}<header class="chirpui-card__header"><span class="chirpui-card__title">{{ title }}</span></header>{% end %}<div class="chirpui-card__body"><div class="chirpui-card__body-content">{% slot %}</div></div></article>{% end %}
    """,
    )
    _write_text(
        components / "document_header.html",
        """
        {% def document_header(title, subtitle=none, meta=none, breadcrumb_items=none, eyebrow=none, path=none, provenance=none, status=none, meta_items=none, cls="") %}<section class="chirpui-document-header {{ cls }}">{% if breadcrumb_items %}<nav class="chirpui-breadcrumbs"><ol>{% for item in breadcrumb_items %}<li>{% if item.get("href") %}<a href="{{ item.href }}">{{ item.label }}</a>{% else %}<span>{{ item.label }}</span>{% end %}</li>{% end %}</ol></nav>{% end %}<h1>{{ title }}</h1>{% if subtitle %}<p>{{ subtitle }}</p>{% end %}{% if status %}<span class="chirpui-document-header__status">{{ status }}</span>{% end %}<div class="chirpui-document-header__actions">{% slot actions %}</div></section>{% end %}
    """,
    )
    _write_text(
        components / "detail_header.html",
        """
        {% def detail_header(title, summary=none, eyebrow=none, cls="") %}<header class="chirpui-detail-header {{ cls }}">{% if eyebrow %}<p class="chirpui-detail-header__eyebrow">{{ eyebrow }}</p>{% end %}<h1 class="chirpui-detail-header__title">{{ title }}</h1>{% if summary %}<p class="chirpui-detail-header__summary">{{ summary }}</p>{% end %}<div class="chirpui-detail-header__badges">{% slot badges %}</div><div class="chirpui-detail-header__meta">{% slot meta %}</div></header>{% end %}
    """,
    )
    _write_text(
        components / "profile_header.html",
        """
        {% def profile_header(name=none, cover_url=none, href=none, cls="", use_slots=false) %}<header class="chirpui-profile-header {{ cls }}">{% if name %}<h1 class="chirpui-profile-header__name">{{ name }}</h1>{% end %}<div class="chirpui-profile-header__bio">{% slot bio %}</div><div class="chirpui-profile-header__stats">{% slot stats %}</div><div class="chirpui-profile-header__action">{% slot actions %}</div>{% slot %}</header>{% end %}
    """,
    )
    _write_text(
        components / "panel.html",
        """
        {% def panel(title=none, subtitle=none, surface_variant="muted", scroll_body=false, cls="") %}<section class="chirpui-surface chirpui-panel {{ cls }}">{% if title %}<header class="chirpui-panel__header"><h2 class="chirpui-panel__title">{{ title }}</h2></header>{% end %}<div class="chirpui-panel__body">{% slot %}</div><footer class="chirpui-panel__footer">{% slot footer %}</footer></section>{% end %}
    """,
    )
    _write_text(
        components / "index_card.html",
        """
        {% def index_card(href, title, description=none, badge=none, cls="") %}<a href="{{ href }}" class="chirpui-index-card {{ cls }}">{% if badge %}<span class="chirpui-index-card__badge">{{ badge }}</span>{% end %}<span class="chirpui-index-card__title">{{ title }}</span>{% if description %}<p class="chirpui-index-card__description">{{ description }}</p>{% end %}</a>{% end %}
    """,
    )
    _write_text(
        components / "badge.html",
        """
        {% def badge(text, variant="primary", icon=none, cls="") %}<span class="chirpui-badge chirpui-badge--{{ variant }}"><span class="chirpui-badge__text">{{ text }}</span></span>{% end %}
    """,
    )
    _write_text(
        components / "breadcrumbs.html",
        """
        {% def breadcrumbs(items, cls="") %}<nav class="chirpui-breadcrumbs"><ol>{% for item in items %}<li>{% if item.get("href") %}<a href="{{ item.href }}">{{ item.label }}</a>{% else %}<span>{{ item.label }}</span>{% end %}</li>{% end %}</ol></nav>{% end %}
    """,
    )
    _write_text(
        components / "sidebar.html",
        """
        {% def sidebar(cls="") %}<nav class="chirpui-sidebar {{ cls }}"><div class="chirpui-sidebar__header">{% slot header %}</div><div class="chirpui-sidebar__nav">{% slot %}</div></nav>{% end %}
        {% def sidebar_section(title="", collapsible=false, cls="") %}<div class="chirpui-sidebar__section"><div class="chirpui-sidebar__section-links">{% slot %}</div></div>{% end %}
        {% def sidebar_link(href, label, icon="", active=false, boost=true, cls="") %}<a class="chirpui-sidebar__link{{ ' chirpui-sidebar__link--active' if active else '' }}" href="{{ href }}"><span class="chirpui-sidebar__label">{{ label }}</span></a>{% end %}
    """,
    )
    _write_text(
        components / "empty.html",
        """
        {% def empty_state(icon=none, title="No items", illustration=none, action_label=none, action_href=none, code=none, suggestions=none, search_hint=none, cls="") %}<div class="chirpui-empty-state"><h2>{{ title }}</h2>{% slot %}{% if action_label and action_href %}<a href="{{ action_href }}">{{ action_label }}</a>{% end %}</div>{% end %}
    """,
    )
    _write_text(
        components / "rendered_content.html",
        """
        {% def rendered_content(compact=false, cls="") %}<div class="chirpui-rendered-content {{ cls }}">{% slot %}</div>{% end %}
    """,
    )
    _write_text(
        components / "nav_progress.html",
        """
        {% def nav_progress(cls="") %}<div class="chirpui-nav-progress {{ cls }}" aria-hidden="true"></div>{% end %}
    """,
    )
    _write_text(
        components / "site_shell.html",
        """
        {% def site_shell(ambient=false, cls="") %}<div class="chirpui-site-shell {{ cls }}"><div class="chirpui-site-shell__header">{% slot header %}</div><div class="chirpui-site-shell__main">{% slot %}</div><div class="chirpui-site-shell__footer">{% slot footer %}</div></div>{% end %}
    """,
    )
    _write_text(
        components / "nav_tree.html",
        """
        {% def nav_tree(items, show_icons=false, branch_mode="disclosure", cls="") %}
        <nav class="chirpui-nav-tree{% if branch_mode == "linked" %} chirpui-nav-tree--linked-branches{% end %} {{ cls }}" aria-label="Navigation"><div class="chirpui-nav-tree__header">{% slot header %}</div><ul class="chirpui-nav-tree__list">{% for item in items %}<li class="chirpui-nav-tree__item{% if item.get("active") %} chirpui-nav-tree__item--active{% end %}{% if item.get("open") %} chirpui-nav-tree__item--open{% end %}">{% if item.get("href") %}<a href="{{ item.href }}" class="chirpui-nav-tree__link{% if item.get("children") | length == 0 %} chirpui-nav-tree__link--leaf{% end %}{% if item.get("active") %} chirpui-nav-tree__link--active{% end %}"{% if item.get("active") %} aria-current="page"{% end %}><span class="chirpui-nav-tree__title">{{ item.title }}</span></a>{% else %}<span class="chirpui-nav-tree__text">{{ item.title }}</span>{% end %}{% if item.get("open") and item.get("children") %}{{ nav_tree_items(item.children) }}{% end %}</li>{% end %}</ul></nav>
        {% end %}
        {% def nav_tree_items(items) %}<ul class="chirpui-nav-tree__list chirpui-nav-tree__list--nested">{% for item in items %}<li class="chirpui-nav-tree__item chirpui-nav-tree__item--child{% if item.get("active") %} chirpui-nav-tree__item--active{% end %}{% if item.get("open") %} chirpui-nav-tree__item--open{% end %}"><a href="{{ item.href }}" class="chirpui-nav-tree__link chirpui-nav-tree__link--leaf{% if item.get("active") %} chirpui-nav-tree__link--active{% end %}"{% if item.get("active") %} aria-current="page"{% end %}><span class="chirpui-nav-tree__title">{{ item.title }}</span></a>{% if item.get("open") and item.get("children") %}{{ nav_tree_items(item.children) }}{% end %}</li>{% end %}</ul>{% end %}
    """,
    )
    _write_text(
        components / "drawer.html",
        """
        {% def drawer(id, title=none, side="right", cls="") %}<dialog id="{{ id }}" class="chirpui-drawer chirpui-drawer--{{ side }} {{ cls }}"><div class="chirpui-drawer__panel">{% if title %}<header class="chirpui-drawer__header"><h2 class="chirpui-drawer__title">{{ title }}</h2><form method="dialog"><button class="chirpui-drawer__close" aria-label="Close">&times;</button></form></header>{% end %}<div class="chirpui-drawer__body">{% slot %}</div></div></dialog>{% end %}
    """,
    )
    _write_text(
        components / "site_footer.html",
        """
        {% def site_footer(layout="columns", cls="") %}<footer class="chirpui-site-footer chirpui-site-footer--{{ layout }} {{ cls }}"><div class="chirpui-site-footer__brand">{% slot brand %}</div>{% slot %}<div class="chirpui-site-footer__colophon">{% slot colophon %}</div></footer>{% end %}
        {% def footer_column(title="", cls="") %}<div class="chirpui-site-footer__column {{ cls }}">{% if title %}<h3>{{ title }}</h3>{% end %}<ul>{% slot %}</ul></div>{% end %}
        {% def footer_link(href, label, glyph="", external=false, cls="") %}<li><a class="chirpui-site-footer__link {{ cls }}" href="{{ href }}">{{ label }}</a></li>{% end %}
    """,
    )
    _write_text(
        components / "metric_grid.html",
        """
        {% def metric_grid(cols=3, gap="md", cls="") %}<div class="chirpui-metric-grid {{ cls }}">{% slot %}</div>{% end %}
        {% def metric_card(value, label, icon=none, trend=none, hint=none, href=none, cls="") %}{% if href %}<a href="{{ href }}" class="chirpui-card chirpui-metric-card {{ cls }}"><span class="chirpui-stat__value">{{ value }}</span><span class="chirpui-stat__label">{{ label }}</span></a>{% else %}<div class="chirpui-card chirpui-metric-card {{ cls }}"><span class="chirpui-stat__value">{{ value }}</span><span class="chirpui-stat__label">{{ label }}</span></div>{% end %}{% end %}
    """,
    )
    _write_text(
        components / "post_card.html",
        """
        {% def post_card(name=none, handle=none, time=none, href=none, cls="") %}<article class="chirpui-post-card {{ cls }}">{% if href %}<a class="chirpui-post-card__name" href="{{ href }}">{{ name }}</a>{% else %}<span class="chirpui-post-card__name">{{ name }}</span>{% end %}<div class="chirpui-post-card__body">{% slot %}</div><footer class="chirpui-post-card__actions">{% slot actions %}</footer></article>{% end %}
    """,
    )
    _write_text(
        components / "search_header.html",
        """
        {% def search_header(title, form_action, query="", search_name="q", subtitle=none, meta=none, breadcrumb_items=none, form_method="get", form_attrs="", form_attrs_map=none, search_placeholder="Search...", button_label="Search", button_icon="search", surface_variant="muted", density="md", wrap="wrap", sticky=false, cls="") %}<div class="chirpui-search-header {{ cls }}"><h1>{{ title }}</h1>{% if subtitle %}<p>{{ subtitle }}</p>{% end %}<form action="{{ form_action }}" method="{{ form_method }}"><input id="{{ search_name }}" name="{{ search_name }}" type="search" value="{{ query }}" placeholder="{{ search_placeholder }}"><button type="submit">{{ button_label }}</button></form>{% slot %}</div>{% end %}
    """,
    )
    _write_text(
        components / "resource_index.html",
        """
        {% from "chirpui/search_header.html" import search_header %}
        {% from "chirpui/empty.html" import empty_state %}
        {% def resource_index(title, search_action, query="", subtitle=none, search_name="q", search_placeholder="Search...", button_label="Search", button_icon="search", search_method="get", filter_action=none, filter_method="get", filter_surface_variant="default", filter_density="sm", filter_label=none, filter_state_name=none, filter_state_value=none, selected_count=0, selected_label="filters selected", selected_aria_label=none, results_title=none, results_subtitle=none, results_layout="stack", results_cols=2, results_gap="md", has_results=true, empty_title="No results found", empty_icon="search", empty_hint=none, empty_message=none, mutation_result_id=none, cls="") %}
        <section class="chirpui-resource-index {{ cls }}">{{ search_header(title, search_action, query=query, search_name=search_name, subtitle=subtitle, search_placeholder=search_placeholder, button_label=button_label, button_icon=button_icon) }}{% if results_title %}<h2>{{ results_title }}</h2>{% end %}{% if has_results %}<div class="chirpui-resource-index__results">{% slot %}</div>{% else %}{{ empty_state(title=empty_title, icon=empty_icon) }}{% end %}</section>
        {% end %}
    """,
    )
    _write_text(
        components / "timeline.html",
        """
        {% def timeline(items=none, cls="") %}<div class="chirpui-timeline {{ cls }}">{% slot %}</div>{% end %}
        {% def timeline_item(title, date, content=none, cls="") %}<div class="chirpui-timeline__item {{ cls }}"><span class="chirpui-timeline__title">{{ title }}</span><span class="chirpui-timeline__date">{{ date }}</span><div class="chirpui-timeline__body">{% slot content %}</div></div>{% end %}
    """,
    )
    _write_text(
        components / "callout.html",
        """
        {% def callout(variant="info", title=none, icon=none, cls="") %}<aside class="chirpui-callout chirpui-callout--{{ variant }} {{ cls }}">{% if title %}<h3>{{ title }}</h3>{% end %}<div class="chirpui-callout__body">{% slot %}</div></aside>{% end %}
    """,
    )
    _write_text(
        components / "status.html",
        """
        {% def status_indicator(label, variant="default", icon=none, pulse=false, cls="") %}<span class="chirpui-status-indicator chirpui-status-indicator--{{ variant }} {{ cls }}">{{ label }}</span>{% end %}
    """,
    )


def _local_css_js_asset_paths(html: str, baseurl: str) -> set[str]:
    paths: set[str] = set()
    base_prefix = f"{baseurl.rstrip('/')}/" if baseurl else "/"
    for raw_url in LOCAL_CSS_JS_RE.findall(html):
        parsed = urlparse(raw_url)
        if parsed.scheme or parsed.netloc:
            continue
        path = parsed.path
        if not path.startswith("/"):
            path = f"/{path}"
        if base_prefix != "/" and path.startswith(base_prefix):
            path = "/" + path[len(base_prefix) :]
        if path.startswith("/assets/"):
            paths.add(path.lstrip("/"))
    return paths


def _local_css_js_asset_paths_for_output(output_dir: Path, baseurl: str) -> set[str]:
    paths: set[str] = set()
    for html_path in output_dir.rglob("*.html"):
        paths.update(_local_css_js_asset_paths(html_path.read_text(encoding="utf-8"), baseurl))
    return paths


async def _asgi_get(app, path: str) -> tuple[int, bytes]:
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(
        {"type": "http", "method": "GET", "path": path, "headers": []},
        receive,
        send,
    )
    status = 0
    body_parts: list[bytes] = []
    for message in messages:
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            body_parts.append(message.get("body", b""))
    return status, b"".join(body_parts)


def test_chirpui_theme_delegates_library_assets_to_contract() -> None:
    """The bundled theme should not hard-code Chirp UI browser asset paths."""
    theme_dir = ROOT.parent / "bengal" / "themes" / "chirpui"
    template_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (theme_dir / "templates").rglob("*.html")
    )
    bridge_css = (theme_dir / "assets" / "css" / "style.css").read_text(encoding="utf-8")

    assert template_text.count("library_asset_tags()") == 1
    assert "chirpui.css" not in template_text
    assert "chirpui-transitions.css" not in template_text
    assert "chirpui.js" not in template_text
    assert "@import" not in bridge_css


def test_chirpui_theme_builds_with_provider_assets(tmp_path, monkeypatch) -> None:
    """The bundled chirpui theme renders without default assets when chirp_ui is present."""
    package_root = tmp_path / "pkg"
    _write_fake_chirp_ui(package_root)
    sys.modules.pop("chirp_ui", None)
    monkeypatch.syspath_prepend(str(package_root))

    site_root = tmp_path / "site"
    shutil.copytree(ROOT / "roots" / "test-chirpui-theme", site_root)

    site = Site.from_config(site_root)
    site.build(BuildOptions(incremental=False, quiet=True))

    index_html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    docs_index_html = (site.output_dir / "docs" / "index.html").read_text(encoding="utf-8")
    getting_started_html = (site.output_dir / "docs" / "getting-started" / "index.html").read_text(
        encoding="utf-8"
    )
    guide_html = (site.output_dir / "docs" / "guide" / "index.html").read_text(encoding="utf-8")
    quickstart_html = (
        site.output_dir / "docs" / "getting-started" / "quickstart" / "index.html"
    ).read_text(encoding="utf-8")
    author_html = (site.output_dir / "authors" / "jane" / "index.html").read_text(encoding="utf-8")
    blog_index_html = (site.output_dir / "blog" / "index.html").read_text(encoding="utf-8")
    blog_html = (site.output_dir / "blog" / "launch" / "index.html").read_text(encoding="utf-8")
    archive_html = (site.output_dir / "history" / "index.html").read_text(encoding="utf-8")
    search_html = (site.output_dir / "search" / "index.html").read_text(encoding="utf-8")
    changelog_html = (site.output_dir / "changelog" / "index.html").read_text(encoding="utf-8")
    release_html = (site.output_dir / "changelog" / "v0-1" / "index.html").read_text(
        encoding="utf-8"
    )
    manifest = AssetManifest.load(site.output_dir / "asset-manifest.json")
    for html_path in site.output_dir.rglob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        assert "Build Error" not in html, html_path
        assert "header-appshell" not in html, html_path
        assert "bengal-enhance" not in html, html_path
        assert "data-chirpui-style-cycle" not in html, html_path

    assert "Build Error" not in index_html
    assert "chirpui-site-shell" in index_html
    assert "chirpui-navbar" in index_html
    assert "chirpui-hero" in index_html
    assert "chirpui-metric-card" in index_html
    assert "chirpui-rendered-content" in index_html

    assert "chirpui-bengal-docs" in guide_html
    assert "chirpui-document-header" in guide_html
    assert "chirpui-rendered-content" in guide_html
    assert "chirpui-panel" in guide_html
    assert "chirpui-document-header" in getting_started_html
    assert "chirpui-rendered-content" in getting_started_html
    assert "chirpui-rendered-content" in docs_index_html
    assert "chirpui-rendered-content" in quickstart_html
    assert "chirpui-nav-tree chirpui-nav-tree--linked-branches" in guide_html
    assert "chirpui-drawer chirpui-drawer--left" in guide_html
    assert 'data-chirpui-drawer-open="chirpui-docs-nav-drawer"' in guide_html
    assert "chirpui-nav-tree__link--active" in guide_html
    assert 'href="/preview/docs/getting-started/quickstart/"' in quickstart_html
    assert "chirpui-nav-tree__list--nested" in quickstart_html
    assert "chirpui-dropdown__item--active" in quickstart_html
    assert 'href="/preview/docs/"' in index_html
    assert "/preview/assets/chirp_ui/chirpui." in guide_html
    assert "/preview/assets/chirp_ui/chirpui." in index_html
    assert re.search(r"/preview/assets/chirp_ui/chirpui\.[0-9a-f]+\.js", index_html)
    assert "/preview/assets/js/chirpui-bengal." in guide_html
    assert "chirpui-rendered-content" in blog_html
    assert "chirpui-prose" not in blog_html
    assert "chirpui-detail-header" in blog_html
    assert "chirpui-post-card" in blog_index_html
    assert "chirpui-resource-index" in blog_index_html
    assert "chirpui-rendered-content" in blog_index_html
    assert "data-chirpui-search-item" in blog_index_html
    assert "chirpui-profile-header" in author_html
    assert "chirpui-resource-index" in archive_html
    assert "chirpui-search-header" in search_html
    assert "chirpui-resource-index" in search_html
    assert "data-chirpui-search-item" in search_html
    assert "data-chirpui-search-group" in search_html
    assert 'data-search-type="doc"' in search_html
    assert 'data-search-group="page"' in search_html
    assert 'data-search-group=""' not in search_html
    assert "chirpui-timeline" in changelog_html
    assert "chirpui-rendered-content" in changelog_html
    assert "chirpui-callout" in release_html
    assert "chirpui-detail-header" in release_html
    assert "chirpui-rendered-content" in release_html

    assert manifest is not None
    css_entry = manifest.get("chirp_ui/chirpui.css")
    assert css_entry is not None
    css_output = site.output_dir / css_entry.output_path
    assert css_output.exists()
    assert "chirpui-transition" in css_output.read_text(encoding="utf-8")
    assert css_entry.provenance == {
        "kind": "theme_library",
        "package": "chirp_ui",
        "mode": "bundle",
        "sources": ["chirpui.css", "chirpui-transitions.css"],
    }
    js_entry = manifest.get("chirp_ui/chirpui.js")
    assert js_entry is not None
    assert js_entry.provenance == {
        "kind": "theme_library",
        "package": "chirp_ui",
        "mode": "link",
        "sources": ["chirpui.js"],
    }
    assert manifest.get("chirp_ui/chirpui-transitions.css") is None
    assert manifest.get("chirp_ui/unused.css") is None
    assert manifest.get("chirp_ui/chirpui/navbar.html") is None

    asset_paths = _local_css_js_asset_paths_for_output(site.output_dir, site.baseurl)
    assert asset_paths, "Chirp UI pages should reference local CSS/JS assets"
    missing_assets = sorted(path for path in asset_paths if not (site.output_dir / path).exists())
    assert not missing_assets, f"Local CSS/JS asset URLs should be serveable: {missing_assets}"


def test_chirpui_provider_assets_are_serveable_at_dev_urls(tmp_path, monkeypatch) -> None:
    """Declared library assets resolve to stable dev URLs and server routes."""
    package_root = tmp_path / "pkg"
    _write_fake_chirp_ui(package_root)
    sys.modules.pop("chirp_ui", None)
    monkeypatch.syspath_prepend(str(package_root))

    site_root = tmp_path / "site"
    shutil.copytree(ROOT / "roots" / "test-chirpui-theme", site_root)

    site = Site.from_config(site_root)
    site.config["baseurl"] = ""
    site.config.setdefault("site", {})["baseurl"] = ""
    site.config["fingerprint_assets"] = False
    site.config["minify_assets"] = False
    site.dev_mode = True
    site.build(BuildOptions(incremental=False, quiet=True))

    index_html = (site.output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="/assets/chirp_ui/chirpui.css"' in index_html
    assert 'src="/assets/chirp_ui/chirpui.js"' in index_html

    asset_paths = _local_css_js_asset_paths_for_output(site.output_dir, site.baseurl)
    assert "assets/chirp_ui/chirpui.css" in asset_paths
    assert "assets/chirp_ui/chirpui.js" in asset_paths

    app = create_bengal_dev_app(
        output_dir=site.output_dir,
        build_in_progress=lambda: False,
    )
    for path in sorted(asset_paths):
        status, body = asyncio.run(_asgi_get(app, f"/{path}"))
        assert status == 200, path
        assert body, path

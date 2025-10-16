"""
Component preview server utilities.

Discovers component manifests and renders template partials with demo contexts.

Manifest format (YAML):

name: "Card"
template: "partials/card.html"
variants:
  - id: "default"
    name: "Default"
    context:
      title: "Hello"
"""

from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class ComponentPreviewServer:
    def __init__(self, site: Site) -> None:
        self.site = site

    def discover_components(self) -> list[dict[str, Any]]:
        dirs = self._component_manifest_dirs()
        logger.debug(
            "component_discovery_start", manifest_dirs=len(dirs), paths=[str(d) for d in dirs]
        )

        manifests = []
        for base in dirs:
            found_count = 0
            for yml in base.glob("*.yaml"):
                try:
                    # Support multi-document YAML files (separated by ---)
                    content = yml.read_text(encoding="utf-8")
                    documents = list(yaml.safe_load_all(content))

                    for data in documents:
                        data = data or {}
                        if not isinstance(data, dict):
                            continue

                        # Handle both 'template' and 'macro' based components
                        has_template = data.get("template")
                        has_macro = data.get("macro")

                        if has_template or has_macro:
                            # Use explicit id or derive from filename
                            comp_id = data.get("id") or yml.stem
                            data["id"] = comp_id
                            data["manifest_path"] = str(yml)

                            # Normalize variants
                            variants = data.get("variants", [])
                            if isinstance(variants, list):
                                for v in variants:
                                    v.setdefault(
                                        "id", v.get("name", "default").lower().replace(" ", "-")
                                    )
                            data["variants"] = variants
                            # Ensure 'component' key exists for tests expecting it
                            data.setdefault("component", data.get("component") or "unknown")
                            manifests.append(data)
                            found_count += 1
                            logger.debug(
                                "component_manifest_loaded",
                                component_id=comp_id,
                                template=data.get("template"),
                                macro=data.get("macro"),
                                variant_count=len(variants),
                                path=str(yml),
                            )
                        elif not (has_template or has_macro):
                            logger.debug(
                                "component_manifest_no_template_or_macro",
                                file=str(yml),
                                has_data=bool(data),
                            )
                except Exception as e:
                    logger.warning(
                        "component_manifest_load_failed",
                        file=str(yml),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            # Also support simple JS component manifests (Button.jsx)
            for js in base.glob("*.jsx"):
                try:
                    txt = js.read_text(encoding="utf-8")
                    # naive extraction of name and component fields
                    import re

                    name_match = re.search(r'name\s*:\s*"([^"]+)"', txt)
                    comp_match = re.search(r'component\s*:\s*"([^"]+)"', txt)
                    if name_match or comp_match:
                        comp_id = js.stem
                        manifests.append(
                            {
                                "id": comp_id,
                                "name": name_match.group(1) if name_match else comp_id,
                                "component": comp_match.group(1) if comp_match else "unknown",
                                "manifest_path": str(js),
                            }
                        )
                        found_count += 1
                        logger.debug(
                            "component_js_manifest_loaded",
                            component_id=comp_id,
                            path=str(js),
                        )
                except Exception as e:
                    logger.debug("component_js_manifest_parse_failed", file=str(js), error=str(e))

            if found_count > 0:
                logger.debug(
                    "component_discovery_dir_complete", directory=str(base), found=found_count
                )

        # De-duplicate by id. We rely on _component_manifest_dirs() ordering to put
        # child theme directories before parents so the first wins (child overrides parent).
        dedup: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        override_count = 0
        for m in manifests:
            cid = m.get("id")
            if cid in dedup:
                override_count += 1
                logger.info(
                    "component_override",
                    component_id=cid,
                    old_path=dedup[cid].get("manifest_path"),
                    new_path=m.get("manifest_path"),
                )
                # Keep the first (child theme) and ignore later duplicates
            else:
                dedup[cid] = m
                order.append(cid)

        result = [dedup[cid] for cid in order]
        logger.info(
            "component_discovery_complete", total_components=len(result), overrides=override_count
        )
        return result

    def render_component(self, template_rel: str, context: dict[str, Any]) -> str:
        logger.debug(
            "component_render_start",
            template=template_rel,
            context_keys=list(context.keys()) if context else [],
        )

        try:
            from bengal.rendering.template_engine import TemplateEngine

            engine = TemplateEngine(self.site)
            ctx_in: dict[str, Any] = dict(context or {})

            # Common alias: if sample uses 'page' but template expects 'article'
            if "page" in ctx_in and "article" not in ctx_in:
                ctx_in["article"] = ctx_in["page"]
                logger.debug("component_context_alias", aliased="page → article")

            # Render template as a standalone fragment
            # Provide site and config via engine.render context
            html = engine.render(template_rel, {"site": self.site, **ctx_in})

            # Get fingerprinted CSS URL (e.g., style.14d56f49.css)
            css_url = engine._asset_url("css/style.css")
            logger.debug(
                "component_render_success",
                template=template_rel,
                css_url=css_url,
                html_size=len(html),
            )

            # Wrap with minimal shell for isolation
            return f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Component Preview</title>
<link rel=\"stylesheet\" href=\"{css_url}\"></head><body>
<div class=\"component-preview\">{html}</div>
</body></html>"""
        except Exception as e:
            logger.error(
                "component_render_failed",
                template=template_rel,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def list_page(self, base_path: str = "/__bengal_components__/") -> str:
        comps = self.discover_components()
        items = []
        for c in comps:
            name = c.get("name") or c.get("id")
            link = f"{base_path}view?c={urllib.parse.quote(c.get('id'))}"
            vcount = len(c.get("variants", []))
            items.append(
                f'<li><a href="{link}">{name}</a> <span class="dim">({vcount} variants)</span></li>'
            )
        items_html = "".join(items) if items else '<li class="dim">No components found</li>'
        return f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>Components</title>
<style>body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;padding:1.5rem}} .dim{{color:#6b7280}}</style>
<h1>Components</h1>
<ul>{items_html}</ul>
</head><body></body></html>"""

    def view_page(self, comp_id: str, variant_id: str | None) -> str:
        logger.debug("component_view_request", component_id=comp_id, variant_id=variant_id)

        comps = {c.get("id"): c for c in self.discover_components()}
        comp = comps.get(comp_id)

        if not comp:
            logger.warning(
                "component_not_found", component_id=comp_id, available=list(comps.keys())
            )
            return f"<h1>Not found</h1><p>Component '{comp_id}' not found.</p>"

        variants = comp.get("variants", [])

        if variant_id:
            variant = next((v for v in variants if v.get("id") == variant_id), None)
            if not variant:
                logger.warning(
                    "component_variant_not_found",
                    component_id=comp_id,
                    variant_id=variant_id,
                    available_variants=[v.get("id") for v in variants],
                )
            ctx = (variant or {}).get("context", {})
            logger.info(
                "component_view_variant",
                component_id=comp_id,
                variant_id=variant_id,
                template=comp.get("template"),
            )
            return self.render_component(comp.get("template"), ctx)

        # Render a gallery of variants on one page
        logger.info(
            "component_view_all_variants",
            component_id=comp_id,
            variant_count=len(variants),
            template=comp.get("template"),
        )
        sections = []
        for v in variants or [{"id": "default", "name": "Default", "context": {}}]:
            html = self.render_component(comp.get("template"), v.get("context", {}))
            sections.append(f"<section><h2>{v.get('name', v.get('id'))}</h2>{html}</section>")
        return "".join(sections)

    def _component_manifest_dirs(self) -> list[Path]:
        # Child first then parents (reuse template engine ordering by reading theme.toml)
        dirs: list[Path] = []
        try:
            from bengal.rendering.template_engine import TemplateEngine

            engine = TemplateEngine(self.site)
            chain = engine._resolve_theme_chain(self.site.theme)
            logger.debug("component_theme_chain_resolved", chain=chain)
        except Exception as e:
            logger.warning(
                "component_theme_chain_resolution_failed",
                theme=self.site.theme,
                error=str(e),
                fallback="attempting_dir_scan",
            )
            chain = []

        # If no chain from engine, infer from theme.toml extends in site themes
        if not chain:
            themes_root = self.site.root_path / "themes"
            if themes_root.exists():
                try:
                    import tomllib
                except Exception:
                    tomllib = None  # py<3.11 users won't hit this in tests

                extends_map: dict[str, str | None] = {}
                for d in sorted(p for p in themes_root.iterdir() if p.is_dir()):
                    slug = d.name
                    extends = None
                    tt = d / "theme.toml"
                    if tomllib and tt.exists():
                        try:
                            data = tomllib.loads(tt.read_text(encoding="utf-8"))
                            extends = data.get("extends")
                        except Exception:
                            extends = None
                    extends_map[slug] = extends

                # Prefer a child if any declares extends
                child = next((k for k, v in extends_map.items() if v), None)
                if child and extends_map[child]:
                    chain = [child, extends_map[child]]
                else:
                    chain = list(extends_map.keys())

        # Ensure active theme is included (including 'default')
        if (not chain) and self.site.theme:
            chain = [self.site.theme]
        # Always include default as a fallback for component manifests
        if "default" not in chain:
            chain.append("default")

        for theme_name in chain:
            site_dir = self.site.root_path / "themes" / theme_name / "dev" / "components"
            if site_dir.exists():
                dirs.append(site_dir)
                logger.debug(
                    "component_manifest_dir_found",
                    type="site",
                    theme=theme_name,
                    path=str(site_dir),
                )

            # installed theme support
            try:
                from bengal.utils.theme_registry import get_theme_package

                pkg = get_theme_package(theme_name)
                if pkg:
                    resolved = pkg.resolve_resource_path("dev/components")
                    if resolved and resolved.exists():
                        dirs.append(resolved)
                        logger.debug(
                            "component_manifest_dir_found",
                            type="installed",
                            theme=theme_name,
                            path=str(resolved),
                        )
            except Exception as e:
                logger.debug(
                    "component_installed_theme_check_failed",
                    theme=theme_name,
                    error=str(e),
                )

            # bundled theme support (optional)
            try:
                import bengal

                bundled = (
                    Path(bengal.__file__).parent / "themes" / theme_name / "dev" / "components"
                )
                if bundled.exists():
                    dirs.append(bundled)
                    logger.debug(
                        "component_manifest_dir_found",
                        type="bundled",
                        theme=theme_name,
                        path=str(bundled),
                    )
            except Exception as e:
                logger.debug("component_bundled_theme_check_failed", theme=theme_name, error=str(e))

        return dirs

    # (No coercion needed; Jinja supports dict attribute/key fallback)


# Backwards-compatible function export for tests
def discover_components(site: Site) -> list[dict[str, Any]]:
    """Discover components using a temporary server instance (compat shim)."""
    return ComponentPreviewServer(site).discover_components()

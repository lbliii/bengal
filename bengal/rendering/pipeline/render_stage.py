"""
Render-stage helpers for the rendering pipeline.

Extracted from core.py so RenderingPipeline stays a coordinator. Behavior is
identical: frozen RenderedPage records, render-time asset tracking, and
markdown variable context still run against the pipeline instance.
"""

from __future__ import annotations

import time as _time
from typing import TYPE_CHECKING, Any, cast

from bengal.cache.parsed_output import apply_parsed_page_to_page, with_parsed_html
from bengal.core.records import (
    ParsedPage,
    parsed_page_from_page_state,
    rendered_page_from_page_state,
)
from bengal.core.section.utils import get_page_section
from bengal.rendering.page_operations import get_content_dependencies
from bengal.rendering.pipeline.output import format_html, write_output
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike
    from bengal.rendering.pipeline.profiler import RenderProfiler

logger = get_logger(__name__)


def enhance_api_docs(pipeline: Any, page: PageLike) -> None:
    """Enhance API documentation with badges."""
    enhancer = pipeline._api_doc_enhancer
    page_type = page.metadata.get("type")
    if enhancer and enhancer.should_enhance(page_type):
        parsed_page = parsed_page_from_page_state(page)
        enhanced = enhancer.enhance(parsed_page.html_content, page_type)
        apply_parsed_page_to_page(
            page,
            with_parsed_html(parsed_page, enhanced),
            seed_counts=False,
            seed_links=False,
            seed_plain_text=False,
        )


def render_and_write(
    pipeline: Any,
    page: PageLike,
    template: str,
    _prof: RenderProfiler | None = None,
    parsed_page: ParsedPage | None = None,
) -> None:
    """Render template and write output.

    RFC: rfc-build-performance-optimizations Phase 2
    Uses render-time asset tracking to avoid post-render HTML parsing.

    RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)
    Optionally records effects for unified dependency tracking.

    Epic: Immutable Page Pipeline, Sprint 2
    Constructs a RenderedPage record after rendering. Passes it to
    write_output so the write phase reads from the immutable record.
    """
    # Allow empty html_content - pages like home pages, section indexes, and
    # taxonomy pages may have no markdown body but should still render
    # (they're driven by template logic and frontmatter, not content)
    if page.html_content is None and parsed_page is None:
        parsed_page = ParsedPage(
            html_content="",
            toc="",
            toc_items=(),
            excerpt="",
            meta_description="",
            plain_text="",
            word_count=0,
            reading_time=0,
            links=(),
        )
        apply_parsed_page_to_page(
            page,
            parsed_page,
            seed_counts=False,
            seed_links=False,
            seed_plain_text=False,
        )

    # Read source HTML from ParsedPage when available (Sprint 1: Immutable Pipeline)
    source_html = parsed_page.html_content if parsed_page else (page.html_content or "")

    # RFC: rfc-build-performance-optimizations Phase 2
    # Track assets during rendering (render-time tracking)
    # RFC: Snapshot-Enabled v2 Opportunities (Effect-Traced Builds)
    # Record render effects if effect tracing is enabled
    from bengal.effects import BuildEffectTracer
    from bengal.rendering.asset_tracking import AssetTracker

    effect_tracer = BuildEffectTracer.get_instance()
    effect_recorder = effect_tracer.record_page_render(
        page,
        template,
        parse_dependencies=frozenset(get_content_dependencies(page)),
    )

    render_start = _time.perf_counter()
    rendered_html = ""

    tracker = AssetTracker()
    with tracker:
        if effect_recorder:
            with effect_recorder:
                if _prof:
                    with _prof.step("render_content"):
                        html_content = pipeline.renderer.render_content(source_html)
                    with _prof.step("render_template"):
                        rendered_html = pipeline.renderer.render_page(
                            page, html_content, parsed_page=parsed_page
                        )
                    with _prof.step("format_html"):
                        rendered_html = format_html(
                            rendered_html, page, cast("SiteLike", pipeline.site)
                        )
                else:
                    html_content = pipeline.renderer.render_content(source_html)
                    rendered_html = pipeline.renderer.render_page(
                        page, html_content, parsed_page=parsed_page
                    )
                    rendered_html = format_html(
                        rendered_html, page, cast("SiteLike", pipeline.site)
                    )
        else:
            if _prof:
                with _prof.step("render_content"):
                    html_content = pipeline.renderer.render_content(source_html)
                with _prof.step("render_template"):
                    rendered_html = pipeline.renderer.render_page(
                        page, html_content, parsed_page=parsed_page
                    )
                with _prof.step("format_html"):
                    rendered_html = format_html(
                        rendered_html, page, cast("SiteLike", pipeline.site)
                    )
            else:
                html_content = pipeline.renderer.render_content(source_html)
                rendered_html = pipeline.renderer.render_page(
                    page, html_content, parsed_page=parsed_page
                )
                rendered_html = format_html(rendered_html, page, cast("SiteLike", pipeline.site))

    render_time_ms = (_time.perf_counter() - render_start) * 1000

    # Get tracked assets from render-time tracking
    tracked_assets = tracker.get_assets()

    page.render_time_ms = render_time_ms

    # Sprint 2: Build immutable RenderedPage record
    rendered_page = rendered_page_from_page_state(
        page,
        rendered_html=rendered_html,
        render_time_ms=render_time_ms,
        dependencies=frozenset(tracked_assets) if tracked_assets else frozenset(),
    )

    # Store rendered output in cache
    if _prof:
        with _prof.step("cache_rendered"):
            pipeline._cache_checker.cache_rendered_output(page, template, rendered_page)
    else:
        pipeline._cache_checker.cache_rendered_output(page, template, rendered_page)

    # Write output (sync or async via write-behind)
    if _prof:
        with _prof.step("write_output"):
            write_output(
                page,
                cast("SiteLike", pipeline.site),
                collector=pipeline._output_collector,
                write_behind=pipeline._write_behind,
                build_cache=pipeline.build_cache,
                rendered_page=rendered_page,
                compare_existing_output=pipeline._compare_existing_output,
            )
    else:
        write_output(
            page,
            cast("SiteLike", pipeline.site),
            collector=pipeline._output_collector,
            write_behind=pipeline._write_behind,
            build_cache=pipeline.build_cache,
            rendered_page=rendered_page,
            compare_existing_output=pipeline._compare_existing_output,
        )

    # Accumulate unified page data during rendering (JSON + search index)
    if _prof:
        with _prof.step("json_accumulate"):
            pipeline._json_accumulator.accumulate_unified_page_data(page)
    else:
        pipeline._json_accumulator.accumulate_unified_page_data(page)

    # RFC: rfc-build-performance-optimizations Phase 2
    # Use render-time tracked assets, fall back to HTML parsing if needed
    if _prof:
        with _prof.step("asset_deps"):
            pipeline._accumulate_asset_deps(
                page, tracked_assets=tracked_assets, rendered_html=rendered_page.rendered_html
            )
    else:
        pipeline._accumulate_asset_deps(
            page, tracked_assets=tracked_assets, rendered_html=rendered_page.rendered_html
        )


def accumulate_asset_deps(
    pipeline: Any,
    page: PageLike,
    tracked_assets: set[str] | None = None,
    rendered_html: str | None = None,
) -> None:
    """
    Accumulate asset dependencies during rendering.

    RFC: rfc-build-performance-optimizations Phase 2
    Uses render-time tracked assets (fast) with fallback to HTML parsing (slow).

    ``pipeline`` may be a RenderingPipeline or a SimpleNamespace used by
    performance tests (getattr for the lazy manifest reverse map).

    Args:
        pipeline: Pipeline or test double with build_context
        page: Page with rendered HTML
        tracked_assets: Assets tracked during render-time (if available)
        rendered_html: Rendered HTML from the immutable render record.
    """
    html = rendered_html if rendered_html is not None else page.rendered_html
    if not pipeline.build_context or not html:
        return

    assets: set[str] = set()

    # RFC: rfc-build-performance-optimizations Phase 2
    # Use render-time tracked assets if available (fast path)
    if tracked_assets:
        assets = tracked_assets
    else:
        # Fallback: parse HTML (slow, but catches assets not using filters)
        try:
            from urllib.parse import urlparse

            from bengal.rendering.asset_extractor import extract_assets_from_html
            from bengal.rendering.assets import get_asset_manifest

            raw_assets = extract_assets_from_html(html)

            # Normalize fingerprinted URLs back to logical paths.
            # When Kida fragment cache hits, asset_url() is not called, so
            # tracked_assets is empty and we fall back to HTML parsing.
            # HTML parsing extracts full fingerprinted URLs like
            # "http://host/assets/css/style.abc123.css", not logical paths
            # like "css/style.css". Use the manifest reverse map to recover
            # the logical path so incremental builds invalidate correctly.
            # Build reverse map once per pipeline instance (lazy, cached).
            # Use getattr so tests can pass a SimpleNamespace as self.
            if not getattr(pipeline, "_manifest_reverse_built", False):
                manifest = get_asset_manifest()
                if manifest and manifest.entries:
                    pipeline._manifest_reverse = {v: k for k, v in manifest.entries.items()}
                pipeline._manifest_reverse_built = True

            if getattr(pipeline, "_manifest_reverse", None) and raw_assets:
                reverse = pipeline._manifest_reverse
                assert reverse is not None  # guarded by truthiness check above
                normalized: set[str] = set()
                for url in raw_assets:
                    path = urlparse(url).path.lstrip("/") if "://" in url else url.lstrip("/")
                    normalized.add(reverse.get(path, url))
                assets = normalized
            else:
                assets = raw_assets
        except Exception as e:
            # Extraction failure should not break render
            # Fallback extraction will handle this page in phase_track_assets
            logger.debug(
                "asset_extraction_failed",
                page=str(page.source_path),
                error=str(e)[:100],
            )

    if assets:
        pipeline.build_context.accumulate_page_assets(page.source_path, assets)


def build_variable_context(pipeline: Any, page: PageLike) -> dict[str, Any]:
    """Build variable context for {{ variable }} substitution in markdown."""
    from bengal.rendering.context import (
        ParamsContext,
        _get_global_contexts,
    )
    from bengal.snapshots.types import NO_SECTION, SectionSnapshot

    section = get_page_section(page)
    metadata = page.metadata if hasattr(page, "metadata") else {}

    # Get snapshot from build_context if available (RFC: rfc-bengal-snapshot-engine)
    snapshot = None
    if pipeline.build_context:
        snapshot = getattr(pipeline.build_context, "snapshot", None)

    # Resolve section to SectionSnapshot (no wrapper needed)
    # PERF: Use BuildContext cached lookup for O(1) instead of O(S) iteration
    section_for_context: SectionSnapshot = NO_SECTION
    if section:
        if pipeline.build_context:
            # O(1) cached lookup via BuildContext
            section_for_context = pipeline.build_context.get_section_snapshot(section)
        elif snapshot:
            # Fallback: O(S) iteration (when no build_context available)
            for sec_snap in snapshot.sections:
                if sec_snap.path == getattr(section, "path", None) or sec_snap.name == getattr(
                    section, "name", ""
                ):
                    section_for_context = sec_snap
                    break

    # Get cached global contexts (site/config are stateless wrappers)
    global_contexts = _get_global_contexts(
        cast("SiteLike", pipeline.site),
        build_context=pipeline.build_context,
    )

    context: dict[str, Any] = {
        # Core objects with cached smart wrappers
        "page": page,
        "site": global_contexts["site"],
        "config": global_contexts["config"],
        # Shortcuts with safe access (per-page, not cached)
        "params": ParamsContext(metadata),
        "meta": ParamsContext(metadata),
        # Section: SectionSnapshot or NO_SECTION sentinel (has params and __bool__)
        "section": section_for_context,
    }

    # Direct frontmatter access for convenience
    if metadata:
        for key, value in metadata.items():
            if key not in context and not key.startswith("_"):
                context[key] = value

    return context

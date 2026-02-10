"""
Fragment-update fast-path service used by the dev server build trigger.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class FragmentFastPathService:
    """Service implementing content/template fragment fast paths."""

    def __init__(
        self,
        site: Any,
        *,
        classify_markdown_change: Callable[
            [Path], tuple[bool, bool, set[str], bool] | None
        ],
        is_content_only_change: Callable[[Path], bool],
        get_template_dirs: Callable[[], list[Path]],
        is_in_template_dir: Callable[[Path, list[Path]], bool],
    ) -> None:
        self.site = site
        self._classify_markdown_change = classify_markdown_change
        self._is_content_only_change = is_content_only_change
        self._get_template_dirs = get_template_dirs
        self._is_in_template_dir = is_in_template_dir

    def try_content_update(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        """Attempt fragment update without a full rebuild."""
        if event_types != {"modified"}:
            return False

        if not all(p.suffix.lower() in (".md", ".markdown") for p in changed_paths):
            return False

        from bengal.server.fragment_update import frontmatter_changes_to_context_paths

        classified_paths: list[
            tuple[Path, bool, bool, set[str], frozenset[str]]
        ] = []  # (path, content_changed, fm_changed, changed_fm_keys, extra_ctx_paths)

        for path in changed_paths:
            result = self._classify_markdown_change(path)
            if result is None:
                if self._is_content_only_change(path):
                    classified_paths.append((path, True, False, set(), frozenset()))
                else:
                    return False
                continue

            content_changed, fm_changed, changed_fm_keys, nav_affecting = result
            if nav_affecting:
                logger.debug(
                    "fragment_fast_path_nav_fm_changed",
                    file=str(path),
                    nav_keys=sorted(changed_fm_keys),
                )
                return False

            if not content_changed and not fm_changed:
                continue

            extra_ctx = frozenset[str]()
            if fm_changed and changed_fm_keys:
                extra_ctx = frontmatter_changes_to_context_paths(changed_fm_keys)
                logger.debug(
                    "fragment_fast_path_fm_change",
                    file=str(path),
                    changed_keys=sorted(changed_fm_keys),
                    context_paths=sorted(extra_ctx),
                )

            classified_paths.append(
                (path, content_changed, fm_changed, changed_fm_keys, extra_ctx)
            )

        if not classified_paths:
            return False

        page_map = self.site.page_by_source_path
        pages_to_update: list[
            tuple[Path, Any, bool, frozenset[str]]
        ] = []  # (path, page, content_changed, extra_ctx_paths)
        for path, content_changed, _fm_changed, _fm_keys, extra_ctx in classified_paths:
            page = page_map.get(path)
            if page is None:
                logger.debug("fragment_fast_path_no_page", file=str(path))
                return False
            pages_to_update.append((path, page, content_changed, extra_ctx))

        from bengal.server.fragment_update import check_cascade_safety

        all_paths = {p for p, _, _, _ in pages_to_update}
        if not check_cascade_safety(self.site, all_paths):
            logger.debug(
                "fragment_fast_path_cascade_detected",
                changed_count=len(all_paths),
            )
            return False

        try:
            from markupsafe import Markup

            from bengal.rendering.context import build_page_context
            from bengal.rendering.engines import create_engine
            from bengal.rendering.pipeline.output import determine_template
            from bengal.rendering.pipeline.thread_local import get_thread_parser
            from bengal.rendering.pipeline.transforms import (
                escape_template_syntax_in_html,
            )
            from bengal.server.fragment_update import (
                diff_content_ast,
                get_affected_blocks,
            )
            from bengal.server.live_reload import send_fragment_payload

            markdown_engine = self.site.config.get("markdown_engine", "patitas")
            parser = get_thread_parser(markdown_engine)
            engine = create_engine(self.site)

            for path, page, content_changed, extra_ctx in pages_to_update:
                source = path.read_text(encoding="utf-8")
                match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", source, flags=re.DOTALL)
                if not match:
                    return False
                body = match.group(2)

                all_changed_ctx: set[str] = set(extra_ctx)
                if content_changed:
                    ast_result = diff_content_ast(path, body, page_ast=getattr(page, "_ast_cache", None))
                    if ast_result is not None:
                        ast_ctx_paths, new_ast = ast_result
                        all_changed_ctx.update(ast_ctx_paths)
                        page._ast_cache = new_ast
                        if not ast_ctx_paths and not extra_ctx:
                            logger.debug("fragment_fast_path_no_change", file=str(path))
                            continue

                if extra_ctx:
                    fm_match = re.match(
                        r"^---\s*\n(.*?)\n---\s*(?:\n|$)",
                        source,
                        flags=re.DOTALL,
                    )
                    if fm_match:
                        try:
                            new_fm = yaml.safe_load(fm_match.group(1)) or {}
                            if isinstance(new_fm, dict):
                                page.metadata.update(new_fm)
                        except yaml.YAMLError as exc:
                            logger.debug(
                                "fragment_fast_path_front_matter_yaml_error",
                                file=str(path),
                                error=str(exc),
                            )

                metadata = dict(page.metadata)
                metadata["_source_path"] = page.source_path
                html_content = parser.parse(body, metadata)
                html_content = escape_template_syntax_in_html(html_content)
                page.html_content = html_content

                context = build_page_context(
                    page=page,
                    site=self.site,
                    content=Markup(html_content),
                    lazy=False,
                )
                template_name = determine_template(page)
                frozen_ctx = (
                    frozenset(all_changed_ctx) if all_changed_ctx else frozenset({"content"})
                )
                blocks_to_render = ["content"]
                affected, meta_available = get_affected_blocks(engine, template_name, frozen_ctx)
                if meta_available and affected:
                    blocks_to_render = list(dict.fromkeys(affected))
                elif meta_available and not affected:
                    logger.debug(
                        "fragment_fast_path_no_blocks_affected",
                        file=str(path),
                        changed_ctx_paths=sorted(frozen_ctx),
                    )
                    continue

                total_html_size = 0
                for block_name in blocks_to_render:
                    rendered = engine.render_fragment(template_name, block_name, context)
                    if rendered is None and block_name == "content":
                        logger.debug(
                            "fragment_fast_path_render_failed",
                            file=str(path),
                            template=template_name,
                            block=block_name,
                        )
                        return False
                    if rendered is not None:
                        total_html_size += len(rendered)
                        send_fragment_payload(block_name, rendered, str(path))

                logger.info(
                    "fragment_fast_path_used",
                    file=str(path.name),
                    template=template_name,
                    blocks=blocks_to_render,
                    html_size=total_html_size,
                    content_changed=content_changed,
                    fm_ctx_paths=sorted(extra_ctx) if extra_ctx else [],
                )

            return True
        except Exception as e:  # noqa: BLE001 - fast path should fail closed
            logger.debug(
                "fragment_fast_path_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def try_template_update(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        """Attempt template fragment update without a full rebuild."""
        if event_types != {"modified"}:
            return False
        if not all(p.suffix.lower() == ".html" for p in changed_paths):
            return False

        template_dirs = self._get_template_dirs()
        if not template_dirs:
            return False
        if not all(self._is_in_template_dir(path, template_dirs) for path in changed_paths):
            return False

        try:
            from markupsafe import Markup

            from bengal.protocols import EngineCapability
            from bengal.rendering.block_cache import BlockCache
            from bengal.rendering.context import build_page_context
            from bengal.rendering.engines import create_engine
            from bengal.rendering.pipeline.output import determine_template
            from bengal.server.live_reload import send_fragment_payload

            engine = create_engine(self.site)
            if not engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION):
                return False

            block_cache = BlockCache()
            all_recompiled: set[str] = set()
            template_names: list[str] = []

            for path in changed_paths:
                tpl_name = path.stem + ".html"
                recompiled = block_cache.recompile_changed_blocks(engine, tpl_name)
                if not recompiled:
                    logger.debug(
                        "template_fragment_no_recompile",
                        template=tpl_name,
                        file=str(path),
                    )
                    return False
                all_recompiled.update(recompiled)
                template_names.append(tpl_name)

            if not all_recompiled:
                return False

            for tpl_name in template_names:
                cacheable = block_cache.analyze_template(engine, tpl_name)
                for block_name in all_recompiled:
                    scope = cacheable.get(block_name, "unknown")
                    if scope != "site":
                        logger.debug(
                            "template_fragment_page_scoped",
                            block=block_name,
                            scope=scope,
                            template=tpl_name,
                        )
                        return False

            page_map = self.site.page_by_source_path
            if not page_map:
                return False
            _representative_path, representative_page = next(iter(page_map.items()))

            html_content = getattr(representative_page, "html_content", "") or ""
            context = build_page_context(
                page=representative_page,
                site=self.site,
                content=Markup(html_content),
                lazy=False,
            )
            template_name = determine_template(representative_page)

            total_html_size = 0
            for block_name in sorted(all_recompiled):
                rendered = engine.render_fragment(template_name, block_name, context)
                if rendered is None:
                    logger.debug(
                        "template_fragment_render_failed",
                        block=block_name,
                        template=template_name,
                    )
                    return False
                total_html_size += len(rendered)
                send_fragment_payload(block_name, rendered, "template-change")

            logger.info(
                "template_fragment_fast_path_used",
                templates=template_names,
                blocks=sorted(all_recompiled),
                html_size=total_html_size,
            )
            return True
        except Exception as e:  # noqa: BLE001 - fast path should fail closed
            logger.debug(
                "template_fragment_fast_path_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

"""
Agent manifest generator for Bengal SSG.

Generates /agent.json — a hierarchical site map for agent navigation.
Unlike index.json (flat search index) or llms.txt (prose), agent.json
provides structured, filterable data for programmatic traversal.

Output Format:
    {
      "site": {"title", "description", "baseurl"},
      "sections": [{"name", "path", "children": [...], "pages": [...]}],
      "formats": {"per_page_json": "/{path}/index.json", ...}
    }

Configuration:
    [output_formats]
    site_wide = ["index_json", "llm_full", "llms_txt", "changelog", "agent_manifest"]

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.llms_txt_generator: Section grouping
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.utils import get_i18n_output_path, get_page_url
from bengal.postprocess.utils import get_section_name
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.section import Section
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


class AgentManifestGenerator:
    """Generate agent.json — hierarchical site map for agents."""

    def __init__(self, site: SiteLike) -> None:
        self.site = site

    def generate(self, pages: list[PageLike]) -> Path:
        """Generate agent.json at site root.

        Args:
            pages: Pre-filtered list of pages (ai_input-permitted)

        Returns:
            Path to agent.json
        """
        output_path = get_i18n_output_path(self.site, "agent.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        page_by_href: dict[str, PageLike] = {
            get_page_url(p, self.site): p for p in pages if p.output_path
        }

        site_info: dict[str, Any] = {
            "title": self.site.title or "Bengal Site",
            "description": getattr(self.site, "description", "") or "",
            "baseurl": self.site.baseurl or "",
        }

        sections_data = self._build_sections(
            getattr(self.site, "sections", []),
            page_by_href,
        )
        root_pages = self._get_root_pages(pages, page_by_href)
        if root_pages:
            sections_data.insert(
                0,
                {
                    "name": "Overview",
                    "path": "/",
                    "children": [],
                    "pages": root_pages,
                },
            )

        of_config = self.site.config.get("output_formats", {})
        site_wide = of_config.get("site_wide", [])
        per_page = of_config.get("per_page", [])

        formats: dict[str, str] = {}
        if "json" in per_page:
            formats["per_page_json"] = "/{path}/index.json"
        if "llm_txt" in per_page:
            formats["per_page_txt"] = "/{path}/index.txt"
        if "changelog" in site_wide:
            formats["changelog"] = "/changelog.json"
        if "llm_full" in site_wide:
            formats["corpus"] = "/llm-full.txt"
        if "llms_txt" in site_wide:
            formats["overview"] = "/llms.txt"

        manifest: dict[str, Any] = {
            "site": site_info,
            "sections": sections_data,
            "formats": formats,
        }

        with AtomicFile(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info("agent_manifest_generated", path=str(output_path))
        return output_path

    def _get_root_pages(
        self,
        pages: list[PageLike],
        page_by_href: dict[str, PageLike],
    ) -> list[dict[str, Any]]:
        """Get pages with no section (root-level)."""
        result: list[dict[str, Any]] = []
        for p in pages:
            if not p.output_path:
                continue
            if get_section_name(p):
                continue
            href = get_page_url(p, self.site)
            if href not in page_by_href:
                continue
            plain = getattr(p, "plain_text", "") or ""
            content_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
            last_mod = self._get_last_modified(p)
            result.append(
                {
                    "title": p.title,
                    "url": href,
                    "type": getattr(p, "type", None) or getattr(p, "kind", "doc"),
                    "description": getattr(p, "description", "") or "",
                    "content_hash": content_hash,
                    "last_modified": last_mod,
                }
            )
        return result

    def _build_sections(
        self,
        sections: list[Section],
        page_by_href: dict[str, PageLike],
    ) -> list[dict[str, Any]]:
        """Recursively build section tree."""
        result: list[dict[str, Any]] = []
        for section in sections:
            path = getattr(section, "href", None) or getattr(section, "_path", None) or ""
            name = getattr(section, "title", None) or getattr(section, "name", "") or ""

            section_pages: list[dict[str, Any]] = []
            for page in getattr(section, "sorted_pages", section.pages):
                href = get_page_url(page, self.site)
                if href not in page_by_href:
                    continue
                p = page_by_href[href]
                plain = getattr(p, "plain_text", "") or ""
                content_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
                last_mod = self._get_last_modified(p)
                section_pages.append(
                    {
                        "title": p.title,
                        "url": href,
                        "type": getattr(p, "type", None) or getattr(p, "kind", "doc"),
                        "description": getattr(p, "description", "") or "",
                        "content_hash": content_hash,
                        "last_modified": last_mod,
                    }
                )

            children = self._build_sections(
                getattr(section, "sorted_subsections", section.subsections),
                page_by_href,
            )

            result.append(
                {
                    "name": name,
                    "path": path,
                    "children": children,
                    "pages": section_pages,
                }
            )
        return result

    def _get_last_modified(self, page: PageLike) -> str | None:
        """Resolve last-modified from frontmatter or mtime."""
        for key in ("lastmod", "last_modified", "updated"):
            val = page.metadata.get(key)
            if val:
                if hasattr(val, "isoformat"):
                    return val.isoformat()
                if isinstance(val, str):
                    return val
        source = getattr(page, "source_path", None)
        if source:
            try:
                mtime = source.stat().st_mtime
                return datetime.fromtimestamp(mtime).isoformat()
            except OSError, ValueError:
                pass
        return None

"""
Site-level llms.txt generator for Bengal SSG.

Generates a curated Markdown overview of the site following the llms.txt
specification (https://llmstxt.org/). Unlike llm-full.txt (which dumps all
content), llms.txt is a navigation aid: a short table of contents that tells
AI agents what the site is and where to find things.

Output Format (per llmstxt.org spec):

    ```markdown
    # Site Title

    > Site description from config.

    ## Getting Started

    - [Installation](/docs/getting-started/installation/): Install and set up your first project
    - [Quick Start](/docs/getting-started/quickstart/): Build and serve a site in 5 minutes

    ## Reference

    - [Configuration](/docs/building/configuration/): Site config and build profiles

    ## Optional

    - [llm-full.txt](/llm-full.txt): Full plain-text content of all pages
    ```

The generator walks the site's section hierarchy and uses page descriptions
from frontmatter to build link annotations. Sections are ordered by weight
(matching the site's navigation order).

Configuration:
Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    site_wide = ["index_json", "llm_full", "llms_txt"]
    ```

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.llm_generator: Site-wide llm-full.txt
- bengal.postprocess.output_formats.txt_generator: Per-page LLM text

"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import get_page_relative_url
from bengal.postprocess.utils import get_section_name
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)

_LLMS_TXT_SPEC_URL = "https://llmstxt.org/"


class SiteLlmsTxtGenerator:
    """Generate llms.txt — a curated site overview for AI agents.

    Walks the site's section hierarchy and produces a short Markdown
    document with an H1 title, blockquote description, and H2 sections
    containing annotated links to key pages.

    Attributes:
        site: Site instance with pages, sections, and configuration.
    """

    def __init__(self, site: SiteLike) -> None:
        self.site = site
        self._logger = get_logger(__name__)

    def generate(self, pages: list[PageLike]) -> Path:
        """Generate llms.txt at the site root.

        Args:
            pages: Pre-filtered list of pages eligible for inclusion
                   (already excludes drafts, hidden, ai_input=false, etc.).

        Returns:
            Path to the generated llms.txt file.
        """
        content = self._render(pages)
        output_path = self.site.output_dir / "llms.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with AtomicFile(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._logger.info("llms_txt_generated", path=str(output_path))
        return output_path

    def _render(self, pages: list[PageLike]) -> str:
        lines: list[str] = []

        title = self.site.title or "Site"
        description = self.site.config.get("description", "")

        lines.append(f"# {title}")
        lines.append("")
        if description:
            lines.append(f"> {description}")
            lines.append("")

        sections = self._group_by_section(pages)

        for section_name, section_pages in sections:
            display_name = self._format_section_name(section_name)
            lines.append(f"## {display_name}")
            lines.append("")
            for page in section_pages:
                url = get_page_relative_url(page, self.site)
                desc = page.description
                if desc:
                    lines.append(f"- [{page.title}]({url}): {desc}")
                else:
                    lines.append(f"- [{page.title}]({url})")
            lines.append("")

        self._append_optional_section(lines)

        return "\n".join(lines)

    def _group_by_section(self, pages: list[PageLike]) -> list[tuple[str, list[PageLike]]]:
        """Group pages by their top-level section, preserving weight order.

        Root-level pages (no section) are collected under a synthetic
        "Overview" group and placed first.
        """
        section_map: dict[str, list[PageLike]] = defaultdict(list)
        root_pages: list[PageLike] = []

        for page in pages:
            if not page.output_path:
                continue
            section_name = get_section_name(page)
            if section_name:
                section_map[section_name].append(page)
            else:
                root_pages.append(page)

        ordered = self._order_sections(section_map)

        result: list[tuple[str, list[PageLike]]] = []
        if root_pages:
            result.append(("Overview", root_pages))
        result.extend(ordered)
        return result

    def _order_sections(
        self, section_map: dict[str, list[PageLike]]
    ) -> list[tuple[str, list[PageLike]]]:
        """Order sections to match the site's navigation structure.

        Uses the site's top-level sections list (which is weight-ordered)
        as the canonical ordering. Sections not in the site hierarchy are
        appended alphabetically.
        """
        known_order: list[str] = []
        for section in getattr(self.site, "sections", []):
            name = getattr(section, "name", "")
            if name:
                known_order.append(name)

        ordered: list[tuple[str, list[PageLike]]] = []
        seen: set[str] = set()

        for name in known_order:
            if name in section_map:
                ordered.append((name, section_map[name]))
                seen.add(name)

        ordered.extend(
            (name, section_map[name]) for name in sorted(section_map.keys()) if name not in seen
        )

        return ordered

    def _format_section_name(self, name: str) -> str:
        """Convert section slug to display name.

        Checks the site's section objects for a proper title first,
        falling back to title-casing the slug.
        """
        for section in getattr(self.site, "sections", []):
            if getattr(section, "name", "") == name:
                section_title = getattr(section, "title", "")
                if section_title and section_title != name:
                    return section_title
        return name.replace("-", " ").replace("_", " ").title()

    def _append_optional_section(self, lines: list[str]) -> None:
        """Append an Optional section with links to machine-readable formats."""
        site_wide = self.site.config.get("output_formats", {}).get("site_wide", [])
        baseurl = self.site.baseurl or ""
        has_optional = False

        optional_lines: list[str] = []
        if "llm_full" in site_wide:
            optional_lines.append(
                f"- [llm-full.txt]({baseurl}/llm-full.txt): Full plain-text content of all pages"
            )
            has_optional = True
        if "index_json" in site_wide:
            optional_lines.append(
                f"- [index.json]({baseurl}/index.json): "
                f"Search index with page metadata and excerpts"
            )
            has_optional = True

        cs_config = self.site.config.get("content_signals", {})
        if cs_config.get("enabled", True):
            optional_lines.append(
                f"- [robots.txt]({baseurl}/robots.txt): Content Signals directives for AI crawlers"
            )
            has_optional = True

        if has_optional:
            lines.append("## Optional")
            lines.append("")
            lines.extend(optional_lines)
            lines.append("")

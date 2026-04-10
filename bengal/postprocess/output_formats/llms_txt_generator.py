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

    - [Installation](/bengal/docs/getting-started/installation/): Install and set up your first project
    - [Quick Start](/bengal/docs/getting-started/quickstart/): Build and serve a site in 5 minutes

    ## Reference

    - [Configuration](/bengal/docs/building/configuration/): Site config and build profiles

    ## Optional

    - [llm-full.txt](/bengal/llm-full.txt): Full plain-text content of all pages
    ```

The generator walks the site's section hierarchy and uses page descriptions
from frontmatter to build link annotations. Sections are ordered by weight
(matching the site's navigation order).

Filtering:
Pages are filtered to keep the file under the 100K character threshold
required by most AI agents. Virtual pages (taxonomy terms, tag listings)
are excluded. A configurable max_pages cap limits the total entries, and
a max_chars cap triggers graceful truncation with a pointer to llm-full.txt.

Configuration:
Controlled via [output_formats] in bengal.toml:

    ```toml
    [output_formats]
    site_wide = ["index_json", "llm_full", "llms_txt"]

    [output_formats.options]
    llms_txt_max_pages = 100
    llms_txt_max_chars = 80000
    ```

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.llm_generator: Site-wide llm-full.txt
- bengal.postprocess.output_formats.txt_generator: Per-page LLM text

"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from bengal.postprocess.output_formats.utils import get_page_url
from bengal.postprocess.utils import get_section_name
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)

_LLMS_TXT_SPEC_URL = "https://llmstxt.org/"

# Default limits to keep llms.txt under the 100K agent threshold
_DEFAULT_MAX_PAGES = 100
_DEFAULT_MAX_CHARS = 80000


class SiteLlmsTxtGenerator:
    """Generate llms.txt — a curated site overview for AI agents.

    Walks the site's section hierarchy and produces a short Markdown
    document with an H1 title, blockquote description, and H2 sections
    containing annotated links to key pages.

    Attributes:
        site: Site instance with pages, sections, and configuration.
        max_pages: Maximum number of page entries to include.
        max_chars: Maximum character count before truncation.
    """

    def __init__(self, site: SiteLike) -> None:
        self.site = site
        self._logger = get_logger(__name__)
        options = site.config.get("output_formats", {}).get("options", {})
        self.max_pages = options.get("llms_txt_max_pages", _DEFAULT_MAX_PAGES)
        self.max_chars = options.get("llms_txt_max_chars", _DEFAULT_MAX_CHARS)
        # Cache section name map for O(1) lookups
        self._section_name_map: dict[str, str] = {
            getattr(s, "name", ""): getattr(s, "title", "")
            for s in getattr(site, "sections", [])
            if getattr(s, "name", "")
        }

    def generate(self, pages: list[PageLike]) -> Path:
        """Generate llms.txt at the site root.

        Args:
            pages: Pre-filtered list of pages eligible for inclusion
                   (already excludes drafts, hidden, ai_input=false, etc.).

        Returns:
            Path to the generated llms.txt file.
        """
        curated = self._curate_pages(pages)
        content = self._render(curated)
        output_path = self.site.output_dir / "llms.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with AtomicFile(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._logger.info(
            "llms_txt_generated",
            path=str(output_path),
            pages_included=len(curated),
            pages_total=len(pages),
            chars=len(content),
        )
        return output_path

    def _curate_pages(self, pages: list[PageLike]) -> list[PageLike]:
        """Filter pages to include only high-value navigation entries.

        Excludes:
        - Virtual/generated pages (taxonomy terms, tag listings)
        - Pages without output paths
        - Pages beyond the max_pages cap (lowest-weight pages preferred)
        """
        curated: list[PageLike] = []

        for page in pages:
            if not page.output_path:
                continue

            # Skip virtual pages (taxonomy term pages, tag listings, etc.)
            if getattr(page, "is_virtual", False) is True:
                continue

            curated.append(page)

        excluded = len(pages) - len(curated)
        if excluded:
            self._logger.debug(
                "llms_txt_curated",
                included=len(curated),
                excluded=excluded,
            )

        # Cap at max_pages — pages are already weight-ordered from the site
        if len(curated) > self.max_pages:
            self._logger.debug(
                "llms_txt_capped",
                before=len(curated),
                max_pages=self.max_pages,
            )
            curated = curated[: self.max_pages]

        return curated

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
        total_pages = sum(len(sp) for _, sp in sections)
        pages_rendered = 0
        truncated = False

        for section_name, section_pages in sections:
            display_name = self._format_section_name(section_name)
            lines.append(f"## {display_name}")
            lines.append("")
            for page in section_pages:
                url = get_page_url(page, self.site)
                desc = page.description
                if desc:
                    lines.append(f"- [{page.title}]({url}): {desc}")
                else:
                    lines.append(f"- [{page.title}]({url})")
                pages_rendered += 1

                # Check character budget after each section
                if self.max_chars and len("\n".join(lines)) > self.max_chars:
                    truncated = True
                    break
            lines.append("")

            if truncated:
                break

        if truncated:
            remaining = total_pages - pages_rendered
            baseurl = (self.site.baseurl or "").rstrip("/")
            lines.append(
                f"*... and {remaining} more pages. "
                f"See [llm-full.txt]({baseurl}/llm-full.txt) for complete content.*"
            )
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

        Uses the cached section name map (which is weight-ordered)
        as the canonical ordering. Sections not in the site hierarchy are
        appended alphabetically.
        """
        ordered: list[tuple[str, list[PageLike]]] = []
        seen: set[str] = set()

        for name in self._section_name_map:
            if name in section_map:
                ordered.append((name, section_map[name]))
                seen.add(name)

        ordered.extend(
            (name, section_map[name]) for name in sorted(section_map.keys()) if name not in seen
        )

        return ordered

    def _format_section_name(self, name: str) -> str:
        """Convert section slug to display name.

        Uses the cached section name map for O(1) lookup,
        falling back to title-casing the slug.
        """
        title = self._section_name_map.get(name, "")
        if title and title != name:
            return title
        return name.replace("-", " ").replace("_", " ").title()

    def _append_optional_section(self, lines: list[str]) -> None:
        """Append an Optional section with links to machine-readable formats."""
        site_wide = self.site.config.get("output_formats", {}).get("site_wide", [])
        baseurl = (self.site.baseurl or "").rstrip("/")
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

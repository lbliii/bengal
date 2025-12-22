"""
Content migration assistant for safe content restructuring.

Provides tools to safely move, split, merge, and reorganize content files
while maintaining link integrity and automatically generating redirects.
All operations can be previewed before execution.

Key Features:
    - MoveOperation: Planned content move
    - MovePreview: Preview showing affected links and redirects
    - LinkUpdate: Link that needs updating after a move
    - Redirect: Redirect rule in multiple formats
    - PageDraft: Draft for split/merge operations
    - ContentMigrator: Debug tool combining all capabilities

Operations:
    - preview_move(): Preview what a move would do
    - execute_move(): Execute with link updates and redirects
    - split_page(): Split large page into sections
    - merge_pages(): Merge multiple pages into one
    - generate_redirects(): Create redirect rules

Example:
    >>> from bengal.debug import ContentMigrator
    >>> migrator = ContentMigrator(site=site)
    >>> preview = migrator.preview_move("docs/old.md", "guides/new.md")
    >>> print(preview.format_summary())
    📦 Move Preview: docs/old.md → guides/new.md

    🔗 3 links would be updated:
       • content/index.md:15
       • content/about.md:42

    ↪️  1 redirect(s) would be created:
       • /docs/old → /guides/new

    ✅ Safe to proceed

    >>> if preview.can_proceed:
    ...     actions = migrator.execute_move(preview)

Related Modules:
    - bengal.health.validators.links: Link validation
    - bengal.postprocess.redirects: Redirect handling
    - bengal.debug.base: Debug tool infrastructure

See Also:
    - bengal/cli/commands/debug.py: CLI integration
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.debug.base import DebugFinding, DebugRegistry, DebugReport, DebugTool, Severity
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    pass


@dataclass
class MoveOperation:
    """
    A planned content move operation.

    Describes the source and destination of a content file move.
    Used as input to preview_move() and stored in MovePreview.

    Attributes:
        source: Source path (relative to content directory).
        destination: Destination path (relative to content directory).
        reason: Optional explanation of why this move is needed.

    Example:
        >>> op = MoveOperation(
        ...     source="docs/api-old.md",
        ...     destination="reference/api.md",
        ...     reason="Reorganizing documentation structure",
        ... )
        >>> print(op)
        docs/api-old.md → reference/api.md
    """

    source: str
    destination: str
    reason: str = ""

    def __str__(self) -> str:
        """Format as source → destination."""
        return f"{self.source} → {self.destination}"


@dataclass
class LinkUpdate:
    """
    A link that needs to be updated after a content move.

    Identifies where a link exists and what it should change to.
    Includes context for review before making changes.

    Attributes:
        file_path: Path to the file containing the link.
        old_link: Current link target (to be replaced).
        new_link: New link target (replacement).
        line: Line number where the link appears.
        context: Surrounding text (markdown link syntax).

    Example:
        >>> update = LinkUpdate(
        ...     file_path="content/index.md",
        ...     old_link="/docs/api-old",
        ...     new_link="/reference/api",
        ...     line=42,
        ...     context="[API Reference](/docs/api-old)",
        ... )
    """

    file_path: str
    old_link: str
    new_link: str
    line: int = 0
    context: str = ""


@dataclass
class Redirect:
    """
    A redirect rule for moved content.

    Supports generating redirect rules in multiple formats for
    different hosting platforms.

    Attributes:
        from_path: Old URL path (source of redirect).
        to_path: New URL path (destination of redirect).
        status_code: HTTP status code (301 permanent, 302 temporary).

    Example:
        >>> redirect = Redirect(
        ...     from_path="/docs/api-old",
        ...     to_path="/reference/api",
        ...     status_code=301,
        ... )
        >>> print(redirect.to_netlify())
        /docs/api-old /reference/api 301
    """

    from_path: str
    to_path: str
    status_code: int = 301

    def to_nginx(self) -> str:
        """Generate nginx redirect rule for server config."""
        return f"rewrite ^{self.from_path}$ {self.to_path} permanent;"

    def to_netlify(self) -> str:
        """Generate Netlify _redirects file format."""
        return f"{self.from_path} {self.to_path} {self.status_code}"

    def to_apache(self) -> str:
        """Generate Apache .htaccess redirect directive."""
        return f"Redirect {self.status_code} {self.from_path} {self.to_path}"


@dataclass
class MovePreview:
    """
    Preview of what a move operation would do.

    Generated by preview_move() to show all effects before execution.
    Allows review of link updates, redirects, and any warnings before
    committing to the move.

    Attributes:
        operation: The move operation being previewed.
        affected_links: Links that would need updating across the site.
        redirects_needed: Redirect rules that would be generated.
        warnings: Any warnings about potential issues.
        can_proceed: Whether the move can safely proceed.

    Example:
        >>> preview = migrator.preview_move("docs/old.md", "guides/new.md")
        >>> if not preview.can_proceed:
        ...     for warning in preview.warnings:
        ...         print(f"⚠️ {warning}")
        >>> else:
        ...     migrator.execute_move(preview)
    """

    operation: MoveOperation
    affected_links: list[LinkUpdate] = field(default_factory=list)
    redirects_needed: list[Redirect] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    can_proceed: bool = True

    def format_summary(self) -> str:
        """
        Format preview as human-readable summary.

        Returns:
            Multi-line summary with affected links, redirects, and status.
        """
        lines = [f"📦 Move Preview: {self.operation}"]
        lines.append("")

        if self.affected_links:
            lines.append(f"🔗 {len(self.affected_links)} links would be updated:")
            for link in self.affected_links[:5]:
                lines.append(f"   • {link.file_path}:{link.line}")
            if len(self.affected_links) > 5:
                lines.append(f"   ... and {len(self.affected_links) - 5} more")
            lines.append("")

        if self.redirects_needed:
            lines.append(f"↪️  {len(self.redirects_needed)} redirect(s) would be created:")
            for redirect in self.redirects_needed:
                lines.append(f"   • {redirect.from_path} → {redirect.to_path}")
            lines.append("")

        if self.warnings:
            lines.append("⚠️  Warnings:")
            for warning in self.warnings:
                lines.append(f"   • {warning}")
            lines.append("")

        status = "✅ Safe to proceed" if self.can_proceed else "❌ Issues found"
        lines.append(status)

        return "\n".join(lines)


@dataclass
class PageDraft:
    """
    A draft of a new or modified page.

    Used by split_page() and merge_pages() to represent the output
    pages before they're written to disk, allowing for preview and
    modification before committing changes.

    Attributes:
        path: Target path for the new page (relative to content dir).
        title: Page title extracted from heading or frontmatter.
        content: Full Markdown content body.
        frontmatter: Merged/generated frontmatter dictionary.
        source_pages: Original pages this draft was derived from.

    Example:
        >>> drafts = migrator.split_page("docs/guide.md")
        >>> for draft in drafts:
        ...     print(f"Would create: {draft.path}")
        ...     print(f"  Title: {draft.title}")
        ...     print(f"  Content length: {len(draft.content)} chars")
    """

    path: str
    title: str
    content: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    source_pages: list[str] = field(default_factory=list)

    def format_preview(self, max_lines: int = 20) -> str:
        """Format as preview."""
        lines = [f"📄 {self.path}"]
        lines.append(f"   Title: {self.title}")
        if self.source_pages:
            lines.append(f"   From: {', '.join(self.source_pages)}")
        lines.append("")
        lines.append("   Content preview:")

        content_lines = self.content.split("\n")[:max_lines]
        for line in content_lines:
            lines.append(f"   │ {line[:60]}")
        if len(self.content.split("\n")) > max_lines:
            lines.append(f"   │ ... ({len(self.content.split(chr(10))) - max_lines} more lines)")

        return "\n".join(lines)


@DebugRegistry.register
class ContentMigrator(DebugTool):
    """
    Tool for safely restructuring content with link integrity.

    Provides safe content reorganization operations that maintain site
    integrity by automatically updating internal links and generating
    redirect rules for external references.

    Capabilities:
        - **Move/Rename**: Relocate content files with automatic link updates.
        - **Split Pages**: Break large pages into multiple smaller pages.
        - **Merge Pages**: Combine multiple pages into a single page.
        - **Redirect Generation**: Create redirect rules for various platforms.
        - **Structure Analysis**: Find orphan pages, large pages, and issues.

    The tool operates in a preview-first mode: all operations can be
    previewed before execution to review the impact.

    Attributes:
        name: Tool identifier ("migrate").
        description: Brief tool description.
        site: Site instance for content access.
        cache: Optional build cache for dependency info.
        root_path: Project root directory.

    Example:
        >>> migrator = ContentMigrator(site=site)
        >>> # Preview a move operation
        >>> preview = migrator.preview_move(
        ...     "docs/old-guide.md",
        ...     "tutorials/getting-started.md"
        ... )
        >>> print(preview.format_summary())
        >>> # Execute if safe
        >>> if preview.can_proceed:
        ...     migrator.execute_move(preview)

    See Also:
        - :class:`MovePreview`: Preview result structure
        - :class:`PageDraft`: Draft page for split/merge
        - :meth:`analyze`: Find content structure issues
    """

    name = "migrate"
    description = "Safely restructure content"

    def analyze(self) -> DebugReport:
        """
        Analyze content structure for migration opportunities.

        Returns:
            DebugReport with structure analysis
        """
        report = self.create_report()
        report.summary = "Content structure analysis"

        if not self.site:
            report.add_finding(
                title="Site not available",
                description="Cannot analyze without site instance",
                severity=Severity.ERROR,
            )
            return report

        # Find potential issues
        findings = self._find_structure_issues()
        report.findings.extend(findings)

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def preview_move(self, source: str, destination: str) -> MovePreview:
        """
        Preview what would happen if a file is moved.

        Args:
            source: Source path (relative to content dir)
            destination: Destination path

        Returns:
            MovePreview with affected links and redirects
        """
        operation = MoveOperation(source=source, destination=destination)
        preview = MovePreview(operation=operation)

        if not self.site:
            preview.warnings.append("Site not available - limited preview")
            return preview

        # Find links that reference the source
        source_url = self._path_to_url(source)
        dest_url = self._path_to_url(destination)

        for page in self.site.pages:
            content = getattr(page, "content", "") or ""
            page_path = str(getattr(page, "source_path", ""))

            # Find links to source
            for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
                link_target = match.group(2)
                if self._links_match(link_target, source_url):
                    line = content[: match.start()].count("\n") + 1
                    preview.affected_links.append(
                        LinkUpdate(
                            file_path=page_path,
                            old_link=link_target,
                            new_link=self._update_link(link_target, dest_url),
                            line=line,
                            context=match.group(0),
                        )
                    )

        # Generate redirect
        preview.redirects_needed.append(Redirect(from_path=source_url, to_path=dest_url))

        # Check for issues
        dest_path = self.root_path / destination
        if dest_path.exists():
            preview.warnings.append(f"Destination already exists: {destination}")
            preview.can_proceed = False

        source_path = self.root_path / source
        if not source_path.exists():
            preview.warnings.append(f"Source does not exist: {source}")
            preview.can_proceed = False

        return preview

    def execute_move(
        self,
        preview: MovePreview,
        update_links: bool = True,
        create_redirects: bool = True,
        dry_run: bool = False,
    ) -> list[str]:
        """
        Execute a previewed move operation.

        Args:
            preview: Move preview from preview_move()
            update_links: Whether to update links in other files
            create_redirects: Whether to generate redirect rules
            dry_run: If True, only report what would be done

        Returns:
            List of actions taken (or that would be taken)
        """
        actions: list[str] = []

        if not preview.can_proceed:
            return ["Move cancelled due to warnings"]

        source_path = self.root_path / preview.operation.source
        dest_path = self.root_path / preview.operation.destination

        # Move the file
        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(dest_path)
        actions.append(f"Moved {preview.operation.source} → {preview.operation.destination}")

        # Update links
        if update_links:
            for link_update in preview.affected_links:
                if not dry_run:
                    self._update_file_link(link_update)
                actions.append(f"Updated link in {link_update.file_path}:{link_update.line}")

        # Create redirects
        if create_redirects and preview.redirects_needed:
            redirects_path = self.root_path / "_redirects"
            redirect_lines = [r.to_netlify() for r in preview.redirects_needed]

            if not dry_run:
                existing = redirects_path.read_text() if redirects_path.exists() else ""
                new_content = existing + "\n".join(redirect_lines) + "\n"
                redirects_path.write_text(new_content)
            actions.append(f"Added {len(preview.redirects_needed)} redirect(s)")

        return actions

    def split_page(
        self,
        page_path: str,
        sections: list[str],
        output_dir: str | None = None,
    ) -> list[PageDraft]:
        """
        Split a large page into multiple smaller pages.

        Args:
            page_path: Path to the page to split
            sections: List of heading names to split at
            output_dir: Optional output directory for new pages

        Returns:
            List of PageDraft objects for the new pages
        """
        drafts: list[PageDraft] = []

        source_path = self.root_path / page_path
        if not source_path.exists():
            return drafts

        content = source_path.read_text()
        base_dir = output_dir or str(Path(page_path).parent)

        # Parse frontmatter
        frontmatter: dict[str, Any] = {}
        body = content
        if content.startswith("---"):
            try:
                import yaml

                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2]
            except Exception as e:
                logger.debug(
                    "debug_migrator_frontmatter_parse_failed",
                    page=page_path,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="using_raw_content",
                )

        # Split by headings
        # Find all h2 headings
        heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(body))

        if not matches:
            # No headings to split on
            return drafts

        # Create index page with links to sections
        index_content = f"# {frontmatter.get('title', 'Index')}\n\n"
        index_content += "This section contains:\n\n"

        prev_end = 0
        intro_content = ""

        for i, match in enumerate(matches):
            heading = match.group(1)
            heading_slug = self._slugify(heading)

            # Check if this heading should be split
            if heading not in sections and heading_slug not in sections:
                continue

            # Get content before this heading (intro or previous section)
            if i == 0:
                intro_content = body[prev_end : match.start()].strip()

            # Get section content
            section_start = match.start()
            section_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            section_content = body[section_start:section_end].strip()

            # Create draft for this section
            section_path = f"{base_dir}/{heading_slug}.md"
            section_fm = {
                "title": heading,
                "parent": page_path,
            }

            drafts.append(
                PageDraft(
                    path=section_path,
                    title=heading,
                    content=section_content,
                    frontmatter=section_fm,
                    source_pages=[page_path],
                )
            )

            # Add to index
            index_content += f"- [{heading}]({heading_slug})\n"

            prev_end = section_end

        # Create index draft
        if intro_content:
            index_content = intro_content + "\n\n" + index_content

        index_fm = frontmatter.copy()
        index_fm["layout"] = "section"

        drafts.insert(
            0,
            PageDraft(
                path=f"{base_dir}/_index.md",
                title=frontmatter.get("title", "Index"),
                content=index_content,
                frontmatter=index_fm,
                source_pages=[page_path],
            ),
        )

        return drafts

    def merge_pages(
        self,
        page_paths: list[str],
        output_path: str,
        title: str | None = None,
    ) -> PageDraft:
        """
        Merge multiple pages into one.

        Args:
            page_paths: Paths to pages to merge
            output_path: Output path for merged page
            title: Optional title for merged page

        Returns:
            PageDraft for the merged page
        """
        sections: list[str] = []
        all_frontmatter: dict[str, Any] = {}

        for page_path in page_paths:
            source_path = self.root_path / page_path
            if not source_path.exists():
                continue

            content = source_path.read_text()

            # Parse frontmatter
            body = content
            if content.startswith("---"):
                try:
                    import yaml

                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1]) or {}
                        body = parts[2]
                        # Merge frontmatter (first page wins for conflicts)
                        for key, value in fm.items():
                            if key not in all_frontmatter:
                                all_frontmatter[key] = value
                except Exception as e:
                    logger.debug(
                        "debug_migrator_merge_frontmatter_parse_failed",
                        page=page_path,
                        error=str(e),
                        error_type=type(e).__name__,
                        action="using_raw_content",
                    )

            # Add section heading and content
            page_title = all_frontmatter.get("title", Path(page_path).stem)
            sections.append(f"## {page_title}\n\n{body.strip()}")

        # Combine content
        merged_title = title or all_frontmatter.get("title", "Merged Document")
        merged_content = f"# {merged_title}\n\n" + "\n\n---\n\n".join(sections)

        all_frontmatter["title"] = merged_title

        return PageDraft(
            path=output_path,
            title=merged_title,
            content=merged_content,
            frontmatter=all_frontmatter,
            source_pages=page_paths,
        )

    def generate_redirects(
        self,
        moves: list[MoveOperation],
        output_format: str = "netlify",
    ) -> str:
        """
        Generate redirect rules for moved content.

        Args:
            moves: List of move operations
            output_format: Output format (netlify, nginx, apache)

        Returns:
            Redirect rules in requested format
        """
        redirects = [
            Redirect(
                from_path=self._path_to_url(move.source),
                to_path=self._path_to_url(move.destination),
            )
            for move in moves
        ]

        if output_format == "netlify":
            return "\n".join(r.to_netlify() for r in redirects)
        elif output_format == "nginx":
            return "\n".join(r.to_nginx() for r in redirects)
        elif output_format == "apache":
            return "\n".join(r.to_apache() for r in redirects)
        else:
            return "\n".join(str(r) for r in redirects)

    def _find_structure_issues(self) -> list[DebugFinding]:
        """Find potential structure issues in content."""
        findings: list[DebugFinding] = []

        if not self.site:
            return findings

        # Find orphan pages
        incoming_links: dict[str, int] = {}
        for page in self.site.pages:
            content = getattr(page, "content", "") or ""
            for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
                target = match.group(2)
                if not target.startswith(("http://", "https://", "#")):
                    incoming_links[target] = incoming_links.get(target, 0) + 1

        orphans = []
        for page in self.site.pages:
            url = getattr(page, "href", "")
            if url and incoming_links.get(url, 0) == 0 and not self._is_in_navigation(page):
                orphans.append(str(getattr(page, "source_path", "")))

        if orphans:
            findings.append(
                DebugFinding(
                    title=f"{len(orphans)} orphan pages found",
                    description="Pages with no incoming links",
                    severity=Severity.WARNING,
                    category="structure",
                    metadata={"orphans": orphans[:10]},
                    suggestion="Add links to these pages or include in navigation",
                )
            )

        # Find very large pages
        large_pages = []
        for page in self.site.pages:
            content = getattr(page, "content", "") or ""
            line_count = content.count("\n")
            if line_count > 500:
                large_pages.append((str(getattr(page, "source_path", "")), line_count))

        if large_pages:
            findings.append(
                DebugFinding(
                    title=f"{len(large_pages)} large pages found (>500 lines)",
                    description="Consider splitting these into smaller pages",
                    severity=Severity.INFO,
                    category="structure",
                    metadata={"pages": large_pages[:10]},
                    suggestion="Use split_page() to break into sections",
                )
            )

        return findings

    def _is_in_navigation(self, page: Any) -> bool:
        """Check if page is in site navigation."""
        # Simplified check - would integrate with menu system
        url = getattr(page, "href", "")
        return url in ("/", "/index.html") or "index" in str(getattr(page, "source_path", ""))

    def _path_to_url(self, path: str) -> str:
        """Convert file path to URL."""
        # Remove content/ prefix if present
        if path.startswith("content/"):
            path = path[8:]

        # Remove .md extension
        if path.endswith(".md"):
            path = path[:-3]

        # Handle index files
        if path.endswith("/index") or path.endswith("/_index"):
            path = path.rsplit("/", 1)[0]

        return "/" + path.strip("/")

    def _links_match(self, link: str, target_url: str) -> bool:
        """Check if a link matches a target URL."""
        # Normalize both
        link_normalized = link.strip("/").rstrip("/")
        target_normalized = target_url.strip("/").rstrip("/")

        return link_normalized == target_normalized

    def _update_link(self, old_link: str, new_url: str) -> str:
        """Update a link to point to new location."""
        # Preserve any anchors or query params
        if "#" in old_link:
            anchor = old_link.split("#", 1)[1]
            return new_url + "#" + anchor
        return new_url

    def _update_file_link(self, link_update: LinkUpdate) -> None:
        """Update a link in a file."""
        file_path = Path(link_update.file_path)
        if not file_path.exists():
            return

        content = file_path.read_text()
        # Replace the specific link
        updated = content.replace(
            f"]({link_update.old_link})",
            f"]({link_update.new_link})",
        )
        file_path.write_text(updated)

    def _slugify(self, text: str) -> str:
        """Convert text to URL slug."""
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        return slug.strip("-")

    def _generate_recommendations(self, report: DebugReport) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations: list[str] = []

        for finding in report.findings:
            if finding.category == "structure":
                if "orphan" in finding.title.lower():
                    recommendations.append("Review orphan pages and add navigation")
                if "large" in finding.title.lower():
                    recommendations.append("Consider splitting large pages into sections")

        if not recommendations:
            recommendations.append("Content structure looks healthy! ✅")

        return recommendations

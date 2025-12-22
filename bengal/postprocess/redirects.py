"""
Redirect page generation for page aliases and URL migration.

Generates lightweight HTML redirect pages for each page alias defined in
frontmatter, allowing old URLs to redirect to new canonical locations.
This preserves SEO value, maintains link stability during content
reorganization, and supports URL migration strategies.

Features:
    - HTML meta refresh redirects with canonical links
    - SEO-friendly noindex directives on redirect pages
    - Conflict detection when multiple pages claim the same alias
    - URL registry integration to prevent shadowing real content
    - Optional _redirects file generation for Netlify/Vercel

How It Works:
    Pages define aliases in frontmatter:

    ```yaml
    ---
    title: "My New Post"
    aliases:
      - /old/posts/my-post/
      - /legacy/content/post-123/
    ---
    ```

    The generator creates redirect HTML files at each alias path that
    redirect to the page's canonical URL.

Configuration:
    Optional _redirects file for platform-specific server-side redirects:

    ```toml
    [redirects]
    generate_redirects_file = true  # Creates _redirects for Netlify/Vercel
    ```

Example:
    >>> from bengal.postprocess.redirects import RedirectGenerator
    >>>
    >>> redirect_gen = RedirectGenerator(site)
    >>> count = redirect_gen.generate()
    >>> print(f"Generated {count} redirect pages")

Related:
    - bengal.orchestration.postprocess: Coordinates redirect generation
    - bengal.core.page: Page objects with aliases metadata
    - bengal.utils.url_registry: URL conflict detection and priority
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


class RedirectGenerator:
    """
    Generates redirect HTML pages for page aliases.

    For each page with aliases defined in frontmatter, creates lightweight
    HTML files at the alias paths that redirect to the canonical URL.
    Includes proper SEO signals (canonical link, noindex, meta refresh).

    Creation:
        Direct instantiation: RedirectGenerator(site)
            - Created by PostprocessOrchestrator for redirect generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages containing aliases
        logger: Logger instance for redirect generation events

    Relationships:
        - Used by: PostprocessOrchestrator for redirect generation
        - Uses: Site for page access, URLRegistry for conflict detection

    Features:
        - HTML meta refresh with 0-second delay (immediate redirect)
        - Canonical link tag pointing to target URL
        - noindex meta tag to prevent redirect pages in search results
        - Fallback link for browsers without JavaScript/meta refresh
        - Conflict detection when multiple pages claim same alias
        - URL registry integration (priority 5 = lowest, never shadows content)
        - Optional _redirects file for Netlify/Vercel server-side redirects

    Example:
        >>> generator = RedirectGenerator(site)
        >>> count = generator.generate()
        >>> print(f"Generated {count} redirect pages")
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize redirect generator.

        Args:
            site: Site instance with pages containing aliases
        """
        self.site = site
        self.logger = get_logger(__name__)

    def generate(self) -> int:
        """
        Generate all redirect pages.

        Iterates through all pages, generates redirect HTML for each alias,
        and optionally generates a _redirects file for platform-specific
        server-side redirects.

        Returns:
            Number of redirects generated
        """
        redirects_generated = 0
        conflicts = 0

        # Collect all aliases to detect conflicts
        alias_map: dict[str, list[tuple[str, str]]] = {}  # alias -> [(page_url, page_title), ...]

        for page in self.site.pages:
            aliases = getattr(page, "aliases", None) or []
            if not aliases:
                continue

            page_url = getattr(page, "href", None) or getattr(page, "permalink", "/")

            for alias in aliases:
                if alias not in alias_map:
                    alias_map[alias] = []
                alias_map[alias].append((page_url, getattr(page, "title", "Untitled")))

        # Check for conflicts (multiple pages claiming same alias)
        for alias, claimants in alias_map.items():
            if len(claimants) > 1:
                self.logger.warning(
                    "redirect_alias_conflict",
                    alias=alias,
                    claimants=[f"{url} ({title})" for url, title in claimants],
                    hint="Multiple pages claim the same alias; only the first will be used",
                )
                conflicts += 1

        # Generate redirect pages (use first claimant for conflicts)
        for alias, claimants in alias_map.items():
            target_url = claimants[0][0]
            if self._generate_redirect(alias, target_url):
                redirects_generated += 1

        if redirects_generated > 0:
            self.logger.info(
                "redirects_generated",
                count=redirects_generated,
                conflicts=conflicts,
            )

        # Optionally generate _redirects file for Netlify/Vercel
        self._generate_redirects_file(alias_map)

        return redirects_generated

    def _generate_redirect(self, from_path: str, to_url: str) -> bool:
        """
        Generate a single redirect HTML page.

        Args:
            from_path: Source path (alias), e.g., "/old/posts/my-post/"
            to_url: Target URL to redirect to, e.g., "/blog/my-post/"

        Returns:
            True if redirect was generated, False if skipped (conflict)
        """
        # Normalize paths
        from_path_normalized = from_path.strip("/")
        if not from_path_normalized:
            self.logger.warning(
                "redirect_invalid_alias",
                alias=from_path,
                reason="empty path after normalization",
            )
            return False

        output_path = self.site.output_dir / from_path_normalized / "index.html"

        # Claim URL in registry before writing (claim-before-write pattern)
        # Priority 5 = redirects (lowest, should never shadow actual content)
        if hasattr(self.site, "url_registry") and self.site.url_registry:
            try:
                self.site.url_registry.claim_output_path(
                    output_path=output_path,
                    site=self.site,
                    owner="redirect",
                    source=f"alias:{from_path}",
                    priority=5,  # Redirects (lowest priority)
                )
            except Exception as e:
                # Registry rejected claim (higher priority content exists)
                self.logger.warning(
                    "redirect_conflict",
                    alias=from_path,
                    target=to_url,
                    reason=f"URL already claimed by higher priority content: {e}",
                )
                return False
        else:
            # Fallback to file existence check if registry not available
            if output_path.exists():
                self.logger.warning(
                    "redirect_conflict",
                    alias=from_path,
                    target=to_url,
                    reason="path already exists (real content takes precedence)",
                )
                return False

        # Generate redirect HTML
        html = self._render_redirect_html(from_path, to_url)

        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        self.logger.debug(
            "redirect_page_created",
            from_path=from_path,
            to_url=to_url,
            output=str(output_path),
        )

        return True

    def _render_redirect_html(self, from_path: str, to_url: str) -> str:
        """
        Render redirect HTML with SEO hints.

        Generates a minimal HTML page that:
        - Redirects immediately via meta refresh
        - Includes canonical link for SEO
        - Has noindex to prevent redirect pages appearing in search
        - Provides fallback link for browsers without JavaScript/meta refresh

        Args:
            from_path: Original path (for display only)
            to_url: Target URL to redirect to

        Returns:
            HTML string for redirect page
        """
        # Ensure to_url starts with / for absolute paths
        if not to_url.startswith("/") and not to_url.startswith("http"):
            to_url = "/" + to_url

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url={to_url}">
    <link rel="canonical" href="{to_url}">
    <title>Redirecting...</title>
    <meta name="robots" content="noindex">
</head>
<body>
    <p>This page has moved. Redirecting to <a href="{to_url}">{to_url}</a>...</p>
</body>
</html>'''

    def _generate_redirects_file(self, alias_map: dict[str, list[tuple[str, str]]]) -> None:
        """
        Generate _redirects file for Netlify/Vercel.

        Only generates if enabled in config:
            [redirects]
            generate_redirects_file = true

        Args:
            alias_map: Map of alias -> [(target_url, title), ...]
        """
        # Check if enabled in config
        redirects_config = self.site.config.get("redirects", {})
        if not redirects_config.get("generate_redirects_file", False):
            return

        if not alias_map:
            return

        lines = []
        for alias, claimants in alias_map.items():
            target_url = claimants[0][0]
            # Netlify format: /from  /to  status_code
            # Ensure alias starts with /
            if not alias.startswith("/"):
                alias = "/" + alias
            lines.append(f"{alias}  {target_url}  301")

        if lines:
            redirects_path = self.site.output_dir / "_redirects"
            redirects_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.logger.info(
                "redirects_file_generated",
                path=str(redirects_path),
                count=len(lines),
            )

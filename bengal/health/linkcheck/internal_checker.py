"""
Internal link checker for page-to-page and anchor validation.

Validates internal links by checking if target pages exist in the built
output directory. Handles relative paths, baseurl stripping, and anchor
validation.

Features:
- Page existence checking via output directory scan
- Anchor validation against page headings
- Source file reference filtering (autodoc .py links)
- Baseurl path stripping for proper resolution

Related:
- bengal.health.linkcheck.orchestrator: Coordinates with external checker
- bengal.health.linkcheck.models: LinkCheckResult data model

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from bengal.health.linkcheck.ignore_policy import IgnorePolicy
from bengal.health.linkcheck.models import LinkCheckResult, LinkKind, LinkStatus
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import SiteLike
    from bengal.rendering.reference_registry import LinkRegistry

logger = get_logger(__name__)


class InternalLinkChecker:
    """
    Validates internal links within a built site.

    Scans the output directory for HTML files and builds an index of valid
    URLs. Checks links against this index and validates anchors when present.

    Validation Coverage:
        - Page-to-page links (absolute site paths)
        - Anchor links (#section-id)
        - Handles baseurl stripping
        - Filters source file references (autodoc)

    Attributes:
        site: Site instance with output_dir
        ignore_policy: IgnorePolicy for filtering certain links
        output_dir: Path to built HTML files
        baseurl_path: Base URL path to strip from links

    Note:
        Relative links are resolved against the referencing page's URL and
        validated like absolute links.

    """

    def __init__(
        self,
        site: SiteLike,
        ignore_policy: IgnorePolicy | None = None,
    ):
        """
        Initialize internal link checker.

        Scans the output directory to build an index of valid URLs.

        Args:
            site: Site instance with output_dir and config
            ignore_policy: Policy for ignoring certain links
        """
        self.site = site
        self.ignore_policy = ignore_policy or IgnorePolicy()
        self.output_dir = site.output_dir

        # Get baseurl to strip from URLs
        baseurl = site.baseurl or ""
        if baseurl:
            # Parse baseurl to get just the path part
            from urllib.parse import urlparse

            parsed = urlparse(baseurl)
            self.baseurl_path = parsed.path.rstrip("/")
        else:
            self.baseurl_path = ""

        # Build index from actual files in output directory
        self._output_paths: set[str] = set()
        self._anchors_by_page: dict[str, set[str]] = {}

        self._build_index_from_scan()

        logger.debug(
            "internal_checker_initialized",
            output_paths_count=len(self._output_paths),
            output_dir=str(self.output_dir),
        )

    @classmethod
    def from_registry(
        cls,
        registry: LinkRegistry,
        site: SiteLike,
        ignore_policy: IgnorePolicy | None = None,
    ) -> InternalLinkChecker:
        """
        Create an InternalLinkChecker pre-populated from a LinkRegistry.

        Skips the output directory scan since the registry already has
        all valid URLs and anchor data.

        Args:
            registry: Pre-built LinkRegistry with page URLs and anchors
            site: Site instance (for baseurl and output_dir)
            ignore_policy: Policy for ignoring certain links
        """
        instance = cls.__new__(cls)
        instance.site = site
        instance.ignore_policy = ignore_policy or IgnorePolicy()
        instance.output_dir = site.output_dir

        baseurl = site.baseurl or ""
        if baseurl:
            parsed = urlparse(baseurl)
            instance.baseurl_path = parsed.path.rstrip("/")
        else:
            instance.baseurl_path = ""

        # Populate from registry instead of scanning output_dir
        instance._output_paths = set(registry.page_urls | registry.auxiliary_urls)
        instance._anchors_by_page = {
            url: set(anchors) for url, anchors in registry.anchors_by_url.items()
        }

        logger.debug(
            "internal_checker_from_registry",
            output_paths_count=len(instance._output_paths),
            anchors_pages=len(registry.anchors_by_url),
        )

        return instance

    def _build_index_from_scan(self) -> None:
        """Build URL index by scanning the output directory for HTML and txt files."""
        if not self.output_dir.exists():
            return

        for html_file in self.output_dir.rglob("*.html"):
            self._index_html_file(html_file)

        # Also index auxiliary output files (.txt for LLM-friendly output)
        for txt_file in self.output_dir.rglob("*.txt"):
            rel_path = txt_file.relative_to(self.output_dir)
            self._output_paths.add(f"/{rel_path}")

    def _index_html_file(self, html_file: Path) -> None:
        """Add a single HTML file to the URL index."""
        rel_path = html_file.relative_to(self.output_dir)

        if rel_path.name == "index.html":
            url = "/" if rel_path.parent == Path(".") else f"/{rel_path.parent}/"
        else:
            url = f"/{rel_path.with_suffix('')}"

        self._output_paths.add(url)
        self._output_paths.add(url.rstrip("/"))
        if url != "/":
            self._output_paths.add(url.rstrip("/") + "/")

    def set_file_index(self, html_files: list[Path]) -> None:
        """Rebuild URL index from a pre-discovered list of HTML files.

        This avoids a redundant ``rglob("*.html")`` when the orchestrator
        has already enumerated the output directory during link extraction.

        Args:
            html_files: List of HTML file paths already discovered.
        """
        self._output_paths.clear()

        for html_file in html_files:
            self._index_html_file(html_file)

        # Re-scan for .txt files (small number, fast)
        if self.output_dir.exists():
            for txt_file in self.output_dir.rglob("*.txt"):
                rel_path = txt_file.relative_to(self.output_dir)
                self._output_paths.add(f"/{rel_path}")

        logger.debug(
            "internal_checker_reindexed",
            output_paths_count=len(self._output_paths),
        )

    def _ref_to_page_url(self, ref: str) -> str:
        """
        Convert a referencing page file path to its served (pretty) URL.

        ``ref`` is the output-relative path of the HTML file that contains the
        link (e.g. ``docs/guide/index.html`` or ``about.html``). The returned
        URL is the base against which relative links on that page resolve, and
        it must match how a browser sees the page so ``urljoin`` reproduces the
        browser's RFC 3986 resolution.

        Bengal serves every page at a trailing-slash pretty URL: a directory
        index (``docs/guide/index.html``) is served at ``/docs/guide/`` and a
        flat-output non-index page (``docs/guide.html``) is *also* served at
        ``/docs/guide/`` (the ``.html`` suffix is stripped and a trailing slash
        is appended -- see :meth:`URLStrategy.url_from_output_path`). Returning
        the trailing-slash form is therefore required for relative links to
        resolve against the page's served directory, exactly as a browser does.

        Args:
            ref: Output-relative HTML file path (uses ``/`` separators).

        Returns:
            Served site-relative URL ending in ``/`` (e.g. ``/docs/guide/``),
            or ``/`` for the root page.
        """
        ref = ref.replace("\\", "/")
        rel = Path(ref)
        if rel.name == "index.html":
            return "/" if rel.parent == Path(".") else f"/{rel.parent.as_posix()}/"
        # Non-index (flat output) page: served at the trailing-slash pretty URL
        # with the ``.html`` suffix stripped, so relative links resolve against
        # the page's own served directory rather than its parent.
        return f"/{rel.with_suffix('').as_posix()}/"

    def _resolved_path_exists(self, path: str) -> bool:
        """
        Check whether a resolved absolute path maps to a built page.

        Normalizes common authoring suffixes (``.md``/``.html``) and trailing
        slashes so a relative link such as ``../other.md`` validates against the
        clean URL (``/section/other/``) recorded in the output index.

        Args:
            path: Absolute site path (already resolved, may include a suffix).

        Returns:
            True if the path matches a known built page or auxiliary file.
        """
        candidates = {path, path.rstrip("/")}
        if path != "/" and not path.endswith("/"):
            candidates.add(path + "/")

        # Strip authoring suffixes that the build rewrites to clean URLs so a
        # link to ``foo.md`` / ``foo.html`` resolves to ``/foo/``.
        for suffix in (".md", ".html"):
            if path.endswith(suffix):
                stem = path[: -len(suffix)]
                candidates.add(stem)
                candidates.add(stem + "/")
                # ``section/index.md`` -> ``/section/``
                if stem.endswith("/index"):
                    parent = stem[: -len("index")]
                    candidates.add(parent)
                    candidates.add(parent.rstrip("/"))

        return any(c in self._output_paths for c in candidates)

    def _check_relative_link(self, url: str, refs: list[str]) -> LinkCheckResult:
        """
        Resolve a relative internal link against each referencing page.

        A relative link (``../other/``, ``./sibling.md``) has no meaning without
        the page it appears on, so it is resolved against every referencing
        page's URL via ``urljoin`` and validated like an absolute link. If it
        fails to resolve for any referencing page, it is reported broken.

        Args:
            url: Relative internal URL (may include a fragment).
            refs: Output-relative paths of pages that contain this link.

        Returns:
            LinkCheckResult — BROKEN for the first page where the link does not
            resolve, otherwise OK.
        """
        from urllib.parse import urljoin

        parsed = urlparse(url)
        link_path = parsed.path

        checked_refs = refs or [""]
        for ref in checked_refs:
            base_url = self._ref_to_page_url(ref) if ref else "/"
            resolved = urljoin(base_url, link_path)

            # Strip baseurl if the relative link climbed into it.
            if self.baseurl_path and resolved.startswith(self.baseurl_path):
                resolved = resolved[len(self.baseurl_path) :] or "/"

            if not self._resolved_path_exists(resolved):
                logger.debug(
                    "internal_relative_link_broken",
                    url=url,
                    ref=ref,
                    resolved=resolved,
                )
                return LinkCheckResult(
                    url=url,
                    kind=LinkKind.INTERNAL,
                    status=LinkStatus.BROKEN,
                    reason="Page not found",
                    first_ref=ref or (refs[0] if refs else None),
                    ref_count=len(refs),
                    metadata={"resolved": resolved},
                )

        logger.debug("internal_relative_link_ok", url=url)
        return LinkCheckResult(
            url=url,
            kind=LinkKind.INTERNAL,
            status=LinkStatus.OK,
            first_ref=refs[0] if refs else None,
            ref_count=len(refs),
        )

    def check_links(self, links: list[tuple[str, str]]) -> dict[str, LinkCheckResult]:
        """
        Check internal links against the output directory index.

        Deduplicates URLs and checks each against the built site structure.

        Args:
            links: List of (url, first_ref) tuples where first_ref is the
                page that contains this link.

        Returns:
            Dict mapping URL string to LinkCheckResult.
        """
        # Group URLs by destination and count references
        url_refs: dict[str, list[str]] = {}
        for url, ref in links:
            if url not in url_refs:
                url_refs[url] = []
            url_refs[url].append(ref)

        # Check each URL
        results: dict[str, LinkCheckResult] = {}
        for url, refs in url_refs.items():
            results[url] = self._check_internal_link(url, refs)

        return results

    def _check_internal_link(self, url: str, refs: list[str]) -> LinkCheckResult:
        """
        Check a single internal link.

        Resolution steps:
            1. Apply ignore policy
            2. Filter source file references (.py files)
            3. Parse URL to extract path and fragment
            4. Strip baseurl if present
            5. Check page existence in output index
            6. Validate anchor if fragment present

        Args:
            url: Internal URL to check (may include fragment).
            refs: List of pages that reference this URL.

        Returns:
            LinkCheckResult with OK/BROKEN/IGNORED status.
        """
        # Check ignore policy
        should_ignore, ignore_reason = self.ignore_policy.should_ignore_url(url)
        if should_ignore:
            logger.debug("ignoring_internal_url", url=url, reason=ignore_reason)
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.IGNORED,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                ignored=True,
                ignore_reason=ignore_reason,
            )

        # Skip source file references FIRST (before parsing)
        # These are common in autodoc-generated content and should not be checked as page links
        # Patterns: bengal/module.py#L1, ../bengal/module.py#L1, module.py#L1, etc.
        if (
            ".py#L" in url  # Python file with line number anchor
            or ".py#" in url  # Python file with any anchor
            or url.endswith(".py")  # Python file without anchor
            or ("/bengal/" in url and ".py" in url)  # Paths containing bengal/ and .py
            or (url.startswith("../") and ".py" in url)  # Relative paths to .py files
        ):
            logger.debug(
                "skipping_source_file_reference",
                url=url,
                reason="source_file_reference_in_autodoc",
            )
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.IGNORED,
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
                ignored=True,
                ignore_reason="Source file reference (autodoc)",
            )

        # Parse URL to separate path and fragment
        parsed = urlparse(url)
        path = parsed.path
        fragment = parsed.fragment

        # Strip baseurl from path if present
        if self.baseurl_path and path.startswith(self.baseurl_path):
            path = path[len(self.baseurl_path) :]
            if not path:  # Handle case where path becomes empty
                path = "/"

        # Handle relative paths by resolving against the referencing page(s).
        if not path.startswith("/"):
            return self._check_relative_link(url, refs)

        # Check if page exists (with or without trailing slash)
        page_exists = path in self._output_paths or path.rstrip("/") in self._output_paths

        if not page_exists:
            logger.debug("internal_link_broken_page_not_found", url=url, path=path)
            return LinkCheckResult(
                url=url,
                kind=LinkKind.INTERNAL,
                status=LinkStatus.BROKEN,
                reason="Page not found",
                first_ref=refs[0] if refs else None,
                ref_count=len(refs),
            )

        # If fragment specified, check if anchor exists
        if fragment:
            # Find the page (try both with and without trailing slash)
            page_url = path if path in self._output_paths else path.rstrip("/")
            anchors = self._anchors_by_page.get(page_url, set())

            if anchors and fragment not in anchors:
                logger.debug(
                    "internal_link_broken_anchor_not_found",
                    url=url,
                    page=page_url,
                    anchor=fragment,
                    available_anchors=list(anchors)[:5],
                )
                return LinkCheckResult(
                    url=url,
                    kind=LinkKind.INTERNAL,
                    status=LinkStatus.BROKEN,
                    reason=f"Anchor #{fragment} not found in page",
                    first_ref=refs[0] if refs else None,
                    ref_count=len(refs),
                    metadata={"available_anchors": list(anchors)[:10]},
                )

        # Link is valid
        logger.debug("internal_link_ok", url=url)
        return LinkCheckResult(
            url=url,
            kind=LinkKind.INTERNAL,
            status=LinkStatus.OK,
            first_ref=refs[0] if refs else None,
            ref_count=len(refs),
        )

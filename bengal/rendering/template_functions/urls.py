"""
URL manipulation functions for templates.

Provides URL manipulation filters and functions for working with URLs in templates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment

_COLAB_BASE = "https://colab.research.google.com/github"
_GITHUB_REPO_RE = re.compile(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$", re.I)


def register(env: TemplateEnvironment, site: SiteLike) -> None:
    """Register functions with template environment."""

    # Create closures that have access to site
    def absolute_url_with_site(url: str) -> str:
        return absolute_url(url, site.baseurl or "")

    def href_filter(path: str) -> str:
        """Apply baseurl to path. For manual paths in templates."""
        from bengal.rendering.utils.url import apply_baseurl

        return apply_baseurl(path, site)

    def build_artifact_url_with_site(filename: str = "build.json", dir_name: str = "") -> str:
        return build_artifact_url(site, filename, dir_name)

    env.filters.update(
        {
            "absolute_url": absolute_url_with_site,
            "url": absolute_url_with_site,
            "href": href_filter,
            "url_encode": url_encode,
            "url_decode": url_decode,
            "url_parse": url_parse,
            "url_param": url_param,
            "url_query": url_query,
        }
    )

    def notebook_download_url_with_site(page) -> str:
        return notebook_download_url(page)

    def notebook_colab_url_with_site(page) -> str:
        return notebook_colab_url(page, site)

    env.globals.update(
        {
            "ensure_trailing_slash": ensure_trailing_slash,
            "build_artifact_url": build_artifact_url_with_site,
            "notebook_download_url": notebook_download_url_with_site,
            "notebook_colab_url": notebook_colab_url_with_site,
        }
    )


def notebook_download_url(page) -> str:
    """
    Return the download URL path for a notebook page's .ipynb file.

    Returns empty string if the page is not from a notebook source.
    The .ipynb is copied to output alongside the HTML during build.
    Use with | absolute_url in templates for full URL.

    Args:
        page: Page object with source_path and _path

    Returns:
        Relative URL path to the .ipynb file, or empty string

    Example:
        {{ notebook_download_url(page) | absolute_url }}
    """
    if not page or not getattr(page, "source_path", None):
        return ""
    if str(page.source_path).lower().endswith(".ipynb"):
        path = getattr(page, "_path", None) or getattr(page, "href", "") or ""
        slug = getattr(page, "slug", None) or (page.source_path.stem if hasattr(page.source_path, "stem") else "")
        if path and slug:
            base = (path or "/").rstrip("/")
            return f"{base}/{slug}.ipynb"
    return ""


def notebook_colab_url(page, site: SiteLike) -> str:
    """
    Build Colab URL for a notebook page from repo config.

    Requires [params] repo_url (e.g. https://github.com/owner/repo).
    Optional: colab_branch (default: main), colab_path_prefix (for sites in subdirs).

    When the site lives in a repo subdirectory (e.g. site/), set colab_path_prefix
    to that directory name so the path matches the repo layout. Example: for
    site/content/docs/notebook.ipynb in repo, use colab_path_prefix: "site".

    Returns empty string if repo_url is missing, not a GitHub URL,
    or page is not from a notebook source.

    Args:
        page: Page object with source_path
        site: Site for config (site.params.repo_url, site.params.colab_branch)

    Returns:
        Full Colab URL or empty string

    Example:
        {{ notebook_colab_url(page) }}
    """
    if not page or not getattr(page, "source_path", None):
        return ""
    if not str(page.source_path).lower().endswith(".ipynb"):
        return ""

    params = getattr(site, "params", None) or {}
    repo_url = params.get("repo_url") or ""
    if not repo_url:
        return ""

    match = _GITHUB_REPO_RE.search(repo_url.strip())
    if not match:
        return ""

    owner, repo = match.group(1), match.group(2).rstrip("/")
    branch = params.get("colab_branch") or params.get("repo_branch") or "main"

    # Resolve path relative to repo root (Colab expects repo-relative path)
    raw_path = str(page.source_path).replace("\\", "/")
    root_path = getattr(site, "root_path", None)
    path_rel: str
    if root_path:
        try:
            src = Path(page.source_path)
            root = Path(root_path)
            if src.is_absolute() and root.is_absolute() and str(src).startswith(str(root)):
                path_rel = str(src.relative_to(root)).replace("\\", "/")
            else:
                path_rel = raw_path
        except (ValueError, TypeError):
            path_rel = raw_path
    else:
        path_rel = raw_path

    # Prepend colab_path_prefix when site is in a repo subdirectory
    prefix = (params.get("colab_path_prefix") or "").strip().rstrip("/")
    path = f"{prefix}/{path_rel}".lstrip("/") if prefix else path_rel

    return f"{_COLAB_BASE}/{owner}/{repo}/blob/{branch}/{path}"


def absolute_url(url: str, base_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Uses centralized URL normalization to ensure consistency.
    Detects file URLs (with extensions) and does not add trailing slashes to them.

    Args:
        url: Relative or absolute URL
        base_url: Base URL to prepend

    Returns:
        Absolute URL

    Example:
        {{ page.href | absolute_url }}
        # Output: https://example.com/posts/my-post/
        {{ '/index.json' | absolute_url }}
        # Output: /index.json (no trailing slash for file URLs)

    """
    from bengal.utils.paths.url_normalization import normalize_url

    if not url:
        return base_url or ""

    # Already absolute (http://, https://, //)
    if url.startswith(("http://", "https://", "//")):
        return url

    # Normalize base URL
    base_url = base_url.rstrip("/") if base_url else ""

    # Detect if this is a file URL (has a file extension)
    # File URLs should NOT get trailing slashes
    # Common file extensions: .json, .xml, .txt, .js, .css, .html, etc.
    last_segment = url.rsplit("/", 1)[-1] if "/" in url else url
    has_file_extension = "." in last_segment and not last_segment.startswith(".")

    # Normalize relative URL - don't add trailing slash for file URLs
    normalized_url = normalize_url(url, ensure_trailing_slash=not has_file_extension)

    # Combine URLs
    # If base_url is empty or just "/", use normalized_url directly
    if not base_url or base_url == "/":
        return normalized_url

    # If normalized_url already starts with base_url, don't duplicate it
    if normalized_url.startswith(base_url):
        return normalized_url

    # Combine and normalize again to handle any edge cases
    result = base_url + normalized_url
    return normalize_url(result, ensure_trailing_slash=not has_file_extension)


def url_encode(text: str) -> str:
    """
    URL encode string (percent encoding).

    Encodes special characters for safe use in URLs.

    Args:
        text: Text to encode

    Returns:
        URL-encoded text

    Example:
        {{ search_query | url_encode }}
        # "hello world" -> "hello%20world"

    """
    if not text:
        return ""

    return quote(str(text))


def url_decode(text: str) -> str:
    """
    URL decode string (decode percent encoding).

    Decodes percent-encoded characters back to original form.

    Args:
        text: Text to decode

    Returns:
        URL-decoded text

    Example:
        {{ encoded_text | url_decode }}
        # "hello%20world" -> "hello world"

    """
    if not text:
        return ""

    return unquote(str(text))


def ensure_trailing_slash(url: str) -> str:
    """
    Ensure URL ends with a trailing slash.

    This is useful for constructing URLs to index files or ensuring
    consistent URL formatting.

    Args:
        url: URL to process

    Returns:
        URL with trailing slash

    Example:
        {{ page_url | ensure_trailing_slash }}
        # "https://example.com/docs" -> "https://example.com/docs/"
        # "https://example.com/docs/" -> "https://example.com/docs/"

    """
    if not url:
        return "/"

    return url if url.endswith("/") else url + "/"


def build_artifact_url(site: SiteLike, filename: str = "build.json", dir_name: str = "") -> str:
    """
    Compute URL for build artifacts (build.json, build.svg).

    Handles all deployment scenarios:
    - Local dev server (no baseurl)
    - Production with baseurl (e.g., GitHub Pages at /my-repo/)
    - i18n prefix strategy (artifacts in language subdirectories)

    Args:
        site: Site instance for config access
        filename: Artifact filename (default: "build.json")
        dir_name: Directory name for artifacts (default: from config or "bengal")

    Returns:
        Absolute URL to the build artifact

    Example:
        {{ build_artifact_url('build.json') }}
        # Output: /bengal/build.json (no baseurl)
        # Output: /my-repo/bengal/build.json (with baseurl)
        # Output: /fr/bengal/build.json (i18n prefix, French)

    """
    config = getattr(site, "config", {}) or {}

    # Get dir_name from argument or config
    if not dir_name:
        build_badge_cfg = config.get("build_badge", {})
        if isinstance(build_badge_cfg, dict):
            dir_name = str(build_badge_cfg.get("dir_name", "bengal"))
        else:
            dir_name = "bengal"

    # Get baseurl - use site.baseurl property for proper nested config access
    baseurl = str(site.baseurl or "").rstrip("/")

    # Check for i18n prefix strategy
    prefix = ""
    i18n = config.get("i18n", {}) or {}
    if i18n.get("strategy") == "prefix":
        current_lang = getattr(site, "current_language", None) or i18n.get("default_language", "en")
        default_lang = i18n.get("default_language", "en")
        default_in_subdir = bool(i18n.get("default_in_subdir", False))
        if default_in_subdir or str(current_lang) != str(default_lang):
            prefix = f"/{current_lang}"

    # Build the path
    path = f"{prefix}/{dir_name}/{filename}".replace("//", "/")

    # Prepend baseurl if configured
    if baseurl:
        return f"{baseurl}{path}"

    return path


def url_parse(url: str | None) -> dict:
    """
    Parse URL into components.

    Args:
        url: URL string to parse

    Returns:
        Dictionary with scheme, host, path, query, fragment, and params

    Example:
        {% let parts = url | url_parse %}
        {{ parts.scheme }}    {# "https" #}
        {{ parts.host }}      {# "example.com" #}
        {{ parts.path }}      {# "/docs/api" #}
        {{ parts.query }}     {# "version=2" #}
        {{ parts.params.version }}  {# ["2"] #}

    """
    if not url:
        return {
            "scheme": "",
            "host": "",
            "path": "",
            "query": "",
            "fragment": "",
            "params": {},
        }

    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "host": parsed.netloc,
        "path": parsed.path,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "params": dict(parse_qs(parsed.query)),
    }


def url_param(url: str | None, param: str, default: str = "") -> str:
    """
    Extract a single query parameter from URL.

    Args:
        url: URL string to parse
        param: Parameter name to extract
        default: Default value if parameter not found

    Returns:
        Parameter value or default

    Example:
        {{ "https://example.com?page=2&sort=date" | url_param('page') }}  # "2"
        {{ url | url_param('missing', 'default') }}  # "default"

    """
    if not url:
        return default

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    values = params.get(param, [])
    return values[0] if values else default


def url_query(data: dict | None) -> str:
    """
    Build query string from dictionary.

    Args:
        data: Dictionary of query parameters

    Returns:
        URL-encoded query string

    Example:
        {{ {'q': 'test', 'page': 1} | url_query }}  # "q=test&page=1"
        {{ filters | url_query }}

    """
    if not data:
        return ""

    return urlencode(data, doseq=True)

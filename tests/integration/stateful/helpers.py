"""
Helper utilities for stateful integration tests.

Provides functions for creating temp sites, tracking builds,
and verifying outputs.
"""

import hashlib
import shutil
import tempfile
from pathlib import Path


def create_temp_site(name: str = "test_site") -> Path:
    """
    Create a temporary site directory with basic structure.

    Returns:
        Path to site root directory
    """
    tmpdir = Path(tempfile.mkdtemp(prefix=f"bengal_{name}_"))

    # Create basic structure
    (tmpdir / "content").mkdir()
    (tmpdir / "themes").mkdir()
    (tmpdir / "themes" / "default").mkdir()
    (tmpdir / "themes" / "default" / "templates").mkdir()
    (tmpdir / "public").mkdir()

    # Create minimal config
    config_content = """
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
"""
    (tmpdir / "bengal.toml").write_text(config_content)

    # Create minimal template
    template_content = """
<!DOCTYPE html>
<html>
<head><title>{{ page.title }}</title></head>
<body>
<h1>{{ page.title }}</h1>
{{ page.content }}
</body>
</html>
"""
    (tmpdir / "themes" / "default" / "templates" / "default.html").write_text(template_content)

    return tmpdir


def write_page(site_dir: Path, rel_path: str, title: str, content: str = "") -> Path:
    """
    Write a content page to the site.

    Args:
        site_dir: Site root directory
        rel_path: Relative path from content/ (e.g., "blog/post.md")
        title: Page title
        content: Page content (optional)

    Returns:
        Path to created page file
    """
    page_path = site_dir / "content" / rel_path
    page_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = f"""---
title: "{title}"
---

"""
    full_content = frontmatter + (content or f"Content for {title}")
    page_path.write_text(full_content)

    return page_path


def delete_page(site_dir: Path, rel_path: str) -> None:
    """
    Delete a content page from the site.

    Args:
        site_dir: Site root directory
        rel_path: Relative path from content/ (e.g., "blog/post.md")
    """
    page_path = site_dir / "content" / rel_path
    if page_path.exists():
        page_path.unlink()


def run_build(site_dir: Path, incremental: bool = False) -> dict[str, any]:
    """
    Run a build and return results.

    Args:
        site_dir: Site root directory
        incremental: Whether to run incremental build

    Returns:
        Dict with build results:
        - output_files: Set of generated file paths
        - success: Whether build succeeded
        - errors: List of error messages
    """
    try:
        # Import here to avoid circular deps
        from bengal.core.site import Site
        from bengal.orchestration.build.options import BuildOptions

        # Load site from config file
        site = Site.from_config(site_dir)

        # Run build using site's build method
        site.build(BuildOptions(incremental=incremental))

        # Collect output files
        output_dir = site.output_dir
        output_files = set()
        if output_dir.exists():
            for file in output_dir.rglob("*"):
                if file.is_file():
                    output_files.add(file.relative_to(output_dir))

        return {
            "output_files": output_files,
            "success": True,
            "errors": [],
        }

    except Exception as e:
        import traceback

        return {
            "output_files": set(),
            "success": False,
            "errors": [str(e), traceback.format_exc()],
        }


def hash_outputs(site_dir: Path) -> dict[str, str]:
    """
    Hash all output files for comparison.

    Args:
        site_dir: Site root directory

    Returns:
        Dict mapping relative paths to SHA256 hashes
    """
    output_dir = site_dir / "public"
    hashes = {}

    if output_dir.exists():
        for file in output_dir.rglob("*"):
            if file.is_file():
                # Compute hash
                sha256 = hashlib.sha256()
                sha256.update(file.read_bytes())

                # Store with relative path
                rel_path = str(file.relative_to(output_dir))
                hashes[rel_path] = sha256.hexdigest()

    return hashes


def extract_internal_links(site_dir: Path, html_file: Path) -> set[str]:
    """
    Extract internal links from an HTML file.

    Args:
        site_dir: Site root directory
        html_file: Path to HTML file (absolute or relative to public/)

    Returns:
        Set of internal link URLs (e.g., {"/about/", "/blog/"})
    """
    import re

    if not html_file.is_absolute():
        html_file = site_dir / "public" / html_file

    if not html_file.exists():
        return set()

    content = html_file.read_text()

    # Find all href attributes
    # Simple regex (not perfect but good enough for testing)
    links = re.findall(r'href=["\'](/[^"\']*)["\']', content)

    return set(links)


def link_target_exists(site_dir: Path, link_url: str) -> bool:
    """
    Check if a link target exists in the output.

    Args:
        site_dir: Site root directory
        link_url: Link URL (e.g., "/about/", "/blog/post/")

    Returns:
        True if target file exists
    """
    output_dir = site_dir / "public"

    # Remove leading slash
    url_path = link_url.lstrip("/")

    # Try different potential file locations
    candidates = [
        output_dir / url_path,  # Exact match
        output_dir / url_path / "index.html",  # Directory index
        output_dir / f"{url_path}.html",  # HTML file
    ]

    return any(c.exists() for c in candidates)


def clean_site(site_dir: Path) -> None:
    """
    Clean up a temporary site directory.

    Args:
        site_dir: Site root directory to remove
    """
    if site_dir.exists():
        shutil.rmtree(site_dir)


def get_cache_path(site_dir: Path) -> Path:
    """
    Get path to build cache file.

    Args:
        site_dir: Site root directory

    Returns:
        Path to cache file (base path, actual file may be .json or .json.zst)
    """
    return site_dir / ".bengal" / "cache.json"


def cache_exists(site_dir: Path) -> bool:
    """Check if build cache exists (handles both .json and .json.zst formats)."""
    base_path = get_cache_path(site_dir)
    return base_path.exists() or base_path.with_suffix(".json.zst").exists()


def read_cache_size(site_dir: Path) -> int:
    """
    Get number of entries in cache.

    Returns:
        Number of cached items, or 0 if cache doesn't exist
    """
    cache_path = get_cache_path(site_dir)
    if not cache_path.exists():
        return 0

    import json

    try:
        cache_data = json.loads(cache_path.read_text())
        return len(cache_data.get("files", {}))
    except Exception:
        return 0

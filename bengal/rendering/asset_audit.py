"""Audit rendered HTML for local CSS/JS references that are not serveable."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

LOCAL_CSS_JS_RE = re.compile(r"""(?:href|src)=["']([^"']+\.(?:css|js)(?:\?[^"']*)?)["']""")


@dataclass(frozen=True, slots=True)
class MissingAssetReference:
    html_path: Path
    url: str
    expected_path: Path


def find_missing_local_asset_references(
    output_dir: Path,
    baseurl: str = "",
    html_paths: Iterable[Path] | None = None,
) -> list[MissingAssetReference]:
    """Find local CSS/JS URLs in rendered HTML that do not exist on disk.

    A site references the same handful of theme assets (CSS/JS) from every page, so
    existence is memoized by resolved path — the output tree is stable for the
    duration of the audit, and the naive code otherwise stats the same files
    thousands of times.

    Args:
        output_dir: Site output root.
        baseurl: Site baseurl, used to normalize a base path prefix.
        html_paths: Explicit HTML paths to scan; when None, the full output tree is
            walked (``rglob``) so hand-authored, special-page, and fragment-cached
            references are all covered — never narrowed to render-tracked assets.
    """
    if not output_dir.exists():
        return []

    base_prefix = _normalized_base_prefix(baseurl)
    from_rglob = html_paths is None
    candidates = html_paths if html_paths is not None else output_dir.rglob("*.html")
    missing: list[MissingAssetReference] = []
    exists_cache: dict[str, bool] = {}
    for html_path in candidates:
        if html_path.suffix.lower() != ".html":
            continue
        if not html_path.is_absolute():
            html_path = output_dir / html_path
        for ref_path, raw_url, resolved in _extract_refs(
            html_path, output_dir, base_prefix, from_rglob
        ):
            expected = output_dir / resolved.lstrip("/")
            exists = exists_cache.get(resolved)
            if exists is None:
                exists = expected.exists()
                exists_cache[resolved] = exists
            if not exists:
                missing.append(
                    MissingAssetReference(
                        html_path=ref_path,
                        url=raw_url,
                        expected_path=expected,
                    )
                )
    return missing


def _extract_refs(
    html_path: Path, output_dir: Path, base_prefix: str, from_rglob: bool
) -> list[tuple[Path, str, str]]:
    """Extract local CSS/JS references from one HTML file (no asset exists() check).

    Mirrors the serial scanner exactly so parallel and serial findings are identical.
    Returns ``(html_path, raw_url, resolved_path)`` tuples in document order.
    """
    # rglob only yields paths that exist; only stat when callers pass paths in. A file
    # that vanishes before read_text still raises OSError, handled below.
    if not from_rglob and not html_path.exists():
        return []
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        html_rel = html_path.relative_to(output_dir)
    except ValueError:
        return []
    refs: list[tuple[Path, str, str]] = []
    for raw_url in LOCAL_CSS_JS_RE.findall(html):
        parsed = urlparse(raw_url)
        if parsed.scheme or parsed.netloc or parsed.path.startswith("//"):
            continue
        resolved = _resolve_asset_path(parsed.path, html_rel)
        if base_prefix != "/" and resolved.startswith(base_prefix):
            resolved = "/" + resolved[len(base_prefix) :]
        if not resolved.endswith((".css", ".js")):
            continue
        refs.append((html_path, raw_url, resolved))
    return refs


def _normalized_base_prefix(baseurl: str) -> str:
    if not isinstance(baseurl, str):
        return "/"
    base = baseurl.strip()
    if not base:
        return "/"
    parsed = urlparse(base)
    if parsed.scheme or parsed.netloc:
        base = parsed.path
    if not base:
        return "/"
    if not base.startswith("/"):
        base = f"/{base}"
    return f"{base.rstrip('/')}/"


def _resolve_asset_path(path: str, html_rel: Path) -> str:
    if path.startswith("/"):
        return posixpath.normpath(path)
    html_parent = html_rel.parent.as_posix()
    if html_parent == ".":
        html_parent = ""
    return posixpath.normpath(f"/{html_parent}/{path}")

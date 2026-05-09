"""Audit rendered HTML for local CSS/JS references that are not serveable."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pathlib import Path

LOCAL_CSS_JS_RE = re.compile(r"""(?:href|src)=["']([^"']+\.(?:css|js)(?:\?[^"']*)?)["']""")


@dataclass(frozen=True, slots=True)
class MissingAssetReference:
    html_path: Path
    url: str
    expected_path: Path


def find_missing_local_asset_references(
    output_dir: Path, baseurl: str = ""
) -> list[MissingAssetReference]:
    """Find local CSS/JS URLs in rendered HTML that do not exist on disk."""
    if not output_dir.exists():
        return []

    missing: list[MissingAssetReference] = []
    base_prefix = f"{baseurl.rstrip('/')}/" if baseurl else "/"
    for html_path in output_dir.rglob("*.html"):
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError:
            continue
        html_rel = html_path.relative_to(output_dir)
        for raw_url in LOCAL_CSS_JS_RE.findall(html):
            parsed = urlparse(raw_url)
            if parsed.scheme or parsed.netloc or parsed.path.startswith("//"):
                continue
            resolved = _resolve_asset_path(parsed.path, html_rel)
            if base_prefix != "/" and resolved.startswith(base_prefix):
                resolved = "/" + resolved[len(base_prefix) :]
            if not resolved.endswith((".css", ".js")):
                continue
            expected = output_dir / resolved.lstrip("/")
            if not expected.exists():
                missing.append(
                    MissingAssetReference(
                        html_path=html_path,
                        url=raw_url,
                        expected_path=expected,
                    )
                )
    return missing


def _resolve_asset_path(path: str, html_rel: Path) -> str:
    if path.startswith("/"):
        return posixpath.normpath(path)
    html_parent = html_rel.parent.as_posix()
    if html_parent == ".":
        html_parent = ""
    return posixpath.normpath(f"/{html_parent}/{path}")

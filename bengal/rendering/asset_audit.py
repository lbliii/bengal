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

# Below this output-file count the per-file scan runs serially — the pool isn't worth it,
# and it keeps small sites (and the whole test-suite) on the exact serial path. Larger
# builds (esp. content-heavy docs/autodoc, where this audit re-reads big rendered HTML and
# is the dominant phase) parallelize the read+regex across a WorkScope.
_PARALLEL_FILE_THRESHOLD = 48


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
    files: list[Path] = []
    for html_path in candidates:
        if html_path.suffix.lower() != ".html":
            continue
        if not html_path.is_absolute():
            html_path = output_dir / html_path
        files.append(html_path)

    # Phase 1 — extract (html_path, raw_url, resolved) per file. Pure and independent, so
    # the read+regex parallelizes across a WorkScope on large builds. Document order is
    # preserved (results re-indexed) so findings are byte-identical to the serial scan.
    per_file = _scan_files(files, output_dir, base_prefix, from_rglob)

    # Phase 2 — one memoized exists() per UNIQUE resolved path. Serial, tiny, preserves order.
    missing: list[MissingAssetReference] = []
    exists_cache: dict[str, bool] = {}
    for refs in per_file:
        for ref_path, raw_url, resolved in refs:
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


def _scan_files(
    files: list[Path], output_dir: Path, base_prefix: str, from_rglob: bool
) -> list[list[tuple[Path, str, str]]]:
    """Extract refs for each file in document order; parallel for large builds.

    Parallel work goes through WorkScope (never a bare ThreadPoolExecutor) so it inherits
    shutdown-safety, context propagation, and timeout enforcement. asset extraction is
    per-file independent (read + regex on a thread-local string), so it scales well and is
    not gated by the shared-object coherency cost that limits the render phase.
    """
    if len(files) < _PARALLEL_FILE_THRESHOLD:
        return [_extract_refs(f, output_dir, base_prefix, from_rglob) for f in files]

    from bengal.utils.concurrency.work_scope import WorkScope
    from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers

    workers = get_optimal_workers(len(files), workload_type=WorkloadType.IO_BOUND)
    if workers <= 1:
        return [_extract_refs(f, output_dir, base_prefix, from_rglob) for f in files]

    # Typed (not a lambda) so the WorkResult value type is inferred and unpacking is sound.
    def scan_indexed(indexed: tuple[int, Path]) -> tuple[int, list[tuple[Path, str, str]]]:
        index, path = indexed
        return index, _extract_refs(path, output_dir, base_prefix, from_rglob)

    out: list[list[tuple[Path, str, str]]] = [[] for _ in files]
    with WorkScope("asset_audit", max_workers=workers) as scope:
        results = scope.map(scan_indexed, list(enumerate(files)))
    for result in results:
        if result.ok and result.value is not None:
            idx, refs = result.value
            out[idx] = refs
    return out


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

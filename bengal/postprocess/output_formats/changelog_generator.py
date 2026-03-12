"""
Build changelog generator for Bengal SSG.

Generates /changelog.json recording what changed in the most recent build —
pages added, modified, or removed, with content hashes. Enables O(1) polling
for agents instead of O(n) per-page checks.

Output Format:
    {
      "build_id": "2026-03-11T14:30:00Z",
      "previous_build_id": "2026-03-10T09:15:00Z",
      "pages_added": ["/docs/new-feature/"],
      "pages_modified": [
        {"url": "/docs/install/", "previous_hash": "a1b2...", "current_hash": "c3d4..."}
      ],
      "pages_removed": ["/docs/deprecated/"],
      "stats": {"total_pages": 142, "added": 1, "modified": 1, "removed": 1}
    }

Configuration:
    [output_formats]
    site_wide = ["index_json", "llm_full", "llms_txt", "changelog"]

Related:
- bengal.postprocess.output_formats: OutputFormatsGenerator facade
- bengal.postprocess.output_formats.json_generator: content_hash per page
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.postprocess.output_formats.utils import get_i18n_output_path, get_page_url
from bengal.utils.io.atomic_write import AtomicFile
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)


class ChangelogGenerator:
    """Generate changelog.json — build diff for agent polling."""

    def __init__(self, site: SiteLike) -> None:
        self.site = site

    def generate(self, pages: list[PageLike]) -> Path | None:
        """Generate changelog.json at site root.

        Args:
            pages: Pre-filtered list of pages (ai_input-permitted)

        Returns:
            Path to changelog.json, or None if generation skipped
        """
        output_path = get_i18n_output_path(self.site, "changelog.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        build_time = getattr(self.site, "build_time", None)
        build_id = (
            build_time.isoformat()
            if isinstance(build_time, datetime)
            else datetime.now().isoformat()
        )

        current_map: dict[str, str] = {}
        for page in pages:
            if not page.output_path:
                continue
            url = get_page_url(page, self.site)
            plain = getattr(page, "plain_text", "") or ""
            current_map[url] = hashlib.sha256(plain.encode("utf-8")).hexdigest()

        previous: dict[str, Any] = {}
        if output_path.exists():
            try:
                previous = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.debug(
                    "changelog_read_failed",
                    path=str(output_path),
                    error=str(e),
                )

        prev_map: dict[str, str] = previous.get("page_hashes", {})

        pages_added: list[str] = []
        pages_modified: list[dict[str, str]] = []
        pages_removed: list[str] = []

        for url in current_map:
            curr_hash = current_map[url]
            prev_hash = prev_map.get(url)
            if prev_hash is None:
                pages_added.append(url)
            elif prev_hash != curr_hash:
                pages_modified.append(
                    {
                        "url": url,
                        "previous_hash": prev_hash,
                        "current_hash": curr_hash,
                    }
                )

        pages_removed = [url for url in prev_map if url not in current_map]

        previous_build_id = previous.get("build_id", "")

        changelog: dict[str, Any] = {
            "build_id": build_id,
            "previous_build_id": previous_build_id or None,
            "pages_added": sorted(pages_added),
            "pages_modified": sorted(pages_modified, key=lambda x: x["url"]),
            "pages_removed": sorted(pages_removed),
            "page_hashes": current_map,
            "stats": {
                "total_pages": len(current_map),
                "added": len(pages_added),
                "modified": len(pages_modified),
                "removed": len(pages_removed),
            },
        }

        with AtomicFile(output_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2, ensure_ascii=False)

        logger.info(
            "changelog_generated",
            path=str(output_path),
            added=len(pages_added),
            modified=len(pages_modified),
            removed=len(pages_removed),
        )
        return output_path

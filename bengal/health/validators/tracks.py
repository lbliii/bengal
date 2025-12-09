"""Track validator for health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class TrackValidator(BaseValidator):
    """
    Validates track definitions and track item references.

    Checks:
    - Track data structure validity
    - Track items reference existing pages
    - Track pages have valid track_id
    """

    name = "Tracks"
    description = "Validates learning track definitions and page references"
    enabled_by_default = True

    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Validate track definitions and references."""
        results = []

        # Check if tracks data exists
        if not hasattr(site.data, "tracks") or not site.data.tracks:
            results.append(
                CheckResult.info(
                    "No tracks defined",
                    "No tracks.yaml file found or tracks data is empty. This is optional.",
                )
            )
            return results

        tracks = site.data.tracks

        # Validate track structure
        for track_id, track in tracks.items():
            if not isinstance(track, dict):
                results.append(
                    CheckResult.error(
                        f"Invalid track structure: {track_id}",
                        f"Track '{track_id}' is not a dictionary. Expected dict with 'title' and 'items' fields.",
                    )
                )
                continue

            # Check required fields
            if "items" not in track:
                results.append(
                    CheckResult.error(
                        f"Track missing 'items' field: {track_id}",
                        f"Track '{track_id}' is missing required 'items' field. Add an 'items' list with page paths.",
                    )
                )
                continue

            if not isinstance(track["items"], list):
                results.append(
                    CheckResult.error(
                        f"Track 'items' must be a list: {track_id}",
                        f"Track '{track_id}' has 'items' field that is not a list. Expected list of page paths.",
                    )
                )
                continue

            # Validate track items reference existing pages
            missing_items = []
            for item_path in track["items"]:
                if not isinstance(item_path, str):
                    results.append(
                        CheckResult.warning(
                            f"Invalid track item type in {track_id}",
                            recommendation=f"Track item must be a string (page path), got {type(item_path).__name__}.",
                        )
                    )
                    continue

                # Use get_page logic to check if page exists
                page = self._get_page(site, item_path)
                if page is None:
                    missing_items.append(item_path)

            if missing_items:
                details_text = (
                    f"The following track items reference pages that don't exist: {', '.join(missing_items[:5])}"
                    + (f" (and {len(missing_items) - 5} more)" if len(missing_items) > 5 else "")
                )
                results.append(
                    CheckResult.warning(
                        f"Track '{track_id}' has {len(missing_items)} missing page(s)",
                        recommendation="Check that page paths in tracks.yaml match actual content files.",
                        details=[details_text],
                    )
                )
            else:
                results.append(
                    CheckResult.success(
                        f"Track '{track_id}' is valid ({len(track['items'])} items)"
                    )
                )

        # Check for track pages with invalid track_id
        track_ids = set(tracks.keys())
        for page in site.pages:
            track_id = page.metadata.get("track_id")
            if track_id and track_id not in track_ids:
                results.append(
                    CheckResult.warning(
                        f"Page '{page.relative_path}' has invalid track_id",
                        recommendation=f"Either add '{track_id}' to tracks.yaml or remove track_id from page metadata.",
                        details=[
                            f"Page references track_id '{track_id}' which doesn't exist in tracks.yaml."
                        ],
                    )
                )

        return results

    def _get_page(self, site: Site, path: str) -> object | None:
        """
        Get page using same logic as get_page template function.

        This mirrors the logic in bengal.rendering.template_functions.get_page
        to ensure validation matches runtime behavior.
        """
        if not path:
            return None

        # Build lookup maps if not already built
        if site._page_lookup_maps is None:
            by_full_path = {}
            by_content_relative = {}

            content_root = site.root_path / "content"

            for p in site.pages:
                by_full_path[str(p.source_path)] = p

                try:
                    rel = p.source_path.relative_to(content_root)
                    rel_str = str(rel).replace("\\", "/")
                    by_content_relative[rel_str] = p
                except ValueError:
                    # Page is not under content root; skip adding to relative map.
                    pass

            site._page_lookup_maps = {"full": by_full_path, "relative": by_content_relative}

        maps = site._page_lookup_maps
        normalized_path = path.replace("\\", "/")

        # Strategy 1: Direct lookup
        if normalized_path in maps["relative"]:
            return maps["relative"][normalized_path]

        # Strategy 2: Try adding .md extension
        path_with_ext = (
            f"{normalized_path}.md" if not normalized_path.endswith(".md") else normalized_path
        )
        if path_with_ext in maps["relative"]:
            return maps["relative"][path_with_ext]

        # Strategy 3: Try full path
        if path in maps["full"]:
            return maps["full"][path]

        return None

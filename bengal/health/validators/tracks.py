"""Track validator for health checks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.build.contracts.keys import content_key
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, CheckStatus
from bengal.utils.paths.normalize import to_posix

if TYPE_CHECKING:
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike


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
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Validate track definitions and references."""
        results: list[CheckResult] = []

        # Check if tracks data exists
        if "tracks" not in site.data or not site.data.tracks:
            results.append(
                CheckResult.info(
                    "No tracks defined",
                    recommendation="No tracks.yaml file found or tracks data is empty. This is optional.",
                )
            )
            return results

        tracks = site.data.tracks
        valid_tracks: list[dict[str, Any]] = []

        # Validate track structure
        for track_id, track in tracks.items():
            # DotDict wraps nested dicts from YAML; unwrap for isinstance check
            raw = getattr(track, "_data", track)
            if not isinstance(raw, dict):
                results.append(
                    CheckResult.error(
                        f"Invalid track structure: {track_id}",
                        code="H801",
                        recommendation=f"Track '{track_id}' is not a dictionary. Expected dict with 'title' and 'items' fields.",
                    )
                )
                continue

            # Check required fields
            if "items" not in track:
                results.append(
                    CheckResult.error(
                        f"Track missing 'items' field: {track_id}",
                        code="H802",
                        recommendation=f"Track '{track_id}' is missing required 'items' field. Add an 'items' list with page paths.",
                    )
                )
                continue

            if not isinstance(track["items"], list):
                results.append(
                    CheckResult.error(
                        f"Track 'items' must be a list: {track_id}",
                        code="H803",
                        recommendation=f"Track '{track_id}' has 'items' field that is not a list. Expected list of page paths.",
                    )
                )
                continue

            # Validate track items reference existing pages
            missing_items = []
            invalid_item_count = 0
            for item_path in track["items"]:
                if not isinstance(item_path, str):
                    invalid_item_count += 1
                    results.append(
                        CheckResult.warning(
                            f"Invalid track item type in {track_id}",
                            code="H804",
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
                        code="H805",
                        recommendation="Check that page paths in tracks.yaml match actual content files.",
                        details=[details_text],
                    )
                )
            elif invalid_item_count == 0:
                valid_tracks.append(
                    {
                        "id": str(track_id),
                        "title": str(track.get("title") or track_id),
                        "items": len(track["items"]),
                    }
                )

        if valid_tracks:
            track_count = len(valid_tracks)
            total_items = sum(track["items"] for track in valid_tracks)
            track_label = "track" if track_count == 1 else "tracks"
            item_label = "item" if total_items == 1 else "items"
            results.append(
                CheckResult(
                    CheckStatus.SUCCESS,
                    f"{track_count} {track_label} valid ({total_items} {item_label} total)",
                    details=[
                        f"{track['id']}: {track['items']} "
                        f"{'item' if track['items'] == 1 else 'items'}"
                        for track in valid_tracks
                    ],
                    metadata={"tracks": valid_tracks, "total_items": total_items},
                )
            )

        # Check for track pages with invalid track_id
        track_ids = set(tracks.keys())
        for page in site.pages:
            track_id = page.metadata.get("track_id")
            if track_id and track_id not in track_ids:
                results.append(
                    CheckResult.warning(
                        f"Page '{page.source_path}' has invalid track_id",
                        code="H806",
                        recommendation=f"Either add '{track_id}' to tracks.yaml or remove track_id from page metadata.",
                        details=[
                            f"Page references track_id '{track_id}' which doesn't exist in tracks.yaml."
                        ],
                    )
                )

        return results

    def _get_page(self, site: SiteLike, path: str) -> object | None:
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
            by_content_key = {}

            content_root = site.root_path / "content"

            for p in site.pages:
                full = (
                    site.root_path / p.source_path
                    if not Path(p.source_path).is_absolute()
                    else Path(p.source_path)
                )
                key = content_key(full, site.root_path)
                by_full_path[key] = p
                by_content_key[key] = p

                try:
                    rel = p.source_path.relative_to(content_root)
                    rel_str = to_posix(rel)
                    by_content_relative[rel_str] = p
                except ValueError:
                    # Page is not under content root; skip adding to relative map.
                    pass

            site._page_lookup_maps = {
                "full": by_full_path,
                "relative": by_content_relative,
                "content_key": by_content_key,
            }

        maps = site._page_lookup_maps
        normalized_path = to_posix(path)

        # Strategy 1: Direct lookup (content-relative)
        if normalized_path in maps["relative"]:
            return maps["relative"][normalized_path]

        # Strategy 2: Try adding .md extension
        path_with_ext = (
            f"{normalized_path}.md" if not normalized_path.endswith(".md") else normalized_path
        )
        if path_with_ext in maps["relative"]:
            return maps["relative"][path_with_ext]

        # Strategy 3: Try content_key format (by_full_path now uses content_key keys)
        if path in maps["full"]:
            return maps["full"][path]

        # Strategy 4: Try content_key (handles path format mismatch)
        for candidate in (normalized_path, path_with_ext):
            key = content_key(site.root_path / "content" / candidate, site.root_path)
            if key in maps["content_key"]:
                return maps["content_key"][key]

        return None

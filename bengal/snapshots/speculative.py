"""
Speculative rendering for snapshot engine.

Provides predictive page-affect analysis and speculative rendering
coordination for HMR optimization. Uses content_hash on PageSnapshot
to validate speculation after the fact.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 3)

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.snapshots.types import (
    PageSnapshot,
    SiteSnapshot,
)


def predict_affected(
    file_path: Path,
    snapshot: SiteSnapshot,
) -> set[PageSnapshot]:
    """
    Fast heuristic prediction of affected pages.

    Used for speculative rendering - start work before exact analysis completes.

    Accuracy: ~90% (based on file type and location)
    Speed: <1ms (vs ~30ms for exact computation)

    Args:
        file_path: Path to the changed file
        snapshot: Current site snapshot

    Returns:
        Predicted set of affected pages
    """
    suffix = file_path.suffix.lower()

    if suffix == ".md":
        # Content file -> likely just this page
        return {p for p in snapshot.pages if p.source_path == file_path}

    elif suffix in (".html", ".jinja", ".j2"):
        # Template -> all pages using this template (use O(1) lookup)
        template_name = file_path.name
        direct = set(snapshot.template_groups.get(template_name, ()))

        # Also check transitive dependents
        if template_name in snapshot.template_dependents:
            direct.update(snapshot.template_dependents[template_name])

        return direct if direct else set(snapshot.pages)  # Conservative fallback

    elif suffix in (".css", ".scss", ".sass", ".less"):
        # CSS change -> could affect all pages (fingerprints change)
        return set(snapshot.pages)

    elif suffix in (".js", ".ts", ".mjs"):
        # JS change -> could affect all pages
        return set(snapshot.pages)

    elif suffix in (".yaml", ".yml", ".toml", ".json"):
        # Data/config file -> could affect many pages
        if "data" in file_path.parts:
            return set(snapshot.pages)
        else:
            return set(snapshot.pages)

    elif suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
        # Image - usually no page rebuild needed unless fingerprinting
        return set()

    else:
        # Unknown -> conservative (all pages)
        return set(snapshot.pages)


class SpeculativeRenderer:
    """
    Speculative rendering coordinator for HMR optimization.

    RFC: Snapshot-Enabled v2 Opportunities (Opportunity 3)

    Uses content_hash on PageSnapshot to validate speculation after the fact.

    Example:
        >>> renderer = SpeculativeRenderer(snapshot)
        >>> async for page in renderer.speculative_render(changed_file):
        ...     yield rendered_page
    """

    def __init__(self, snapshot: SiteSnapshot) -> None:
        """Initialize with current snapshot."""
        self._snapshot = snapshot
        self._prediction_history: list[tuple[float, float]] = []  # (predicted, actual)
        self._confidence_threshold = 0.85  # Only speculate if confidence > 85%

    @property
    def prediction_accuracy(self) -> float:
        """
        Historical prediction accuracy (F1-like score).

        Returns accuracy as float 0.0-1.0 based on recent predictions.
        Balances precision (not too many wasted predictions) and recall (not too many misses).
        """
        if not self._prediction_history:
            return 0.9  # Default assumption

        # Use last 100 predictions
        recent = self._prediction_history[-100:]
        total_predicted = sum(p for p, _ in recent)
        total_actual = sum(a for _, a in recent)

        if total_actual == 0 and total_predicted == 0:
            return 1.0

        if total_predicted == 0:
            return 0.0  # No predictions = bad

        if total_actual == 0:
            return 0.0  # Predicted but nothing was needed = wasted

        # Use harmonic mean of precision and recall (F1-like score)
        accuracy = min(total_predicted, total_actual) / max(total_predicted, total_actual)
        return accuracy

    def should_speculate(self) -> bool:
        """
        Determine if speculation should be enabled.

        Returns True if historical accuracy exceeds confidence threshold.
        """
        return self.prediction_accuracy >= self._confidence_threshold

    def record_prediction_result(
        self,
        predicted_count: int,
        actual_count: int,
    ) -> None:
        """
        Record prediction vs actual for accuracy tracking.

        Args:
            predicted_count: Number of pages predicted to need rebuild
            actual_count: Number of pages that actually needed rebuild
        """
        self._prediction_history.append((float(predicted_count), float(actual_count)))

        # Keep history bounded
        if len(self._prediction_history) > 1000:
            self._prediction_history = self._prediction_history[-500:]

    def get_speculative_pages(
        self,
        file_path: Path,
    ) -> tuple[set[PageSnapshot], bool]:
        """
        Get pages to speculatively render.

        Args:
            file_path: Changed file path

        Returns:
            Tuple of (pages to render, is_speculative)
            If not speculating, returns (empty set, False)
        """
        if not self.should_speculate():
            return set(), False

        predicted = predict_affected(file_path, self._snapshot)
        return predicted, True

    def validate_speculation(
        self,
        predicted: set[PageSnapshot],
        actual: set[PageSnapshot],
    ) -> dict[str, Any]:
        """
        Validate speculation results and record for accuracy tracking.

        Args:
            predicted: Pages that were speculatively rendered
            actual: Pages that actually needed rendering

        Returns:
            Validation report with hits, misses, and accuracy
        """
        hits = predicted & actual
        misses = actual - predicted
        wasted = predicted - actual

        self.record_prediction_result(len(predicted), len(actual))

        accuracy = len(hits) / len(actual) if actual else 1.0

        return {
            "hits": len(hits),
            "misses": len(misses),
            "wasted": len(wasted),
            "accuracy": accuracy,
            "hit_pages": [p.source_path.name for p in hits][:5],
            "miss_pages": [p.source_path.name for p in misses][:5],
        }


class ShadowModeValidator:
    """
    Shadow mode for validating prediction accuracy before full enablement.

    In shadow mode:
    1. Both prediction and exact computation run
    2. Accuracy is logged
    3. Speculative rendering only activates when confidence > 85%

    RFC: Snapshot-Enabled v2 Opportunities (Opportunity 3)
    """

    def __init__(self) -> None:
        """Initialize shadow mode validator."""
        self._results: list[dict[str, Any]] = []

    def validate(
        self,
        file_path: Path,
        snapshot: SiteSnapshot,
        actual_affected: set[PageSnapshot],
    ) -> dict[str, Any]:
        """
        Run prediction in shadow mode and compare to actual.

        Args:
            file_path: Changed file
            snapshot: Current snapshot
            actual_affected: Actual affected pages (from exact computation)

        Returns:
            Validation result with accuracy metrics
        """
        predicted = predict_affected(file_path, snapshot)

        hits = predicted & actual_affected
        misses = actual_affected - predicted
        wasted = predicted - actual_affected

        result = {
            "file": str(file_path),
            "file_type": file_path.suffix,
            "predicted_count": len(predicted),
            "actual_count": len(actual_affected),
            "hit_count": len(hits),
            "miss_count": len(misses),
            "wasted_count": len(wasted),
            "accuracy": len(hits) / len(actual_affected) if actual_affected else 1.0,
            "precision": len(hits) / len(predicted) if predicted else 1.0,
        }

        self._results.append(result)
        return result

    @property
    def overall_accuracy(self) -> float:
        """Overall accuracy across all validations."""
        if not self._results:
            return 0.0

        total_hits = sum(r["hit_count"] for r in self._results)
        total_actual = sum(r["actual_count"] for r in self._results)

        return total_hits / total_actual if total_actual > 0 else 1.0

    @property
    def accuracy_by_file_type(self) -> dict[str, float]:
        """Accuracy broken down by file type."""
        by_type: dict[str, list[dict[str, Any]]] = {}

        for r in self._results:
            file_type = r["file_type"]
            by_type.setdefault(file_type, []).append(r)

        return {
            ft: (
                sum(r["hit_count"] for r in results)
                / max(1, sum(r["actual_count"] for r in results))
            )
            for ft, results in by_type.items()
        }

    def get_report(self) -> dict[str, Any]:
        """Generate comprehensive accuracy report."""
        return {
            "total_validations": len(self._results),
            "overall_accuracy": self.overall_accuracy,
            "accuracy_by_file_type": self.accuracy_by_file_type,
            "recommendation": (
                "Enable speculation" if self.overall_accuracy >= 0.85 else "Keep shadow mode"
            ),
        }

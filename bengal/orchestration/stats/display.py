"""Build statistics display compatibility wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.output import CLIOutput  # Backward-compatible patch target for tests.
import bengal.output.build_stats_presenter as _presenter

if TYPE_CHECKING:
    from bengal.orchestration.stats.models import BuildStats
    from bengal.utils.stats_protocol import DisplayableStats


def display_simple_build_stats(stats: BuildStats, output_dir: str | None = None) -> None:
    """Backward-compatible wrapper for simple stats display."""
    _presenter.CLIOutput = CLIOutput
    _presenter.display_simple_build_stats(stats, output_dir=output_dir)


def display_build_stats(
    stats: DisplayableStats, show_art: bool = True, output_dir: str | None = None
) -> None:
    """Backward-compatible wrapper for rich stats display."""
    _presenter.CLIOutput = CLIOutput
    _presenter.display_build_stats(stats, show_art=show_art, output_dir=output_dir)

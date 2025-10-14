from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.cache.dependency_tracker import DependencyTracker
    from bengal.core.asset import Asset
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.utils.build_stats import BuildStats
    from bengal.utils.live_progress import LiveProgressManager
    from bengal.utils.profile import BuildProfile
    from bengal.utils.progress import ProgressReporter


@dataclass
class BuildContext:
    """
    Shared build context passed across orchestrators.

    Introduced to reduce implicit global state usage and make dependencies explicit.
    Fields are optional to maintain backward compatibility while we thread this through.
    """

    site: Site | None = None
    pages: list[Page] | None = None
    assets: list[Asset] | None = None
    tracker: DependencyTracker | None = None
    stats: BuildStats | None = None
    profile: BuildProfile | None = None
    progress_manager: LiveProgressManager | None = None
    reporter: ProgressReporter | None = None

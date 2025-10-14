from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BuildContext:
    """
    Shared build context passed across orchestrators.

    Introduced to reduce implicit global state usage and make dependencies explicit.
    Fields are optional to maintain backward compatibility while we thread this through.
    """

    site: Any | None = None
    pages: list[Any] | None = None
    assets: list[Any] | None = None
    tracker: Any | None = None
    stats: Any | None = None
    profile: Any | None = None
    progress_manager: Any | None = None
    reporter: Any | None = None

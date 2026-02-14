"""
DX (Developer Experience) utilities.

Provides environment detection and contextual hints for Docker, WSL,
Kubernetes, and other deployment contexts.
"""

from bengal.utils.dx.detection import (
    is_ci,
    is_docker,
    is_kubernetes,
    is_wsl,
    is_wsl_windows_drive,
)
from bengal.utils.dx.hints import Hint, collect_hints

__all__ = [
    "Hint",
    "collect_hints",
    "is_ci",
    "is_docker",
    "is_kubernetes",
    "is_wsl",
    "is_wsl_windows_drive",
]

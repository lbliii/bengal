"""
Skeleton system for Bengal site scaffolding.

This package provides the skeleton system used by the `bengal new` command
to scaffold new sites. Skeletons define the directory structure, files,
and configuration for different types of sites.

Classes:
    Skeleton: Defines a complete site skeleton with components
    Component: Individual component within a skeleton (directory, file, etc.)
    Hydrator: Processes and renders skeleton templates

Related:
    - bengal/cli/commands/new/: New site command implementation
    - bengal/cli/templates/: Site templates that use skeletons
"""

from __future__ import annotations

from .hydrator import Hydrator
from .schema import Component, Skeleton

__all__ = ["Component", "Hydrator", "Skeleton"]

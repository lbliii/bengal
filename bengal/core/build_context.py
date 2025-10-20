"""
Compatibility shim for BuildContext.

Historically, `BuildContext` was defined here under `bengal.core`. The
canonical definition now lives in `bengal.utils.build_context`. Import and
re-export to maintain backward compatibility with older imports.
"""

# Re-export canonical BuildContext

from __future__ import annotations

from bengal.utils.build_context import BuildContext  # noqa: F401

__all__ = ["BuildContext"]

"""
Template engine protocol definitions.

.. deprecated:: 0.2.0
    Import from :mod:`bengal.protocols` instead::
    
        # Old (deprecated)
        from bengal.rendering.engines.protocol import TemplateEngineProtocol
        
        # New (preferred)
        from bengal.protocols import TemplateEngine, TemplateRenderer

This module re-exports protocols from :mod:`bengal.protocols` for
backwards compatibility. Deprecation warnings are emitted on import.

New Composable Protocols:
    The monolithic TemplateEngineProtocol has been split into focused protocols:
    - TemplateRenderer: Core rendering (render_template, render_string)
    - TemplateIntrospector: Discovery (template_exists, get_template_path, list_templates)
    - TemplateValidator: Validation (validate)
    - TemplateEngine: Full engine (combines all three)

See Also:
- :mod:`bengal.protocols`: Canonical protocol definitions
- :mod:`bengal.protocols.rendering`: Template engine protocols

"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

# Re-export from canonical location
from bengal.protocols.rendering import (
    EngineCapability as _EngineCapability,
    TemplateEngine as _TemplateEngine,
    TemplateEngineProtocol as _TemplateEngineProtocol,
    TemplateEnvironment as _TemplateEnvironment,
    TemplateIntrospector as _TemplateIntrospector,
    TemplateRenderer as _TemplateRenderer,
    TemplateValidator as _TemplateValidator,
)

if TYPE_CHECKING:
    # For type checkers, provide direct access without warnings
    from bengal.protocols.rendering import (
        EngineCapability,
        TemplateEngine,
        TemplateEngineProtocol,
        TemplateEnvironment,
        TemplateIntrospector,
        TemplateRenderer,
        TemplateValidator,
    )


def __getattr__(name: str):
    """Emit deprecation warning for old import paths."""
    _exports = {
        "TemplateEnvironment": _TemplateEnvironment,
        "EngineCapability": _EngineCapability,
        "TemplateEngineProtocol": _TemplateEngineProtocol,
        "TemplateEngine": _TemplateEngine,
        "TemplateRenderer": _TemplateRenderer,
        "TemplateIntrospector": _TemplateIntrospector,
        "TemplateValidator": _TemplateValidator,
    }
    
    if name in _exports:
        warnings.warn(
            f"Import {name} from bengal.protocols instead of "
            f"bengal.rendering.engines.protocol. "
            f"This import path will be removed in version 1.0.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _exports[name]
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TemplateEnvironment",
    "EngineCapability",
    "TemplateEngineProtocol",
    "TemplateEngine",
    "TemplateRenderer",
    "TemplateIntrospector",
    "TemplateValidator",
]

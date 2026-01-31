"""
Configuration validation for required keys.

.. deprecated:: 0.3.0
    This module is deprecated. Import from :mod:`bengal.config.validators` instead.

    The functionality has been consolidated into validators.py for a single
    validation entry point. This module remains for backward compatibility
    but re-exports from validators.py.

Example:
    >>> # Preferred (new)
    >>> from bengal.config.validators import validate_config, REQUIRED_KEYS

    >>> # Deprecated (still works)
    >>> from bengal.config.validation import validate_config

See Also:
- :mod:`bengal.config.validators`: Consolidated validation module.
- :mod:`bengal.config.loader`: Configuration loading.

"""

from __future__ import annotations

# Re-export from consolidated validators module for backward compatibility
from bengal.config.validators import (
    REQUIRED_KEYS,
    validate_config,
    validate_required_keys,
)

__all__ = [
    "REQUIRED_KEYS",
    "validate_config",
    "validate_required_keys",
]

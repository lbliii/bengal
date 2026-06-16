"""Diagnostics adapter — the only Bengal-specific coupling in ``bengal/css/``.

Extraction into a standalone package means swapping this one module for a local
logger; everything else in the subpackage is plain stdlib.
"""

from bengal.utils.observability.logger import get_logger

_logger = get_logger("bengal.css")


def warn(event: str, **fields: object) -> None:
    """Emit a structured warning diagnostic."""
    _logger.warning(event, **fields)

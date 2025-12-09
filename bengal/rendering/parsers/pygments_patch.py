"""
Pygments performance patch for python-markdown.

This module provides a process-wide performance optimization that replaces
Pygments' lexer lookup functions with cached versions. This avoids expensive
plugin discovery on every code block during markdown rendering.

Performance Impact (826-page site):
    - Before: 86s (73% in plugin discovery)
    - After: ~29s (3× faster)

Warning:
    This patch affects the global markdown.extensions.codehilite module state.
    It is safe for CLI tools and single-process applications, but may not be
    suitable for multi-tenant web applications.

Usage:

```python
# One-time application (typical usage):
PygmentsPatch.apply()

# Temporary patching (for testing):
with PygmentsPatch():
    # Patch is active here
    parser.parse(content)
# Patch is removed here
```
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class PygmentsPatch:
    """
    Context manager and utility class for patching Pygments lexer lookups.

    This patch replaces expensive Pygments plugin discovery with cached lexer
    instances, dramatically improving markdown parsing performance.

    The patch is applied at the module level to markdown.extensions.codehilite,
    affecting all uses of that module in the current process.

    Attributes:
        _patched: Class-level flag indicating if patch is currently active
        _codehilite_module: Reference to the patched module (if active)
        _originals: Saved original functions for restoration
    """

    _patched: bool = False
    _codehilite_module: ModuleType | None = None
    _originals: dict[str, Any] = {}

    def __init__(self) -> None:
        """Initialize the patch context manager."""
        self._context_applied = False

    def __enter__(self) -> PygmentsPatch:
        """Apply the patch on context enter."""
        if not self._patched:
            self.apply()
            self._context_applied = True
        return self

    def __exit__(self, *args: Any) -> None:
        """Remove the patch on context exit."""
        if self._context_applied:
            self.restore()
            self._context_applied = False

    @classmethod
    def apply(cls) -> bool:
        """
        Apply the Pygments caching patch to markdown.extensions.codehilite.

        This method is idempotent - calling it multiple times is safe.

        Returns:
            bool: True if patch was applied, False if already applied or failed.
        """
        if cls._patched:
            logger.debug("pygments_patch_already_applied")
            return False

        try:
            from markdown.extensions import codehilite

            from bengal.rendering.pygments_cache import get_lexer_cached

            # Save originals for restoration
            cls._codehilite_module = codehilite
            cls._originals = {
                "get_lexer_by_name": codehilite.get_lexer_by_name,
                "guess_lexer": codehilite.guess_lexer,
            }

            # Create patched versions using cached lexer lookup
            def cached_get_lexer_by_name(lang: str, **options: Any) -> Any:
                """Cached version of get_lexer_by_name."""
                return get_lexer_cached(language=lang)

            def cached_guess_lexer(code: str, **options: Any) -> Any:
                """Cached version of guess_lexer."""
                return get_lexer_cached(code=code)

            # Apply patches to module
            codehilite.get_lexer_by_name = cached_get_lexer_by_name
            codehilite.guess_lexer = cached_guess_lexer

            cls._patched = True

            logger.debug(
                "pygments_patch_applied",
                target="markdown.extensions.codehilite",
                patched=["get_lexer_by_name", "guess_lexer"],
                scope="process-wide",
            )
            return True

        except ImportError as e:
            # codehilite not available, skip patching
            logger.debug("pygments_patch_skipped", reason="codehilite_unavailable", error=str(e))
            return False
        except Exception as e:
            logger.warning("pygments_patch_failed", error=str(e), error_type=type(e).__name__)
            return False

    @classmethod
    def restore(cls) -> bool:
        """
        Restore the original Pygments functions.

        This removes the patch and restores the original behavior.
        Primarily useful for testing.

        Returns:
            bool: True if patch was restored, False if not currently patched.
        """
        if not cls._patched:
            logger.debug("pygments_patch_not_active", action="restore_skipped")
            return False

        try:
            if cls._codehilite_module is None or not cls._originals:
                logger.warning("pygments_patch_restore_failed", reason="missing_references")
                return False

            # Restore original functions
            codehilite = cls._codehilite_module
            codehilite.get_lexer_by_name = cls._originals["get_lexer_by_name"]  # type: ignore[attr-defined]
            codehilite.guess_lexer = cls._originals["guess_lexer"]  # type: ignore[attr-defined]

            # Clear state
            cls._patched = False
            cls._codehilite_module = None
            cls._originals = {}

            logger.debug("pygments_patch_restored", target="markdown.extensions.codehilite")
            return True

        except Exception as e:
            logger.error(
                "pygments_patch_restore_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    @classmethod
    def is_patched(cls) -> bool:
        """
        Check if the patch is currently active.

        Returns:
            bool: True if patched, False otherwise.
        """
        return cls._patched

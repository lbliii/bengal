"""
Pygments lexer caching to dramatically improve syntax highlighting performance.

Problem: pygments.lexers.guess_lexer() triggers expensive plugin discovery
via importlib.metadata on EVERY code block, causing 60+ seconds overhead
on large sites with many code blocks.

Solution: Cache lexers by language name to avoid repeated plugin discovery.

Performance Impact (measured on 826-page site):
- Before: 86s (73% in Pygments plugin discovery)
- After: ~29s (3× faster)
"""

import threading

from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Thread-safe lexer cache
_lexer_cache: dict[str, any] = {}
_cache_lock = threading.Lock()

# Stats for monitoring
_cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}


# Known language aliases and non-highlight languages
# Normalize common fence language names that Pygments does not recognize directly
_LANGUAGE_ALIASES: dict[str, str] = {
    # Templating
    "jinja2": "html+jinja",
    "jinja": "html+jinja",
    # Static site ecosystem aliases
    "go-html-template": "html",  # Highlight as HTML rather than warning
}

# Languages that should not be highlighted by Pygments
# These are typically handled by client-side libraries (e.g., Mermaid)
_NO_HIGHLIGHT_LANGUAGES = {
    "mermaid",
}

# Data formats and plain text files that don't have/need lexers
# These will fall back to text rendering without warnings
_QUIET_FALLBACK_LANGUAGES = {
    "csv",
    "tsv",
    "txt",
    "text",
    "log",
    "logs",
    "plain",
    "plaintext",
}


def _normalize_language(language: str) -> str:
    """Normalize a requested language to a Pygments-friendly name.

    Applies alias mapping and lowercases the language name.
    """
    lang_lower = language.lower()
    return _LANGUAGE_ALIASES.get(lang_lower, lang_lower)


def get_lexer_cached(language: str | None = None, code: str = "") -> any:
    """
    Get a Pygments lexer with aggressive caching.

    Strategy:
    1. If language specified: cache by language name (fast path)
    2. If no language: hash code sample and cache guess result
    3. Fallback: return text lexer if all else fails

    Args:
        language: Optional language name (e.g., 'python', 'javascript')
        code: Code content (used for guessing if language not specified)

    Returns:
        Pygments lexer instance

    Performance:
        - Cached lookup: ~0.001ms
        - Uncached lookup: ~30ms (plugin discovery)
        - Cache hit rate: >95% after first few pages
    """
    global _cache_stats

    # Fast path: language specified
    if language:
        normalized = _normalize_language(language)
        cache_key = f"lang:{normalized}"

        with _cache_lock:
            if cache_key in _lexer_cache:
                _cache_stats["hits"] += 1
                return _lexer_cache[cache_key]

            _cache_stats["misses"] += 1

        # Do not attempt highlighting for known non-highlight languages
        if normalized in _NO_HIGHLIGHT_LANGUAGES:
            try:
                lexer = get_lexer_by_name("text")
            except Exception:
                # Extremely unlikely, but ensure we return something
                lexer = get_lexer_by_name("text")
            with _cache_lock:
                _lexer_cache[cache_key] = lexer
            # Use debug level to avoid noisy warnings for expected cases
            logger.debug("no_highlight_language", language=language, normalized=normalized)
            return lexer

        # Data formats that don't have lexers - use text without warnings
        if normalized in _QUIET_FALLBACK_LANGUAGES:
            lexer = get_lexer_by_name("text")
            with _cache_lock:
                _lexer_cache[cache_key] = lexer
            # Debug level - expected behavior, not an issue
            logger.debug(
                "data_format_as_text",
                language=language,
                normalized=normalized,
                note="Data format rendered as plain text (expected)",
            )
            return lexer

        # Try to get lexer by name
        try:
            lexer = get_lexer_by_name(normalized)
            with _cache_lock:
                _lexer_cache[cache_key] = lexer
            logger.debug(
                "lexer_cached", language=language, normalized=normalized, cache_key=cache_key
            )
            return lexer
        except ClassNotFound:
            # Language not recognized by Pygments
            logger.warning(
                "unknown_lexer",
                language=language,
                normalized=normalized,
                fallback="text",
                hint=(
                    f"Language '{language}' not recognized by Pygments. "
                    "Rendering as plain text. "
                    "Check language name spelling or see Pygments docs for supported languages."
                ),
            )
            # Cache the fallback too
            lexer = get_lexer_by_name("text")
            with _cache_lock:
                _lexer_cache[cache_key] = lexer
            return lexer

    # Slow path: guess lexer from code
    # Cache by hash of first 200 chars (representative sample)
    _cache_stats["guess_calls"] += 1

    code_sample = code[:200] if len(code) > 200 else code
    cache_key = f"guess:{hash(code_sample)}"

    with _cache_lock:
        if cache_key in _lexer_cache:
            _cache_stats["hits"] += 1
            return _lexer_cache[cache_key]

        _cache_stats["misses"] += 1

    # Expensive guess operation
    try:
        lexer = guess_lexer(code)
        with _cache_lock:
            _lexer_cache[cache_key] = lexer
        logger.debug("lexer_guessed", guessed_language=lexer.name, cache_key=cache_key[:20])
        return lexer
    except Exception as e:
        logger.warning("lexer_guess_failed", error=str(e), fallback="text")
        lexer = get_lexer_by_name("text")
        with _cache_lock:
            _lexer_cache[cache_key] = lexer
        return lexer


def clear_cache():
    """Clear the lexer cache. Useful for testing or memory management."""
    global _lexer_cache, _cache_stats
    with _cache_lock:
        _lexer_cache.clear()
        _cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}
    logger.info("lexer_cache_cleared")


def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.

    Returns:
        Dict with hits, misses, guess_calls, hit_rate
    """
    with _cache_lock:
        stats = _cache_stats.copy()
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / total if total > 0 else 0
        stats["cache_size"] = len(_lexer_cache)
    return stats


def log_cache_stats():
    """Log cache statistics. Call at end of build for visibility."""
    stats = get_cache_stats()
    logger.info(
        "pygments_cache_stats",
        hits=stats["hits"],
        misses=stats["misses"],
        guess_calls=stats["guess_calls"],
        hit_rate=f"{stats['hit_rate']:.1%}",
        cache_size=stats["cache_size"],
    )


class PygmentsPatch:
    """
    Monkey-patch adapter for Pygments used in tests.

    Provides a context manager and static methods to apply/restore a
    patch that routes markdown.codehilite lookups through our cached
    helpers, without changing public APIs.
    """

    _original_get = None
    _original_guess = None
    _patched = False
    _nesting_count = 0

    def __enter__(self):
        self.apply()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.restore()

    @classmethod
    def apply(cls) -> bool:
        """Apply monkey patches; idempotent. Returns True if applied."""
        if cls._patched:
            # Already patched; bump nesting and return False
            try:
                cls._nesting_count += 1
            except Exception:
                cls._nesting_count = max(1, getattr(cls, "_nesting_count", 0))
            return False
        try:
            from markdown.extensions import codehilite as md_codehilite

            cls._original_get = (
                getattr(md_codehilite, "get_lexer_by_name", None) or md_codehilite.get_lexer_by_name
                if hasattr(md_codehilite, "get_lexer_by_name")
                else None
            )
            cls._original_guess = (
                getattr(md_codehilite, "guess_lexer", None) or md_codehilite.guess_lexer
                if hasattr(md_codehilite, "guess_lexer")
                else None
            )

            def _patched_get_lexer_by_name(name: str, *args, **kwargs):
                return get_lexer_cached(name)

            def _patched_guess_lexer(code: str, *args, **kwargs):
                return get_lexer_cached(None, code)

            md_codehilite.get_lexer_by_name = _patched_get_lexer_by_name
            md_codehilite.guess_lexer = _patched_guess_lexer
            cls._patched = True
            cls._nesting_count = 1
            return True
        except Exception:
            # If codehilite is unavailable, do nothing
            return False

    @classmethod
    def restore(cls) -> bool:
        """Restore original functions; returns True if restoration occurred."""
        if not cls._patched:
            return False
        try:
            from markdown.extensions import codehilite as md_codehilite

            # Decrement nesting and only unpatch when reaching zero
            if cls._nesting_count > 1:
                cls._nesting_count -= 1
                return False
            # Actually restore when exiting outermost context
            if cls._original_get is not None:
                md_codehilite.get_lexer_by_name = cls._original_get
            if cls._original_guess is not None:
                md_codehilite.guess_lexer = cls._original_guess
            cls._patched = False
            cls._nesting_count = 0
            return True
        except Exception:
            # If module is not present, consider restored
            cls._patched = False
            return True

    @classmethod
    def is_patched(cls) -> bool:
        """Return current patch state."""
        return cls._patched

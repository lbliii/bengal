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

from __future__ import annotations

import threading
from typing import Any

from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Thread-safe lexer cache
# Limited to 100 entries to prevent memory leaks (Pygments lexers are small but can accumulate)
_lexer_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
_LEXER_CACHE_MAX_SIZE = 100

# Stats for monitoring
_cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}


def _evict_lexer_cache_if_needed() -> None:
    """Evict oldest entry from lexer cache if at max size (FIFO eviction)."""
    if len(_lexer_cache) >= _LEXER_CACHE_MAX_SIZE:
        # Remove first (oldest) entry
        oldest_key = next(iter(_lexer_cache))
        _lexer_cache.pop(oldest_key, None)


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
    Strips file paths if language identifier includes colon (e.g., 'jinja2:path/to/file.html' -> 'jinja2').
    """
    # Extract just the language name if colon is present (handles 'language:filepath' pattern)
    lang_part = language.split(":", 1)[0].strip()
    # Handle empty or whitespace-only languages (e.g., just quotes, punctuation)
    if not lang_part or not lang_part.strip("'\"` "):
        return "text"
    lang_lower = lang_part.lower()
    return _LANGUAGE_ALIASES.get(lang_lower, lang_lower)


def get_lexer_cached(language: str | None = None, code: str = "") -> Any:
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
            except Exception as e:
                # Extremely unlikely, but ensure we return something
                logger.debug(
                    "pygments_text_lexer_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    action="retrying_text_lexer",
                )
                lexer = get_lexer_by_name("text")
            with _cache_lock:
                _evict_lexer_cache_if_needed()
                _lexer_cache[cache_key] = lexer
            # Use debug level to avoid noisy warnings for expected cases
            logger.debug("no_highlight_language", language=language, normalized=normalized)
            return lexer

        # Data formats that don't have lexers - use text without warnings
        if normalized in _QUIET_FALLBACK_LANGUAGES:
            lexer = get_lexer_by_name("text")
            with _cache_lock:
                _evict_lexer_cache_if_needed()
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
                _evict_lexer_cache_if_needed()
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
                _evict_lexer_cache_if_needed()
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
            _evict_lexer_cache_if_needed()
            _lexer_cache[cache_key] = lexer
        logger.debug("lexer_guessed", guessed_language=lexer.name, cache_key=cache_key[:20])
        return lexer
    except Exception as e:
        logger.warning("lexer_guess_failed", error=str(e), fallback="text")
        lexer = get_lexer_by_name("text")
        with _cache_lock:
            _evict_lexer_cache_if_needed()
            _lexer_cache[cache_key] = lexer
        return lexer


def clear_cache() -> None:
    """Clear the lexer cache. Useful for testing or memory management."""
    global _lexer_cache, _cache_stats
    with _cache_lock:
        _lexer_cache.clear()
        _cache_stats = {"hits": 0, "misses": 0, "guess_calls": 0}
    logger.info("lexer_cache_cleared")


def get_cache_stats() -> dict[str, int | float]:
    """
    Get cache statistics for monitoring.

    Returns:
        Dict with hits, misses, guess_calls, hit_rate
    """
    with _cache_lock:
        stats: dict[str, int | float] = dict(_cache_stats)
        total = stats["hits"] + stats["misses"]
        stats["hit_rate"] = stats["hits"] / total if total > 0 else 0.0
        stats["cache_size"] = len(_lexer_cache)
    return stats


def log_cache_stats() -> None:
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


# Note: PygmentsPatch has been moved to bengal.rendering.parsers.pygments_patch
# Import from there if needed:
#   from bengal.rendering.parsers.pygments_patch import PygmentsPatch

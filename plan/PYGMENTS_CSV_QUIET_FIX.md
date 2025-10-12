# Pygments CSV Warning Fix

**Date:** 2025-10-12  
**Status:** ✅ Complete

## Problem

Users were seeing noisy warnings when using CSV code blocks:

```
● unknown_lexer  language=csv normalized=csv fallback=text
```

### Root Cause

1. CSV is not recognized by Pygments as a valid lexer language
2. CSV was not in any special handling list (`_NO_HIGHLIGHT_LANGUAGES` or `_LANGUAGE_ALIASES`)
3. The code defaulted to WARNING level for all unrecognized languages
4. This warning was unhelpful and noisy for common data formats like CSV

## Solution

### Changes Made

**File:** `bengal/rendering/pygments_cache.py`

#### 1. Added New Category: Quiet Fallback Languages

Created a new set for data formats that don't need syntax highlighting:

```python
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
```

#### 2. Added Special Handling Logic

Added handling for these languages before attempting Pygments lookup:

```python
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
```

#### 3. Improved Warning Message

For truly unknown languages, added a more helpful warning message:

```python
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
```

## Benefits

1. **Reduced Noise**: CSV and other data formats no longer trigger warnings
2. **Better UX**: Debug-level logging for expected behavior
3. **More Helpful**: When warnings do appear, they include actionable hints
4. **Extensible**: Easy to add more data formats to the quiet list

## Log Level Hierarchy

Now the system uses three levels:

1. **DEBUG**: Expected cases
   - `no_highlight_language` - Mermaid, etc.
   - `data_format_as_text` - CSV, TSV, TXT, etc.
   - `lexer_cached` - Successful cache hits

2. **WARNING**: Unexpected cases requiring attention
   - `unknown_lexer` - Truly unrecognized languages (with helpful hint)

3. **INFO**: Informational events
   - Cache statistics, etc.

## Testing

The fix addresses the real-world case in:
- `examples/showcase/content/docs/data-tables.md` (line 54) - CSV code block

## Files Modified

1. `/Users/llane/Documents/github/python/bengal/bengal/rendering/pygments_cache.py`
   - Added `_QUIET_FALLBACK_LANGUAGES` set
   - Added special handling logic
   - Improved warning messages

## Answer to User Questions

> **Q1: Why is it unknown_lexer?**
>
> A: Pygments doesn't have a CSV lexer. CSV is a data format, not a programming language, so it doesn't have syntax highlighting rules.

> **Q2: Can this kind of notification be improved?**
>
> A: Yes! Fixed by:
> - Using DEBUG level for expected cases (data formats)
> - Adding helpful hints to warnings for truly unknown languages
> - Grouping similar formats together

> **Q3: Didn't we intend to mute the case of CSV for Pygments?**
>
> A: Yes! CSV should be silent. It's now in `_QUIET_FALLBACK_LANGUAGES` and logs at DEBUG level only.

## Related Formats Handled

The fix also covers other common data/text formats:
- `csv` - Comma-separated values
- `tsv` - Tab-separated values  
- `txt`, `text`, `plain`, `plaintext` - Plain text files
- `log`, `logs` - Log files

These all render as plain text without warnings, which is the correct behavior.

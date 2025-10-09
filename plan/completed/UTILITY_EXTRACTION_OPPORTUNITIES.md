# Utility Extraction Opportunities

**Date:** 2025-10-09  
**Status:** 📋 Analysis Complete  

## Executive Summary

After analyzing the Bengal codebase, I've identified **6 major categories** of code that should be extracted into dedicated utilities, plus **8 new utility categories** that would significantly improve code quality, reduce duplication, and enhance maintainability.

---

## Part 1: Code That Should Be Extracted to Utils

### 🔤 1. Text Utilities (`bengal/utils/text.py`)

**Problem:** Slugification logic is duplicated in 3+ places with slight variations.

**Current Locations:**
- `bengal/rendering/parser.py:629` - `_slugify()` method in MistuneParser
- `bengal/rendering/template_functions/strings.py:92` - `slugify()` function
- `bengal/rendering/template_functions/taxonomies.py:184` - `tag_url()` uses slugify pattern

**Code Comparison:**

```python
# parser.py version (with HTML unescape)
def _slugify(self, text: str) -> str:
    import html
    text = html.unescape(text)
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

# strings.py version (without HTML unescape)
def slugify(text: str) -> str:
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text.strip('-')
    return text
```

**Recommendation:** Create canonical slugify with options:

```python
# bengal/utils/text.py
def slugify(
    text: str,
    unescape_html: bool = True,
    max_length: Optional[int] = None,
    separator: str = '-'
) -> str:
    """
    Convert text to URL-safe slug.
    
    Args:
        text: Text to slugify
        unescape_html: Whether to decode HTML entities first
        max_length: Maximum slug length (None = unlimited)
        separator: Character to use between words
        
    Returns:
        URL-safe slug
        
    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Test &amp; Code", unescape_html=True)
        'test-code'
        >>> slugify("Very Long Title Here", max_length=10)
        'very-long'
    """
    if not text:
        return ''
    
    # Decode HTML entities if requested
    if unescape_html:
        import html
        text = html.unescape(text)
    
    # Convert to lowercase
    text = text.lower().strip()
    
    # Remove non-word characters (except spaces and hyphens)
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace multiple spaces/hyphens with separator
    text = re.sub(r'[-\s]+', separator, text)
    
    # Remove leading/trailing separators
    text = text.strip(separator)
    
    # Apply max length
    if max_length and len(text) > max_length:
        # Try to break at word boundary
        text = text[:max_length].rsplit(separator, 1)[0]
    
    return text


def strip_html(text: str, decode_entities: bool = True) -> str:
    """
    Remove all HTML tags from text.
    
    Currently in: bengal/rendering/template_functions/strings.py:157
    
    Args:
        text: HTML text
        decode_entities: Whether to decode HTML entities
        
    Returns:
        Plain text with HTML removed
    """
    if not text:
        return ''
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    if decode_entities:
        import html
        text = html.unescape(text)
    
    return text


def truncate_words(text: str, word_count: int, suffix: str = "...") -> str:
    """
    Truncate text to specified word count.
    
    Currently in: bengal/rendering/template_functions/strings.py
    Should be extracted for reuse in excerpts, summaries, etc.
    """
    if not text:
        return ''
    
    words = text.split()
    if len(words) <= word_count:
        return text
    
    return ' '.join(words[:word_count]) + suffix


def generate_excerpt(
    html: str, 
    word_count: int = 50, 
    suffix: str = "..."
) -> str:
    """
    Generate excerpt from HTML content.
    
    Currently implemented in multiple places:
    - bengal/postprocess/output_formats.py:674
    - Various template functions
    
    This is a common operation that should be standardized.
    """
    # Strip HTML tags
    text = strip_html(html, decode_entities=True)
    # Truncate to word count
    return truncate_words(text, word_count, suffix)
```

**Impact:** 
- ✅ Eliminates 3 duplicate implementations
- ✅ Provides consistent behavior across codebase
- ✅ Easier to test and maintain
- ✅ Can be reused in new features

---

### 📁 2. File I/O Utilities (`bengal/utils/file_io.py`)

**Problem:** File reading with error handling and encoding fallback is duplicated in 5+ places.

**Current Locations:**
- `bengal/discovery/content_discovery.py:192` - File reading with encoding fallback
- `bengal/rendering/template_functions/files.py:78` - File reading with error logging
- `bengal/rendering/template_functions/data.py:75` - JSON/YAML loading
- `bengal/config/loader.py:137` - TOML/YAML loading

**Pattern Analysis:**

```python
# Pattern 1: UTF-8 with latin-1 fallback (content_discovery.py)
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    try:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    except Exception:
        raise IOError(f"Cannot decode {file_path}")

# Pattern 2: Silent fallback (template_functions/files.py)
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content
except (IOError, UnicodeDecodeError):
    return ''  # Silent failure with logging
```

**Recommendation:** Create robust file I/O utilities:

```python
# bengal/utils/file_io.py
from pathlib import Path
from typing import Optional, Callable, Any
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def read_text_file(
    file_path: Path,
    encoding: str = 'utf-8',
    fallback_encoding: Optional[str] = 'latin-1',
    on_error: str = 'raise',  # 'raise', 'return_empty', 'return_none'
    caller: Optional[str] = None
) -> Optional[str]:
    """
    Read text file with robust error handling.
    
    Args:
        file_path: Path to file
        encoding: Primary encoding to try
        fallback_encoding: Fallback encoding if primary fails
        on_error: Error handling strategy
        caller: Caller identifier for logging
        
    Returns:
        File contents or None (depending on on_error)
        
    Raises:
        FileNotFoundError: If file doesn't exist and on_error='raise'
        IOError: If file cannot be read and on_error='raise'
    """
    if not file_path.exists():
        logger.warning("file_not_found", 
                      path=str(file_path), 
                      caller=caller or "file_io")
        if on_error == 'raise':
            raise FileNotFoundError(f"File not found: {file_path}")
        return '' if on_error == 'return_empty' else None
    
    if not file_path.is_file():
        logger.warning("path_not_file",
                      path=str(file_path),
                      caller=caller or "file_io")
        if on_error == 'raise':
            raise ValueError(f"Path is not a file: {file_path}")
        return '' if on_error == 'return_empty' else None
    
    # Try primary encoding
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        logger.debug("file_read",
                    path=str(file_path),
                    encoding=encoding,
                    size_bytes=len(content),
                    caller=caller or "file_io")
        return content
    
    except UnicodeDecodeError as e:
        if fallback_encoding:
            logger.warning("encoding_fallback",
                         path=str(file_path),
                         primary=encoding,
                         fallback=fallback_encoding,
                         caller=caller or "file_io")
            try:
                with open(file_path, 'r', encoding=fallback_encoding) as f:
                    content = f.read()
                logger.debug("file_read_fallback",
                           path=str(file_path),
                           encoding=fallback_encoding,
                           size_bytes=len(content),
                           caller=caller or "file_io")
                return content
            except Exception as fallback_error:
                logger.error("encoding_fallback_failed",
                           path=str(file_path),
                           error=str(fallback_error),
                           caller=caller or "file_io")
        
        if on_error == 'raise':
            raise IOError(f"Cannot decode {file_path}: {e}") from e
        return '' if on_error == 'return_empty' else None
    
    except IOError as e:
        logger.error("file_read_error",
                    path=str(file_path),
                    error=str(e),
                    caller=caller or "file_io")
        if on_error == 'raise':
            raise
        return '' if on_error == 'return_empty' else None


def load_json(
    file_path: Path,
    on_error: str = 'return_empty',
    caller: Optional[str] = None
) -> Any:
    """
    Load JSON file with error handling.
    
    Currently duplicated in:
    - bengal/rendering/template_functions/data.py:80
    - Various other locations
    """
    import json
    
    content = read_text_file(file_path, on_error=on_error, caller=caller)
    if not content:
        return {} if on_error == 'return_empty' else None
    
    try:
        data = json.loads(content)
        logger.debug("json_loaded",
                    path=str(file_path),
                    keys=len(data) if isinstance(data, dict) else None,
                    caller=caller or "file_io")
        return data
    except json.JSONDecodeError as e:
        logger.error("json_parse_error",
                    path=str(file_path),
                    error=str(e),
                    line=e.lineno,
                    column=e.colno,
                    caller=caller or "file_io")
        if on_error == 'raise':
            raise
        return {} if on_error == 'return_empty' else None


def load_yaml(
    file_path: Path,
    on_error: str = 'return_empty',
    caller: Optional[str] = None
) -> Any:
    """
    Load YAML file with error handling.
    
    Currently duplicated in:
    - bengal/config/loader.py:142
    - bengal/rendering/template_functions/data.py:94
    """
    import yaml
    
    content = read_text_file(file_path, on_error=on_error, caller=caller)
    if not content:
        return {} if on_error == 'return_empty' else None
    
    try:
        data = yaml.safe_load(content)
        logger.debug("yaml_loaded",
                    path=str(file_path),
                    keys=len(data) if isinstance(data, dict) else None,
                    caller=caller or "file_io")
        return data or {}
    except yaml.YAMLError as e:
        logger.error("yaml_parse_error",
                    path=str(file_path),
                    error=str(e),
                    caller=caller or "file_io")
        if on_error == 'raise':
            raise
        return {} if on_error == 'return_empty' else None


def load_data_file(
    file_path: Path,
    on_error: str = 'return_empty',
    caller: Optional[str] = None
) -> Any:
    """
    Auto-detect and load JSON/YAML/TOML file.
    
    Replaces logic currently in:
    - bengal/rendering/template_functions/data.py:40
    """
    suffix = file_path.suffix.lower()
    
    if suffix == '.json':
        return load_json(file_path, on_error=on_error, caller=caller)
    elif suffix in ('.yaml', '.yml'):
        return load_yaml(file_path, on_error=on_error, caller=caller)
    elif suffix == '.toml':
        import toml
        content = read_text_file(file_path, on_error=on_error, caller=caller)
        if not content:
            return {} if on_error == 'return_empty' else None
        try:
            return toml.loads(content)
        except toml.TomlDecodeError as e:
            logger.error("toml_parse_error",
                        path=str(file_path),
                        error=str(e),
                        caller=caller or "file_io")
            if on_error == 'raise':
                raise
            return {} if on_error == 'return_empty' else None
    else:
        logger.warning("unsupported_format",
                      path=str(file_path),
                      suffix=suffix,
                      caller=caller or "file_io")
        if on_error == 'raise':
            raise ValueError(f"Unsupported file format: {suffix}")
        return {} if on_error == 'return_empty' else None
```

**Impact:**
- ✅ Eliminates 5+ duplicate implementations
- ✅ Consistent error handling across codebase
- ✅ Better logging and observability
- ✅ Easier to add new features (e.g., caching)

---

### 📅 3. Date Utilities (`bengal/utils/dates.py`)

**Problem:** Date parsing and formatting logic scattered across multiple locations.

**Current Locations:**
- `bengal/core/page/metadata.py:31` - Date property with parsing
- `bengal/rendering/template_functions/dates.py:24` - `time_ago()` with parsing
- `bengal/rendering/template_functions/dates.py:85` - `date_iso()` with parsing
- `bengal/rendering/template_functions/dates.py:115` - `date_rfc822()` with parsing

**Pattern:**

```python
# Repeated in 4 places with slight variations
if isinstance(date, str):
    try:
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return str(date)
```

**Recommendation:**

```python
# bengal/utils/dates.py
from datetime import datetime, date as date_type
from typing import Optional, Union

DateLike = Union[datetime, date_type, str, None]


def parse_date(value: DateLike) -> Optional[datetime]:
    """
    Parse various date formats into datetime.
    
    Handles:
    - datetime objects (pass through)
    - date objects (convert to datetime)
    - ISO strings (parse)
    - RFC822 strings (parse)
    - Custom formats (parse)
    
    Args:
        value: Date value in various formats
        
    Returns:
        datetime object or None if parsing fails
        
    Examples:
        >>> parse_date("2025-10-09")
        datetime.datetime(2025, 10, 9, 0, 0)
        >>> parse_date("2025-10-09T14:30:00Z")
        datetime.datetime(2025, 10, 9, 14, 30)
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, date_type):
        return datetime.combine(value, datetime.min.time())
    
    if isinstance(value, str):
        # Try ISO format first
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        
        # Try common formats
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    
    return None


def format_date_iso(date: DateLike) -> str:
    """Format date as ISO 8601 string."""
    dt = parse_date(date)
    return dt.isoformat() if dt else ''


def format_date_rfc822(date: DateLike) -> str:
    """Format date as RFC 822 string (for RSS)."""
    dt = parse_date(date)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z") if dt else ''


def format_date_human(date: DateLike, format: str = '%B %d, %Y') -> str:
    """Format date in human-readable format."""
    dt = parse_date(date)
    return dt.strftime(format) if dt else ''


def time_ago(date: DateLike) -> str:
    """
    Convert date to human-readable "time ago" format.
    
    Currently in: bengal/rendering/template_functions/dates.py:24
    """
    dt = parse_date(date)
    if not dt:
        return ''
    
    # Make timezone-naive for comparison
    if dt.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(timezone.utc)
    else:
        now = datetime.now()
    
    diff = now - dt
    
    if diff.total_seconds() < 0:
        return "just now"
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days < 30:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
```

**Impact:**
- ✅ Single source of truth for date parsing
- ✅ Easier to add new date formats
- ✅ Consistent behavior across templates and code
- ✅ Better error handling

---

### 🔍 4. Path Utilities (`bengal/utils/paths.py`)

**Problem:** Path manipulation and validation repeated in many places.

**Current Issues:**
- mkdir with parents=True, exist_ok=True appears 37 times
- Path validation logic duplicated
- Relative path resolution patterns repeated

**Recommendation:**

```python
# bengal/utils/paths.py
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path, mode: int = 0o755) -> Path:
    """
    Ensure directory exists, creating if necessary.
    
    Standardizes the common pattern:
        path.mkdir(parents=True, exist_ok=True)
    
    Args:
        path: Directory path
        mode: Directory permissions
        
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path


def ensure_parent_dir(file_path: Path) -> Path:
    """
    Ensure parent directory of file exists.
    
    Common pattern before writing files.
    
    Args:
        file_path: File path
        
    Returns:
        The file path (for chaining)
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def safe_relative_to(path: Path, base: Path) -> Optional[Path]:
    """
    Safely compute relative path, returning None on error.
    
    Wraps path.relative_to() with exception handling.
    
    Args:
        path: Path to make relative
        base: Base path
        
    Returns:
        Relative path or None if path is not under base
    """
    try:
        return path.relative_to(base)
    except ValueError:
        return None


def is_under(path: Path, base: Path) -> bool:
    """
    Check if path is under base directory.
    
    Args:
        path: Path to check
        base: Base directory
        
    Returns:
        True if path is under base
    """
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def normalize_path(path: Path) -> Path:
    """
    Normalize path (resolve symlinks, make absolute).
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized absolute path
    """
    return path.resolve()


def find_file_upwards(
    filename: str,
    start_dir: Path,
    stop_at: Optional[Path] = None
) -> Optional[Path]:
    """
    Find file by searching upwards from start_dir.
    
    Useful for finding config files, .git directories, etc.
    
    Args:
        filename: Filename to search for
        start_dir: Directory to start search from
        stop_at: Directory to stop at (default: filesystem root)
        
    Returns:
        Path to file or None if not found
        
    Example:
        >>> find_file_upwards('bengal.toml', Path.cwd())
        Path('/path/to/project/bengal.toml')
    """
    current = start_dir.resolve()
    stop = stop_at.resolve() if stop_at else None
    
    while True:
        candidate = current / filename
        if candidate.exists():
            return candidate
        
        if stop and current == stop:
            return None
        
        parent = current.parent
        if parent == current:  # Reached filesystem root
            return None
        
        current = parent
```

**Impact:**
- ✅ Reduces boilerplate
- ✅ Consistent error handling
- ✅ More readable code

---

### 🔢 5. Collection Utilities (`bengal/utils/collections.py`)

**Problem:** Common collection operations repeated throughout codebase.

**Recommendation:**

```python
# bengal/utils/collections.py
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


def group_by(
    items: Iterable[T],
    key_func: Callable[[T], K]
) -> Dict[K, List[T]]:
    """
    Group items by key function.
    
    Args:
        items: Items to group
        key_func: Function to extract grouping key
        
    Returns:
        Dictionary mapping keys to lists of items
        
    Example:
        >>> pages = [page1, page2, page3]
        >>> by_section = group_by(pages, lambda p: p.section)
    """
    groups: Dict[K, List[T]] = {}
    for item in items:
        key = key_func(item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups


def chunk(items: List[T], size: int) -> List[List[T]]:
    """
    Split list into chunks of specified size.
    
    Useful for pagination, batch processing, etc.
    
    Args:
        items: Items to chunk
        size: Chunk size
        
    Returns:
        List of chunks
    """
    return [items[i:i + size] for i in range(0, len(items), size)]


def flatten(items: Iterable[Iterable[T]]) -> List[T]:
    """
    Flatten nested iterables into single list.
    
    Args:
        items: Nested iterables
        
    Returns:
        Flattened list
    """
    return [item for sublist in items for item in sublist]


def unique_by(
    items: Iterable[T],
    key_func: Callable[[T], K]
) -> List[T]:
    """
    Get unique items based on key function.
    
    Preserves order of first occurrence.
    
    Args:
        items: Items to deduplicate
        key_func: Function to extract uniqueness key
        
    Returns:
        List of unique items
    """
    seen = set()
    result = []
    for item in items:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def sort_by_multiple(
    items: List[T],
    *key_funcs: Callable[[T], Any]
) -> List[T]:
    """
    Sort by multiple key functions (in order).
    
    Args:
        items: Items to sort
        *key_funcs: Key functions in priority order
        
    Returns:
        Sorted list
        
    Example:
        >>> sort_by_multiple(pages, 
        ...     lambda p: p.weight,
        ...     lambda p: p.date,
        ...     lambda p: p.title)
    """
    result = items.copy()
    for key_func in reversed(key_funcs):
        result.sort(key=key_func)
    return result
```

**Impact:**
- ✅ Common operations become one-liners
- ✅ More functional programming style
- ✅ Easier to test

---

### ✅ 6. Validation Utilities (`bengal/utils/validation.py`)

**Problem:** Validation patterns repeated across configuration, pages, templates.

**Recommendation:**

```python
# bengal/utils/validation.py
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import re


class ValidationError(Exception):
    """Validation failed."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    """Chainable validation builder."""
    
    def __init__(self, value: Any, field: str):
        self.value = value
        self.field = field
        self.errors: List[str] = []
    
    def required(self, message: Optional[str] = None) -> 'Validator':
        """Value must be present."""
        if self.value is None or self.value == '':
            self.errors.append(message or f"{self.field} is required")
        return self
    
    def type_check(self, expected_type: type, message: Optional[str] = None) -> 'Validator':
        """Value must be of specified type."""
        if self.value is not None and not isinstance(self.value, expected_type):
            self.errors.append(
                message or f"{self.field} must be {expected_type.__name__}, got {type(self.value).__name__}"
            )
        return self
    
    def min_length(self, length: int, message: Optional[str] = None) -> 'Validator':
        """Value must have minimum length."""
        if self.value is not None and len(self.value) < length:
            self.errors.append(
                message or f"{self.field} must be at least {length} characters"
            )
        return self
    
    def max_length(self, length: int, message: Optional[str] = None) -> 'Validator':
        """Value must have maximum length."""
        if self.value is not None and len(self.value) > length:
            self.errors.append(
                message or f"{self.field} must be at most {length} characters"
            )
        return self
    
    def pattern(self, regex: str, message: Optional[str] = None) -> 'Validator':
        """Value must match regex pattern."""
        if self.value is not None and not re.match(regex, str(self.value)):
            self.errors.append(
                message or f"{self.field} must match pattern {regex}"
            )
        return self
    
    def one_of(self, choices: List[Any], message: Optional[str] = None) -> 'Validator':
        """Value must be one of specified choices."""
        if self.value is not None and self.value not in choices:
            self.errors.append(
                message or f"{self.field} must be one of {choices}"
            )
        return self
    
    def custom(self, validator_func: Callable[[Any], bool], message: str) -> 'Validator':
        """Custom validation function."""
        if self.value is not None:
            try:
                if not validator_func(self.value):
                    self.errors.append(message)
            except Exception as e:
                self.errors.append(f"{self.field} validation failed: {e}")
        return self
    
    def raise_if_invalid(self):
        """Raise ValidationError if any validation failed."""
        if self.errors:
            raise ValidationError('\n'.join(self.errors), self.field)
    
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0


def validate(value: Any, field: str) -> Validator:
    """
    Create validator for value.
    
    Example:
        >>> validate(config.get('title'), 'title') \\
        ...     .required() \\
        ...     .type_check(str) \\
        ...     .min_length(1) \\
        ...     .raise_if_invalid()
    """
    return Validator(value, field)


def validate_dict(
    data: Dict[str, Any],
    schema: Dict[str, Validator]
) -> Dict[str, List[str]]:
    """
    Validate dictionary against schema.
    
    Args:
        data: Data to validate
        schema: Schema mapping field names to validators
        
    Returns:
        Dictionary of field names to error messages
    """
    errors = {}
    for field, validator_builder in schema.items():
        value = data.get(field)
        validator = validator_builder(value, field)
        if not validator.is_valid():
            errors[field] = validator.errors
    return errors
```

**Impact:**
- ✅ Declarative validation
- ✅ Better error messages
- ✅ Easier to add new validation rules

---

## Part 2: New Utilities We Should Create

### 📊 7. Performance Utilities (`bengal/utils/performance.py`)

**Why:** Timing and profiling code scattered throughout, should be centralized.

```python
# bengal/utils/performance.py
import time
import functools
from typing import Callable, TypeVar, Optional
from contextlib import contextmanager
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@contextmanager
def timer(operation: str, threshold_ms: Optional[float] = None):
    """
    Context manager for timing operations.
    
    Example:
        >>> with timer("render_page"):
        ...     render(page)
    """
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        
        if threshold_ms and duration_ms > threshold_ms:
            logger.warning("slow_operation",
                         operation=operation,
                         duration_ms=duration_ms,
                         threshold_ms=threshold_ms)
        else:
            logger.debug("operation_complete",
                       operation=operation,
                       duration_ms=duration_ms)


def timed(operation: Optional[str] = None):
    """
    Decorator for timing functions.
    
    Example:
        >>> @timed("render_page")
        ... def render(page):
        ...     ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with timer(op_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class PerformanceMonitor:
    """
    Track performance metrics across operations.
    
    Example:
        >>> monitor = PerformanceMonitor()
        >>> with monitor.track("parse"):
        ...     parse_content()
        >>> monitor.print_summary()
    """
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def track(self, operation: str):
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
    
    def print_summary(self):
        """Print summary of tracked operations."""
        print("\n" + "=" * 60)
        print("Performance Summary:")
        print("=" * 60)
        
        for op, durations in sorted(self.metrics.items()):
            count = len(durations)
            total = sum(durations) * 1000
            avg = total / count if count > 0 else 0
            min_ms = min(durations) * 1000 if durations else 0
            max_ms = max(durations) * 1000 if durations else 0
            
            print(f"  {op:30s} "
                  f"count={count:4d} "
                  f"total={total:8.1f}ms "
                  f"avg={avg:6.1f}ms "
                  f"min={min_ms:6.1f}ms "
                  f"max={max_ms:6.1f}ms")
        
        print("=" * 60)
```

---

### 🌐 8. URL Utilities (`bengal/utils/urls.py`)

**Why:** URL manipulation beyond what URLStrategy provides.

```python
# bengal/utils/urls.py
from urllib.parse import urljoin, urlparse, urlunparse, quote, unquote
from typing import Optional, Dict


def normalize_url(url: str) -> str:
    """
    Normalize URL (lowercase scheme/host, remove default ports, etc.)
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    parsed = urlparse(url)
    
    # Lowercase scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Remove default ports
    if netloc.endswith(':80') and scheme == 'http':
        netloc = netloc[:-3]
    elif netloc.endswith(':443') and scheme == 'https':
        netloc = netloc[:-4]
    
    return urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def add_query_params(url: str, params: Dict[str, str]) -> str:
    """
    Add query parameters to URL.
    
    Args:
        url: Base URL
        params: Query parameters to add
        
    Returns:
        URL with query parameters
    """
    from urllib.parse import parse_qs, urlencode
    
    parsed = urlparse(url)
    query_dict = parse_qs(parsed.query)
    
    # Add new params
    for key, value in params.items():
        query_dict[key] = [value]
    
    new_query = urlencode(query_dict, doseq=True)
    
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                      parsed.params, new_query, parsed.fragment))


def is_external_url(url: str, base_domain: Optional[str] = None) -> bool:
    """
    Check if URL is external (different domain).
    
    Args:
        url: URL to check
        base_domain: Base domain to compare against
        
    Returns:
        True if URL is external
    """
    if not url:
        return False
    
    # Relative URLs are not external
    if url.startswith('/') and not url.startswith('//'):
        return False
    
    # Anchor links are not external
    if url.startswith('#'):
        return False
    
    parsed = urlparse(url)
    
    # No netloc = not external
    if not parsed.netloc:
        return False
    
    # Compare domains if base_domain provided
    if base_domain:
        return not parsed.netloc.endswith(base_domain)
    
    # Has netloc = external
    return True


def sanitize_url(url: str) -> str:
    """
    Sanitize URL for safety (remove javascript:, data:, etc.)
    
    Args:
        url: URL to sanitize
        
    Returns:
        Sanitized URL or empty string if unsafe
    """
    if not url:
        return ''
    
    url = url.strip()
    
    # Block dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    url_lower = url.lower()
    
    for protocol in dangerous_protocols:
        if url_lower.startswith(protocol):
            return ''
    
    return url
```

---

### 🎨 9. HTML Utilities (`bengal/utils/html.py`)

**Why:** HTML manipulation beyond basic escaping.

```python
# bengal/utils/html.py
import html as html_module
import re
from typing import Optional, List
from bs4 import BeautifulSoup


def minify_html(html: str) -> str:
    """
    Minify HTML (remove unnecessary whitespace).
    
    Args:
        html: HTML to minify
        
    Returns:
        Minified HTML
    """
    # Remove comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # Remove whitespace between tags
    html = re.sub(r'>\s+<', '><', html)
    
    # Collapse multiple spaces
    html = re.sub(r'\s+', ' ', html)
    
    return html.strip()


def extract_text(html: str, strip: bool = True) -> str:
    """
    Extract plain text from HTML.
    
    Args:
        html: HTML content
        strip: Whether to strip whitespace
        
    Returns:
        Plain text
    """
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    if strip:
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_headings(html: str) -> List[Dict[str, str]]:
    """
    Extract headings from HTML.
    
    Args:
        html: HTML content
        
    Returns:
        List of heading dicts with 'level', 'text', 'id'
    """
    soup = BeautifulSoup(html, 'html.parser')
    headings = []
    
    for tag in soup.find_all(re.compile(r'^h[1-6]$')):
        headings.append({
            'level': int(tag.name[1]),
            'text': tag.get_text(strip=True),
            'id': tag.get('id', '')
        })
    
    return headings


def add_target_blank(html: str, external_only: bool = True) -> str:
    """
    Add target="_blank" to links.
    
    Args:
        html: HTML content
        external_only: Only add to external links
        
    Returns:
        Modified HTML
    """
    from bengal.utils.urls import is_external_url
    
    soup = BeautifulSoup(html, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        if external_only:
            if is_external_url(link['href']):
                link['target'] = '_blank'
                link['rel'] = 'noopener noreferrer'
        else:
            link['target'] = '_blank'
            link['rel'] = 'noopener noreferrer'
    
    return str(soup)


def add_image_dimensions(html: str, root_path: Path) -> str:
    """
    Add width/height attributes to images.
    
    Improves page load performance by preventing layout shifts.
    
    Args:
        html: HTML content
        root_path: Root path for resolving image paths
        
    Returns:
        Modified HTML
    """
    from PIL import Image
    
    soup = BeautifulSoup(html, 'html.parser')
    
    for img in soup.find_all('img', src=True):
        # Skip if already has dimensions
        if img.get('width') and img.get('height'):
            continue
        
        # Try to get image dimensions
        src = img['src']
        if src.startswith('/'):
            image_path = root_path / src.lstrip('/')
            
            if image_path.exists():
                try:
                    with Image.open(image_path) as pil_img:
                        img['width'] = str(pil_img.width)
                        img['height'] = str(pil_img.height)
                except Exception:
                    pass  # Skip if can't read image
    
    return str(soup)
```

---

### 🔐 10. Security Utilities (`bengal/utils/security.py`)

**Why:** Security concerns should be centralized and auditable.

```python
# bengal/utils/security.py
import hashlib
import secrets
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Sanitize filename to prevent directory traversal attacks.
    
    Args:
        filename: Filename to sanitize
        replacement: Character to replace invalid chars with
        
    Returns:
        Safe filename
        
    Example:
        >>> sanitize_filename("../../etc/passwd")
        '______etc_passwd'
    """
    # Remove path separators
    filename = filename.replace('/', replacement).replace('\\', replacement)
    
    # Remove null bytes
    filename = filename.replace('\0', '')
    
    # Remove potentially dangerous characters
    dangerous = ['..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous:
        filename = filename.replace(char, replacement)
    
    # Ensure filename isn't empty
    if not filename or filename == replacement:
        filename = 'unnamed'
    
    return filename


def is_safe_path(path: Path, base: Path) -> bool:
    """
    Check if path is safely contained within base directory.
    
    Prevents directory traversal attacks.
    
    Args:
        path: Path to check
        base: Base directory
        
    Returns:
        True if path is safe (under base)
    """
    try:
        path_resolved = path.resolve()
        base_resolved = base.resolve()
        
        # Check if resolved path is under base
        return str(path_resolved).startswith(str(base_resolved))
    except Exception:
        return False


def compute_checksum(content: str, algorithm: str = 'sha256') -> str:
    """
    Compute cryptographic checksum of content.
    
    Useful for cache keys, integrity checks, etc.
    
    Args:
        content: Content to hash
        algorithm: Hash algorithm
        
    Returns:
        Hexadecimal checksum
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode('utf-8'))
    return hasher.hexdigest()


def compute_file_checksum(file_path: Path, algorithm: str = 'sha256') -> str:
    """
    Compute checksum of file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm
        
    Returns:
        Hexadecimal checksum
    """
    hasher = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    
    return hasher.hexdigest()


def generate_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        Hexadecimal token
    """
    return secrets.token_hex(length)
```

---

### 🎯 11. Caching Utilities (`bengal/utils/caching.py`)

**Why:** Decorator-based caching for expensive operations.

```python
# bengal/utils/caching.py
import functools
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
import pickle

T = TypeVar('T')


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Simple memoization decorator (in-memory cache).
    
    Example:
        >>> @memoize
        ... def expensive_operation(x):
        ...     return x ** 2
    """
    cache = {}
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create cache key from arguments
        key = (args, tuple(sorted(kwargs.items())))
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        
        return cache[key]
    
    return wrapper


def disk_cache(
    cache_dir: Path,
    key_func: Optional[Callable[..., str]] = None,
    serializer: str = 'json'  # 'json' or 'pickle'
):
    """
    Disk-based cache decorator.
    
    Args:
        cache_dir: Directory to store cache files
        key_func: Function to generate cache key from arguments
        serializer: Serialization format
        
    Example:
        >>> @disk_cache(Path('.cache'))
        ... def parse_markdown(content):
        ...     return expensive_parse(content)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default: hash of arguments
                arg_str = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
                key = hashlib.sha256(arg_str.encode()).hexdigest()
            
            cache_file = cache_dir / f"{func.__name__}_{key}.cache"
            
            # Try to load from cache
            if cache_file.exists():
                try:
                    if serializer == 'json':
                        with open(cache_file, 'r') as f:
                            return json.load(f)
                    else:  # pickle
                        with open(cache_file, 'rb') as f:
                            return pickle.load(f)
                except Exception:
                    pass  # Cache corrupted, recompute
            
            # Compute and cache
            result = func(*args, **kwargs)
            
            # Save to cache
            cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                if serializer == 'json':
                    with open(cache_file, 'w') as f:
                        json.dump(result, f)
                else:  # pickle
                    with open(cache_file, 'wb') as f:
                        pickle.dump(result, f)
            except Exception:
                pass  # Failed to cache, but return result
            
            return result
        
        return wrapper
    return decorator


class TTLCache:
    """
    Time-to-live cache with automatic expiration.
    
    Example:
        >>> cache = TTLCache(ttl_seconds=300)
        >>> cache.set('key', 'value')
        >>> cache.get('key')
        'value'
    """
    def __init__(self, ttl_seconds: float):
        import time
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}
        self.time = time.time
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache, or default if expired/missing."""
        if key in self.cache:
            # Check if expired
            age = self.time() - self.timestamps[key]
            if age < self.ttl_seconds:
                return self.cache[key]
            else:
                # Expired, remove
                del self.cache[key]
                del self.timestamps[key]
        
        return default
    
    def set(self, key: str, value: Any):
        """Set value in cache."""
        self.cache[key] = value
        self.timestamps[key] = self.time()
    
    def clear(self):
        """Clear all cached values."""
        self.cache.clear()
        self.timestamps.clear()
```

---

### 📝 12. String Formatting Utilities (`bengal/utils/formatting.py`)

**Why:** Common string formatting operations.

```python
# bengal/utils/formatting.py
import textwrap
from typing import Optional


def wrap_text(
    text: str,
    width: int = 80,
    indent: str = '',
    subsequent_indent: Optional[str] = None
) -> str:
    """
    Wrap text to specified width.
    
    Args:
        text: Text to wrap
        width: Maximum line width
        indent: Indent for first line
        subsequent_indent: Indent for subsequent lines
        
    Returns:
        Wrapped text
    """
    if subsequent_indent is None:
        subsequent_indent = indent
    
    return textwrap.fill(
        text,
        width=width,
        initial_indent=indent,
        subsequent_indent=subsequent_indent
    )


def dedent(text: str) -> str:
    """
    Remove common leading whitespace from text.
    
    Useful for multi-line strings in code.
    """
    return textwrap.dedent(text)


def indent(text: str, prefix: str = '    ') -> str:
    """
    Add prefix to each line.
    
    Args:
        text: Text to indent
        prefix: Prefix to add
        
    Returns:
        Indented text
    """
    return textwrap.indent(text, prefix)


def pluralize(
    count: int,
    singular: str,
    plural: Optional[str] = None
) -> str:
    """
    Return singular or plural form based on count.
    
    Args:
        count: Count
        singular: Singular form
        plural: Plural form (default: singular + 's')
        
    Returns:
        Appropriate form
        
    Example:
        >>> pluralize(1, 'page')
        'page'
        >>> pluralize(2, 'page')
        'pages'
        >>> pluralize(2, 'box', 'boxes')
        'boxes'
    """
    if count == 1:
        return singular
    return plural if plural else singular + 's'


def humanize_bytes(size_bytes: int) -> str:
    """
    Format bytes as human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable string
        
    Example:
        >>> humanize_bytes(1024)
        '1.0 KB'
        >>> humanize_bytes(1536)
        '1.5 KB'
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def humanize_number(num: int) -> str:
    """
    Format number with thousand separators.
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string
        
    Example:
        >>> humanize_number(1234567)
        '1,234,567'
    """
    return f"{num:,}"


def truncate_middle(text: str, max_length: int, separator: str = '...') -> str:
    """
    Truncate text in the middle (useful for file paths).
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        separator: Separator to use
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_middle('/very/long/path/to/file.txt', 20)
        '/very/.../file.txt'
    """
    if len(text) <= max_length:
        return text
    
    sep_len = len(separator)
    available = max_length - sep_len
    left = available // 2
    right = available - left
    
    return text[:left] + separator + text[-right:]
```

---

### 🔍 13. Diff Utilities (`bengal/utils/diff.py`)

**Why:** Useful for incremental builds, debugging, and testing.

```python
# bengal/utils/diff.py
import difflib
from typing import List, Tuple
from enum import Enum


class ChangeType(Enum):
    """Type of change in diff."""
    ADDED = 'added'
    REMOVED = 'removed'
    MODIFIED = 'modified'
    UNCHANGED = 'unchanged'


def text_diff(old: str, new: str) -> str:
    """
    Generate unified diff of two texts.
    
    Args:
        old: Old text
        new: New text
        
    Returns:
        Unified diff string
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm='',
        fromfile='old',
        tofile='new'
    )
    
    return ''.join(diff)


def html_diff(old: str, new: str) -> str:
    """
    Generate HTML diff of two texts.
    
    Args:
        old: Old text
        new: New text
        
    Returns:
        HTML diff
    """
    differ = difflib.HtmlDiff()
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    
    return differ.make_file(old_lines, new_lines)


def list_diff(
    old_list: List[str],
    new_list: List[str]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compute difference between two lists.
    
    Args:
        old_list: Old list
        new_list: New list
        
    Returns:
        Tuple of (added, removed, unchanged)
    """
    old_set = set(old_list)
    new_set = set(new_list)
    
    added = list(new_set - old_set)
    removed = list(old_set - new_set)
    unchanged = list(old_set & new_set)
    
    return added, removed, unchanged


def dict_diff(old_dict: dict, new_dict: dict) -> dict:
    """
    Compute difference between two dictionaries.
    
    Args:
        old_dict: Old dictionary
        new_dict: New dictionary
        
    Returns:
        Dictionary describing changes
    """
    added = {k: v for k, v in new_dict.items() if k not in old_dict}
    removed = {k: v for k, v in old_dict.items() if k not in new_dict}
    modified = {
        k: {'old': old_dict[k], 'new': new_dict[k]}
        for k in old_dict
        if k in new_dict and old_dict[k] != new_dict[k]
    }
    unchanged = {k: v for k, v in old_dict.items() if k in new_dict and old_dict[k] == new_dict[k]}
    
    return {
        'added': added,
        'removed': removed,
        'modified': modified,
        'unchanged': unchanged
    }
```

---

### 🎲 14. Testing Utilities (`bengal/utils/testing.py`)

**Why:** Common test utilities and fixtures.

```python
# bengal/utils/testing.py
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


@contextmanager
def temp_directory():
    """
    Context manager for temporary directory.
    
    Automatically cleaned up on exit.
    
    Example:
        >>> with temp_directory() as tmpdir:
        ...     (tmpdir / 'test.txt').write_text('hello')
    """
    tmpdir = Path(tempfile.mkdtemp())
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@contextmanager
def temp_file(suffix: str = '', content: Optional[str] = None):
    """
    Context manager for temporary file.
    
    Args:
        suffix: File suffix
        content: Initial content
        
    Example:
        >>> with temp_file('.md', '# Hello') as tmpfile:
        ...     print(tmpfile.read_text())
    """
    import tempfile
    
    fd, path = tempfile.mkstemp(suffix=suffix)
    tmpfile = Path(path)
    
    try:
        if content:
            tmpfile.write_text(content)
        yield tmpfile
    finally:
        tmpfile.unlink(missing_ok=True)


def create_test_site(
    tmpdir: Path,
    pages: Optional[dict] = None,
    config: Optional[dict] = None
) -> Path:
    """
    Create test site structure.
    
    Args:
        tmpdir: Temporary directory
        pages: Dictionary mapping paths to content
        config: Site configuration
        
    Returns:
        Path to site root
        
    Example:
        >>> site_root = create_test_site(tmpdir, {
        ...     'content/index.md': '# Home',
        ...     'content/about.md': '# About'
        ... })
    """
    # Create directories
    (tmpdir / 'content').mkdir()
    (tmpdir / 'themes').mkdir()
    
    # Create pages
    if pages:
        for path, content in pages.items():
            file_path = tmpdir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
    
    # Create config
    if config:
        import toml
        config_path = tmpdir / 'bengal.toml'
        config_path.write_text(toml.dumps(config))
    
    return tmpdir
```

---

## Implementation Plan

### Phase 1: High-Impact Extractions (Week 1)
1. ✅ `bengal/utils/text.py` - Slugify is used everywhere
2. ✅ `bengal/utils/file_io.py` - File reading is critical path
3. ✅ `bengal/utils/dates.py` - Date handling is common

### Phase 2: Code Quality (Week 2)
4. ✅ `bengal/utils/paths.py` - Reduces boilerplate
5. ✅ `bengal/utils/validation.py` - Better error handling
6. ✅ `bengal/utils/collections.py` - Cleaner code

### Phase 3: Advanced Features (Week 3)
7. ✅ `bengal/utils/performance.py` - Better profiling
8. ✅ `bengal/utils/urls.py` - URL safety
9. ✅ `bengal/utils/html.py` - HTML processing
10. ✅ `bengal/utils/security.py` - Security hardening

### Phase 4: Developer Experience (Week 4)
11. ✅ `bengal/utils/caching.py` - Performance optimization
12. ✅ `bengal/utils/formatting.py` - String utilities
13. ✅ `bengal/utils/diff.py` - Debugging and incremental builds
14. ✅ `bengal/utils/testing.py` - Test utilities

---

## Benefits

### Code Quality
- ✅ **DRY Principle:** Eliminate 20+ duplicate implementations
- ✅ **Single Responsibility:** Each utility has clear purpose
- ✅ **Testability:** Utilities are easier to test in isolation
- ✅ **Maintainability:** Bug fixes in one place benefit entire codebase

### Developer Experience
- ✅ **Discoverability:** Developers know where to find common operations
- ✅ **Consistency:** Same behavior across codebase
- ✅ **Documentation:** Well-documented utils serve as reference
- ✅ **Productivity:** Less time writing boilerplate

### Performance
- ✅ **Optimization:** Optimize once, benefit everywhere
- ✅ **Caching:** Decorator-based caching for expensive operations
- ✅ **Profiling:** Built-in performance monitoring

### Security
- ✅ **Centralization:** Security-critical code in one place
- ✅ **Auditability:** Easier to review and test
- ✅ **Best Practices:** Implement once, use everywhere

---

## Testing Strategy

Each utility module should have comprehensive tests:

```
tests/unit/utils/
  ├── test_text.py
  ├── test_file_io.py
  ├── test_dates.py
  ├── test_paths.py
  ├── test_validation.py
  ├── test_collections.py
  ├── test_performance.py
  ├── test_urls.py
  ├── test_html.py
  ├── test_security.py
  ├── test_caching.py
  ├── test_formatting.py
  ├── test_diff.py
  └── test_testing.py
```

---

## Migration Strategy

### For Each Utility:

1. **Create:** Write new utility module with comprehensive tests
2. **Identify:** Find all locations using old pattern (grep/codebase_search)
3. **Replace:** Update code to use new utility
4. **Test:** Run tests to ensure no regressions
5. **Document:** Update relevant documentation
6. **Remove:** Delete old duplicate implementations

### Gradual Migration:

- Start with high-impact utilities (text, file_io, dates)
- Keep old code working during migration
- Use deprecation warnings if needed
- Complete migration one module at a time

---

## Summary

This analysis identifies:

- **6 categories** of code that should be extracted to utilities
- **8 new utility categories** that would improve the codebase
- **20+ duplicate implementations** that can be eliminated
- **Clear implementation plan** with phased approach
- **Significant benefits** in code quality, DX, performance, and security

**Recommendation:** Start with Phase 1 (text, file_io, dates) as these have the highest impact and are used throughout the codebase. The extractions will pay immediate dividends in code quality and maintainability.


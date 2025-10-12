# Content Type Strategy Refactor

**Date**: 2025-10-12  
**Status**: ✅ Complete

## Problem

Content type handling logic was scattered across multiple files:
- Section Orchestrator: detection, template mapping, pagination rules
- Core Section: generic weight-based sorting  
- Renderer: type-specific date sorting at render time
- No single source of truth for content type behavior

**Issues:**
- Hard to maintain (changes needed in 3+ files)
- Logic duplication (sorting in 2 places)
- Hidden bugs (index page not filtered, wrong sorting)
- Difficult to extend (adding new type = hunt through codebase)

## Solution

Implemented **Strategy Pattern** for content types with centralized behavior.

### New Architecture

```
bengal/content_types/
├── __init__.py         # Public API
├── base.py             # ContentTypeStrategy base class
├── strategies.py       # Concrete strategies (Blog, Docs, API, etc.)
└── registry.py         # Type detection & lookup
```

### Content Type Strategy Interface

```python
class ContentTypeStrategy:
    """Base strategy defining content type behavior"""

    def sort_pages(self, pages) -> list:
        """How to sort pages for display"""

    def filter_display_pages(self, pages, index_page) -> list:
        """What pages to show in lists"""

    def should_paginate(self, count, config) -> bool:
        """Whether to use pagination"""

    def get_template(self) -> str:
        """What template to use"""

    def detect_from_section(self, section) -> bool:
        """Auto-detect if this type applies"""
```

### Implemented Strategies

| Strategy | Template | Sorting | Pagination | Detection |
|----------|----------|---------|------------|-----------|
| **BlogStrategy** | `blog/list.html` | By date (newest first) | Yes | Name: blog, posts, news; Has dates |
| **DocsStrategy** | `doc/list.html` | By weight, then title | No | Name: docs, documentation |
| **ApiReferenceStrategy** | `api-reference/list.html` | Discovery order | No | Name: api, reference; Type hints |
| **CliReferenceStrategy** | `cli-reference/list.html` | Discovery order | No | Name: cli, commands |
| **TutorialStrategy** | `tutorial/list.html` | By weight | No | Name: tutorials, guides |
| **PageStrategy** | `index.html` | By weight, then title | No | Default fallback |

## Implementation

### 1. Created Strategy Classes

**`bengal/content_types/base.py`:**
- Base `ContentTypeStrategy` class
- Default implementations for common behavior
- Clean interface for all content types

**`bengal/content_types/strategies.py`:**
- `BlogStrategy`: Date-sorted, paginated chronological content
- `DocsStrategy`: Weight-sorted, unpaginated documentation  
- `ApiReferenceStrategy`: Original order, unpaginated API docs
- `CliReferenceStrategy`: Original order, unpaginated CLI docs
- `TutorialStrategy`: Weight-sorted sequential tutorials
- `PageStrategy`: Generic fallback

**`bengal/content_types/registry.py`:**
- `CONTENT_TYPE_REGISTRY`: Maps type names to strategies
- `get_strategy(type)`: Lookup strategy by name
- `detect_content_type(section)`: Auto-detect from heuristics
- `register_strategy(type, strategy)`: Add custom types

### 2. Refactored Section Orchestrator

**Before** (scattered logic):
```python
def _detect_content_type(self, section):
    # 60+ lines of detection logic
    if name in ("blog", "posts"...):
        return "archive"
    # ... more conditions

def _should_paginate(self, section, type):
    # Type-specific rules hardcoded
    if type in ("api-reference", "cli-reference"...):
        return False
    # ... more conditions

def _get_template_for_content_type(self, type):
    # Hardcoded template map
    template_map = {...}
    return template_map.get(type)
```

**After** (delegates to strategies):
```python
def _detect_content_type(self, section):
    return detect_content_type(section)  # 1 line!

def _should_paginate(self, section, type):
    strategy = get_strategy(type)
    return strategy.should_paginate(len(section.pages), self.site.config)

def _get_template_for_content_type(self, type):
    return get_strategy(type).get_template()

def _prepare_posts_list(self, section, type):
    strategy = get_strategy(type)
    filtered = strategy.filter_display_pages(section.regular_pages, section.index_page)
    return strategy.sort_pages(filtered)
```

### 3. Simplified Renderer

**Before** (duplicate sorting logic):
```python
if page_type in ("api-reference", "cli-reference"):
    posts = all_posts  # Keep original
else:
    posts = sorted(all_posts, key=lambda p: p.date, reverse=True)
```

**After** (uses pre-sorted data):
```python
# Posts already filtered & sorted by strategy!
posts = page.metadata.get("_posts", section.pages)
```

### 4. Fixed Bugs

**Bug 1: Index Page in List**
- **Root cause**: `section.regular_pages` included index page
- **Fix**: `strategy.filter_display_pages()` explicitly filters it out

**Bug 2: Wrong Sorting**
- **Root cause**: Renderer sorted at render time, after weight sort
- **Fix**: Strategy sorts once in orchestrator, renderer uses pre-sorted list

**Bug 3: posts Variable Override**
- **Root cause**: Renderer set `posts = section.pages` for index pages
- **Fix**: Check for `_posts` in metadata first: `posts = metadata.get("_posts", section.pages)`

## Benefits

✅ **Single source of truth** - One strategy per content type  
✅ **Easy to extend** - Add new type = one new strategy class  
✅ **Testable** - Each strategy isolated and testable  
✅ **Maintainable** - All logic for a type in one place  
✅ **Consistent** - Same behavior everywhere  
✅ **Performant** - Sort once, not per-render  

## Examples

### Adding a Custom Content Type

```python
from bengal.content_types import ContentTypeStrategy, register_strategy

class GalleryStrategy(ContentTypeStrategy):
    default_template = "gallery/list.html"

    def sort_pages(self, pages):
        # Sort by image count, then title
        return sorted(pages, key=lambda p:
            (p.metadata.get("image_count", 0), p.title))

    def detect_from_section(self, section):
        return section.name.lower() == "gallery"

register_strategy("gallery", GalleryStrategy())
```

### Using in Frontmatter

```yaml
---
title: Photo Gallery
type: gallery  # Uses GalleryStrategy automatically
---
```

## Test Results

### aaa Example Site (Blog)

**Before refactor:**
- ❌ 4 cards (included index page)
- ❌ Wrong order (alphabetical)

**After refactor:**
- ✅ 3 cards (index excluded)
- ✅ Correct order (newest first):
  1. Welcome Post (Oct 12)
  2. Getting Started (Oct 11)
  3. Tips (Oct 10)

## Files Modified

- `bengal/content_types/__init__.py` - New module
- `bengal/content_types/base.py` - Base strategy class
- `bengal/content_types/strategies.py` - Concrete strategies
- `bengal/content_types/registry.py` - Registry & detection
- `bengal/orchestration/section.py` - Uses strategies
- `bengal/rendering/renderer.py` - Uses pre-sorted data

## Migration Notes

**Backward Compatible:** ✅

- Existing sites work without changes
- Content type detection unchanged (same heuristics)
- Template selection unchanged (same templates)
- Only internal implementation changed

## Future Enhancements

Possible extensions:
- Per-type metadata validation
- Type-specific template contexts
- Custom filters per type
- Type-aware search ranking
- Type icons/badges

## Conclusion

The strategy pattern provides a clean, extensible architecture for content type handling. Each type's behavior is isolated in one place, making the system easier to understand, maintain, and extend.

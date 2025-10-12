# Site.Data Feature Implementation Plan

**Date:** October 12, 2025  
**Priority:** High  
**Inspired by:** [Hugo's .Site.Data](https://gohugo.io/methods/site/data/)

## Problem

Currently, Bengal has `get_data('path/to/file.yaml')` but it's:
- Verbose (need to call function each time)
- Not cached (data loaded repeatedly)
- Not as discoverable
- Requires knowing exact paths

## Proposed Solution

Implement Hugo-style `site.data` that automatically loads files from `data/` directory.

### Example Usage

```
project/
├── data/
│   ├── authors.yaml
│   ├── books/
│   │   ├── fiction.yaml
│   │   └── nonfiction.yaml
│   └── resume.yaml
├── content/
└── templates/
```

```jinja2
{# Access data with clean dot notation #}
{{ site.data.authors }}

{# Nested directories become nested access #}
{{ site.data.books.fiction }}

{# Still keep get_data() for dynamic paths #}
{{ get_data('data/' ~ page.metadata.data_file) }}
```

## Implementation

### 1. Load Data on Site Init

```python
# In bengal/core/site.py

class Site:
    def __init__(self, ...):
        # ... existing init ...
        self.data = self._load_data_directory()

    def _load_data_directory(self) -> dict[str, Any]:
        """
        Load all files from data/ directory into a nested dict.

        Similar to Hugo's .Site.Data:
        - data/authors.yaml → site.data.authors
        - data/books/fiction.yaml → site.data.books.fiction
        """
        from pathlib import Path
        from bengal.utils.file_io import load_data_file

        data = {}
        data_dir = self.root_path / "data"

        if not data_dir.exists():
            return data

        for file_path in data_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.json', '.yaml', '.yml', '.toml']:
                # Convert path to nested dict key
                # data/books/fiction.yaml → ['books', 'fiction']
                relative = file_path.relative_to(data_dir)
                parts = list(relative.with_suffix('').parts)

                # Load the data
                content = load_data_file(file_path, on_error='return_empty')

                # Insert into nested dict
                current = data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = content

        return data
```

### 2. Make it Accessible in Templates

Already works! Since `site` is passed to template context in `renderer.py`, templates can access `site.data` automatically.

```python
# bengal/rendering/renderer.py (already exists)

context = {
    "page": page,
    "content": content,
    "site": self.site,  # ← Already passed!
    # ...
}
```

### 3. Add DotDict Wrapper for Clean Access

To enable `site.data.books.fiction` instead of `site.data['books']['fiction']`:

```python
# In bengal/utils/dotdict.py (new file)

class DotDict(dict):
    """
    Dict subclass that allows dot notation access.

    Avoids Jinja2 gotcha by NOT exposing dict methods via dot notation.
    """

    def __getattr__(self, key):
        """Allow dot notation: obj.key"""
        try:
            value = self[key]
            # Recursively wrap nested dicts
            if isinstance(value, dict) and not isinstance(value, DotDict):
                return DotDict(value)
            return value
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        """Allow dot notation assignment"""
        self[key] = value

    def __delattr__(self, key):
        """Allow dot notation deletion"""
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
```

Then wrap the data:

```python
# In bengal/core/site.py

def _load_data_directory(self) -> DotDict:
    # ... load files ...
    return DotDict(data)  # ← Wrap in DotDict
```

### 4. Resume Template Improvements

With this feature, the resume template becomes cleaner:

```yaml
# content/resume/index.md (minimal)
---
title: Resume  
section: resume
---

You can add custom content here that will appear at the bottom of the resume.
```

```yaml
# data/resume.yaml (all structured data)
name: Your Full Name
headline: Software Engineer
contact: {...}
experience: [...]
education: [...]
skills: [...]
```

```jinja2
{# templates/resume/single.html #}
{% set resume = site.data.resume %}

<h1>{{ resume.name }}</h1>
<p>{{ resume.headline }}</p>

{# Clean access, no .items() collision #}
{% for skill_group in resume.skills %}
  <h3>{{ skill_group.category }}</h3>
  {% for skill in skill_group.skills %}  {# ← Renamed from 'items' #}
    <span>{{ skill }}</span>
  {% endfor %}
{% endfor %}

{# Page content appears at bottom #}
{{ content | safe }}
```

## Benefits

### 1. **Separation of Concerns**
- Content in `content/`
- Data in `data/`
- Templates in `templates/`

### 2. **Reusability**
```jinja2
{# Use same data across multiple pages #}
{% for author in site.data.authors %}
  ...
{% endfor %}
```

### 3. **Performance**
- Data loaded once at site init
- Cached for all pages
- No repeated file I/O

### 4. **Easier Maintenance**
```
data/
├── team.yaml          ← Easy to find and edit
├── products.yaml
└── testimonials.yaml
```

### 5. **Avoids Frontmatter Bloat**
```yaml
# Before: 200 lines of frontmatter
---
name: ...
experience: [100 lines]
education: [50 lines]
...
---

# After: Just metadata
---
title: Resume
section: resume
---
```

## Migration Path

### Phase 1: Keep get_data() (Current)
```jinja2
{% set resume = get_data('data/resume.yaml') %}
```

### Phase 2: Add site.data (New Feature)
```jinja2
{% set resume = site.data.resume %}
```

### Phase 3: Both work! (Backward Compatible)
- Old templates using `get_data()` continue working
- New templates use `site.data` for cleaner syntax
- `get_data()` still useful for dynamic paths

## Additional Features

### 1. Data Reload on Change (Dev Mode)
```python
# In watch mode, reload data/ directory on file changes
if self.watch_mode:
    self.watch_data_directory()
```

### 2. Multiple Data Directories
```toml
[data]
directories = ["data", "external/data"]
```

### 3. Data Merging
```python
# Override/extend data by environment
data/
├── base.yaml
└── development.yaml  # Merges with base
```

### 4. Data Preprocessing
```python
# Add computed fields
def _load_data_directory(self):
    data = {...}

    # Add helper computed fields
    if 'team' in data:
        data['team_count'] = len(data['team'])

    return DotDict(data)
```

## Comparison with Hugo

| Feature | Hugo | Bengal (Proposed) |
|---------|------|-------------------|
| Auto-load `data/` | ✅ | ✅ |
| Dot notation access | ✅ | ✅ |
| Nested directories | ✅ | ✅ |
| CSV support | ✅ | 🔄 Could add |
| XML support | ✅ | 🔄 Could add |
| JSON/YAML/TOML | ✅ | ✅ |
| Dynamic loading | via transform.Unmarshal | via get_data() |

## Testing

```python
# tests/unit/core/test_site_data.py

def test_site_data_loading(tmp_path):
    # Create data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create data file
    (data_dir / "authors.yaml").write_text("""
    - name: Victor Hugo
      books: 20
    """)

    # Initialize site
    site = Site(root_path=tmp_path)

    # Check data loaded
    assert 'authors' in site.data
    assert site.data.authors[0]['name'] == 'Victor Hugo'

    # Check dot notation
    assert site.data.authors[0].name == 'Victor Hugo'  # via DotDict

def test_nested_data_directories(tmp_path):
    # data/books/fiction.yaml
    (tmp_path / "data" / "books").mkdir(parents=True)
    (tmp_path / "data" / "books" / "fiction.yaml").write_text("...")

    site = Site(root_path=tmp_path)

    # Access nested
    assert 'books' in site.data
    assert 'fiction' in site.data.books
    assert site.data.books.fiction  # Dot notation works

def test_backward_compatibility(tmp_path):
    """Ensure get_data() still works"""
    # Both should work:
    # {{ site.data.authors }}
    # {{ get_data('data/authors.yaml') }}
    pass
```

## Documentation

### User Guide
- Add "Working with Data Files" page
- Document `site.data` vs `get_data()`
- Show resume template as example
- Document DotDict behavior and gotchas

### Template Reference
```markdown
## site.data

Access data files from the `data/` directory.

**Usage:**
```jinja2
{# Access data file #}
{{ site.data.filename }}

{# Nested directories #}
{{ site.data.directory.filename }}

{# Iterate #}
{% for item in site.data.collection %}
  {{ item.name }}
{% endfor %}
```

**Example:**
```
data/authors.yaml → {{ site.data.authors }}
data/books/fiction.yaml → {{ site.data.books.fiction }}
```
```

## Implementation Priority

1. ✅ **Immediate** - Core implementation (~2 hours)
   - Load data/ directory on site init
   - Make accessible via site.data

2. **Short Term** - Polish (~2 hours)
   - Add DotDict wrapper for clean access
   - Add tests
   - Update documentation

3. **Medium Term** - Nice to have (~4 hours)
   - Watch data/ directory for changes in dev mode
   - Add CSV support (via pandas)
   - Data preprocessing hooks

## Conclusion

**Should we implement this?**

**YES!** It would:
1. Make the resume template much cleaner
2. Follow familiar patterns from Hugo
3. Encourage better separation of concerns
4. Provide performance benefits (caching)
5. Maintain backward compatibility

**Effort:** ~4 hours for core + polish  
**Impact:** High - Makes data-driven templates much more ergonomic

The `.items` gotcha we hit would be avoided with DotDict, and the pattern of keeping data in `data/` separate from content in `content/` is a proven best practice.

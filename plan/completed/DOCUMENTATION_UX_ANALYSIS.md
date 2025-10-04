# Documentation UX Analysis - API & CLI Layouts

**Date:** October 4, 2025  
**Issue:** Inconsistent layouts and confusing UX between `/api/` and `/cli/` documentation pages

---

## 🐛 The Problem

### Visual Inconsistencies

1. **`/api/` page** shows:
   - ✅ Subsection tiles/cards grid (good for navigation)
   - ✅ Section stats (17 pages, 17 subsections, 101 total)
   - ❌ Pagination controls (confusing - doesn't work, page 2 doesn't exist)
   - ❌ Uses `archive.html` template (designed for blog posts, not API docs)

2. **`/cli/` page** shows:
   - ✅ Regular page content (CLI command overview)
   - ✅ Table of contents sidebar
   - ✅ Breadcrumbs
   - ❌ NO subsection navigation (can't see subcommands easily)
   - ❌ Uses `page.html` template (not optimized for reference docs)

### Root Cause Analysis

#### Why `/api/` Uses Archive Template

```
content/api/
  ├── (NO _index.md or index.md)
  ├── autodoc.md
  ├── bengal.md
  └── ... (17 direct pages + 17 subsections)

↓ Section Orchestrator detects missing index

SectionOrchestrator._create_archive_index() creates:
  - Virtual page with template: 'archive.html'
  - Includes: _posts (pages), _subsections, _paginator
  - Output: /api/index.html
```

**Result:** Archive template is designed for **blog-style post listings** with:
- Featured/regular post cards
- Pagination for browsing posts
- Date-based sorting

This is **wrong for API documentation** where you want:
- Module/package navigation
- Alphabetical organization  
- Hierarchical structure visibility

#### Why `/cli/` Uses Page Template

```
content/cli/
  ├── index.md  ← Regular page (not _index.md!)
  └── commands/
      ├── autodoc.md
      ├── build.md
      └── ... (9 command pages)

↓ index.md is treated as regular page

Uses page.html template:
  - Shows page content
  - Table of contents
  - NO section navigation
  - NO subsection discovery
```

**Result:** Page template is designed for **regular content pages** with:
- Article-style reading experience
- Related posts
- Reading time

This is **partially wrong for CLI docs** where you want:
- Command hierarchy visible
- Quick access to all commands
- Reference-style layout

---

## 📊 Documentation UX Best Practices

### Python API Documentation (like Sphinx, pdoc, etc.)

**User Journey:**
1. Land on API overview → See all modules/packages at a glance
2. Click into module → See classes, functions, constants
3. Click into class → See methods, attributes, inheritance
4. Navigate between related APIs easily

**Layout Requirements:**
- **Left sidebar:** Module/package tree navigation
- **Center:** Current module/class/function documentation
- **Right sidebar:** On-page TOC for long API pages
- **No pagination:** Users expect to browse by hierarchy, not pages
- **Search:** Critical for API docs

**Visual Design:**
- Clean, reference-style layout
- Syntax highlighting for code examples
- Type annotations prominently displayed
- Inheritance and relationships clear
- Links to source code

### CLI Documentation (like Click, Typer, etc.)

**User Journey:**
1. Land on CLI overview → See all commands at a glance
2. Understand command hierarchy (groups vs commands)
3. Click into command → See usage, options, examples
4. Copy-paste examples quickly

**Layout Requirements:**
- **Overview page:** List of all commands with one-line descriptions
- **Command pages:** Usage, arguments, options, examples
- **Grouping:** Subcommands under parent commands
- **No pagination:** Commands are typically few enough to show all
- **Code examples:** Easy to copy

**Visual Design:**
- Terminal-style code blocks
- Clear option/argument tables
- Examples with actual commands
- Quick reference cards

---

## 🎯 Recommended Solution

### Create Specialized Templates

We need **3 new templates** for documentation:

#### 1. `api-reference/list.html` - API Section Index

**Purpose:** Landing page for API section (modules overview)

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Navigation Bar                                      │
├─────────────────────────────────────────────────────┤
│ Breadcrumbs: Home > API                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📦 Python API Reference                            │
│                                                     │
│  Browse all modules, classes, and functions         │
│                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ 📁 autodoc   │ │ 📁 cache     │ │ 📁 config    ││
│  │ 5 modules    │ │ 2 modules    │ │ 2 modules    ││
│  └──────────────┘ └──────────────┘ └──────────────┘│
│                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ 📄 bengal    │ │ 📁 core      │ │ ...          ││
│  │ Main module  │ │ 5 modules    │ │              ││
│  └──────────────┘ └──────────────┘ └──────────────┘│
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Key Features:**
- Module/package cards (NOT subsection tiles)
- Search box for API docs
- Statistics (# of classes, functions, etc.)
- NO pagination
- Alphabetically sorted or by importance

#### 2. `api-reference/single.html` - Individual API Page

**Purpose:** Documentation for a single module, class, or function

**Layout:**
```
┌──────────┬─────────────────────────────────┬──────────┐
│          │ Breadcrumbs: Home > API > Module │          │
│ Module   ├─────────────────────────────────┤   TOC    │
│ Tree     │                                 │          │
│          │ # module_name                   │ • Class1 │
│ > autodoc│                                 │ • Class2 │
│   - base │ Module description              │ • func1  │
│   - config│                                │ • func2  │
│ > cache  │ ## Classes                      │          │
│ > config │                                 │          │
│          │ ### Class1                      │          │
│          │ Description...                  │          │
│          │                                 │          │
│          │ #### Methods                    │          │
│          │ - method1()                     │          │
│          │ - method2()                     │          │
│          │                                 │          │
└──────────┴─────────────────────────────────┴──────────┘
```

**Key Features:**
- 3-column layout (navigation tree, content, TOC)
- Syntax highlighting
- Type annotations
- Source code links
- Searchable within page

#### 3. `cli-reference/list.html` - CLI Overview

**Purpose:** Landing page showing all CLI commands

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Navigation Bar                                      │
├─────────────────────────────────────────────────────┤
│ Breadcrumbs: Home > CLI                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ⌨️  Bengal CLI Reference                           │
│                                                     │
│  Fast & fierce static site generation              │
│                                                     │
│  ## Commands                                        │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 📚 autodoc                                   │   │
│  │ Generate API documentation from Python code │   │
│  │ [Full docs →]                                │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 🔨 build                                     │   │
│  │ Build the static site                        │   │
│  │ [Full docs →]                                │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ## Getting Help                                    │
│                                                     │
│  ```bash                                            │
│  bengal --help                                      │
│  ```                                                │
└─────────────────────────────────────────────────────┘
```

**Key Features:**
- Command cards with icons and descriptions
- Usage examples
- Links to detailed command docs
- NO pagination
- Grouped by command type if applicable

#### 4. `cli-reference/single.html` - Individual Command

**Purpose:** Detailed documentation for a single CLI command

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Breadcrumbs: Home > CLI > build                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  # bengal build                                     │
│                                                     │
│  🔨 Build the static site                           │
│                                                     │
│  ## Usage                                           │
│                                                     │
│  ```bash                                            │
│  bengal build [OPTIONS]                             │
│  ```                                                │
│                                                     │
│  ## Options                                         │
│                                                     │
│  | Option | Description | Default |                │
│  |--------|-------------|---------|                │
│  | --clean | Clean before build | false |          │
│  | --draft | Include drafts | false |              │
│                                                     │
│  ## Examples                                        │
│                                                     │
│  ```bash                                            │
│  # Basic build                                      │
│  bengal build                                       │
│                                                     │
│  # Clean build with drafts                          │
│  bengal build --clean --draft                       │
│  ```                                                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Implementation Plan

### Phase 1: Create Template Structure

```
bengal/themes/default/templates/
  ├── api-reference/
  │   ├── list.html      ← Section index (module overview)
  │   └── single.html    ← Individual module/class page
  ├── cli-reference/
  │   ├── list.html      ← Command overview
  │   └── single.html    ← Individual command page
  └── partials/
      ├── api-module-card.html    ← Module card component
      ├── api-nav-tree.html       ← API navigation tree
      ├── cli-command-card.html   ← Command card component
      └── cli-options-table.html  ← Options/args table
```

### Phase 2: Update Template Selection Logic

**Option A: Convention-based (Recommended)**

Detect section name patterns:
```python
def _get_template_name(self, page: Page) -> str:
    # 1. Explicit template (highest priority)
    if 'template' in page.metadata:
        return page.metadata['template']
    
    # 2. Section-based patterns
    if hasattr(page, '_section') and page._section:
        section_name = page._section.name
        is_section_index = (
            page.source_path.stem in ('_index', 'index') or
            page.metadata.get('type') == 'archive'  # Generated archives
        )
        
        # API documentation sections
        if section_name in ('api', 'reference', 'api-reference'):
            if is_section_index:
                return 'api-reference/list.html'
            else:
                return 'api-reference/single.html'
        
        # CLI documentation sections
        if section_name in ('cli', 'commands', 'cli-reference'):
            if is_section_index:
                return 'cli-reference/list.html'
            else:
                return 'cli-reference/single.html'
        
        # Generic section templates
        if is_section_index:
            templates_to_try = [
                f"{section_name}/list.html",
                f"{section_name}.html",
            ]
        else:
            templates_to_try = [
                f"{section_name}/single.html",
                f"{section_name}.html",
            ]
        
        for template_name in templates_to_try:
            if self._template_exists(template_name):
                return template_name
    
    # 3. Fallback
    if page.source_path.stem == '_index':
        return 'index.html'
    return 'page.html'
```

**Option B: Metadata-based**

Use frontmatter to specify documentation type:
```yaml
---
title: "API Reference"
doc_type: api-reference  # or 'cli-reference', 'tutorial', etc.
---
```

### Phase 3: Fix Archive Generation for Documentation

The `SectionOrchestrator` should detect documentation sections and use appropriate templates:

```python
def _create_archive_index(self, section: 'Section') -> 'Page':
    """Create archive index with appropriate template based on section type."""
    
    # Detect documentation sections
    doc_type = self._detect_doc_type(section)
    
    if doc_type == 'api-reference':
        template = 'api-reference/list.html'
        page_type = 'api-reference'
    elif doc_type == 'cli-reference':
        template = 'cli-reference/list.html'
        page_type = 'cli-reference'
    else:
        # Regular archive (blog-style)
        template = 'archive.html'
        page_type = 'archive'
    
    archive_page = Page(
        source_path=virtual_path,
        content="",
        metadata={
            'title': section.title,
            'template': template,
            'type': page_type,
            '_generated': True,
            '_section': section,
            '_posts': section.pages,
            '_subsections': section.subsections,
            # NO _paginator for documentation sections!
        }
    )
    
    return archive_page

def _detect_doc_type(self, section: 'Section') -> Optional[str]:
    """Detect if section is API docs, CLI docs, or regular content."""
    if section.name in ('api', 'reference', 'api-reference'):
        return 'api-reference'
    if section.name in ('cli', 'commands', 'cli-reference'):
        return 'cli-reference'
    
    # Check if pages have doc-type markers
    if section.pages:
        first_page = section.pages[0]
        if 'python-module' in first_page.metadata.get('type', ''):
            return 'api-reference'
        if 'cli-reference' in first_page.metadata.get('type', ''):
            return 'cli-reference'
    
    return None
```

### Phase 4: Remove Pagination from Documentation Archives

Documentation sections should NOT have pagination:

```python
# In _create_archive_index()
if doc_type in ('api-reference', 'cli-reference'):
    # NO paginator for documentation
    archive_page.metadata.update({
        '_posts': section.pages,
        '_subsections': section.subsections,
        # No _paginator, no _page_num
    })
else:
    # Regular archive with pagination
    paginator = Paginator(section.pages, per_page=10)
    archive_page.metadata.update({
        '_posts': section.pages,
        '_paginator': paginator,
        '_page_num': 1,
    })
```

---

## 🎨 Template Partial Design

### `partials/api-module-card.html`

```jinja2
{# 
  API Module Card Component
  
  Usage:
    {% include 'partials/api-module-card.html' with {
      'module': module_page,
      'is_package': True/False
    } %}
#}

<article class="api-module-card">
    <div class="api-module-icon">
        {% if is_package %}
        📁
        {% else %}
        📄
        {% endif %}
    </div>
    
    <div class="api-module-content">
        <h3>
            <a href="{{ url_for(module) }}">{{ module.title }}</a>
        </h3>
        
        {% if module.metadata.description %}
        <p class="api-module-description">
            {{ module.metadata.description | truncate(120) }}
        </p>
        {% endif %}
        
        <div class="api-module-meta">
            {% if module.metadata.classes %}
            <span>{{ module.metadata.classes | length }} classes</span>
            {% endif %}
            
            {% if module.metadata.functions %}
            <span>{{ module.metadata.functions | length }} functions</span>
            {% endif %}
        </div>
    </div>
</article>
```

### `partials/cli-command-card.html`

```jinja2
{#
  CLI Command Card Component
  
  Usage:
    {% include 'partials/cli-command-card.html' with {
      'command': command_page
    } %}
#}

<article class="cli-command-card">
    <div class="cli-command-header">
        <h3>
            {% if command.metadata.emoji %}
            {{ command.metadata.emoji }}
            {% endif %}
            <a href="{{ url_for(command) }}">{{ command.title }}</a>
        </h3>
    </div>
    
    <div class="cli-command-content">
        {% if command.metadata.description %}
        <p>{{ command.metadata.description }}</p>
        {% endif %}
        
        {% if command.metadata.usage %}
        <code class="cli-usage">{{ command.metadata.usage }}</code>
        {% endif %}
        
        <a href="{{ url_for(command) }}" class="cli-command-link">
            Full documentation →
        </a>
    </div>
</article>
```

---

## ✅ Success Criteria

After implementation:

1. **`/api/` page:**
   - ✅ Shows module/package cards (not generic subsection tiles)
   - ✅ NO pagination controls
   - ✅ Search box for API docs
   - ✅ Hierarchical navigation
   - ✅ Uses `api-reference/list.html` template

2. **`/cli/` page:**
   - ✅ Shows command cards with descriptions
   - ✅ Quick usage examples
   - ✅ Links to detailed command pages
   - ✅ NO pagination
   - ✅ Uses `cli-reference/list.html` template

3. **Individual API pages:**
   - ✅ 3-column layout (nav tree, content, TOC)
   - ✅ Syntax highlighting
   - ✅ Type annotations visible
   - ✅ Uses `api-reference/single.html` template

4. **Individual CLI pages:**
   - ✅ Command usage clearly shown
   - ✅ Options/arguments table
   - ✅ Copy-paste examples
   - ✅ Uses `cli-reference/single.html` template

---

## 📝 Next Steps

1. Create templates in phases:
   - Start with `api-reference/list.html` to fix `/api/` page
   - Then `cli-reference/list.html` to fix `/cli/` page
   - Then single page templates

2. Update template selection logic to recognize doc sections

3. Fix archive generation to not add pagination to docs

4. Add partials for reusable components

5. Style with CSS specific to reference documentation

6. Test with both autodoc-generated and manual content

---

## 🤔 Discussion Questions

1. **Template naming:** Do we like `api-reference/list.html` or prefer `api/index.html`?

2. **Section detection:** Should we auto-detect based on section name (`api`, `cli`) or require explicit metadata?

3. **Navigation tree:** Should API nav tree show all modules or be collapsible?

4. **Search:** Do we want built-in search for API docs or rely on browser find?

5. **CLI organization:** How to handle command groups (e.g., `bengal new site` vs `bengal new page`)?

6. **Backwards compatibility:** Should old `archive.html` still work for sections that want pagination?


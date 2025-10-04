# Documentation UX - Before & After Comparison

**Date:** October 4, 2025

---

## Current State (Broken)

### `/api/` - Current Rendering

```
┌────────────────────────────────────────────────────────────┐
│ Breadcrumbs: Home > Api > Api                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ Section Stats:                                       │  │
│ │ • 17 pages in this section                           │  │
│ │ • 17 subsections                                     │  │
│ │ • 101 total pages (including subsections)            │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ ## Subsections                                             │
│                                                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│ │ Autodoc      │ │ Bengal       │ │ Cache        │       │
│ │ 5 pages      │ │ 1 pages      │ │ 2 pages      │       │
│ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│ │ Config       │ │ Core         │ │ ...          │       │
│ │ 2 pages      │ │ 5 pages      │ │              │       │
│ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                            │
│ ⚠️ PAGINATION (broken)                                     │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ ← Previous  [1] 2 3 4 5  Next →                      │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘

Template: archive.html (WRONG - designed for blog posts!)
Type: archive
Issues:
  ❌ Shows pagination (page 2+ don't exist)
  ❌ Generic "subsections" - not API-specific
  ❌ No search functionality
  ❌ No module tree navigation
  ❌ Stats are generic, not API-focused
```

### `/cli/` - Current Rendering

```
┌────────────────────────────────────────────────────────────┐
│ Breadcrumbs: Home > Cli > main CLI                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ # main CLI Reference                                       │
│                                                            │
│ 🐯 Bengal SSG - A high-performance static site generator. │
│                                                            │
│ Fast & fierce static site generation with personality!     │
│                                                            │
│ ## Commands                                                │
│                                                            │
│ ### autodoc                                                │
│                                                            │
│ 📚 Generate API documentation from Python source code.     │
│                                                            │
│ Extracts documentation via AST parsing...                  │
│                                                            │
│ **Usage:**                                                 │
│ ```bash                                                    │
│ main autodoc [OPTIONS]                                     │
│ ```                                                        │
│                                                            │
│ [Full documentation →](commands/autodoc)                   │
│                                                            │
│ ---                                                        │
│                                                            │
│ ### build                                                  │
│ (same pattern repeats...)                                  │
│                                                            │
└────────────────────────────────────────────────────────────┘

Template: page.html (PARTIALLY WRONG - not reference-optimized)
Type: (none - regular page)
Issues:
  ⚠️ Inline command docs make page very long
  ❌ No command navigation sidebar
  ❌ No quick reference table
  ❌ Can't see all commands at a glance
  ❌ Has to scroll to see all commands
```

---

## Desired State (Fixed)

### `/api/` - Proposed Design

```
┌────────────────────────────────────────────────────────────┐
│ Breadcrumbs: Home > API Reference                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ # 📦 Python API Reference                                  │
│                                                            │
│ Complete API documentation for Bengal SSG                  │
│                                                            │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ 🔍 Search API...                          [Search]   │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ 📊 **101 modules** | **45 classes** | **200+ functions**  │
│                                                            │
│ ## Core Modules                                            │
│                                                            │
│ ┌─────────────────────────────────────────┐               │
│ │ 📁 bengal.autodoc           ⭐ Popular   │               │
│ │ Automatic documentation generation       │               │
│ │ 📄 5 modules · 12 classes · 30 functions│               │
│ └─────────────────────────────────────────┘               │
│                                                            │
│ ┌─────────────────────────────────────────┐               │
│ │ 📄 bengal                                │               │
│ │ Main package exports                     │               │
│ │ 📄 1 module · 3 classes · 8 functions   │               │
│ └─────────────────────────────────────────┘               │
│                                                            │
│ ┌─────────────────────────────────────────┐               │
│ │ 📁 bengal.cache                          │               │
│ │ Build caching and dependency tracking    │               │
│ │ 📄 2 modules · 4 classes · 15 functions │               │
│ └─────────────────────────────────────────┘               │
│                                                            │
│ ## View All                                                │
│ • Alphabetical | By Category | Most Used                  │
│                                                            │
│ ✅ NO PAGINATION (all modules visible or searchable)       │
│                                                            │
└────────────────────────────────────────────────────────────┘

Template: api-reference/list.html (NEW - API-specific!)
Type: api-reference
Improvements:
  ✅ API-specific module cards
  ✅ Shows actual API metrics (classes, functions)
  ✅ Search functionality for modules
  ✅ Popular/featured modules highlighted
  ✅ NO pagination
  ✅ Grouped by importance or category
```

### `/cli/` - Proposed Design

```
┌────────────────────────────────────────────────────────────┐
│ Breadcrumbs: Home > CLI Reference                          │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ # ⌨️  Bengal CLI Reference                                 │
│                                                            │
│ 🐯 Bengal SSG - A high-performance static site generator. │
│                                                            │
│ Fast & fierce static site generation with personality!     │
│                                                            │
│ ## Quick Start                                             │
│                                                            │
│ ```bash                                                    │
│ # Create a new site                                        │
│ bengal new site my-site                                    │
│                                                            │
│ # Build and serve                                          │
│ cd my-site                                                 │
│ bengal serve                                               │
│ ```                                                        │
│                                                            │
│ ## Commands                                                │
│                                                            │
│ ┌────────────────────────────────────────────────────┐    │
│ │ 🔨 **build**                                       │    │
│ │ Build the static site                              │    │
│ │ bengal build [OPTIONS]                             │    │
│ │ [Full documentation →](commands/build)             │    │
│ └────────────────────────────────────────────────────┘    │
│                                                            │
│ ┌────────────────────────────────────────────────────┐    │
│ │ 🚀 **serve**                                       │    │
│ │ Start development server with hot reload           │    │
│ │ bengal serve [OPTIONS]                             │    │
│ │ [Full documentation →](commands/serve)             │    │
│ └────────────────────────────────────────────────────┘    │
│                                                            │
│ ┌────────────────────────────────────────────────────┐    │
│ │ 📚 **autodoc**                                     │    │
│ │ Generate API documentation                         │    │
│ │ bengal autodoc [OPTIONS]                           │    │
│ │ [Full documentation →](commands/autodoc)           │    │
│ └────────────────────────────────────────────────────┘    │
│                                                            │
│ ┌────────────────────────────────────────────────────┐    │
│ │ ✨ **new**                                         │    │
│ │ Create new site, page, or section                  │    │
│ │ bengal new <type> <name>                           │    │
│ │ [Full documentation →](commands/new)               │    │
│ └────────────────────────────────────────────────────┘    │
│                                                            │
│ ## Getting Help                                            │
│                                                            │
│ ```bash                                                    │
│ bengal --help                   # Show all commands        │
│ bengal COMMAND --help           # Show command help        │
│ ```                                                        │
│                                                            │
└────────────────────────────────────────────────────────────┘

Template: cli-reference/list.html (NEW - CLI-specific!)
Type: cli-reference
Improvements:
  ✅ Command cards with clear hierarchy
  ✅ One-line usage preview
  ✅ Condensed view (not full docs inline)
  ✅ Quick start section at top
  ✅ Easy to scan all commands
  ✅ Links to detailed pages
```

---

## Individual Page Layouts

### API Module Page - `api-reference/single.html`

```
┌────────┬──────────────────────────────────────┬─────────┐
│ 📦 API │ Home > API > autodoc > base          │   TOC   │
│  Tree  ├──────────────────────────────────────┤         │
│        │                                      │ Classes │
│ autodoc│ # bengal.autodoc.base                │ --------│
│ ├─base │                                      │ • Config│
│ ├─config│ Base classes for autodoc system    │ • Parser│
│ ├─gen...│                                     │         │
│ ├─utils│ **Source:** bengal/autodoc/base.py  │ Functions│
│ cache  │                                      │ -------- │
│ config │ ## Classes                           │ • parse()│
│ core   │                                      │ • load() │
│        │ ### AutodocConfig                    │         │
│        │                                      │         │
│        │ ```python                            │         │
│        │ class AutodocConfig:                 │         │
│        │     output_dir: Path                 │         │
│        │     source_dir: Path                 │         │
│        │ ```                                  │         │
│        │                                      │         │
│        │ Configuration for autodoc generator  │         │
│        │                                      │         │
│        │ #### Attributes                      │         │
│        │ - **output_dir** (Path): Where to... │         │
│        │ - **source_dir** (Path): Python src  │         │
│        │                                      │         │
│        │ #### Methods                         │         │
│        │                                      │         │
│        │ ##### validate()                     │         │
│        │                                      │         │
│        │ ```python                            │         │
│        │ def validate(self) -> bool           │         │
│        │ ```                                  │         │
│        │                                      │         │
│        │ Validate configuration settings      │         │
│        │                                      │         │
│        │ **Returns:** bool - True if valid    │         │
│        │                                      │         │
└────────┴──────────────────────────────────────┴─────────┘

Features:
  ✅ 3-column layout (tree, content, TOC)
  ✅ Collapsible module tree
  ✅ Syntax highlighted code
  ✅ Type annotations
  ✅ Parameter/return documentation
  ✅ Source code links
  ✅ Search within page
```

### CLI Command Page - `cli-reference/single.html`

```
┌─────────────────────────────────────────────────────────┐
│ Home > CLI > build                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ # bengal build                                          │
│                                                         │
│ 🔨 Build the static site                                │
│                                                         │
│ Generates HTML files from your content, applies         │
│ templates, processes assets, and outputs a production-  │
│ ready site.                                             │
│                                                         │
│ ## Usage                                                │
│                                                         │
│ ```bash                                                 │
│ bengal build [SOURCE] [OPTIONS]                         │
│ ```                                                     │
│                                                         │
│ ## Arguments                                            │
│                                                         │
│ | Argument | Type   | Description        | Default |    │
│ |----------|--------|--------------------|---------│    │
│ | SOURCE   | Path   | Site directory     | .       │    │
│                                                         │
│ ## Options                                              │
│                                                         │
│ | Option        | Type | Description       | Default |  │
│ |---------------|------|-------------------|---------│  │
│ | --clean       | flag | Clean before build| false   │  │
│ | --draft       | flag | Include drafts    | false   │  │
│ | --config PATH | path | Config file       | auto    │  │
│                                                         │
│ ## Examples                                             │
│                                                         │
│ ### Basic build                                         │
│                                                         │
│ ```bash                                                 │
│ bengal build                                            │
│ ```                                                     │
│                                                         │
│ ### Clean build with drafts                             │
│                                                         │
│ ```bash                                                 │
│ bengal build --clean --draft                            │
│ ```                                                     │
│                                                         │
│ ### Build from different directory                      │
│                                                         │
│ ```bash                                                 │
│ bengal build /path/to/site --config custom.toml        │
│ ```                                                     │
│                                                         │
│ ## See Also                                             │
│                                                         │
│ • [bengal serve](../serve) - Development server         │
│ • [bengal clean](../clean) - Clean output directory     │
│                                                         │
└─────────────────────────────────────────────────────────┘

Features:
  ✅ Clear command syntax
  ✅ Argument/option tables
  ✅ Multiple examples
  ✅ Easy to copy commands
  ✅ Related commands links
  ✅ 1-column focused layout
```

---

## Summary of Changes

| Aspect | Current | Proposed |
|--------|---------|----------|
| **API Index Template** | `archive.html` (blog-style) | `api-reference/list.html` (API-specific) |
| **API Index Pagination** | ❌ Shows but broken | ✅ None (not needed) |
| **API Module Cards** | Generic subsections | API-specific with metrics |
| **API Navigation** | None | Module tree sidebar |
| **CLI Index Template** | `page.html` (generic) | `cli-reference/list.html` (CLI-specific) |
| **CLI Overview** | All inline (long) | Condensed cards |
| **CLI Command Cards** | Inline docs | Card with link to detail |
| **Command Documentation** | Mixed in overview | Dedicated pages |
| **Search** | Browser find only | API search planned |
| **Consistency** | Inconsistent | Unified reference docs |

---

## User Experience Improvements

### Before: Confusion & Frustration
- "Why is there pagination on API docs?"
- "Where are all the CLI commands?"
- "How do I navigate between modules?"
- "This looks like a blog, not documentation"
- "Page 2 doesn't work..."

### After: Clear & Professional
- "I can see all API modules at a glance"
- "Command overview is concise and scannable"
- "Easy to navigate the module hierarchy"
- "Looks like professional reference documentation"
- "No broken features"

---

## Implementation Priority

1. **High Priority (Fixes Broken UX):**
   - ✅ Create `api-reference/list.html` to fix `/api/` pagination issue
   - ✅ Remove pagination from documentation archives
   - ✅ Update template selection to use new templates

2. **Medium Priority (Improves UX):**
   - Create `cli-reference/list.html` for better CLI overview
   - Add API module cards partial
   - Add CLI command cards partial

3. **Low Priority (Nice to Have):**
   - Create `api-reference/single.html` with 3-column layout
   - Create `cli-reference/single.html` with examples
   - Add search functionality
   - Add module tree navigation

---

## Next Action

Let's start by creating the `api-reference/list.html` template to fix the immediate `/api/` issues, then work our way through the rest of the implementation.


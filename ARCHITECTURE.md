# Bengal SSG - Architecture Documentation

## Overview

Bengal SSG follows a modular architecture with clear separation of concerns to avoid "God objects" and maintain high performance even with large sites.

## Core Components

### 1. Object Model

#### Site Object (`bengal/core/site.py`)
- **Purpose**: Orchestrates the entire website build process
- **Responsibilities**:
  - Holds configuration and global metadata
  - Manages collections of pages, sections, and assets
  - Coordinates the build process (sequential or parallel)
  - Triggers post-processing tasks
  - Collects taxonomies (tags, categories)
  - Generates dynamic pages (archives, tag pages)
- **Key Methods**:
  - `build()`: Main build orchestration
  - `collect_taxonomies()`: Gather tags/categories from all pages
  - `generate_dynamic_pages()`: Create archive and taxonomy pages
  - `discover_content()`: Find and parse all content files
  - `discover_assets()`: Find all static assets

#### Page Object (`bengal/core/page.py`)
- **Purpose**: Represents a single content page
- **Attributes**:
  - Source path and content
  - Metadata (frontmatter)
  - Parsed AST
  - Rendered HTML
  - Links and tags
  - Output path
- **Properties**:
  - `title`: Get page title from metadata or generate from filename
  - `date`: Get page date from metadata
  - `slug`: Get URL slug for the page
  - `url`: Get the full URL path (e.g., `/posts/my-post/`)
- **Methods**:
  - `render()`: Render page with template
  - `validate_links()`: Check for broken links
  - `extract_links()`: Extract all links from content

#### Section Object (`bengal/core/section.py`)
- **Purpose**: Represents a logical grouping of pages (folder structure)
- **Attributes**:
  - Hierarchy information
  - Collection of pages and subsections
  - Inherited metadata
  - Optional index page
- **Methods**:
  - `aggregate_content()`: Collect metadata from all pages
  - `walk()`: Iteratively traverse section hierarchy
  - `apply_section_template()`: Generate section index

#### Asset Object (`bengal/core/asset.py`)
- **Purpose**: Handles static files (images, CSS, JS)
- **Methods**:
  - `minify()`: Minify CSS/JS
  - `optimize()`: Optimize images
  - `hash()`: Generate fingerprint for cache busting
  - `copy_to_output()`: Copy to output directory

### 2. Rendering Pipeline

The rendering pipeline is divided into clear stages:

```
Parse → Build AST → Apply Templates → Render Output → Post-process
```

#### Parser (`bengal/rendering/parser.py`)
- Converts Markdown (or other formats) to HTML
- Extracts table of contents
- Supports extensions (code highlighting, tables, etc.)

#### Template Engine (`bengal/rendering/template_engine.py`)
- Jinja2-based templating
- Supports nested templates and partials
- Custom filters and global functions
- Multiple template directories (custom, theme, default)

#### Renderer (`bengal/rendering/renderer.py`)
- Applies templates to pages
- Determines which template to use based on page metadata
- Fallback rendering for error cases

#### Pipeline Coordinator (`bengal/rendering/pipeline.py`)
- Orchestrates all stages for each page
- Handles output path determination
- Writes final output to disk

### 3. Discovery System

#### Content Discovery (`bengal/discovery/content_discovery.py`)
- Walks content directory recursively
- Creates Page and Section objects
- Parses frontmatter
- Organizes content into hierarchy

#### Asset Discovery (`bengal/discovery/asset_discovery.py`)
- Finds all static assets
- Preserves directory structure
- Creates Asset objects with metadata

### 4. Configuration System

#### Config Loader (`bengal/config/loader.py`)
- Supports TOML and YAML formats
- Auto-detects config files
- Provides sensible defaults
- Flattens nested configuration for easy access

### 5. Post-Processing

#### Sitemap Generator (`bengal/postprocess/sitemap.py`)
- Generates XML sitemap for SEO
- Includes all pages with metadata
- Configurable priority and change frequency

#### RSS Generator (`bengal/postprocess/rss.py`)
- Generates RSS feed
- Includes recent posts
- Supports custom descriptions

#### Link Validator (`bengal/rendering/link_validator.py`)
- Validates internal and external links
- Reports broken links
- Can be extended for comprehensive validation

### 6. Development Server

#### Dev Server (`bengal/server/dev_server.py`)
- Built-in HTTP server
- File system watching with watchdog
- Automatic rebuild on changes
- Hot reload support (future enhancement)

### 7. CLI (`bengal/cli.py`)
- Click-based command-line interface
- Commands:
  - `bengal build`: Build the site
  - `bengal serve`: Start dev server
  - `bengal clean`: Clean output
  - `bengal new site/page`: Create new content
  - `bengal --version`: Show version

### 8. Utilities (`bengal/utils/`)

#### Paginator (`bengal/utils/pagination.py`)
- **Purpose**: Generic pagination utility for splitting long lists
- **Features**:
  - Configurable items per page
  - Page range calculation (smart ellipsis)
  - Template context generation
  - Type-safe generic implementation
- **Usage**: Used for archive pages and tag pages

## Design Principles

### 1. Avoiding Stack Overflow
- **Iterative Traversal**: Section hierarchy uses `walk()` method instead of deep recursion
- **Configurable Limits**: Can set max recursion depth if needed
- **Tail Call Patterns**: Where recursion is used, structured for optimization

### 2. Avoiding God Objects
- **Single Responsibility**: Each class has one clear purpose
- **Composition over Inheritance**: Objects compose other objects rather than inheriting
- **Clear Dependencies**: Site → Sections → Pages (one direction)

### 3. Performance Optimization
- **Parallel Processing**: Pages can be rendered in parallel using ThreadPoolExecutor
- **Incremental Builds**: Track file changes and rebuild only what's needed (future enhancement)
- **Caching**: Template caching, AST caching (future enhancement)
- **Lazy Loading**: Parse content only when needed

### 4. Extensibility
- **Plugin System**: Hooks for pre/post build events (future enhancement)
- **Custom Content Types**: Easy to add new parsers
- **Template Flexibility**: Custom templates override defaults
- **Theme System**: Self-contained themes with templates and assets

## Data Flow

```
Content Files (Markdown)
    ↓
Content Discovery
    ↓
Page Objects
    ↓
Markdown Parser → AST
    ↓
Template Engine
    ↓
Rendered HTML
    ↓
Output Files

Assets
    ↓
Asset Discovery
    ↓
Asset Objects
    ↓
Optimization Pipeline
    ↓
Output Files
```

## Performance Considerations

### Current Optimizations
1. **Parallel Page Rendering**: Multiple pages rendered simultaneously
2. **Efficient File I/O**: Batch operations where possible
3. **Minimal Dependencies**: Only necessary libraries included

### Future Optimizations
1. **Incremental Builds**: Only rebuild changed files
2. **Content Caching**: Cache parsed content between builds
3. **Asset Deduplication**: Share common assets
4. **Build Profiling**: Identify bottlenecks

## Extension Points

### 1. Custom Content Types
Implement a new parser in `bengal/rendering/parser.py`:
```python
class ReStructuredTextParser:
    def parse(self, content: str) -> str:
        # Convert RST to HTML
        pass
```

### 2. Custom Post-Processors
Add new generators in `bengal/postprocess/`:
```python
class RobotsGenerator:
    def generate(self, site: Site) -> None:
        # Generate robots.txt
        pass
```

### 3. Build Hooks (Future)
```python
@bengal.hook('pre_build')
def custom_pre_build(site):
    # Custom logic before build
    pass
```

## Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Full build tests with sample sites
4. **Performance Tests**: Benchmark builds with large sites

## Recent Additions (Phase 2A & 2B)

### Taxonomy System
- **Automatic Collection**: Tags and categories extracted from all pages
- **Dynamic Pages**: Tag index and individual tag pages auto-generated
- **Organized Data**: Taxonomies stored in structured format for templates

### Dynamic Page Generation
- **Archive Pages**: Automatically created for sections (e.g., `/posts/`)
- **Tag Pages**: Individual pages for each tag (e.g., `/tags/tutorial/`)
- **Tag Index**: Central page listing all tags (`/tags/`)
- **Virtual Pages**: Generated pages behave like real pages in the system

### Pagination System
- **Generic Paginator**: Reusable utility class for any list
- **Automatic Pagination**: Archives and tag pages paginate when > 10 items
- **URL Structure**: Page 1 at base URL, subsequent at `/page/N/`
- **Template Context**: Full pagination data (current, total, next, previous)
- **Configurable**: Per-page count configurable globally or per-section

### Theme Enhancements
- **Breadcrumb Navigation**: Auto-generated from URL structure
- **404 Page**: Professional error page with helpful navigation
- **Responsive Pagination Controls**: With proper accessibility
- **Template Partials**: Reusable components (article-card, tag-list, pagination)

## Roadmap

**Completed:**
- [x] Core object model
- [x] Rendering pipeline
- [x] CLI basics
- [x] Dev server
- [x] Taxonomy system
- [x] Dynamic page generation
- [x] Pagination system
- [x] Production-ready default theme

**Next Priorities:**
- [ ] Incremental builds (track file changes, rebuild only what's needed)
- [ ] Parallel rendering optimization
- [ ] Plugin system with hooks
- [ ] Advanced asset pipeline (minification, optimization)
- [ ] Comprehensive documentation site
- [ ] Performance benchmarking

**Future:**
- [ ] Hot reload in browser
- [ ] Build caching
- [ ] Multi-language support
- [ ] Search functionality
- [ ] Content versioning


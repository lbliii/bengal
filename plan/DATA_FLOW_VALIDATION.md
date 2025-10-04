# Data Transformation Flow - Code Validation

**Validation Date**: October 4, 2025  
**Validated Against**: bengal/orchestration/build.py (actual execution flow)

This document validates the data transformation diagram against the actual codebase implementation, line by line.

---

## ✅ Validation Summary

| Phase | My Diagram | Actual Code | Status | Notes |
|-------|------------|-------------|--------|-------|
| 0 | Missing | Site.from_config() | ❌ **MISSING** | Config loading happens before build() |
| 1a | Content Discovery | content.discover() | ✅ **CORRECT** | Line 86 |
| 1b | Missing | _setup_page_references() | ❌ **MISSING** | Part of Phase 1, not shown |
| 1c | Missing | _apply_cascades() | ⚠️ **MISLABELED** | Called in Phase 1, not after |
| 1d | Missing | _build_xref_index() | ❌ **MISSING** | Cross-reference index building |
| 2 | Missing | finalize_sections() | ❌ **MISSING** | Auto-generate section indexes |
| 3 | Taxonomy & Pages | collect_and_generate() | ✅ **CORRECT** | Line 117 |
| 4 | Menus | menu.build() | ✅ **CORRECT** | Line 121 |
| 5 | Missing | Incremental work detection | ❌ **MISSING** | Line 124-150 |
| 6a | Missing | _set_output_paths_for_all_pages() | ❌ **MISSING** | Before rendering |
| 6b | Rendering | render.process() | ✅ **CORRECT** | Line 161 |
| 7 | Missing | Asset processing | ⚠️ **INCOMPLETE** | Line 175 |
| 8 | Post-processing | postprocess.run() | ✅ **CORRECT** | Line 182 |
| 9 | Missing | Cache saving | ❌ **MISSING** | Line 187 |
| 10 | Missing | Health check | ❌ **MISSING** | Line 207 |

---

## 🔍 Phase-by-Phase Validation

### Phase 0: Site Initialization (MISSING FROM DIAGRAM)

**Actual Code:**
```python
# bengal/cli.py:63
site = Site.from_config(root_path, config_path)

# bengal/core/site.py:112-128
@classmethod
def from_config(cls, root_path: Path, config_path: Optional[Path] = None) -> 'Site':
    from bengal.config.loader import ConfigLoader
    
    loader = ConfigLoader(root_path)
    config = loader.load(config_path)  # ← DATA TRANSFORMATION HERE
    
    return cls(root_path=root_path, config=config)
```

**Config Loading:** `bengal/config/loader.py:40-100`
```python
def load(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
    # Tries: bengal.toml, bengal.yaml, bengal.yml
    if config_path:
        return self._load_file(config_path)
    
    # Auto-detect config file
    for filename in ['bengal.toml', 'bengal.yaml', 'bengal.yml']:
        config_file = self.root_path / filename
        if config_file.exists():
            return self._load_file(config_file)

def _load_toml(self, config_path: Path) -> Dict[str, Any]:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = toml.load(f)  # ← RAW TOML → DICT
    return self._flatten_config(config)  # ← DICT → FLATTENED DICT
```

**Data Transformation:**
```
bengal.toml (TOML text)
    ↓ toml.load()
Raw dict {'site': {'title': 'X'}, 'build': {...}}
    ↓ _flatten_config()
Flattened dict {'title': 'X', 'site': {'title': 'X'}, ...}
    ↓ ConfigValidator.validate()
Validated config dict
    ↓
Site.config
```

**Verdict:** ❌ **MISSING** - Diagram doesn't show config loading at all!

---

### Phase 1a: Content Discovery

**Actual Code:** `bengal/orchestration/build.py:84-87`
```python
# Phase 1: Content Discovery
discovery_start = time.time()
self.content.discover()  # ← HERE
self.stats.discovery_time_ms = (time.time() - discovery_start) * 1000
```

**What it calls:** `bengal/orchestration/content.py:36-42`
```python
def discover(self) -> None:
    self.discover_content()  # ← Discovers pages and sections
    self.discover_assets()   # ← Discovers CSS, JS, images
```

**Content Discovery:** `bengal/discovery/content_discovery.py:29-64`
```python
def discover(self) -> Tuple[List[Section], List[Page]]:
    for item in sorted(self.content_dir.iterdir()):
        if item.is_file() and self._is_content_file(item):
            page = self._create_page(item)  # ← CREATE PAGE
            self.pages.append(page)
        elif item.is_dir():
            section = Section(name=item.name, path=item)  # ← CREATE SECTION
            self._walk_directory(item, section)
            self.sections.append(section)
```

**Frontmatter Parsing:** `bengal/discovery/content_discovery.py:147-184`
```python
def _parse_content_file(self, file_path: Path) -> tuple:
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()  # ← FILE TEXT
    
    post = frontmatter.loads(file_content)  # ← PARSE FRONTMATTER
    content = post.content     # ← MARKDOWN STRING
    metadata = dict(post.metadata)  # ← METADATA DICT
    return content, metadata
```

**Page Creation:** `bengal/discovery/content_discovery.py:137-145`
```python
def _create_page(self, file_path: Path) -> Page:
    content, metadata = self._parse_content_file(file_path)
    
    page = Page(
        source_path=file_path,
        content=content,      # ← RAW MARKDOWN
        metadata=metadata,    # ← FRONTMATTER DICT
    )
    return page
```

**Data Transformation:**
```
content/blog/post.md (file on disk)
    ↓ open().read()
"---\ntitle: Post\n---\n# Content" (string)
    ↓ frontmatter.loads()
Post object: {metadata: {...}, content: "..."}
    ↓ Page(...)
Page object with metadata dict and content string
```

**Verdict:** ✅ **CORRECT** - My diagram shows this accurately.

---

### Phase 1b: Reference Setup (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/content.py:44-70`
```python
def discover_content(self, content_dir: Optional[Path] = None) -> None:
    # ... discovery code ...
    
    # Set up page references for navigation
    self._setup_page_references()  # ← LINE 64
    
    # Apply cascading frontmatter from sections to pages
    self._apply_cascades()  # ← LINE 67
    
    # Build cross-reference index for O(1) lookups
    self._build_xref_index()  # ← LINE 70
```

**Reference Setup:** `bengal/orchestration/content.py:103-146`
```python
def _setup_page_references(self) -> None:
    # Set site reference on all pages (including top-level pages)
    for page in self.site.pages:
        page._site = self.site  # ← TRANSFORMATION: Add _site reference
        if not hasattr(page, '_section'):
            page._section = None  # ← TRANSFORMATION: Initialize _section
    
    # Set section references
    for section in self.site.sections:
        section._site = self.site  # ← TRANSFORMATION: Add _site reference
        
        # Set section reference on all pages in this section
        for page in section.pages:
            page._section = section  # ← TRANSFORMATION: Link to section
```

**Data Transformation:**
```
BEFORE:
Page(
    source_path=Path("content/blog/post.md"),
    metadata={'title': 'Post'},
    _site=None,      # ← NOT SET
    _section=None    # ← NOT SET
)

AFTER:
Page(
    source_path=Path("content/blog/post.md"),
    metadata={'title': 'Post'},
    _site=<Site object>,     # ← NOW SET
    _section=<Section 'blog'>  # ← NOW SET
)
```

**Verdict:** ❌ **MISSING** - Diagram doesn't show this critical step!

---

### Phase 1c: Cascade Application

**Actual Code:** `bengal/orchestration/content.py:148-206`
```python
def _apply_cascades(self) -> None:
    # Process all top-level sections (they will recurse to subsections)
    for section in self.site.sections:
        self._apply_section_cascade(section, parent_cascade=None)

def _apply_section_cascade(self, section: 'Section', 
                          parent_cascade: Optional[Dict[str, Any]] = None) -> None:
    # Merge parent cascade with this section's cascade
    accumulated_cascade = {}
    
    if parent_cascade:
        accumulated_cascade.update(parent_cascade)
    
    if 'cascade' in section.metadata:
        accumulated_cascade.update(section.metadata['cascade'])
    
    # Apply accumulated cascade to all pages in this section
    for page in section.pages:
        if accumulated_cascade:
            for key, value in accumulated_cascade.items():
                if key not in page.metadata:  # ← TRANSFORMATION
                    page.metadata[key] = value  # ← ADDS CASCADED VALUES
```

**Data Transformation:**
```
Section metadata: {'cascade': {'type': 'post', 'layout': 'blog'}}
Page metadata (before): {'title': 'My Post', 'author': 'John'}

↓ _apply_section_cascade()

Page metadata (after): {
    'title': 'My Post',      # From page (unchanged)
    'author': 'John',        # From page (unchanged)
    'type': 'post',          # From cascade (ADDED)
    'layout': 'blog'         # From cascade (ADDED)
}
```

**Verdict:** ✅ **CORRECT** - My diagram shows this, but **wrong order**!  
It happens in Phase 1, not as a separate phase after reference setup.

---

### Phase 1d: Cross-Reference Index Building (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/content.py:208-262`
```python
def _build_xref_index(self) -> None:
    self.site.xref_index = {
        'by_path': {},      # 'docs/getting-started' -> Page
        'by_slug': {},      # 'getting-started' -> [Pages]
        'by_id': {},        # Custom IDs from frontmatter -> Page
        'by_heading': {},   # Heading text -> [(Page, anchor)]
    }
    
    for page in self.site.pages:
        # Index by relative path
        rel_path = page.source_path.relative_to(content_dir)
        path_key = str(rel_path.with_suffix('')).replace('\\', '/')
        self.site.xref_index['by_path'][path_key] = page
        
        # Index by slug
        if hasattr(page, 'slug') and page.slug:
            self.site.xref_index['by_slug'].setdefault(page.slug, []).append(page)
        
        # Index custom IDs
        if 'id' in page.metadata:
            self.site.xref_index['by_id'][page.metadata['id']] = page
```

**Data Transformation:**
```
site.pages = [Page1, Page2, Page3]

↓ _build_xref_index()

site.xref_index = {
    'by_path': {
        'docs/guide': Page1,
        'blog/post': Page2
    },
    'by_slug': {
        'guide': [Page1],
        'post': [Page2]
    },
    'by_id': {
        'installation-guide': Page1
    },
    'by_heading': {...}
}
```

**Verdict:** ❌ **MISSING** - This is a significant data transformation not shown!

---

### Phase 2: Section Finalization (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/build.py:95-113`
```python
# Phase 2: Section Finalization (ensure all sections have index pages)
print("\n✨ Generated pages:")
self.sections.finalize_sections()  # ← LINE 97

# Validate section structure
section_errors = self.sections.validate_sections()
```

**What it does:** `bengal/orchestration/section.py:45-82`
```python
def finalize_sections(self) -> None:
    for section in self.site.sections:
        self._finalize_recursive(section)

def _finalize_recursive(self, section: 'Section') -> None:
    # Ensure this section has an index page
    if not section.index_page:
        # Generate archive index
        archive_page = self._create_archive_index(section)  # ← CREATE PAGE
        section.index_page = archive_page
        self.site.pages.append(archive_page)  # ← ADD TO SITE
```

**Archive Page Creation:** `bengal/orchestration/section.py:176-246`
```python
def _create_archive_index(self, section: 'Section') -> 'Page':
    # Detect content type (api-reference, cli-reference, archive, etc.)
    content_type = self._detect_content_type(section)
    
    # Create virtual path
    virtual_path = self.url_strategy.make_virtual_path(
        self.site, 'archives', section.name
    )
    
    # Create archive page
    archive_page = Page(
        source_path=virtual_path,
        content="",  # ← NO SOURCE CONTENT
        metadata={
            'title': section.title,
            'template': template,
            'type': content_type,
            '_generated': True,      # ← MARKS AS GENERATED
            '_virtual': True,
            '_section': section,
            '_posts': section.pages,  # ← REFERENCE TO CONTENT
        }
    )
    
    # Compute output path
    archive_page.output_path = self.url_strategy.compute_archive_output_path(
        section=section, page_num=1, site=self.site
    )
    
    # Ensure page is correctly initialized (sets _site, validates)
    self.initializer.ensure_initialized_for_section(archive_page, section)
    
    return archive_page
```

**Data Transformation:**
```
BEFORE:
Section(
    name='api',
    pages=[Page1, Page2, Page3],
    index_page=None  # ← NO INDEX PAGE
)

↓ _create_archive_index()

NEW PAGE CREATED:
Page(
    source_path=Path(".bengal/virtual/archives/api.md"),
    content="",
    metadata={
        '_generated': True,
        '_section': <Section 'api'>,
        '_posts': [Page1, Page2, Page3],
        'template': 'api-reference/list.html'
    },
    output_path=Path("public/api/index.html"),
    _site=<Site>,
    _section=<Section 'api'>
)

AFTER:
Section(
    name='api',
    pages=[Page1, Page2, Page3, ArchivePage],  # ← ADDED
    index_page=ArchivePage  # ← NOW SET
)
site.pages += [ArchivePage]  # ← ADDED TO SITE
```

**Verdict:** ❌ **MISSING** - Major transformation not in diagram!

---

### Phase 3: Taxonomies & Dynamic Pages

**Actual Code:** `bengal/orchestration/build.py:115-118`
```python
# Phase 3: Taxonomies & Dynamic Pages
taxonomy_start = time.time()
self.taxonomy.collect_and_generate()  # ← HERE
self.stats.taxonomy_time_ms = (time.time() - taxonomy_start) * 1000
```

**What it does:** `bengal/orchestration/taxonomy.py:44-50`
```python
def collect_and_generate(self) -> None:
    self.collect_taxonomies()     # ← Collect tags/categories
    self.generate_dynamic_pages()  # ← Generate tag pages
```

**Taxonomy Collection:** `bengal/orchestration/taxonomy.py:52-98`
```python
def collect_taxonomies(self) -> None:
    # Initialize taxonomy structure
    self.site.taxonomies = {'tags': {}, 'categories': {}}
    
    # Collect from all pages
    for page in self.site.pages:
        # Collect tags
        if page.tags:
            for tag in page.tags:
                tag_key = tag.lower().replace(' ', '-')
                if tag_key not in self.site.taxonomies['tags']:
                    self.site.taxonomies['tags'][tag_key] = {
                        'name': tag,
                        'slug': tag_key,
                        'pages': []
                    }
                self.site.taxonomies['tags'][tag_key]['pages'].append(page)
```

**Data Transformation:**
```
Pages with tags:
Page1.tags = ['Python', 'Tutorial']
Page2.tags = ['Python']
Page3.tags = ['Rust']

↓ collect_taxonomies()

site.taxonomies = {
    'tags': {
        'python': {
            'name': 'Python',
            'slug': 'python',
            'pages': [Page1, Page2]
        },
        'tutorial': {
            'name': 'Tutorial',
            'slug': 'tutorial',
            'pages': [Page1]
        },
        'rust': {
            'name': 'Rust',
            'slug': 'rust',
            'pages': [Page3]
        }
    },
    'categories': {}
}
```

**Tag Page Generation:** `bengal/orchestration/taxonomy.py:167-223`
```python
def _create_tag_pages(self, tag_slug: str, tag_data: Dict[str, Any]) -> List['Page']:
    pages_to_create = []
    per_page = self.site.config.get('pagination', {}).get('per_page', 10)
    
    paginator = Paginator(tag_data['pages'], per_page=per_page)
    
    for page_num in range(1, paginator.num_pages + 1):
        tag_page = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': f"Posts tagged '{tag_data['name']}'",
                'template': 'tag.html',
                '_generated': True,
                '_tag': tag_data['name'],
                '_posts': tag_data['pages'],
                '_paginator': paginator,
                '_page_num': page_num
            }
        )
        
        tag_page.output_path = self.url_strategy.compute_tag_output_path(
            tag_slug=tag_slug, page_num=page_num, site=self.site
        )
        
        self.initializer.ensure_initialized(tag_page)
        pages_to_create.append(tag_page)
    
    return pages_to_create
```

**Verdict:** ✅ **CORRECT** - My diagram shows this accurately.

---

### Phase 4: Menus

**Actual Code:** `bengal/orchestration/build.py:120-121`
```python
# Phase 4: Menus
self.menu.build()  # ← HERE
```

**What it does:** `bengal/orchestration/menu.py:33-69`
```python
def build(self) -> None:
    from bengal.core.menu import MenuBuilder
    
    menu_config = self.site.config.get('menu', {})
    
    for menu_name, items in menu_config.items():
        builder = MenuBuilder()
        
        # Add config-defined items
        if isinstance(items, list):
            builder.add_from_config(items)
        
        # Add items from page frontmatter
        for page in self.site.pages:
            page_menu = page.metadata.get('menu', {})
            if menu_name in page_menu:
                builder.add_from_page(page, menu_name, page_menu[menu_name])
        
        # Build hierarchy
        self.site.menu[menu_name] = builder.build_hierarchy()
        self.site.menu_builders[menu_name] = builder
```

**Data Transformation:**
```
Config:
menu = {
    'main': [
        {'name': 'Home', 'url': '/', 'weight': 1},
        {'name': 'Blog', 'url': '/blog/', 'weight': 2}
    ]
}

Page frontmatter:
metadata = {
    'menu': {
        'main': {'weight': 3}  # Use page title and URL
    }
}

↓ menu.build()

site.menu = {
    'main': [
        MenuItem(name='Home', url='/', weight=1),
        MenuItem(name='Blog', url='/blog/', weight=2),
        MenuItem(name='About', url='/about/', weight=3)  # From page
    ]
}
```

**Verdict:** ✅ **CORRECT** - My diagram shows this accurately.

---

### Phase 5: Incremental Build Work Detection (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/build.py:123-150`
```python
# Phase 5: Determine what to build (incremental)
pages_to_build = self.site.pages
assets_to_process = self.site.assets

if incremental:
    pages_to_build, assets_to_process, change_summary = self.incremental.find_work(
        verbose=verbose
    )
    
    if not pages_to_build and not assets_to_process:
        print("✓ No changes detected - skipping build")
        self.stats.skipped = True
        return self.stats
```

**Data Transformation:**
```
ALL PAGES:
site.pages = [Page1, Page2, Page3, Page4, Page5]

↓ incremental.find_work() (compares hashes)

FILTERED:
pages_to_build = [Page2, Page4]  # Only changed pages

site.pages remains unchanged (full list)
but we only render pages_to_build
```

**Verdict:** ❌ **MISSING** - Incremental build filtering not shown!

---

### Phase 6a: Output Path Pre-computation (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/render.py:40-57`
```python
def process(self, pages: List['Page'], parallel: bool = True, ...) -> None:
    # PRE-PROCESS: Set output paths for ALL pages before rendering starts
    # This ensures that page.url works correctly in templates (e.g., for navigation)
    # Even if a page isn't being rendered yet, its URL needs to be available
    self._set_output_paths_for_all_pages()  # ← LINE 57
    
    if parallel and len(pages) > 1:
        self._render_parallel(pages, tracker, quiet, stats)
    else:
        self._render_sequential(pages, tracker, quiet, stats)
```

**What it does:** `bengal/orchestration/render.py:127-163`
```python
def _set_output_paths_for_all_pages(self) -> None:
    content_dir = self.site.root_path / "content"
    pretty_urls = self.site.config.get('pretty_urls', True)
    
    for page in self.site.pages:
        # Skip if already set (e.g., generated pages)
        if page.output_path:
            continue
        
        # Skip generated pages (they set their own paths)
        if page.metadata.get('_generated'):
            continue
        
        # Compute output path for regular pages
        try:
            rel_path = page.source_path.relative_to(content_dir)
        except ValueError:
            rel_path = Path(page.source_path.name)
        
        output_rel_path = rel_path.with_suffix('.html')
        
        if pretty_urls:
            if output_rel_path.stem in ("index", "_index"):
                output_rel_path = output_rel_path.parent / "index.html"
            else:
                # about.md → about/index.html
                output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        
        page.output_path = self.site.output_dir / output_rel_path
```

**Data Transformation:**
```
BEFORE:
Page(
    source_path=Path("content/blog/post.md"),
    output_path=None  # ← NOT SET
)

↓ _set_output_paths_for_all_pages()

AFTER:
Page(
    source_path=Path("content/blog/post.md"),
    output_path=Path("public/blog/post/index.html")  # ← NOW SET
)
```

**Why critical:** `page.url` property depends on `output_path`:
```python
# bengal/core/page.py:93-146
@property
def url(self) -> str:
    if not self.output_path:
        return self._fallback_url()  # Wrong URL!
    
    # Compute from output_path
    rel_path = self.output_path.relative_to(self._site.output_dir)
    # ... build URL
```

**Verdict:** ❌ **MISSING** - Critical transformation not shown!

---

### Phase 6b: Page Rendering

**Actual Code:** `bengal/orchestration/build.py:152-164`
```python
# Phase 6: Render Pages
rendering_start = time.time()
self.render.process(pages_to_build, parallel=parallel, tracker=tracker, stats=self.stats)
self.stats.rendering_time_ms = (time.time() - rendering_start) * 1000
```

**Per-Page Processing:** `bengal/rendering/pipeline.py:88-174`
```python
def process_page(self, page: Page) -> None:
    # Stage 0: Determine output path (fallback if not set)
    if not page.output_path:
        page.output_path = self._determine_output_path(page)
    
    # Stage 1 & 2: Parse content with variable substitution
    if hasattr(self.parser, 'parse_with_toc_and_context'):
        context = {
            'page': page,
            'site': self.site,
            'config': self.site.config
        }
        parsed_content, toc = self.parser.parse_with_toc_and_context(
            page.content, page.metadata, context
        )
    
    page.parsed_ast = parsed_content  # ← TRANSFORMATION (markdown → HTML)
    
    # Post-process: Enhance API documentation with badges
    from bengal.rendering.api_doc_enhancer import get_enhancer
    enhancer = get_enhancer()
    page_type = page.metadata.get('type')
    if enhancer.should_enhance(page_type):
        page.parsed_ast = enhancer.enhance(page.parsed_ast, page_type)
    
    page.toc = toc  # ← TRANSFORMATION (extract TOC)
    
    # Stage 3: Extract links for validation
    page.extract_links()  # ← TRANSFORMATION (HTML → link list)
    
    # Stage 4: Render content to HTML
    html_content = self.renderer.render_content(parsed_content)
    
    # Stage 5: Apply template
    page.rendered_html = self.renderer.render_page(page, html_content)
    
    # Stage 6: Write output
    self._write_output(page)
```

**Data Transformations:**
```
1. Markdown → HTML with {{ variable }} substitution:
   page.content = "# {{ page.title }}"
   ↓ parse_with_toc_and_context()
   parsed_html = "<h1>My Post</h1>"

2. HTML → Enhanced HTML (for API docs):
   parsed_html = "<p>@async</p>"
   ↓ enhancer.enhance()
   parsed_html = "<p><span class='api-badge'>@async</span></p>"

3. HTML → TOC:
   parsed_html = "<h1 id='intro'>Intro</h1><h2 id='section'>Section</h2>"
   ↓ extract TOC
   toc = "<ul><li><a href='#intro'>Intro</a>...</li></ul>"

4. HTML → Links:
   parsed_html = "<a href='/about/'>About</a>"
   ↓ extract_links()
   page.links = ['/about/']

5. HTML + Template → Final HTML:
   html_content = "<h1>My Post</h1>"
   template = "{% extends 'base.html' %}..."
   ↓ render_page()
   page.rendered_html = "<!DOCTYPE html><html>...</html>"

6. Final HTML → File:
   page.rendered_html
   ↓ write()
   public/blog/post/index.html
```

**Verdict:** ⚠️ **PARTIALLY CORRECT** - My diagram shows rendering but misses:
- API doc enhancement step
- Link extraction step
- Separate render_content() and render_page() steps

---

### Phase 7: Asset Processing

**Actual Code:** `bengal/orchestration/build.py:170-178`
```python
# Phase 7: Process Assets
assets_start = time.time()
self.assets.process(assets_to_process, parallel=parallel)
self.stats.assets_time_ms = (time.time() - assets_start) * 1000
```

**Verdict:** ⚠️ **INCOMPLETE** - My diagram mentions assets briefly but doesn't show transformations.

---

### Phase 8: Post-processing

**Actual Code:** `bengal/orchestration/build.py:180-183`
```python
# Phase 8: Post-processing
postprocess_start = time.time()
self.postprocess.run(parallel=parallel)
self.stats.postprocess_time_ms = (time.time() - postprocess_start) * 1000
```

**Verdict:** ✅ **CORRECT** - My diagram shows this accurately.

---

### Phase 9: Cache Saving (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/build.py:185-187`
```python
# Phase 9: Update cache
if incremental or self.site.config.get("cache_enabled", True):
    self.incremental.save_cache(pages_to_build, assets_to_process)
```

**Verdict:** ❌ **MISSING** - Cache persistence not shown!

---

### Phase 10: Health Check (MISSING FROM DIAGRAM)

**Actual Code:** `bengal/orchestration/build.py:206-207`
```python
# Phase 10: Health Check
self._run_health_check()
```

**Verdict:** ❌ **MISSING** - Health check validation not shown!

---

## 🎯 Critical Missing Transformations

### 1. **Config Loading** (Phase 0)
```
bengal.toml → ConfigLoader → Site.config
```

### 2. **Reference Setup** (Phase 1b)
```
Page(metadata={...}) → page._site = site → Page(metadata={...}, _site=<Site>)
```

### 3. **Cross-Reference Index** (Phase 1d)
```
List[Page] → build index → site.xref_index = {'by_path': {...}, 'by_slug': {...}}
```

### 4. **Section Auto-Index Generation** (Phase 2)
```
Section(index_page=None) → create archive → Section(index_page=<Page>)
```

### 5. **Output Path Pre-computation** (Phase 6a)
```
Page(output_path=None) → compute paths → Page(output_path=Path("public/..."))
```

### 6. **API Doc Enhancement** (Phase 6b substep)
```
"<p>@async</p>" → enhance → "<p><span class='api-badge'>@async</span></p>"
```

### 7. **Link Extraction** (Phase 6b substep)
```
"<a href='/about/'>About</a>" → extract → page.links = ['/about/']
```

---

## 📊 Accuracy Summary

**Total Phases in Actual Code**: 11 (0-10)  
**Phases in My Diagram**: 11 (1-11, but wrong numbering)  
**Correctly Represented**: 4  
**Missing**: 7  
**Partially Correct**: 3  
**Mislabeled/Wrong Order**: 2  

**Overall Accuracy**: ~36% ❌

---

## ✅ What to Fix

1. **Add Phase 0**: Config loading (toml → dict)
2. **Expand Phase 1**: Show reference setup, cascades, xref index as sub-phases
3. **Add Phase 2**: Section finalization (auto-generate indexes)
4. **Fix Phase Order**: Taxonomies come BEFORE site population, not after
5. **Add Phase 6a**: Output path pre-computation (critical for URLs!)
6. **Expand Phase 6b**: Show sub-transformations:
   - Variable substitution
   - Markdown parsing
   - API enhancement
   - Link extraction
   - Template rendering
7. **Add Phase 9**: Cache saving
8. **Add Phase 10**: Health check

---

## 🔗 Critical Dependencies

These dependencies explain **why** order matters:

```
Config loading → Site creation → Content discovery
Content discovery → Reference setup → Cascades → XRef index
Section finalization → Taxonomy collection (needs all pages)
Taxonomy collection → Menu building (needs taxonomy pages)
Output path computation → Rendering (page.url needs output_path)
Rendering → Post-processing (needs all pages rendered)
Post-processing → Cache saving (needs render stats)
```

**Key Insight**: My diagram showed transformations out of order, which would break these dependencies!



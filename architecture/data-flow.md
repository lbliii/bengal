
## Complete Build Pipeline (from build.py)

```
┌─────────────────────────────────────────────────────────────────┐
│                         BUILD START                              │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: CONTENT DISCOVERY (ContentOrchestrator)                │
│   content/ (Markdown files)                                     │
│       ↓                                                          │
│   ContentDiscovery.discover()                                   │
│       ↓                                                          │
│   Page Objects (with frontmatter + raw content)                 │
│   Section Objects (directory structure)                         │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: SECTION FINALIZATION (SectionOrchestrator)             │
│   - Ensure sections have index pages                            │
│   - Validate section structure                                  │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: TAXONOMIES (TaxonomyOrchestrator)                      │
│   - Collect tags/categories from pages                          │
│   - Generate taxonomy pages (tag list, archive, etc.)           │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: MENUS (MenuOrchestrator)                               │
│   - Build navigation structure                                  │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: INCREMENTAL FILTERING (IncrementalOrchestrator)        │
│   - Detect changed files (if incremental mode)                  │
│   - Filter to pages/assets that need rebuilding                 │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 6: RENDERING (RenderOrchestrator)                         │
│   For each page:                                                │
│       Page Object (content + metadata)                          │
│           ↓                                                      │
│       RenderingPipeline.process_page()                          │
│           ↓                                                      │
│       ┌─────────────────────────────────┐                       │
│       │ 1. Markdown Parsing             │                       │
│       │    - parse_with_toc_and_context │                       │
│       │    - Variable substitution      │                       │
│       │    - Output: HTML + TOC         │                       │
│       └───────────┬─────────────────────┘                       │
│                   ↓                                              │
│       ┌─────────────────────────────────┐                       │
│       │ 2. Post-processing              │                       │
│       │    - API doc enhancement        │                       │
│       │    - Link extraction            │                       │
│       └───────────┬─────────────────────┘                       │
│                   ↓                                              │
│       ┌─────────────────────────────────┐                       │
│       │ 3. Template Application         │                       │
│       │    - Jinja2 TemplateEngine      │                       │
│       │    - Inject content into layout │                       │
│       │    - Output: Complete HTML      │                       │
│       └───────────┬─────────────────────┘                       │
│                   ↓                                              │
│       page.rendered_html                                        │
│           ↓                                                      │
│       Write to output/ (atomic)                                 │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 7: ASSETS (AssetOrchestrator)                             │
│   assets/ (CSS, JS, images, fonts, etc.)                        │
│       ↓                                                          │
│   AssetDiscovery.discover()                                     │
│       ↓                                                          │
│   Asset Objects                                                 │
│       ↓                                                          │
│   For each asset:                                               │
│       - Minify (CSS/JS) → asset.minify()                        │
│       - Optimize (images) → asset.optimize()                    │
│       - Hash fingerprint (cache busting)                        │
│       - Copy to output/assets/ (with fingerprint)               │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 8: POST-PROCESSING (PostprocessOrchestrator)              │
│   - Generate sitemap.xml                                        │
│   - Generate RSS feed                                           │
│   - Validate links                                              │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 9: CACHE UPDATE (IncrementalOrchestrator)                 │
│   - Save build cache for next incremental build                 │
│   - Update dependency graph                                     │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 10: HEALTH CHECK                                          │
│   - Run validators                                              │
│   - Generate health report                                      │
└───────────────────────────────────┬─────────────────────────────┘
                                    ↓
                            BUILD COMPLETE
```

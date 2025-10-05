# RFC Action Plan: Concrete Next Steps

**Date:** October 5, 2025  
**Based on:** RFC_OPTIMIZATION_ANALYSIS.md  
**Goal:** Implement highest ROI optimizations for Bengal SSG

---

## TL;DR

**The RFC assumes problems Bengal doesn't have.** Most recommendations are already implemented or not applicable.

**Actual Quick Win:** Jinja2 bytecode caching (10-15% speedup, 2 days work)

---

## Phase 1: Immediate Quick Wins (Week 1-2)

### ✅ Task 1: Jinja2 Bytecode Caching
**ROI:** 💰 HIGH (10-15% speedup)  
**Effort:** 2 days  
**Risk:** LOW

**Implementation:**
```python
# File: bengal/rendering/template_engine.py

from jinja2.bccache import FileSystemBytecodeCache

class TemplateEngine:
    def _create_environment(self):
        # Add bytecode cache
        cache_dir = self.site.output_dir / ".bengal-cache" / "templates"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(['html', 'xml']),
            bytecode_cache=FileSystemBytecodeCache(str(cache_dir)),  # NEW
            auto_reload=False,  # Disable auto-reload in production
        )
        return env
```

**Testing:**
```bash
# Run benchmarks before/after
python tests/performance/benchmark_full_build.py

# Expected improvement:
# 100 pages: 1.66s → 1.45s (12% faster)
```

**Config option:**
```toml
# bengal.toml
[build]
cache_templates = true  # Default: true
```

---

### ✅ Task 2: CLI Profiling Mode
**ROI:** 💰 MEDIUM (enables data-driven optimization)  
**Effort:** 3 days  
**Risk:** LOW

**Implementation:**
```python
# File: bengal/cli.py

@click.option('--profile', is_flag=True, help='Enable profiling mode')
def build(config_file, parallel, incremental, profile):
    """Build the site."""
    
    if profile:
        import cProfile
        import pstats
        from io import StringIO
        
        pr = cProfile.Profile()
        pr.enable()
        
    # Run build
    stats = site.build(parallel=parallel, incremental=incremental)
    
    if profile:
        pr.disable()
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        # Save profile data
        profile_path = site.output_dir / ".bengal-cache" / "profile.txt"
        profile_path.write_text(s.getvalue())
        
        click.echo(f"\n📊 Profile saved to {profile_path}")
        click.echo("\nTop time consumers:")
        click.echo(s.getvalue()[:1000])  # Show first 1000 chars
```

**Usage:**
```bash
bengal build --profile

# Output:
# 📊 Profile saved to public/.bengal-cache/profile.txt
# 
# Top time consumers:
#   27.3%  jinja2.Template.render
#   21.1%  mistune.create_markdown
#   8.2%   bs4.BeautifulSoup
#   ...
```

---

## Phase 2: Medium-Term Optimizations (Month 1-2)

### 🔥 Task 3: Parsed Content Caching
**ROI:** 🔥 VERY HIGH (20-30% incremental speedup)  
**Effort:** 2 weeks  
**Risk:** MEDIUM (cache invalidation)

**Problem:**
Incremental builds re-parse unchanged markdown files.

**Solution:**
Cache parsed HTML and TOC in build cache.

**Implementation:**
```python
# File: bengal/cache/build_cache.py

@dataclass
class BuildCache:
    # Add new field
    parsed_content: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get_parsed_content(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get cached parsed content if unchanged."""
        key = str(file_path)
        if key not in self.parsed_content:
            return None
        
        # Verify file hasn't changed
        if self.is_changed(file_path):
            return None
        
        return self.parsed_content[key]
    
    def store_parsed_content(self, file_path: Path, html: str, toc: str, metadata: dict):
        """Store parsed content in cache."""
        self.parsed_content[str(file_path)] = {
            'html': html,
            'toc': toc,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }
```

```python
# File: bengal/rendering/pipeline.py

def process_page(self, page: Page):
    # Try cache first
    if self.cache and not page.metadata.get('_generated'):
        cached = self.cache.get_parsed_content(page.source_path)
        if cached:
            page.parsed_ast = cached['html']
            page.toc = cached['toc']
            # Skip parsing! Jump to template rendering
            page.rendered_html = self.renderer.render_page(page, cached['html'])
            self._write_output(page)
            return
    
    # Cache miss - parse as usual
    parsed_content, toc = self.parser.parse_with_toc_and_context(...)
    
    # Store in cache for next build
    if self.cache:
        self.cache.store_parsed_content(page.source_path, parsed_content, toc, page.metadata)
    
    # Continue with template rendering...
```

**Testing:**
```bash
# Create site with 100 pages
# Full build
time bengal build  # 1.66s

# Change one page
echo "Updated" >> content/posts/post-1.md

# Incremental with parsed content cache
time bengal build --incremental  # Currently: 0.047s, Target: 0.035s (25% faster)
```

**Risks:**
1. Cache invalidation on template changes (already tracked ✓)
2. Cache size growth (implement LRU eviction)
3. Metadata changes not detected (hash metadata too)

---

### 💰 Task 4: Optimize Hot Paths (Based on Profiling)
**ROI:** 💰 MEDIUM (10-20% targeted improvements)  
**Effort:** 2 weeks  
**Risk:** LOW

**Approach:**
1. Run profiling on realistic sites (100-500 pages)
2. Identify functions using >5% of total time
3. Optimize top 3-5 functions
4. Re-benchmark to validate

**Example Hot Path (hypothetical):**
```python
# If profiling shows BeautifulSoup parsing is slow:

# Current: Parse HTML for link extraction
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
links = [a.get('href') for a in soup.find_all('a')]

# Optimized: Use regex for simple link extraction
import re
LINK_PATTERN = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>')
links = LINK_PATTERN.findall(html)  # 5-10x faster
```

**Note:** This is an example. Actual optimizations depend on profiling results.

---

## Phase 3: Long-Term Architecture (Month 3-6)

### 📋 Task 5: Plugin System (Already Planned v0.4.0)
**ROI:** 📋 MEDIUM-LONG TERM  
**Effort:** 1 month  
**Priority:** ARCHITECTURAL

**Goal:**
Allow users to add custom optimization strategies.

**Design:**
```python
# User code: my_site_plugin.py
from bengal.plugins import BuildHook

@BuildHook.register('pre_render')
def custom_cache(page, context):
    """User-defined caching strategy."""
    if page.metadata.get('heavy_processing'):
        # Use external cache (Redis, memcached, etc.)
        cached = redis_client.get(f"page:{page.slug}")
        if cached:
            return cached
    return None

@BuildHook.register('post_render')  
def custom_minify(html, page):
    """Custom HTML optimization."""
    # User can experiment with aggressive minification
    return minify_html(html, aggressive=True)
```

**Config:**
```toml
[plugins]
enabled = ["my_site_plugin"]
```

**Benefit:**
- Users can experiment without forking
- Collect real-world data on what optimizations matter
- Gradual incorporation into core

---

## Anti-Pattern: What NOT to Do

### ❌ Do NOT Implement from RFC:

1. **Rope Data Structures** - No benefit, high complexity
2. **Interval Trees** - Would make parsing slower
3. **Suffix Arrays** - No use case exists
4. **ProcessPoolExecutor** - ThreadPool is correct for I/O workload

### ⚠️ Defer Until Proven Need:

1. **Template DAG System** - Jinja2 caching is good enough for now
2. **mmap/Streaming Large Files** - No evidence of >10MB markdown files
3. **Compressed File Support** - Not a requested feature

---

## Success Metrics

### Phase 1 (Immediate)
- ✅ Jinja2 caching: 10-15% faster builds
- ✅ Profiling: Identify top 5 bottlenecks

### Phase 2 (Month 1-2)
- ✅ Parsed content caching: 20-30% faster incremental builds
- ✅ Hot path optimization: 10-20% targeted improvements
- **Target:** 100 pages in <1.2s (from 1.66s), incremental <0.03s (from 0.047s)

### Phase 3 (Month 3-6)
- ✅ Plugin system: 5+ community plugins
- ✅ User-reported optimizations incorporated

---

## Timeline

```
Week 1-2:   Phase 1 (Quick Wins)
Week 3-6:   Phase 2 Part 1 (Parsed Content Caching)
Week 7-10:  Phase 2 Part 2 (Hot Path Optimization)
Month 3-6:  Phase 3 (Plugin System - already planned)
```

---

## Next Steps

1. **Immediate:** Implement Jinja2 bytecode caching (2 days)
2. **This week:** Add CLI profiling mode (3 days)
3. **Next sprint:** Design parsed content caching (2 weeks)
4. **Ongoing:** Run profiling on diverse sites to identify actual bottlenecks

---

## Conclusion

**The RFC's algorithmic optimizations are not the right fit for Bengal.**

Instead, focus on:
1. ✅ Better caching (templates, parsed content)
2. ✅ Data-driven optimization (profiling)
3. ✅ Extensibility (plugins for user experiments)

**Bengal is already fast (1.66s for 100 pages, 18-42x incremental speedup).** These improvements will make it even faster with low risk and clear benefits.


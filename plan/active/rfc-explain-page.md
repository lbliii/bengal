# RFC: "Explain This Page" Mode

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 90% 🟢

---

## Executive Summary

Add a `bengal explain` command that shows complete traceability for how any page gets built: its source file, template chain, dependencies, shortcodes used, cache status, output location, and why it might be slow or broken.

---

## Problem Statement

### Current State

When debugging build issues, users must piece together information from:
- File system exploration
- Config file inspection
- Template source reading
- Mental model of Bengal's rendering pipeline

**Evidence**:
- No introspection/debug commands in CLI
- Build errors point to symptoms, not root causes

### Pain Points

1. **Black box rendering**: "Why does this page look wrong?"
2. **Template confusion**: "Which template is actually being used?"
3. **Dependency mystery**: "What does this page depend on?"
4. **Cache confusion**: "Is this page cached? Why is it stale?"
5. **Slow page diagnosis**: "Why does this page take so long?"

### User Impact

Debugging requires deep Bengal knowledge. New users get stuck. Even experts waste time on mundane tracing.

---

## Goals & Non-Goals

**Goals**:
- Full traceability for any page
- Show template resolution chain
- List all dependencies (content, templates, data)
- Display cache status and invalidation reasons
- Identify shortcodes and their impact
- Explain rendering pipeline stages

**Non-Goals**:
- Auto-fix issues (diagnosis only)
- Performance optimization (separate profiler RFC)
- Real-time monitoring (batch analysis)

---

## Architecture Impact

**Affected Subsystems**:
- **CLI** (`bengal/cli/`): New explain command
- **Core** (`bengal/core/`): Page metadata exposure
- **Rendering** (`bengal/rendering/`): Template chain tracking
- **Cache** (`bengal/cache/`): Status introspection

**New Components**:
- `bengal/debug/` - Debug and introspection utilities
- `bengal/debug/explainer.py` - Page explanation logic
- `bengal/debug/tracer.py` - Dependency tracing

---

## Proposed CLI Interface

### Basic Explain

```bash
bengal explain docs/guide.md

# Output:
# 
# 📄 Page Explanation: docs/guide.md
# 
# ┌─ Source ────────────────────────────────────────────────┐
# │ Path:     content/docs/guide.md                         │
# │ Size:     4.2 KB (156 lines)                           │
# │ Modified: 2024-12-08 14:30:22                          │
# │ Encoding: UTF-8                                         │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Frontmatter ───────────────────────────────────────────┐
# │ title: "Getting Started Guide"                         │
# │ template: doc                                          │
# │ weight: 10                                             │
# │ tags: [tutorial, beginner]                             │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Template Chain ────────────────────────────────────────┐
# │ 1. doc.html (theme: default)                           │
# │    └─ extends: base.html                               │
# │       └─ includes: partials/nav.html                   │
# │       └─ includes: partials/sidebar.html               │
# │       └─ includes: partials/footer.html                │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Dependencies ──────────────────────────────────────────┐
# │ Content:                                               │
# │   • docs/_index.md (section)                           │
# │   • _data/navigation.yaml                              │
# │ Templates:                                             │
# │   • templates/doc.html                                 │
# │   • templates/base.html                                │
# │   • templates/partials/nav.html (3 more...)            │
# │ Assets:                                                │
# │   • assets/images/diagram.png                          │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Shortcodes Used ───────────────────────────────────────┐
# │ • code-tabs (3 uses)                                   │
# │ • admonition (5 uses)                                  │
# │ • include (1 use) → snippets/example.md                │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Cache Status ──────────────────────────────────────────┐
# │ Status:    STALE                                       │
# │ Reason:    Source file modified                        │
# │ Last hit:  2024-12-08 14:25:00                         │
# │ Cache key: abc123...                                   │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Output ────────────────────────────────────────────────┐
# │ Path: public/docs/guide/index.html                     │
# │ URL:  /docs/guide/                                     │
# │ Size: 12.4 KB                                          │
# └─────────────────────────────────────────────────────────┘
```

### Verbose Mode

```bash
bengal explain docs/guide.md --verbose

# Additional output:
# 
# ┌─ Render Pipeline ───────────────────────────────────────┐
# │ 1. Parse frontmatter         0.2ms                     │
# │ 2. Parse markdown            1.8ms                     │
# │ 3. Process shortcodes        4.5ms                     │
# │    └─ code-tabs (3×)         2.1ms                     │
# │    └─ admonition (5×)        0.8ms                     │
# │    └─ include (1×)           1.6ms                     │
# │ 4. Build context             0.3ms                     │
# │ 5. Render template           3.2ms                     │
# │ 6. Post-process              0.5ms                     │
# │ ────────────────────────────────────                   │
# │ Total:                      10.5ms                     │
# └─────────────────────────────────────────────────────────┘
# 
# ┌─ Template Variables ────────────────────────────────────┐
# │ page.title       = "Getting Started Guide"             │
# │ page.url         = "/docs/guide/"                      │
# │ page.section     = Section(docs)                       │
# │ page.toc         = [TOCEntry×5]                        │
# │ site.pages       = [Page×156]                          │
# │ site.taxonomies  = {tags: [...], categories: [...]}    │
# └─────────────────────────────────────────────────────────┘
```

### Why Is It Broken?

```bash
bengal explain docs/broken.md --diagnose

# Output:
# 
# 📄 Page Diagnosis: docs/broken.md
# 
# ⚠️ Issues Found:
# 
# 1. ❌ Template Error
#    Template 'custom-doc.html' not found
#    ├─ Specified in: frontmatter (template: custom-doc)
#    ├─ Searched in:
#    │   • templates/custom-doc.html (not found)
#    │   • themes/default/templates/custom-doc.html (not found)
#    └─ Suggestion: Use 'doc' or create custom-doc.html
# 
# 2. ⚠️ Broken Internal Link
#    Link to '/docs/missing/' not found
#    ├─ Line 45: [See missing guide](/docs/missing/)
#    └─ Suggestion: Check if page exists or update link
# 
# 3. ⚠️ Missing Image
#    Image 'diagram.png' not found
#    ├─ Line 67: ![Diagram](diagram.png)
#    ├─ Searched in: content/docs/, assets/images/
#    └─ Suggestion: Add image or fix path
```

### Why Is It Slow?

```bash
bengal explain docs/api-reference.md --performance

# Output:
# 
# 📄 Performance Analysis: docs/api-reference.md
# 
# ⏱️ Total Render Time: 450ms (SLOW - avg is 15ms)
# 
# 🐢 Bottlenecks:
# 
# 1. Large Content (45% of time)
#    • 4,521 lines of markdown
#    • Suggestion: Split into multiple pages
# 
# 2. Shortcode: diagram (35% of time)
#    • 12 uses, 150ms total
#    • Each diagram renders SVG dynamically
#    • Suggestion: Pre-render diagrams or use images
# 
# 3. Include: full-api-schema.md (15% of time)
#    • Included file is 2,100 lines
#    • Suggestion: Use excerpt or link instead
# 
# 📊 Comparison:
#    This page: 450ms
#    Site average: 15ms
#    Ratio: 30x slower than average
```

---

## Detailed Design

### Page Explainer

```python
# bengal/debug/explainer.py
from dataclasses import dataclass

@dataclass
class PageExplanation:
    """Complete explanation of how a page is built."""
    
    # Source information
    source: SourceInfo
    
    # Parsed frontmatter
    frontmatter: dict
    
    # Template resolution
    template_chain: list[TemplateInfo]
    
    # Dependencies
    dependencies: DependencyInfo
    
    # Shortcodes
    shortcodes: list[ShortcodeUsage]
    
    # Cache status
    cache: CacheInfo
    
    # Output
    output: OutputInfo
    
    # Performance (if measured)
    performance: PerformanceInfo | None = None
    
    # Issues (if diagnosed)
    issues: list[Issue] | None = None


class PageExplainer:
    """Generate explanations for pages."""
    
    def __init__(self, site: Site):
        self.site = site
    
    def explain(
        self, 
        page_path: str,
        verbose: bool = False,
        diagnose: bool = False,
        performance: bool = False,
    ) -> PageExplanation:
        """Generate complete explanation for a page."""
        
        page = self.site.get_page(page_path)
        
        explanation = PageExplanation(
            source=self._get_source_info(page),
            frontmatter=page.frontmatter,
            template_chain=self._resolve_template_chain(page),
            dependencies=self._get_dependencies(page),
            shortcodes=self._get_shortcode_usage(page),
            cache=self._get_cache_status(page),
            output=self._get_output_info(page),
        )
        
        if verbose:
            explanation.performance = self._measure_performance(page)
        
        if diagnose:
            explanation.issues = self._diagnose_issues(page)
        
        if performance:
            explanation.performance = self._analyze_performance(page)
        
        return explanation
    
    def _resolve_template_chain(self, page: Page) -> list[TemplateInfo]:
        """Resolve the complete template inheritance chain."""
        chain = []
        
        # Start with page's template
        template_name = page.template or self._get_default_template(page)
        template = self.site.template_engine.get_template(template_name)
        
        visited = set()
        while template and template.name not in visited:
            visited.add(template.name)
            
            info = TemplateInfo(
                name=template.name,
                source=self._find_template_source(template.name),
                includes=self._get_template_includes(template),
            )
            chain.append(info)
            
            # Check for extends
            parent_name = self._get_parent_template(template)
            if parent_name:
                template = self.site.template_engine.get_template(parent_name)
            else:
                break
        
        return chain
    
    def _get_dependencies(self, page: Page) -> DependencyInfo:
        """Get all dependencies for a page."""
        deps = DependencyInfo()
        
        # Content dependencies
        deps.content.append(page.section.index_page)  # Section index
        
        # Data files
        if page.uses_data:
            for data_ref in page.data_references:
                deps.data.append(data_ref)
        
        # Templates
        for tpl in self._resolve_template_chain(page):
            deps.templates.append(tpl.source)
        
        # Assets referenced in content
        for asset_ref in self._extract_asset_refs(page):
            deps.assets.append(asset_ref)
        
        # Includes from shortcodes
        for shortcode in self._get_shortcode_usage(page):
            if shortcode.name == "include":
                deps.includes.append(shortcode.args.get("file"))
        
        return deps
    
    def _get_shortcode_usage(self, page: Page) -> list[ShortcodeUsage]:
        """Extract shortcode usage from page content."""
        usages = []
        
        # Parse content for shortcode patterns
        for match in SHORTCODE_PATTERN.finditer(page.raw_content):
            name = match.group("name")
            usages.append(ShortcodeUsage(
                name=name,
                line=page.raw_content[:match.start()].count("\n") + 1,
                args=self._parse_shortcode_args(match),
            ))
        
        # Group by name and count
        grouped = {}
        for usage in usages:
            if usage.name not in grouped:
                grouped[usage.name] = []
            grouped[usage.name].append(usage)
        
        return [
            ShortcodeUsage(
                name=name,
                count=len(instances),
                lines=[i.line for i in instances],
                args=instances[0].args if instances else {},
            )
            for name, instances in grouped.items()
        ]
    
    def _get_cache_status(self, page: Page) -> CacheInfo:
        """Get cache status for a page."""
        cache = self.site.cache
        
        cache_key = cache.get_key(page)
        is_cached = cache.has(cache_key)
        
        if is_cached:
            entry = cache.get_entry(cache_key)
            status = "HIT"
            
            # Check if stale
            if page.source_path.stat().st_mtime > entry.created_at:
                status = "STALE"
                reason = "Source file modified"
            elif self._any_dependency_changed(page, entry):
                status = "STALE"
                reason = "Dependency changed"
            else:
                reason = None
        else:
            status = "MISS"
            reason = "Not in cache"
        
        return CacheInfo(
            status=status,
            reason=reason,
            cache_key=cache_key,
            last_hit=entry.last_hit if is_cached else None,
        )
    
    def _diagnose_issues(self, page: Page) -> list[Issue]:
        """Diagnose potential issues with a page."""
        issues = []
        
        # Check template exists
        template_name = page.template or self._get_default_template(page)
        if not self._template_exists(template_name):
            issues.append(Issue(
                severity="error",
                type="template_not_found",
                message=f"Template '{template_name}' not found",
                details={
                    "specified_in": "frontmatter" if page.template else "default",
                    "searched_paths": self._get_template_search_paths(template_name),
                },
                suggestion=f"Use 'doc' or create {template_name}.html",
            ))
        
        # Check internal links
        for link in page.internal_links:
            if not self._link_target_exists(link):
                issues.append(Issue(
                    severity="warning",
                    type="broken_link",
                    message=f"Link to '{link.target}' not found",
                    details={"line": link.line, "raw": link.raw},
                    suggestion="Check if page exists or update link",
                ))
        
        # Check images
        for img in self._extract_images(page):
            if not self._image_exists(img, page):
                issues.append(Issue(
                    severity="warning",
                    type="missing_image",
                    message=f"Image '{img.src}' not found",
                    details={
                        "line": img.line,
                        "searched_paths": self._get_image_search_paths(img, page),
                    },
                    suggestion="Add image or fix path",
                ))
        
        return issues
```

### Reporter

```python
# bengal/debug/reporter.py
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

class ExplanationReporter:
    """Format and display page explanations."""
    
    def __init__(self):
        self.console = Console()
    
    def print(self, explanation: PageExplanation):
        """Print formatted explanation."""
        
        self.console.print(f"\n📄 [bold]Page Explanation: {explanation.source.path}[/bold]\n")
        
        # Source panel
        self._print_panel("Source", [
            f"Path:     {explanation.source.path}",
            f"Size:     {explanation.source.size_human} ({explanation.source.lines} lines)",
            f"Modified: {explanation.source.modified}",
        ])
        
        # Frontmatter panel
        if explanation.frontmatter:
            self._print_panel("Frontmatter", [
                f"{k}: {self._format_value(v)}"
                for k, v in explanation.frontmatter.items()
            ])
        
        # Template chain
        self._print_template_chain(explanation.template_chain)
        
        # Dependencies
        self._print_dependencies(explanation.dependencies)
        
        # Shortcodes
        if explanation.shortcodes:
            self._print_shortcodes(explanation.shortcodes)
        
        # Cache status
        self._print_cache(explanation.cache)
        
        # Output
        self._print_panel("Output", [
            f"Path: {explanation.output.path}",
            f"URL:  {explanation.output.url}",
            f"Size: {explanation.output.size_human}",
        ])
        
        # Issues (if any)
        if explanation.issues:
            self._print_issues(explanation.issues)
        
        # Performance (if measured)
        if explanation.performance:
            self._print_performance(explanation.performance)
    
    def _print_template_chain(self, chain: list[TemplateInfo]):
        """Print template inheritance as tree."""
        tree = Tree("📁 Template Chain")
        
        current = tree
        for i, tpl in enumerate(chain):
            prefix = "└─ " if i == len(chain) - 1 else "├─ "
            node = current.add(f"{tpl.name} ({tpl.source})")
            
            for include in tpl.includes:
                node.add(f"includes: {include}")
            
            current = node
        
        self.console.print(Panel(tree, title="Template Chain"))
    
    def _print_issues(self, issues: list[Issue]):
        """Print diagnosed issues."""
        self.console.print("\n⚠️ [bold]Issues Found:[/bold]\n")
        
        for i, issue in enumerate(issues, 1):
            icon = "❌" if issue.severity == "error" else "⚠️"
            self.console.print(f"{i}. {icon} [bold]{issue.type.replace('_', ' ').title()}[/bold]")
            self.console.print(f"   {issue.message}")
            
            if issue.details:
                for k, v in issue.details.items():
                    self.console.print(f"   ├─ {k}: {v}")
            
            self.console.print(f"   └─ [green]Suggestion: {issue.suggestion}[/green]")
            self.console.print()
```

---

## Configuration

```toml
# bengal.toml
[debug]
# Enable verbose explain by default
verbose_explain = false

# Show timing information
show_timing = true

# Cache status display
show_cache_details = true
```

---

## Implementation Plan

### Phase 1: Core Explain (1 week)
- [ ] Source and frontmatter display
- [ ] Template chain resolution
- [ ] Basic CLI command

### Phase 2: Dependencies & Shortcodes (1 week)
- [ ] Dependency tracking
- [ ] Shortcode extraction
- [ ] Cache status

### Phase 3: Diagnosis Mode (1 week)
- [ ] Issue detection
- [ ] Broken link checking
- [ ] Missing asset detection

### Phase 4: Performance Mode (1 week)
- [ ] Timing breakdown
- [ ] Bottleneck identification
- [ ] Comparison with averages

---

## Success Criteria

- [ ] `bengal explain` shows complete page info
- [ ] Template chain is accurate
- [ ] Dependencies are tracked correctly
- [ ] Cache status reflects reality
- [ ] Issues are diagnosed accurately
- [ ] <1s to generate explanation

---

## References

- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [Rails Console](https://guides.rubyonrails.org/command_line.html#rails-console)
- [Webpack Stats](https://webpack.js.org/api/stats/)




# Documentation Site Parser Strategy

**Date:** October 3, 2025  
**Context:** Choosing between Mistune (fast) and python-markdown (full features)  
**Use Case:** Software documentation sites

---

## The Challenge

**Documentation sites need:**
- ✅ Admonitions (`!!! note`, `!!! warning`, `!!! danger`) - **Critical!**
- ✅ Footnotes for citations and references
- ✅ Definition lists for glossaries and API docs
- ✅ Tables (both have this)
- ✅ Code blocks with syntax highlighting (both have this)
- ✅ TOC generation (both have this)

**Mistune currently has:**
- ✅ Tables
- ✅ Code blocks
- ✅ Task lists
- ✅ TOC (custom implementation)
- ❌ Admonitions (would need custom plugin)
- ❌ Footnotes (would need custom plugin)
- ❌ Definition lists (would need custom plugin)

---

## Recommended Strategy

### Option 1: Use python-markdown (Simple, Works Now)

**For documentation sites, stick with python-markdown:**

```toml
[build]
markdown_engine = "python-markdown"  # Full features for docs
```

**Why:**
- ✅ All features work out of the box
- ✅ No custom plugin development needed
- ✅ Mature, well-tested
- ⚠️ Slightly slower (3.78s vs 2.59s for 78 pages)

**Verdict:** This is the pragmatic choice for docs sites right now.

---

### Option 2: Hybrid Approach (Best of Both Worlds)

Use Mistune for simple pages, python-markdown for complex ones:

```toml
[build]
markdown_engine = "python-markdown"  # Default for docs

[markdown]
# Pages matching these patterns use python-markdown (full features)
complex_patterns = ["**/docs/**", "**/guides/**", "**/tutorials/**"]
# Everything else can use mistune (fast)
simple_patterns = ["**/blog/**", "**/posts/**"]
```

**Benefits:**
- Blog posts get fast builds (Mistune)
- Documentation gets full features (python-markdown)
- Automatic per-page selection

**Implementation:** ~2 hours to add pattern matching

---

### Option 3: Add Admonitions Plugin to Mistune (Most Work)

Build custom Mistune plugins for docs features.

**Effort:**
- Admonitions plugin: 4-6 hours
- Footnotes plugin: 3-4 hours
- Definition lists plugin: 2-3 hours
- Testing: 2-3 hours
- **Total: 11-16 hours**

**Benefits:**
- Fast builds with all features
- Full control over rendering
- Educational

**Downsides:**
- Significant development time
- Maintenance burden
- May have edge cases vs python-markdown

---

## Performance Comparison

| Scenario | Engine | Time (78 pages) | Features |
|----------|--------|----------------|----------|
| **Docs site (current)** | python-markdown | 3.78s | ✅ All |
| Blog site | Mistune | 2.59s | ⚠️ Most |
| **Hybrid** | Mixed | ~3.2s | ✅ All |

**Key insight:** 1 second difference isn't worth losing critical features.

---

## Recommendation for Documentation Sites

### Use python-markdown (for now)

**Reasoning:**
1. **You need admonitions** - Critical for:
   - Notes, warnings, tips
   - API deprecation notices
   - Breaking changes
   - Installation instructions

2. **You need footnotes** - For:
   - Academic citations
   - API references
   - External links
   - Version notes

3. **You need definition lists** - For:
   - Glossaries
   - API parameter tables
   - Configuration options
   - Command reference

4. **3.78s is still fast** - Compared to:
   - MkDocs: 5-8s
   - Sphinx: 10-15s
   - Jekyll: 10-15s

**You're already 2x faster than MkDocs!**

---

## When to Consider Mistune Plugins

**Build custom plugins if:**
- ✅ You have 10-15 hours to invest
- ✅ You need <2s builds (500+ pages)
- ✅ You want to learn Mistune internals
- ✅ You're okay with maintenance burden

**Don't build plugins if:**
- ❌ Current speed is acceptable
- ❌ Limited development time
- ❌ Need rock-solid features
- ❌ Small team / side project

---

## Example: Admonitions Plugin for Mistune

If you DO want to build it, here's the pattern:

```python
import re
from mistune import BlockParser

class AdmonitionPlugin:
    """
    Parse admonitions:
    !!! note "Title"
        Content here
        More content
    """
    
    PATTERN = re.compile(
        r'^!!! (\w+)(?: "([^"]+)")?\n'
        r'((?:    .+\n?)*)',
        re.MULTILINE
    )
    
    def parse_admonition(self, m, state):
        admon_type = m.group(1)  # note, warning, danger, etc.
        title = m.group(2) or admon_type.title()
        content = m.group(3)
        
        # Dedent content (remove 4 spaces)
        content = '\n'.join(line[4:] for line in content.split('\n'))
        
        state.append_token({
            'type': 'admonition',
            'attrs': {
                'type': admon_type,
                'title': title,
            },
            'raw': content
        })
        return m.end()
    
    def render_admonition(self, token):
        admon_type = token['attrs']['type']
        title = token['attrs']['title']
        content = self.render_children(token)
        
        return (
            f'<div class="admonition {admon_type}">\n'
            f'  <p class="admonition-title">{title}</p>\n'
            f'  {content}\n'
            f'</div>\n'
        )

# Register with Mistune
def plugin(md):
    md.block.register('admonition', PATTERN, parse_admonition)
    md.renderer.register('admonition', render_admonition)
    return md

# Usage
md = mistune.create_markdown(plugins=[plugin])
```

**Effort:** 4-6 hours to get this production-ready with tests.

---

## Hybrid Implementation (If You Want It)

Here's how to add per-directory engine selection:

```python
# bengal/rendering/parser.py - Add to create_markdown_parser()

def create_markdown_parser(
    engine: Optional[str] = None,
    page_path: Optional[Path] = None,
    config: Optional[dict] = None
) -> BaseMarkdownParser:
    """
    Factory function with smart engine selection.
    
    Args:
        engine: Explicit engine choice
        page_path: Path to the page being parsed
        config: Site config with pattern matching rules
    """
    # Explicit engine wins
    if engine:
        return _create_engine(engine)
    
    # Check if we should use pattern matching
    if page_path and config and config.get('markdown', {}).get('auto_select'):
        patterns = config['markdown']
        
        # Check complex patterns (need full features)
        complex = patterns.get('complex_patterns', [])
        for pattern in complex:
            if page_path.match(pattern):
                return _create_engine('python-markdown')
        
        # Check simple patterns (can use fast engine)
        simple = patterns.get('simple_patterns', [])
        for pattern in simple:
            if page_path.match(pattern):
                return _create_engine('mistune')
    
    # Default
    return _create_engine(config.get('markdown_engine', 'python-markdown'))
```

**Config:**
```toml
[markdown]
auto_select = true

# Full features for these paths
complex_patterns = [
    "**/docs/**",
    "**/guides/**", 
    "**/tutorials/**"
]

# Fast builds for these paths
simple_patterns = [
    "**/blog/**",
    "**/posts/**"
]
```

**Effort:** 2-3 hours to implement and test.

---

## Decision Matrix

| Approach | Time | Speed | Features | Maintenance |
|----------|------|-------|----------|-------------|
| **python-markdown** | 0 hrs | 3.78s | ✅ All | Low |
| **Hybrid** | 2-3 hrs | 3.2s | ✅ All | Medium |
| **Mistune + plugins** | 15+ hrs | 2.59s | ✅ All* | High |

*After building plugins

---

## Final Recommendation

**For documentation sites: Use python-markdown.**

**Why:**
1. You need admonitions (critical!)
2. 3.78s is already fast (2x faster than MkDocs)
3. Zero development time
4. Battle-tested for docs
5. Keep Mistune as an option for blogs later

**You can always add plugins later if:**
- You grow to 500+ pages and need <2s builds
- You have the development time
- You've validated it's actually a bottleneck

**Right now:** Ship your docs site with python-markdown. You're already winning on speed vs alternatives!

---

## Summary

**Documentation sites → python-markdown**  
**Blog sites → Mistune**  
**Mixed sites → Hybrid (implement pattern matching)**

Your current setup with python-markdown is the right choice for docs!


# RFC: Bengal Native Markdown Parser

**Status**: Draft (Exploratory)  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P3 (Low - Research)  
**Related**: `bengal/rendering/parsers/`, `bengal/directives/`  
**Confidence**: 65% 🟡 (Exploratory - needs benchmarking)

---

## Executive Summary

Mistune is ~2,200 lines of pure Python and serves Bengal well. However, Bengal's documentation-centric use case has specific patterns that a purpose-built parser could exploit for significant speedups:

- **Directives are first-class** — Bengal's content uses 2,900+ directive markers
- **TOC extraction is always needed** — Currently a post-processing step
- **Code blocks dominate** — Documentation sites are code-heavy
- **CommonMark compliance is secondary** — Users write for Bengal, not GitHub

This RFC explores three paths:

| Option | Approach | Speedup | Effort | Risk |
|--------|----------|---------|--------|------|
| **A** | Rust wrapper (pyromark) | 5-10x | 2 weeks | Low |
| **B** | Two-pass hybrid | 2-3x | 3 weeks | Medium |
| **C** | Full native parser | 10-20x | 2-3 months | High |

**Recommendation**: Start with **Option A** (pyromark integration) for immediate gains, then evaluate **Option B** if directive handling remains a bottleneck.

---

## Problem Statement

### Current Architecture

```
                    ┌─────────────────┐
                    │  Raw Markdown   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Variable Subst  │  Pre-processing
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Mistune      │  Block + Inline parsing
                    │  Block Parser   │  (~500 lines)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Mistune      │
                    │  Inline Parser  │  (~400 lines)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Directive      │  Fenced directive plugin
                    │  Processing     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  HTMLRenderer   │  Token → HTML
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  TOC Extraction │  Post-processing (regex)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Link Transform │  Post-processing
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Final HTML    │
                    └─────────────────┘
```

### Profiling Data (Estimated)

| Phase | Time (per page) | % of Total |
|-------|-----------------|------------|
| Mistune block parsing | 1.5ms | 30% |
| Mistune inline parsing | 1.0ms | 20% |
| Directive processing | 1.5ms | 30% |
| Post-processing (TOC, links) | 0.5ms | 10% |
| HTML generation | 0.5ms | 10% |
| **Total** | **5.0ms** | 100% |

### Key Observations

1. **Directive-heavy content** — Bengal docs average 19 directives per page
2. **Regex overhead** — Mistune compiles regex patterns per-parse
3. **Double parsing** — TOC extraction re-parses HTML output
4. **Generic patterns** — Mistune handles CommonMark edge cases Bengal doesn't need

---

## Option A: Rust Wrapper (pyromark)

### Approach

Use **pyromark** (Python bindings for Rust's `pulldown-cmark`) for core markdown parsing, with Bengal handling directives as a post-processing layer.

```
                    ┌─────────────────┐
                    │  Raw Markdown   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Pre-scan for   │  Extract directive blocks
                    │  Directives     │  (fast regex)
                    └────────┬────────┘
                             │
               ┌─────────────┴─────────────┐
               │                           │
      ┌────────▼────────┐         ┌────────▼────────┐
      │   pyromark      │         │  Directive      │
      │ (Rust/pulldown) │         │  Parser         │
      │    ~0.2ms       │         │  (recursive)    │
      └────────┬────────┘         └────────┬────────┘
               │                           │
               └─────────────┬─────────────┘
                             │
                    ┌────────▼────────┐
                    │  Merge & Render │
                    └─────────────────┘
```

### Implementation

```python
# bengal/rendering/parsers/pyromark/__init__.py

"""
Pyromark-based parser using Rust's pulldown-cmark for core parsing.

Dependencies:
    pip install pyromark

Performance:
    5-10x faster than pure Python mistune for core parsing.
    Directive handling remains in Python.
"""

from __future__ import annotations

import re
from typing import Any

import pyromark

from bengal.rendering.parsers.base import BaseMarkdownParser

# Fast regex for directive block extraction
DIRECTIVE_BLOCK = re.compile(
    r'^(:{3,})\{([a-z_-]+)\}(.*?)$'  # Opening: :::{name}
    r'([\s\S]*?)'                     # Content
    r'^\1$',                          # Closing: :::
    re.MULTILINE
)

class PyromarkParser(BaseMarkdownParser):
    """
    Hybrid parser: Rust for markdown, Python for directives.

    Performance Profile:
        - Core markdown: 0.2-0.5ms (Rust)
        - Directive handling: 1.0-2.0ms (Python)
        - Total: ~2.5ms (50% faster than pure mistune)
    """

    def __init__(self):
        # Pre-compile directive patterns
        self._directive_pattern = DIRECTIVE_BLOCK

        # Import directive processors
        from bengal.directives.factory import create_directive_processor
        self._directive_processor = create_directive_processor()

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse markdown with hybrid approach."""
        # Phase 1: Extract directive blocks (fast scan)
        directives, plain_content = self._extract_directives(content)

        # Phase 2: Parse plain markdown with Rust
        html = pyromark.html(plain_content)

        # Phase 3: Process directives and merge
        html = self._inject_directives(html, directives)

        return html

    def _extract_directives(self, content: str) -> tuple[list, str]:
        """Extract directive blocks, leave placeholders."""
        directives = []

        def replace_directive(match):
            idx = len(directives)
            directives.append({
                'fence': match.group(1),
                'name': match.group(2),
                'title': match.group(3),
                'content': match.group(4),
            })
            return f'<!-- BENGAL_DIRECTIVE_{idx} -->'

        plain = self._directive_pattern.sub(replace_directive, content)
        return directives, plain

    def _inject_directives(self, html: str, directives: list) -> str:
        """Replace placeholders with rendered directives."""
        for idx, directive in enumerate(directives):
            placeholder = f'<!-- BENGAL_DIRECTIVE_{idx} -->'
            rendered = self._directive_processor.render(directive)
            html = html.replace(placeholder, rendered)
        return html
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ 5-10x faster core parsing | ❌ New dependency (Rust runtime) |
| ✅ Low implementation effort | ❌ Two-pass for directives |
| ✅ Proven, maintained library | ❌ Less control over internals |
| ✅ CommonMark compliant | ❌ May have edge case differences |

### Estimated Effort

- Integration: 1 week
- Testing: 1 week
- **Total: 2 weeks**

---

## Option B: Two-Pass Hybrid Parser

### Approach

Build a Bengal-native parser that uses a fast first pass to identify structure, then selectively applies detailed parsing only where needed.

```
                    ┌─────────────────┐
                    │  Raw Markdown   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  PASS 1: Scan   │  O(n) character scan
                    │  Block Structure│  Identify: headings, code, directives
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Block Router   │  Dispatch by type
                    └────────┬────────┘
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
┌──────▼──────┐       ┌──────▼──────┐       ┌──────▼──────┐
│ Plain Block │       │ Code Block  │       │  Directive  │
│  (fast)     │       │  (verbatim) │       │  (recurse)  │
└──────┬──────┘       └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  PASS 2: Inline │  Only for text blocks
                    │  (lazy/cached)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Emit HTML     │  Direct string building
                    └─────────────────┘
```

### Key Optimizations

#### 1. Single-Character Block Detection

Instead of regex, scan character-by-character:

```python
def scan_block_structure(content: str) -> list[Block]:
    """
    O(n) scan identifying block boundaries.

    Block markers detected:
    - '#' at line start → heading
    - '```' or '~~~' → fenced code
    - ':::' → directive
    - '>' → block quote
    - '-', '*', '1.' → list
    - Blank line → paragraph end
    """
    blocks = []
    i = 0
    line_start = 0

    while i < len(content):
        c = content[i]

        # At line start, check for block markers
        if i == line_start:
            if c == '#':
                blocks.append(scan_heading(content, i))
                i = blocks[-1].end
            elif c == '`' and content[i:i+3] == '```':
                blocks.append(scan_fenced_code(content, i))
                i = blocks[-1].end
            elif c == ':' and content[i:i+3] == ':::':
                blocks.append(scan_directive(content, i))
                i = blocks[-1].end
            # ... other block types

        if c == '\n':
            line_start = i + 1
        i += 1

    return blocks
```

#### 2. Lazy Inline Parsing

Don't parse inline content until accessed:

```python
@dataclass
class ParagraphBlock:
    raw: str
    _parsed: str | None = None

    @property
    def html(self) -> str:
        if self._parsed is None:
            self._parsed = parse_inline(self.raw)
        return self._parsed
```

#### 3. Direct HTML Emission

Skip AST for simple cases:

```python
def emit_heading(level: int, text: str, id: str) -> str:
    """Direct HTML generation, no intermediate tokens."""
    return f'<h{level} id="{id}">{text}</h{level}>\n'

def emit_code_block(code: str, lang: str) -> str:
    """Code blocks need no inline parsing."""
    escaped = html_escape(code)
    return f'<pre><code class="language-{lang}">{escaped}</code></pre>\n'
```

#### 4. Integrated TOC

Build TOC during parsing, not as post-process:

```python
class BengalParser:
    def parse(self, content: str) -> ParseResult:
        self.toc_items = []
        html = self._parse_blocks(content)
        toc = self._render_toc()
        return ParseResult(html=html, toc=toc)

    def _parse_heading(self, block: HeadingBlock) -> str:
        id = slugify(block.text)
        self.toc_items.append((block.level, id, block.text))
        return emit_heading(block.level, block.text, id)
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ Optimized for Bengal's patterns | ❌ More implementation effort |
| ✅ Integrated TOC extraction | ❌ Must handle edge cases |
| ✅ No external dependencies | ❌ Maintenance burden |
| ✅ Full control over behavior | ❌ Risk of spec divergence |

### Estimated Effort

- Block parser: 1 week
- Inline parser: 1 week
- Directive integration: 0.5 weeks
- Testing: 0.5 weeks
- **Total: 3 weeks**

---

## Option C: Full Native Parser (Rust Hotpaths)

### Approach

Build a complete Bengal parser with performance-critical paths in Rust via PyO3.

```
┌────────────────────────────────────────────────────────────────┐
│                        bengal_parser                           │
├─────────────────────────────┬──────────────────────────────────┤
│      Python Layer           │         Rust Layer (PyO3)        │
│                             │                                  │
│  ┌───────────────────────┐  │  ┌────────────────────────────┐  │
│  │  BengalParser class   │  │  │  block_scan() → Vec<Block> │  │
│  │  - Configuration      │◄─┼──│  inline_parse() → Vec<Tok> │  │
│  │  - Directive registry │  │  │  emit_html() → String      │  │
│  │  - Plugin hooks       │  │  │  slugify() → String        │  │
│  └───────────────────────┘  │  └────────────────────────────┘  │
│                             │                                  │
│  ┌───────────────────────┐  │  ┌────────────────────────────┐  │
│  │  Directive Processing │  │  │  SIMD text scanning        │  │
│  │  - Python callbacks   │  │  │  Zero-copy slicing         │  │
│  │  - Template rendering │  │  │  Pre-compiled patterns     │  │
│  └───────────────────────┘  │  └────────────────────────────┘  │
└─────────────────────────────┴──────────────────────────────────┘
```

### Rust Core Implementation

```rust
// bengal_parser_core/src/lib.rs

use pyo3::prelude::*;
use memchr::memmem;

/// Block types recognized by the scanner
#[pyclass]
#[derive(Clone)]
pub enum BlockType {
    Heading { level: u8 },
    Paragraph,
    FencedCode { fence: String, info: String },
    Directive { fence: String, name: String, title: String },
    BlockQuote,
    List { ordered: bool, start: u32 },
    ThematicBreak,
    BlankLine,
}

/// A block with its span in the source
#[pyclass]
pub struct Block {
    #[pyo3(get)]
    pub block_type: BlockType,
    #[pyo3(get)]
    pub start: usize,
    #[pyo3(get)]
    pub end: usize,
    #[pyo3(get)]
    pub content_start: usize,
    #[pyo3(get)]
    pub content_end: usize,
}

/// Fast block structure scanner
#[pyfunction]
pub fn scan_blocks(content: &str) -> Vec<Block> {
    let bytes = content.as_bytes();
    let mut blocks = Vec::with_capacity(content.len() / 50); // Estimate
    let mut pos = 0;

    while pos < bytes.len() {
        let line_start = pos;

        // Skip leading spaces (up to 3 for CommonMark)
        let indent = bytes[pos..].iter().take(3).take_while(|&&b| b == b' ').count();
        pos += indent;

        if pos >= bytes.len() {
            break;
        }

        match bytes[pos] {
            b'#' => {
                if let Some(block) = scan_atx_heading(content, line_start) {
                    pos = block.end;
                    blocks.push(block);
                    continue;
                }
            }
            b'`' | b'~' => {
                if let Some(block) = scan_fenced(content, line_start, bytes[pos]) {
                    pos = block.end;
                    blocks.push(block);
                    continue;
                }
            }
            b':' => {
                if let Some(block) = scan_directive(content, line_start) {
                    pos = block.end;
                    blocks.push(block);
                    continue;
                }
            }
            // ... other block types
            _ => {}
        }

        // Default: scan as paragraph
        pos = scan_to_line_end(bytes, pos);
    }

    blocks
}

/// SIMD-accelerated fence finder
fn find_fence_end(content: &str, fence: &str, start: usize) -> Option<usize> {
    // Use memchr for SIMD-accelerated search
    let searcher = memmem::Finder::new(fence.as_bytes());
    let search_area = &content.as_bytes()[start..];

    for pos in searcher.find_iter(search_area) {
        // Verify it's at line start
        if pos == 0 || search_area[pos - 1] == b'\n' {
            // Verify nothing follows on line except whitespace
            let line_end = memchr::memchr(b'\n', &search_area[pos..])
                .map(|i| pos + i)
                .unwrap_or(search_area.len());
            let after_fence = &search_area[pos + fence.len()..line_end];
            if after_fence.iter().all(|&b| b == b' ' || b == b'\t') {
                return Some(start + line_end);
            }
        }
    }
    None
}

/// Python module
#[pymodule]
fn bengal_parser_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_blocks, m)?)?;
    m.add_class::<Block>()?;
    m.add_class::<BlockType>()?;
    Ok(())
}
```

### Python Integration

```python
# bengal/rendering/parsers/native/__init__.py

"""
Bengal Native Parser with Rust acceleration.

Uses PyO3-based Rust extension for hot paths:
- Block structure scanning (10x faster)
- Inline parsing (5x faster)
- HTML emission (3x faster)

Directives remain in Python for flexibility.
"""

from __future__ import annotations

from typing import Any

from bengal_parser_core import scan_blocks, Block, BlockType
from bengal.rendering.parsers.base import BaseMarkdownParser


class NativeParser(BaseMarkdownParser):
    """
    Bengal's native parser with Rust-accelerated hot paths.

    Performance:
        - Block scanning: 0.05ms (Rust SIMD)
        - Inline parsing: 0.3ms (Rust)
        - Directive processing: 1.0ms (Python)
        - HTML emission: 0.1ms (Rust)
        - Total: ~1.5ms (70% faster than mistune)
    """

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        # Phase 1: Rust block scan
        blocks = scan_blocks(content)

        # Phase 2: Process blocks
        html_parts = []
        toc_items = []

        for block in blocks:
            block_content = content[block.content_start:block.content_end]

            match block.block_type:
                case BlockType.Heading(level=level):
                    html, toc_item = self._render_heading(level, block_content)
                    html_parts.append(html)
                    toc_items.append(toc_item)

                case BlockType.FencedCode(fence=_, info=info):
                    html_parts.append(self._render_code(block_content, info))

                case BlockType.Directive(name=name, title=title):
                    html_parts.append(self._render_directive(name, title, block_content))

                case BlockType.Paragraph():
                    html_parts.append(self._render_paragraph(block_content))

                # ... other block types

        html = ''.join(html_parts)
        self._toc = toc_items
        return html
```

### Build Configuration

```toml
# pyproject.toml additions

[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
features = ["pyo3/extension-module"]
python-source = "bengal"
module-name = "bengal_parser_core"
```

### Pros & Cons

| Pros | Cons |
|------|------|
| ✅ Maximum performance (10-20x) | ❌ Rust expertise required |
| ✅ SIMD text scanning | ❌ Complex build pipeline |
| ✅ Full control over everything | ❌ Platform-specific binaries |
| ✅ Zero-copy parsing possible | ❌ 2-3 month development |

### Estimated Effort

- Rust core: 4-6 weeks
- Python integration: 2 weeks
- Build/CI setup: 1 week
- Testing: 2 weeks
- **Total: 2-3 months**

---

## Performance Comparison (Projected)

| Parser | Per-Page | 1000 Pages | Relative |
|--------|----------|------------|----------|
| Python-Markdown | 12ms | 12s | 0.4x |
| Mistune (current) | 5ms | 5s | 1.0x |
| **Option A: pyromark** | 2.5ms | 2.5s | **2x** |
| **Option B: Hybrid** | 2ms | 2s | **2.5x** |
| **Option C: Native** | 1.5ms | 1.5s | **3.3x** |

*Note: These are projections. Actual benchmarks needed.*

---

## Recommendation

### Short-term (Next 2 weeks)

**Implement Option A (pyromark integration)**

- Lowest risk, fastest to implement
- Immediate 2x speedup for markdown-heavy sites
- Validates the hybrid architecture

### Medium-term (Next 2 months)

**Evaluate Option B (Two-pass hybrid)**

- If directive processing is still the bottleneck after Option A
- Gives more control without Rust complexity
- Can be done incrementally

### Long-term (Future)

**Consider Option C (Native with Rust)**

- Only if Bengal becomes a high-traffic project
- Requires dedicated Rust expertise
- Better to contribute to pyromark than build from scratch

---

## Implementation Plan (Option A)

### Week 1: Integration

- [ ] Add pyromark dependency
- [ ] Create `PyromarkParser` class
- [ ] Implement directive extraction pre-pass
- [ ] Implement directive injection post-pass
- [ ] Benchmark against mistune

### Week 2: Testing & Polish

- [ ] Port test suite to new parser
- [ ] Handle edge cases (nested directives, etc.)
- [ ] Add configuration option (`markdown.parser = "pyromark"`)
- [ ] Update documentation
- [ ] Performance comparison report

---

## Open Questions

1. **pyromark availability** — Is it stable enough for production?
2. **Directive edge cases** — How do we handle directives inside code blocks?
3. **Memory usage** — Does pre-scanning increase memory overhead?
4. **Thread safety** — Is pyromark safe for parallel rendering?

---

## Appendix: Why Not Just Optimize Mistune?

Mistune is already well-optimized for its design goals. The main opportunities are:

1. **Different parsing strategy** — Mistune uses regex scanner; alternatives use char-by-char
2. **Avoid re-parsing** — TOC extraction currently re-parses HTML
3. **Skip unused features** — CommonMark edge cases Bengal doesn't need
4. **Native code** — Rust/C for hot paths

These are architectural changes that would fork mistune significantly, making a new parser cleaner.

---

## References

- **pyromark**: https://pyromark.readthedocs.io/
- **pulldown-cmark** (Rust): https://github.com/raphlinus/pulldown-cmark
- **Ultra Markdown** (C): https://umarkdown.netlify.app/
- **mistune source**: `/Users/llane/Documents/github/python/mistune/src/mistune/`
- **Bengal parser**: `/Users/llane/Documents/github/python/bengal/bengal/rendering/parsers/`

---

## Changelog

- 2025-12-23: Initial exploratory draft
  - Analyzed mistune architecture (~2,200 lines)
  - Identified Bengal-specific optimization opportunities
  - Proposed three implementation options
  - Recommended phased approach starting with pyromark



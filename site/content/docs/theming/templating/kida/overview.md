---
title: Kida Overview
nav_title: Overview
description: Why Kida is a serious, production-ready template engine for modern Python applications
weight: 5
type: doc
draft: false
lang: en
tags:
- explanation
- kida
- architecture
- performance
keywords:
- kida overview
- template engine comparison
- production template engine
- high performance templates
category: explanation
---

# Kida Overview

**Kida** is a next-generation template engine designed from the ground up for **production Python applications**. It's not a toy project or a simple syntax improvement—it's a **serious, high-performance solution** built with modern Python's capabilities in mind.

## Why Kida Exists

Template engines are critical infrastructure. They're used in every request, every page render, every build. Yet most template engines were designed decades ago, before:

- Free-threaded Python (PEP 703)
- Modern AST manipulation capabilities
- Performance-conscious Python development
- Serverless architectures requiring fast cold starts

Kida was built to address these gaps, providing a **production-ready template engine** that leverages modern Python's strengths.

## Production-Ready Features

### Performance First

Kida achieves **5.6x faster rendering than Jinja2** (arithmetic mean) through:

- **AST-to-AST compilation**: Direct Python AST generation eliminates string manipulation overhead
- **StringBuilder pattern**: O(n) output construction vs O(n²) string concatenation
- **Compile-time optimizations**: Constant folding, dead code elimination, filter inlining
- **Automatic block caching**: Site-scoped blocks cached automatically for 10-100x faster builds

**Real-world impact**: A site that takes 60 seconds to build with Jinja2 takes **~11 seconds** with Kida. For large sites (1000+ pages), this can mean the difference between minutes and hours.

### Free-Threading Ready

Kida is designed for **Python 3.14t+ free-threaded builds**:

- Declares GIL independence via PEP 703's `_Py_mod_gil = 0`
- Thread-safe by design: All public APIs are thread-safe
- No shared mutable state: Templates are immutable after compilation
- Concurrent rendering: Multiple templates can render simultaneously without contention

**Real-world impact**: In free-threaded Python, Kida can render multiple templates concurrently, providing **linear scaling** with CPU cores.

### Modern Architecture

Kida's architecture is built for maintainability and performance:

```
Template Source
      │
      ▼
┌─────────────┐
│   Lexer     │  O(n) single-pass tokenization
│             │  • O(1) dict-based operator lookup
│             │  • Compiled regex patterns (class-level)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   Parser    │  Recursive descent, no backtracking
│             │  • Immutable AST nodes (dataclasses)
│             │  • Source location tracking
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Optimizer   │  Pure-Python AST transformations
│ (optional)  │  • Constant folding
│             │  • Dead code elimination
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Compiler   │  O(1) dispatch → Python AST
│             │  • LOAD_FAST caching
│             │  • Precise error source mapping
└─────┬───────┘
      │
      ▼
   Template    Immutable, thread-safe render()
```

**Key architectural advantages**:

1. **AST-to-AST compilation**: No string manipulation means faster compilation and better error messages
2. **Immutable AST**: Thread-safe by design, enables concurrent compilation
3. **Source location tracking**: Every AST node knows its source location for precise error reporting
4. **Pure Python**: No C dependencies, easier to maintain and deploy

### Developer Experience

Kida provides a **modern, ergonomic syntax** without sacrificing familiarity:

- **Jinja2-compatible**: Existing templates work without changes
- **Unified endings**: `{% end %}` closes all blocks (no need to remember `{% endif %}`, `{% endfor %}`, etc.)
- **Pattern matching**: Clean `{% match %}...{% case %}` syntax replaces verbose `if/elif` chains
- **Pipeline operator**: Left-to-right readable filter chains (`|>`)
- **Modern operators**: Optional chaining (`?.`), null coalescing (`??`), range literals (`1..10`)
- **True lexical scoping**: Functions have access to outer scope (unlike Jinja2 macros)

## Production Use Cases

### High-Traffic Websites

**Problem**: Template rendering is a bottleneck. Every millisecond counts.

**Solution**: Kida's 5.6x faster rendering means:
- Lower server costs (fewer servers needed)
- Better user experience (faster page loads)
- Higher throughput (more requests per second)

**Example**: A site serving 1M requests/day with Jinja2 might need 10 servers. With Kida, you might need only 2-3 servers.

### Large Static Sites

**Problem**: Build times grow linearly with site size. A 1000-page site might take hours to build.

**Solution**: Kida's automatic block caching provides 10-100x faster builds:
- Site-scoped blocks (nav, footer, sidebar) cached once per build
- Page-specific blocks render per page
- **Result**: Build time grows sub-linearly with site size

**Example**: A 1000-page site that takes 60 minutes to build with Jinja2 might take **6-10 minutes** with Kida.

### Free-Threaded Python Applications

**Problem**: Traditional template engines are GIL-bound, limiting concurrency.

**Solution**: Kida is free-threading ready:
- Declares GIL independence
- Thread-safe by design
- Concurrent rendering without contention

**Example**: In Python 3.14t+, Kida can render 8 templates concurrently on an 8-core CPU, providing **near-linear scaling**.

### Serverless Applications

**Problem**: Cold starts are expensive. Template compilation adds latency.

**Solution**: Kida's bytecode caching provides near-instant cold starts:
- Compiled templates cached to disk
- Version-aware invalidation
- **90%+ cold-start reduction**

**Example**: A serverless function that takes 500ms to compile templates on cold start might take **<50ms** with Kida's bytecode cache.

## Comparison with Jinja2

Kida is not a drop-in replacement for Jinja2—it's a **modern alternative** that provides:

| Feature | Kida | Jinja2 |
|---------|------|--------|
| **Performance** | 5.6x faster | Baseline |
| **Free-threading** | Optimized | GIL-bound |
| **Block caching** | Automatic | Manual/None |
| **Fragment caching** | Built-in | Extension required |
| **Compilation** | AST-to-AST | String-based |
| **Error messages** | Precise source location | Line numbers |
| **Syntax** | Modern + Jinja2-compatible | Traditional |
| **Dependencies** | Pure Python | Pure Python |

**When to use Kida**:
- ✅ You need maximum performance
- ✅ You're building large sites (100+ pages)
- ✅ You're using free-threaded Python (3.14t+)
- ✅ You want modern syntax features
- ✅ You need automatic caching

**When Jinja2 might be better**:
- ✅ You need 100% Jinja2 compatibility (Kida is mostly compatible)
- ✅ You're using extensions that require Jinja2 internals
- ✅ You have a small site (<50 pages) where performance doesn't matter

## Technical Excellence

### Zero External Dependencies

Kida is **pure Python** with zero external C dependencies:
- Easier to deploy (no compilation needed)
- Easier to maintain (no C code to debug)
- Works everywhere Python works

### Comprehensive Testing

Kida is thoroughly tested:
- Unit tests for all AST nodes
- Integration tests for template rendering
- Performance benchmarks against Jinja2
- Compatibility tests for Jinja2 syntax

### Production Proven

Kida is used in production by Bengal, a static site generator that builds sites with thousands of pages. It's battle-tested and production-ready.

## Getting Started

Kida is Bengal's default template engine. No configuration needed:

```yaml
# bengal.yaml
site:
  template_engine: kida  # Default, can be omitted
```

Your existing Jinja2 templates work without changes—Kida can parse Jinja2 syntax automatically.

## Next Steps

- **Understand the architecture**: [Architecture Guide](/docs/theming/templating/kida/architecture/)
- **See performance benchmarks**: [Performance Guide](/docs/theming/templating/kida/performance/)
- **Learn the syntax**: [Syntax Reference](/docs/reference/kida-syntax/)
- **Try it hands-on**: [Tutorial](/docs/tutorials/getting-started-with-kida/)

:::{seealso}
- [Kida Architecture](/docs/theming/templating/kida/architecture/) — Deep dive into how Kida works
- [Kida Performance](/docs/theming/templating/kida/performance/) — Benchmarks and optimization strategies
- [Kida Comparison](/docs/theming/templating/kida/comparison/) — Feature-by-feature comparison with Jinja2
:::

# Kida Complexity Analysis

## Overview

All operations in Kida are designed for **O(n)** template processing where n = template size.

---

## Lexer Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `tokenize()` | **O(n)** | Single pass through source |
| `_advance()` | O(1) amortized | Character-by-character |
| `_find_next_construct()` | O(n) | Three `str.find()` but only advances position |
| `_next_code_token()` | **O(1)** | Dict lookup for operators (after optimization) |
| `_scan_string()` | O(s) | Where s = string length |
| `_scan_name()` | O(m) | Where m = identifier length |

**Total**: O(n) where n = source length

### Bottleneck Fixed
- **Before**: `_next_code_token()` iterated through 24 operators → O(24) = O(1) but slow
- **After**: Dict-based operator lookup → O(1) average with hash

---

## Parser Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `parse()` | **O(t)** | Where t = number of tokens |
| `_parse_body()` | O(t) | Linear scan |
| `_parse_expression()` | O(d) | Where d = expression depth |
| `_match()` | **O(1)** | Set membership (after optimization) |
| `_parse_binary()` | O(k) | Where k = chained operators |

**Total**: O(t) where t = tokens ≈ O(n)

### Bottleneck Fixed
- **Before**: `_match(*types)` created tuple, used `in` → O(k)
- **After**: Frozenset for common type checks → O(1) average

---

## Compiler Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `compile()` | **O(a)** | Where a = AST nodes |
| `_compile_node()` | O(1) | Dispatch table lookup |
| `_compile_expr()` | O(e) | Where e = expression depth |
| `ast.fix_missing_locations()` | O(a) | Python stdlib |
| `compile()` builtin | O(a) | Python bytecode compilation |

**Total**: O(a) where a = AST nodes ≈ O(n)

### Bottleneck Fixed
- **Before**: `isinstance()` chains in `_compile_node()` → O(k) where k = node types
- **After**: Type dispatch dict → O(1) average

---

## Runtime Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `render()` | **O(g + c)** | Globals + context size |
| Context lookup `ctx['x']` | O(1) | Dict access |
| `_escape()` | **O(n)** | Single pass (after optimization) |
| Buffer append | O(1) amortized | List append |
| `''.join(buf)` | O(n) | Final string concatenation |

**Total**: O(n) where n = output size

### Bottleneck Fixed
- **Before**: `_escape()` used 5 chained `.replace()` → O(5n)
- **After**: Single-pass `str.translate()` → O(n)

---

## Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| Lexer | O(1) | Generator-based, no buffering |
| Tokens | O(t) | List of tokens |
| AST | O(a) | Immutable nodes |
| Compiled code | O(a) | Python bytecode |
| Render buffer | O(o) | Output size |

**Total**: O(n) space where n = max(source, output)

---

## Comparison with Jinja2

| Operation | Kida | Jinja2 |
|-----------|------|--------|
| Lexer | O(n) | O(n) |
| Parser | O(n) | O(n) |
| Compiler | O(n) | O(n) |
| **Render** | **O(n)** | **O(n) with O(k) generator overhead** |
| **Escape** | **O(n)** | **O(5n)** |
| Context lookup | O(1) | O(d) where d = context chain depth |
| Filter dispatch | O(1) | O(1) + introspection overhead |

---

## Memory Access Patterns

### Kida (Optimized)
```
Compile: Template → Tokens → AST → Python AST → Code Object
Render:  Code Object → Buffer (list) → ''.join() → String
```
- **No generator suspension points**
- **No missing value checks**
- **Direct dict access**

### Jinja2
```
Compile: Template → Tokens → AST → Python Source String → Code Object
Render:  Code Object → Generator → yield → concat → String
```
- **Generator suspension per yield**
- **Missing value checks per variable**
- **Context chain traversal**

---

## Threading Characteristics

| Aspect | Kida | Jinja2 |
|--------|------|--------|
| Compile | Thread-safe (immutable) | Thread-safe |
| Render | **Lock-free** (local state only) | Lock-free |
| Cache | Copy-on-write | LRU with locks |
| Free-threading | **PEP 703 declared** | Not declared |

---

## Benchmarks (Measured)

**Test conditions**: Both engines with `autoescape=True`, Python 3.12

| Template Type | Kida | Jinja2 | Speedup |
|--------------|------|--------|---------|
| Simple `{{ name }}` | 0.005s | 0.045s | **8.9x** |
| Filter chain `{{ x \| upper \| trim }}` | 0.006s | 0.050s | **8.9x** |
| Conditionals `{% if %}` | 0.004s | 0.039s | **11.2x** |
| For loop (100 items) | 0.014s | 0.028s | **2.1x** |
| For loop (1000 items) | 0.013s | 0.024s | **1.8x** |
| Dict attr `{{ item.name }}` | 0.006s | 0.026s | **4.3x** |
| HTML escape heavy | 0.019s | 0.044s | **2.3x** |

**Summary**:
- Arithmetic mean: **5.6x faster**
- Geometric mean: **4.4x faster**
- Wins: **7/7 benchmarks**

---

## Optimization Checklist

### Lexer
- [x] Class-level compiled regex (no per-instance compilation)
- [x] Dict-based operator lookup O(1) (vs O(k) list iteration)
- [x] Single-pass tokenization
- [ ] Optional Rust extension for 10x speedup

### Parser
- [x] Frozenset for type matching
- [x] Recursive descent (no backtracking)
- [x] Immutable AST nodes
- [ ] Pratt parser for expressions (future)

### Compiler
- [x] Dispatch table for node types O(1) (vs isinstance chains)
- [x] AST-to-AST (no string manipulation)
- [x] Compile-time filter binding
- [x] Loop variable direct access (LOAD_FAST vs dict lookup)
- [x] Cached local function references (_e, _s, _append)
- [ ] Constant folding optimization pass

### Runtime
- [x] Single-pass HTML escape via str.translate()
- [x] Fast path escape check (skip if no escapable chars)
- [x] Direct dict context access
- [x] Safe getattr with dict fallback for {{ item.attr }}
- [ ] Pre-allocate buffer based on template size estimate

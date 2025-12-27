# RFC: Kida Modernization for Python 3.14+ and 3.15

- **Status**: Implemented (Phase 1)
- **Author**: Kida Core Team / AI Assistant
- **Date**: 2025-12-26
- **Target Version**: Kida 2.0 / Bengal 1.5

---

## 1. Executive Summary

This RFC outlines the modernization of the Kida template engine for **Python 3.14.0** and the upcoming **Python 3.15**. Phase 1 (Stability and Foundation) is now complete, including native Zstandard caching and PEP 750 support.

Key pillars:
1.  **GIL-less Rendering**: Exploiting PEP 779 (Free-threaded Python) for true parallel build cycles. (Verified 🟢)
2.  **Native Zstandard Caching**: Adopting PEP 784 for high-speed, high-ratio fragment compression. (Implemented ✅)
3.  **T-String Interpolation**: Leveraging PEP 750 for specialized string processing. (Implemented via `kida.k` ✅)
4.  **Deferred Type Validation**: Utilizing PEP 649 for complex `autodoc` type resolution. (Pending)
5.  **Tachyon Profiling**: Integrating Python 3.15's dedicated profiling package for template bottleneck detection. (Pending)

---

## 2. Background

Kida currently uses an AST-to-AST compiler that generates optimized Python bytecode. While performant, it is still bound by the Global Interpreter Lock (GIL) and relies on external libraries or older compression formats for caching. With the release of Python 3.14 on Oct. 7, 2025, the Python ecosystem has shifted towards free-threading and specialized syntax (t-strings) that align perfectly with Kida's design principles of **Explicit Scoping** and **High Signal-to-Noise**.

---

## 3. Proposal

### 3.1. Massively Parallel Rendering (PEP 779)
Kida’s AST is already immutable and its compiler is stateless. We will officially certify Kida for **Free-threaded Python 3.14**.
-   **Action**: Audit the `ctx` (Context) dictionary for thread-safety. Move from standard `dict` to thread-safe variants or ensure that each thread in a multi-core render loop operates on a unique context projection.
-   **Benefit**: True O(N) scaling for large documentation builds on multi-core workstations.

### 3.2. Zstandard Fragment Caching (PEP 784)
The `{% cache %}` block currently relies on `pickle` or `gzip`. Python 3.14 introduces `compression.zstd` in the standard library.
-   **Action**: Update `kida/compiler/statements/special_blocks.py` to use `zstd` by default for fragment storage.
-   **Benefit**: Faster cache writes and lower memory footprint for large sites like the Bengal 10k suite.

### 3.3. Template String Literals (PEP 750 / t-strings)
Python 3.14's "t-strings" allow custom processing of string literals at the syntax level.
-   **Action**: Explore a `k"..."` literal for Bengal. This would allow developers to write inline Kida expressions directly in Python code that are pre-compiled into Kida AST.
-   **Example**:
    ```python
    header = k"<h1>{{ page.title | upper }}</h1>"
    # Compiles to Kida AST immediately, bypassing runtime parsing.
    ```

### 3.4. Deferred Annotation Support (PEP 649)
Kida’s `{% template %}` tag and the `autodoc` extractor often struggle with circular type imports during extraction.
-   **Action**: Adopt PEP 649’s deferred evaluation for all type hints in Kida components.
-   **Benefit**: More robust `autodoc` generation for complex Python packages without "NameError: name 'X' is not defined" during type-checking phases.

### 3.5. Template Performance Inspector (Python 3.15 / PEP 799)
Python 3.15 introduces the `Tachyon` profiler.
-   **Action**: Build a `KidaProfiler` that hooks into PEP 799. This will provide a "Flame Graph" for templates, showing exactly which macro or filter is stalling the build.
-   **Benefit**: Identifies "Heavy Macros" in seconds, allowing developers to optimize their `{% cache %}` strategies.

---

## 4. Implementation Plan

### Phase 1: Stability (Q1 2026)
-   Audit all compiler mixins for 3.14 compatibility.
-   Implement Zstandard caching backend.
-   Verify thread-safety of the `Environment` and `Template` objects.

### Phase 2: Optimization (Q2 2026)
-   Introduce `t-string` support for inline Kida.
-   Optimize `match` statements using the new 3.14 "newer compiler" interpreter optimizations.

### Phase 3: Introspection (Q3 2026 - Python 3.15 Release)
-   Integrate `Tachyon` profiling.
-   Release the "Kida Inspector" browser overlay for Bengal.

---

## 5. Alternatives Considered
-   **Staying on Python 3.12/3.13**: While stable, we would miss the 2x-3x performance gains promised by the 3.14 JIT and free-threading.
-   **Jinja-Compat Only**: Limiting modernization to Jinja syntax would hinder Kida's goal of being a next-generation engine.

## 6. References
- [Python 3.14.0 Release Notes](https://www.python.org/downloads/release/python-3140/)
- [PEP 750: Template Strings](https://peps.python.org/pep-0750/)
- [PEP 779: Free-threaded Python](https://peps.python.org/pep-0779/)
- [What's New in Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html)

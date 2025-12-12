# RFC: Enforce `PageProxy` transparency contract for postprocess + incremental builds

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-12  
**Confidence**: 86% 🟢

---

## Executive summary

Introduce an explicit, tested “**Page-like contract**” for incremental builds so that post-processing and output formats cannot regress when `site.pages` contains a mix of `Page` and `PageProxy`.

This RFC focuses on **preventing runtime breakage** (e.g., missing attributes) and **making violations loud and actionable**, without requiring template authors to know about proxies.

---

## Problem statement

### Current behavior

Incremental builds use `PageProxy` as a lazy-loaded stand-in for unchanged pages. The code explicitly documents a “TRANSPARENCY CONTRACT” and warns that `PageProxy` must implement everything used by templates and post-processing (`bengal/core/page/proxy.py:61-77`).

During cached discovery, unchanged pages are replaced with `PageProxy`, and critical fields like `output_path` are copied over for later post-processing (`bengal/discovery/content_discovery.py:318-353`).

Post-processing **always** generates output formats (including `index.json`) when enabled, because search depends on them (`bengal/orchestration/postprocess.py:127-166`).

Output format generators consume page attributes like:
- `plain_text`, `title`, `metadata`, `tags`, `date`, `_section` (`bengal/postprocess/output_formats/index_generator.py:185-238`)
- `plain_text`, `parsed_ast`, `content`, `output_path`, `date`, `tags`, `_section` (`bengal/postprocess/output_formats/json_generator.py:157-245`)
- visibility properties like `in_sitemap`, `in_rss` (`bengal/postprocess/sitemap.py:108-187`, `bengal/postprocess/rss.py:87-176`)

### Why this is a P0 risk

Because the “contract” is currently **implicit**, it is easy to:
- Add a new output-format or postprocess feature that reads a new property from `Page`
- Forget to add the corresponding implementation to `PageProxy`
- Ship a regression that only appears in certain incremental scenarios (when postprocess runs and proxies are present)

The code already acknowledges this class of failure as “CRITICAL” (`bengal/core/page/proxy.py:61-77`), but there is no single authoritative list of required attributes and no contract test that would fail at review time.

---

## Goals

1. **Make required page attributes explicit** for postprocess/output formats (and any other core code path that operates over `site.pages`).
2. **Prevent regressions** by adding tests that fail when the contract is violated.
3. **Fail clearly**: contract violations should produce actionable error messages, not mysterious template/postprocess crashes.
4. **Preserve performance**: avoid forcing eager loads for unchanged pages unless strictly required for correctness.

## Non-goals

- Proving correctness of arbitrary user templates (Jinja2 can access any attribute dynamically).
- Reworking incremental build semantics or changing when postprocess runs.
- Refactoring the caching model (e.g., moving `plain_text` into caches) as part of this RFC (can be follow-up work).

---

## Architecture impact

### Affected subsystems

- **Core**: `bengal/core/page/proxy.py` (where the proxy contract lives)
- **Discovery**: `bengal/discovery/content_discovery.py` (where proxies are created and inserted)
- **Postprocess**: `bengal/postprocess/*` and `bengal/orchestration/postprocess.py` (where `site.pages` is consumed)
- **Tests**: `tests/unit/core/test_page_proxy.py`, plus new integration/contract tests

---

## Design options

### Option A: “Contract test only” (minimal)

Add a contract test that enumerates required attributes for postprocess/output formats and asserts:
- `PageProxy` provides them (attribute exists)
- Accessing “should-be-cached” attributes does not trigger `_ensure_loaded()` (where applicable)

**Pros**
- Smallest change; immediate regression protection.

**Cons**
- Contract list lives only in tests unless also formalized in code.
- Does not improve runtime error clarity when violations happen outside tests.

### Option B: Explicit `Protocol` + shared contract list (recommended)

1. Create a single source of truth for the contract, e.g. `bengal/core/page/contracts.py`:
   - `PageLikeForPostprocess` (a `typing.Protocol`)
   - A constant list/set of “required attributes used by core code paths”
2. Update postprocess/output format generators to type against the protocol (documentation + mypy guidance).
3. Add tests that validate `PageProxy` satisfies the contract.

**Pros**
- Central, reusable contract; tests and runtime code can reference the same list.
- Improves maintainability: adding new postprocess behavior must update one contract.

**Cons**
- Protocols won’t guarantee runtime template safety (out of scope).

### Option C: Runtime guardrails (additional safety)

Add a small runtime validation step in postprocess (dev-mode only, or behind a config flag):
- iterate `site.pages`
- verify required attributes exist
- raise a purpose-built error with “add delegate to `PageProxy`” guidance

**Pros**
- Fast feedback during development; avoids shipping broken builds.

**Cons**
- Must be carefully scoped to avoid overhead in large sites.

---

## Recommended approach

Adopt **Option B**, with an optional **Option C** runtime validation toggle.

This aligns with the existing code’s stated expectations:
- The proxy is intended to be “transparent to callers” (`bengal/core/page/proxy.py:39-77`)
- Postprocess runs tasks that depend on page attributes (`bengal/orchestration/postprocess.py:127-166`)
- Output formats expect rich attributes across all pages (`bengal/postprocess/output_formats/index_generator.py:185-238`)

---

## Detailed design (proposed)

### 1) Define an explicit contract for postprocess consumption

Add a protocol (example sketch):

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

class PageLikeForPostprocess(Protocol):
    source_path: Path
    output_path: Path | None
    title: str
    metadata: dict[str, Any]
    tags: list[str]
    date: Any  # datetime | None (kept flexible to match existing types)

    # URL-ish
    url: str
    relative_url: str
    permalink: str

    # Visibility
    in_sitemap: bool
    in_rss: bool

    # Content used by index/json/llm generators
    plain_text: str
```

The initial contract scope should be driven by current call sites in:
- `bengal/postprocess/output_formats/index_generator.py`
- `bengal/postprocess/output_formats/json_generator.py`
- `bengal/postprocess/rss.py`
- `bengal/postprocess/sitemap.py`

### 2) Contract tests

Add a unit test that:
- Constructs a `PageProxy` via cached discovery patterns (or via a fixture)
- Ensures it provides the contract attributes without raising
- Verifies “cached” fields remain non-loading where intended

Existing tests already cover some of this (metadata access does not trigger lazy load: `tests/unit/core/test_page_proxy.py:89-105`).

This RFC extends testing to cover **postprocess-specific** expectations.

### 3) (Optional) Runtime validation toggle

Add `build.validate_page_proxy_contract` (default: `false`) or a similar config flag.
When enabled, validate that `site.pages` objects satisfy the `PageLikeForPostprocess` attribute set before running output formats.

---

## Rollout plan

1. **Introduce contract definition** (protocol + attribute list) and keep it private/internal.
2. **Add contract tests** that fail if a required attribute is missing on `PageProxy`.
3. **Wire optional runtime validation** behind a config flag (dev-focused).
4. If regressions are found (e.g., missing `plain_text` on `PageProxy`), address them as follow-up implementation commits, not as part of this RFC’s acceptance criteria.

---

## Acceptance criteria

- A single, explicit contract exists for postprocess page consumption.
- Tests fail when `PageProxy` does not satisfy the contract.
- Contract is documented with evidence-backed references to the consuming code.

---

## Risks and mitigations

- **Risk**: Contract becomes stale as new generators are added.  
  **Mitigation**: Require updates to the shared contract list when postprocess/output formats change; tests should exercise those paths.

- **Risk**: Over-eager contract increases proxy eager-loading.  
  **Mitigation**: Keep contract minimal and oriented to correctness; optimize later by caching expensive fields explicitly.

---

## References (evidence)

- `bengal/core/page/proxy.py:61-77` — Proxy “TRANSPARENCY CONTRACT” warning.
- `bengal/discovery/content_discovery.py:318-353` — Replacing unchanged pages with `PageProxy`, copying `output_path`.
- `bengal/orchestration/postprocess.py:127-166` — Output formats treated as critical and always generated when enabled.
- `bengal/postprocess/output_formats/index_generator.py:185-238` — Uses `page.plain_text`, `page.title`, `page.metadata`, `page.tags`, `page.date`, `page._section`.
- `bengal/postprocess/output_formats/json_generator.py:157-245` — Uses `page.plain_text`, `page.parsed_ast`, `page.content`, `page.tags`, `page.output_path`.
- `bengal/postprocess/sitemap.py:108-187` — Uses `page.in_sitemap`, `page.output_path`, `page.slug`, `page.translation_key`, `page.date`.
- `bengal/postprocess/rss.py:87-176` — Uses `page.in_rss`, `page.output_path`, `page.slug`, `page.content`, `page.metadata`, `page.date`.

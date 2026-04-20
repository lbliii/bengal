# RFC: Template Error Codes, Overlay Protocol, and Class Decomposition

**Status**: Draft
**Created**: 2026-04-17
**Epic**: [immutable-floating-sun] Track A Sprint A0
**Supersedes**: N/A
**Dependencies**: `bengal/errors/codes.py` (ErrorCode enum), `bengal/rendering/errors/exceptions.py:153-205`

---

## Context

Sprint A0 of the Errors & Site S-Tier epic. Three design questions must be settled on paper before any code moves in Sprint A1:

1. Which `ErrorCode` does each of the seven current `_classify_error` branches map to?
2. What WebSocket message schema does the dev-server browser overlay use?
3. How does `TemplateRenderError` decompose into focused classes — what are each class's responsibilities, public surface, and complexity targets?

This RFC settles all three.

---

## Part 1 — Error Code Taxonomy

### Current Classifier Branches

`bengal/rendering/errors/exceptions.py:153-205` currently returns one of eight string constants. Five already have canonical `ErrorCode` values in `bengal/errors/codes.py:150-165`; four do not.

| Branch | Trigger | Existing code | Action |
|---|---|---|---|
| `"syntax"` | `TemplateSyntaxError`, `KidaSyntaxError`, `TemplateAssertionError` (non-filter) | `R002 template_syntax_error` | REUSE |
| `"undefined"` | `UndefinedError`, `KidaUndefinedError` | `R003 template_undefined_variable` | REUSE |
| `"filter"` | `TemplateAssertionError` with "unknown filter", or "no filter named" | `R004 template_filter_error` | REUSE |
| `"runtime"` | `TemplateRuntimeError`, `KidaRuntimeError` | — | **NEW: R014** |
| `"callable"` | `TypeError: 'NoneType' object is not callable` | — | **NEW: R015** |
| `"none_access"` | `TypeError: argument of type 'NoneType' is not iterable/subscriptable` | — | **NEW: R016** |
| `"type_comparison"` | `TypeError: not supported between instances of ...` | — | **NEW: R017** |
| `"other"` | Fallback | `R010 render_output_error` | REUSE as fallback |

### Additional Codes for Structural Errors (Not Yet Surfaced)

The current classifier returns "syntax" or "other" for several structural failures that deserve their own codes. These will be distinguished in A1.1 when the classifier gains explicit branches:

| Condition | Proposed code | Current fallback |
|---|---|---|
| Include/extends target not found | **R018 template_include_not_found** (distinct from existing `R005 template_include_error` which is general) | currently `R002 syntax` or `R005` ambiguously |
| Circular include/extends detected | **R019 template_circular_include** | currently unhandled, bubbles as RecursionError |

### Final Additions to `ErrorCode` Enum

Add under the rendering section (currently R013 is the last assigned; R014+ is free):

```python
# Template runtime / data errors (R014-R017)
R014 = "template_runtime_error"          # TemplateRuntimeError / KidaRuntimeError
R015 = "template_callable_error"         # NoneType called; filter/function is None
R016 = "template_none_access_error"      # iterating/subscripting None
R017 = "template_type_comparison_error"  # TypeError comparing mixed types (e.g. int < str)

# Template structural errors (R018-R019)
R018 = "template_include_not_found"      # {% include "x.html" %} target missing
R019 = "template_circular_include"       # Include cycle detected
```

Reserve **R020-R040** for future template-error specialization (by category: include errors R018-R025, macro errors R026-R030, block/inheritance errors R031-R035, context-bound errors R036-R040). Not added now — add on demand.

### Classifier → ErrorCode Mapping (Final)

```python
# bengal/rendering/errors/classifier.py (A1.1)
_CLASSIFICATION_MAP = {
    "syntax":           ErrorCode.R002,  # template_syntax_error
    "undefined":        ErrorCode.R003,  # template_undefined_variable
    "filter":           ErrorCode.R004,  # template_filter_error
    "runtime":          ErrorCode.R014,  # template_runtime_error (NEW)
    "callable":         ErrorCode.R015,  # template_callable_error (NEW)
    "none_access":      ErrorCode.R016,  # template_none_access_error (NEW)
    "type_comparison":  ErrorCode.R017,  # template_type_comparison_error (NEW)
    "include_missing":  ErrorCode.R018,  # template_include_not_found (NEW branch)
    "circular_include": ErrorCode.R019,  # template_circular_include (NEW branch)
    "other":            ErrorCode.R010,  # render_output_error (fallback)
}
```

### Acceptance (A0.1)

- [x] Every branch in current classifier has a code assignment
- [x] Zero net new codes where existing ones fit (R002/R003/R004 reused)
- [x] Four new codes added only for unmapped branches (R014-R017)
- [x] Two reserved for A1.1 structural-error branches (R018-R019)
- [x] Documented in this RFC for peer review before Sprint A1

---

## Part 2 — Overlay Transport Protocol

### Goals

The dev-server browser overlay (Sprint A3) needs:
- Push error state from build → client without full page reload
- Dismiss-to-recover on successful rebuild
- No new server dependency (reuse existing Pounce ASGI WebSocket)

### Message Schema

Single channel, two message types. JSON-encoded over existing `/ws/reload` (or equivalent) WebSocket.

#### `build_error`

Sent when a build completes with at least one rendering error.

```json
{
  "type": "build_error",
  "schema_version": 1,
  "timestamp": "2026-04-17T15:34:12Z",
  "errors": [
    {
      "code": "R015",
      "code_name": "template_callable_error",
      "docs_url": "/docs/reference/errors/#r015",
      "title": "Template calls a None value as a function",
      "message": "A function or filter being called is None.",
      "hint": "Check that all filters and template functions are properly registered.",
      "suggestions": [
        {"label": "Did you mean?", "value": "format_date", "distance": 1}
      ],
      "frame": {
        "file": "templates/post.html",
        "file_abs": "/abs/path/to/templates/post.html",
        "line": 23,
        "column": 14,
        "lines": [
          {"n": 20, "text": "<article>"},
          {"n": 21, "text": "  <header>"},
          {"n": 22, "text": "    <time datetime=\"{{ page.date }}\">"},
          {"n": 23, "text": "      {{ page.date | format_datte }}", "is_error": true},
          {"n": 24, "text": "    </time>"},
          {"n": 25, "text": "  </header>"},
          {"n": 26, "text": "</article>"}
        ]
      },
      "inclusion_chain": [
        {"template": "_base.html", "line": 12},
        {"template": "post.html",  "line": 23}
      ],
      "page_source": "content/posts/2026-04-17-hello.md",
      "stack": [
        "File \"templates/post.html\", line 23, in template",
        "..."
      ]
    }
  ]
}
```

#### `build_ok`

Sent when a rebuild succeeds after a failed build. Signals overlay dismiss.

```json
{
  "type": "build_ok",
  "schema_version": 1,
  "timestamp": "2026-04-17T15:34:45Z",
  "build_ms": 142
}
```

### Client Contract

- On `build_error`: render overlay (first error only; subsequent errors shown via carousel control in overlay)
- On `build_ok`: animate-dismiss overlay within 200ms
- On WebSocket disconnect: no change to overlay state; on reconnect, request current state via `{"type": "status"}` → server responds with current build state

### Server Implementation Notes

- No new dependency required. `bengal/server/dev_server.py` already uses Pounce ASGI; add message type handling to existing reload channel or split into `/ws/errors` (decide in A3.2 — recommendation: same channel, different `type` field, simpler).
- Overlay HTML is served from the build output when `--continue-on-error` is set (A4.1) OR injected client-side via WebSocket message (A3.1 static HTML + JS). Both paths use the same schema.
- Payload size budget: 10 KB per error (generous — keeps source frame + stack under limits). Reject payloads > 64 KB defensively.

### Acceptance (A0.2)

- [x] Schema defined for `build_error` and `build_ok`
- [x] `schema_version: 1` field in both (allows non-breaking evolution)
- [x] Reuses existing Pounce WebSocket channel — no new server dep
- [x] Client contract specifies dismiss-on-ok behavior
- [x] Payload size budget set

---

## Part 3 — Class Decomposition Spec

### Target Module Layout

```
bengal/rendering/errors/           [SLIM — renderer-local]
├── __init__.py                    # Re-exports for back-compat (one release)
├── classifier.py                  # ErrorClassifier — branch → ErrorCode
├── context_extractor.py           # SourceContextExtractor → SourceFrame
├── jinja_adapter.py               # from_jinja2_error factory
└── report.py                      # TemplateErrorReport (frozen dataclass)

bengal/errors/                     [UNIFIED — canonical]
└── suggestions.py                 # (extended) absorbs rendering suggestion helpers
```

### Class Contracts

#### `ErrorClassifier` (new — `bengal/rendering/errors/classifier.py`)

```python
from bengal.errors.codes import ErrorCode

class ErrorClassifier:
    """Map a template exception to a canonical ErrorCode."""

    def classify(self, exc: BaseException) -> ErrorCode: ...

    # Internals (private)
    def _is_callable_error(self, exc: BaseException) -> bool: ...
    def _is_type_comparison(self, exc: BaseException) -> bool: ...
    def _is_none_access(self, exc: BaseException) -> bool: ...
    def _is_filter_error(self, exc: BaseException) -> bool: ...
```

**Target metrics:**
- LOC: ≤ 150
- Max McCabe: 10 (current `_classify_error` is 22)
- Public methods: 1 (`classify`)
- Dependencies: `bengal.errors.codes`, `jinja2.exceptions`, `kida.exceptions` (import-level, not deferred)
- Pure function — no I/O, no file reads

**Test plan:**
- One unit test per ErrorCode in `_CLASSIFICATION_MAP` with a crafted exception
- Parametrized test for message-based classification (e.g. TypeError with "'NoneType' object is not callable" → R015)
- Target coverage: ≥ 95%

#### `SourceContextExtractor` (new — `bengal/rendering/errors/context_extractor.py`)

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, slots=True)
class SourceFrame:
    file: str                    # Template-relative path
    file_abs: Path | None        # Absolute path, if resolvable
    line: int | None             # 1-indexed
    column: int | None           # 1-indexed, None if unknown
    lines: tuple[tuple[int, str, bool], ...]  # (n, text, is_error_line)

class SourceContextExtractor:
    """Build a SourceFrame from an exception and the template engine."""

    def extract(
        self,
        exc: BaseException,
        template_name: str,
        template_engine: TemplateEngine,
    ) -> SourceFrame | None: ...

    # Internals
    def _resolve_template_path(self, engine, name) -> Path | None: ...
    def _find_first_code_line(self, lines: list[str], exc: BaseException) -> int: ...
    def _extract_line_from_traceback(self, exc: BaseException) -> int | None: ...
```

**Target metrics:**
- LOC: ≤ 200
- Max McCabe: 10 (current `_extract_context` is 21; `_find_first_code_line` acceptable at ≤ 8)
- I/O: file reads (template source) — documented, not deferred
- Returns `SourceFrame | None` (None on total failure, never raises)

**Test plan:**
- Happy path: exception with lineno + filename → SourceFrame with correct line highlighted
- Fallback: TypeError without lineno → uses traceback walk
- Recovery: template file unreadable → returns frame with `lines=()` (not None)
- Callable-error line preference: TypeError prefers lines with `{{ ... ( ... }}` patterns
- Target coverage: ≥ 90%

#### `SuggestionEngine` (extended — `bengal/errors/suggestions.py`)

Extends the existing suggestion engine. Adds a dispatch method:

```python
# bengal/errors/suggestions.py
class SuggestionEngine:
    # existing methods ...

    def suggest_for_template_error(
        self,
        code: ErrorCode,
        exc: BaseException,
        frame: SourceFrame | None,
        template_engine: TemplateEngine,
    ) -> Suggestion | None: ...
```

The four moved functions (`_identify_none_callable`, `_suggest_type_comparison`, `_find_alternatives`, `_generate_enhanced_suggestions`) become private methods of `SuggestionEngine`, each under 40 LOC, each McCabe ≤ 8.

**Target metrics:**
- The 174-LOC McCabe-26 `_generate_enhanced_suggestions` in `display.py` is **deleted** — its logic splits across `SuggestionEngine.suggest_for_template_error` and per-code helper methods.

**Test plan:**
- Unit test per code: R003 "undefined var" → "Did you mean?" with Levenshtein
- Unit test: R015 callable with traceback → identifies None filter name
- Unit test: R017 type comparison → extracts mixed types from message
- Regression test: existing suggestion output snapshots preserved (no text regression from the split)

#### `TemplateErrorReport` (new — `bengal/rendering/errors/report.py`)

Frozen dataclass. Replaces `TemplateRenderError`'s role as a data carrier:

```python
from dataclasses import dataclass
from bengal.errors.codes import ErrorCode

@dataclass(frozen=True, slots=True)
class TemplateErrorReport:
    code: ErrorCode
    title: str
    message: str
    hint: str | None
    suggestion: Suggestion | None
    frame: SourceFrame | None
    inclusion_chain: InclusionChain | None
    page_source: Path | None
    stack: tuple[str, ...]
    exc: BaseException  # original, for re-raise if needed

    @property
    def docs_url(self) -> str: return self.code.docs_url
```

**Target metrics:**
- LOC: ≤ 80
- Zero methods beyond `__init__` auto-generated + `docs_url` property
- No I/O, no classification, no extraction — pure data

#### `from_jinja2_error` factory (new — `bengal/rendering/errors/jinja_adapter.py`)

```python
def build_template_error_report(
    exc: BaseException,
    template_name: str,
    page_source: Path | None,
    template_engine: TemplateEngine,
) -> TemplateErrorReport:
    """Factory: compose classifier + extractor + suggester into a report."""
```

This is the **single public entry point** — replaces `TemplateRenderError.from_jinja2_error`. `bengal/rendering/renderer.py:497` will call this instead.

**Target metrics:**
- LOC: ≤ 80
- McCabe: ≤ 6
- Composition only — no logic of its own beyond wiring

### TemplateRenderError Deprecation

After A1-A2 complete:

- `TemplateRenderError` exists only as a back-compat shim in `bengal/rendering/errors/__init__.py` that constructs a `BengalRenderingError` + `TemplateErrorReport` and warns `DeprecationWarning`
- Removed entirely in v0.5.0
- Internal callers migrated in A2.1

### Acceptance (A0.3)

- [x] Each of 5 classes has a contract (public surface + target metrics)
- [x] All classes ≤ 200 LOC target
- [x] All classes max McCabe ≤ 10 target
- [x] Test plan per class
- [x] Single public entry point identified (`build_template_error_report`)
- [x] Back-compat path documented

---

## Summary of Sprint A0 Deliverables

This RFC satisfies all three A0 acceptance criteria in one document:

| Task | Artifact | Location |
|---|---|---|
| A0.1 | Error code taxonomy | Part 1 above |
| A0.2 | Overlay transport schema | Part 2 above |
| A0.3 | Class decomposition spec | Part 3 above |

Sprint A1 may now proceed.

---

## Changelog

- 2026-04-17: Initial draft.

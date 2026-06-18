<!-- markdownlint-disable MD013 MD060 -->

# RFC: Tokenizer-Based CSS Minifier (`bengal/css/`)

**Status**: Drafted
**Created**: 2026-06-16
**Scope**: `bengal/assets/`, `bengal/core/asset/`, themes, tests, benchmarks
**Tracking issue**: [#510 — CSS minifier breaks `@scope (...) to (...)` by gluing `to(`](https://github.com/lbliii/bengal/issues/510)
**Stewards touched**: Assets, Core, Tests, Performance, Public Contracts

## Decisions on record (2026-06-16)

- **Ambition: aggressive.** The end-state target is a cssnano-class engine with a
  structural (cascade-rewriting) optimization tier — not just whitespace removal.
  The aggressive tier is designed in full here (see "Level 'aggressive'" and
  "Structural correctness oracle"), gated behind opt-in and a stronger proof than
  the lossless tiers, and built only after the safe engine is solid.
- **Extraction: internal-first.** Ships as the internal `bengal/css/` subpackage,
  architected so a later standalone PyPI extraction is a near-verbatim copy. No
  early spin-out.
- **Code: not yet.** This pass refines the design only; no implementation lands
  until the design is accepted.

## TL;DR

Replace Bengal's heuristic, character-level CSS minifier with a proper
**CSS tokenizer + minifying serializer** in a new self-contained `bengal/css/`
subpackage, designed for clean extraction into a standalone zero-dependency
package later. Correctness becomes *structural* (decided at tokenize time)
instead of a growing pile of property-name special cases. Issue #510 is fixed
as a side effect, along with the whole bug class it belongs to.

## Problem

### The reported bug (#510)

`minify_css` strips whitespace around `(` unconditionally, rewriting the
`@scope (…) to (…)` prelude's `to` keyword into a `to(` **function token**.
Browsers then drop the entire scoped block. On `minify: true` (production /
GitHub Pages) every `@scope (.block) to (.block .block)` envelope silently
loses its rules; on `minify: false` (local preview) it works. That is the worst
possible failure mode: invisible until deployed.

### The real problem (root cause)

The bug is not a missing special case — it is the *architecture*. The current
minifier in `bengal/assets/css_minifier.py:74` is a single ~330-line
character-by-character state machine that decides whether to keep each
whitespace run from **local heuristics**:

- `_MULTI_VALUE_PROPS`, `_FUNCTION_LIST_PROPS`, `_SLASH_PROPS`, `_CALC_FUNCTIONS`,
  `_CSS_KEYWORDS`, `_VALUE_KEYWORDS`, `_CSS_UNITS` frozensets
  (`css_minifier.py:27-70`) enumerate properties/keywords by hand.
- `needs_space_before()` (`css_minifier.py:214`) is a ladder of ~15 special
  cases (calc operators, font shorthand, grid slashes, descendant selectors…).

Every CSS feature that needs a space the heuristics didn't anticipate is a
latent `to(`-style corruption. `@scope … to` is just the one a user happened to
hit. The same shape lurks in: container/style queries, `@supports` function
syntax, `unicode-range`, `An+B` (`:nth-child`), custom-property values,
math-function nesting, and any future syntax. Patching `to` specifically (the
issue's suggested fix) repairs one symptom and leaves the class open.

### Secondary problems this exposes

1. **Two parallel minifiers.** `bengal/assets/css_minifier.py:minify_css`
   (used by `asset_core.py:421`) and
   `bengal/core/asset/css_transforms.py:lossless_minify_css` (exported from
   `bengal/core/asset/__init__.py`) are independent reimplementations of the
   same idea with different bugs.
2. **Regex CSS rewriting in core.** `transform_css_nesting` and
   `remove_duplicate_bare_h1_rules` (`css_transforms.py:18,107`) are
   brace-counting regex transforms living in `bengal/core/` — flagged transitional
   debt by the Core steward, and structurally fragile.
3. **No correctness oracle.** Coverage is example-based golden strings
   (`tests/unit/utils/test_css_minifier.py`, `tests/unit/core/test_asset_processing.py`).
   There is no invariant that proves minification never changes meaning, which
   is exactly why #510 shipped.

## Goals

- **Correct by construction.** Whitespace/comment removal must never change the
  meaningful CSS token stream. The function-token vs `ident (` distinction is
  decided during tokenization, not guessed afterward.
- **One CSS engine.** A single subpackage owns all CSS string transforms;
  delete the duplicate minifiers and the core regex transforms.
- **Pure Python, zero runtime deps.** Honors the "pure Python default build
  path, zero npm" non-negotiable. No `lightningcss` at runtime.
- **Free-threading safe.** Stateless pure functions over `str -> str`; immutable
  token records; no module-level mutable state.
- **Extraction-ready.** `bengal/css/` depends on nothing bengal-specific except
  a thin diagnostics shim, so it can become a standalone PyPI package with a
  near-verbatim copy.
- **Provable quality.** Property-based round-trip invariants + a browser-grammar
  regression corpus + optional differential testing against `lightningcss`.
- **Tiered output.** A lossless `safe` default (parity with today's intent),
  opt-in value-level normalization, and an opt-in **structural** tier that is
  *cascade-invariant by construction* — it may never change which declaration
  wins for any element in any state.

## Non-Goals

- No npm, Node, PostCSS, or JS build phase.
- No autoprefixer / vendor-prefix injection (that is a transform, not minification;
  out of scope).
- No SCSS/Less compilation.
- **No cascade-changing optimization, ever — at any level.** The aggressive tier
  rewrites *structure*, never *resolution*: if any transform could change which
  declaration wins for some element/state, it is excluded from the safe-aggressive
  set (see catalog below). "Aggressive" means "does more work," not "takes risks
  with correctness."
- No new runtime dependency. `lightningcss` stays an optional **dev/bench-only**
  tool, as it already is in `tests/unit/test_no_dev_deps_in_production.py:31`.

## Prior art: rosettes & patitas (reuse the proven patterns)

Two sibling b-stack packages already solved the hard parts of "robust pure-Python
tokenize → parse → transform → serialize" pipelines, with the exact
free-threading discipline this RFC needs. The CSS engine should mirror them
rather than invent a new shape.

### rosettes (syntax highlighter) — borrow the *lexer discipline*

`rosettes/src/rosettes/lexers/_state_machine.py` is a hand-written state-machine
lexer framework whose stated design principles are a perfect fit:

- **Zero regex → no ReDoS.** "Crafted input cannot cause exponential backtracking
  because there IS no backtracking." A minifier ingesting arbitrary user CSS in a
  build wants exactly this safety property.
- **O(n) single pass, no backtracking** — predictable performance.
- **Thread-safe by construction**: `tokenize()` uses *only local variables*;
  shared character classes are frozen class attributes (`DIGITS`, `IDENT_START`,
  `WHITESPACE`, …). This is the same rule Bengal's Python guide mandates.
- **Reusable scanners**: `scan_while`, `scan_until`, `scan_string`,
  `scan_block_comment` — directly applicable to CSS strings, `url()`, and
  `/* */` comments.

What **not** to reuse: rosettes' existing `lexers/css_sm.py` is a *highlighting*
lexer. It classifies tokens for color (`NAME_CLASS`, `NAME_ATTRIBUTE`, …) using
look-ahead heuristics ("is the next non-space char a `:`? then it's a property"),
and it does **not** make the CSS-Syntax-L3 function-token distinction the minifier
depends on. So the CSS engine borrows rosettes' *framework and discipline* but
keeps its own spec-accurate token model. (Bengal already uses rosettes for the
*highlighting* path via `patitas.highlighting`; this RFC does not touch that.)

To stay extraction-ready and zero-dependency, **copy the ~100-line scanner
helpers** into `bengal/css/` rather than importing rosettes. They are tiny,
stable, and the standalone package must not pull in a highlighter.

`rosettes/src/rosettes/_parallel.py` also shows the "split at safe boundaries
(newlines) → tokenize chunks on 3.14t → ordered merge" pattern. For CSS this is
likely unnecessary (the asset pipeline already parallelizes *per file* in
`AssetOrchestrator`), but it is the reference if one giant bundled stylesheet ever
dominates a build.

### patitas (markdown parser) — borrow the *pipeline architecture*

Patitas is the blueprint for the whole `bengal/css/` shape:

| Patitas module | CSS engine analogue | Pattern to copy |
|---|---|---|
| `tokens.py` | `tokenizer.py` | Frozen `Token` dataclass + `TokenType` enum, immutable, source location, shareable across threads. |
| `parser.py` + `nodes.py` | `parser.py` (rule tree) | Lexer → parser → **frozen AST nodes with `slots` and tuple children**. |
| `visitor.py` | `structural.py` passes | Visitor walk over the tree for transforms. |
| `serialization.py` (+ round-trip tests) | serializer + `cascade.py` oracle | AST ⇄ data **round-trip as a correctness proof**. |
| `stringbuilder.py` | serializer output | O(n) list-append + single `join()` accumulator (no O(n²) concat). |
| `config.py` (ContextVar, immutable) | `MinifyLevel`/options | Immutable, ContextVar-scoped config; restore after work. |
| `incremental.py` / `differ.py` / `cache.py` | future incremental minify | Content+config-keyed caching; never cache when inputs aren't hashable. |
| `errors.py`, `protocols.py`, `py.typed` | `errors.py`, protocols | Typed public contract; structural protocols over concrete coupling. |

Patitas' steward rules also encode the contract hygiene this RFC should inherit:
frozen slotted AST nodes, immutable ContextVar config that is restored after
`parse()`, cache keys that include content + config, and "core must not import
orchestration." `bengal/css/` should hold the same line.

**Caveat — follow Bengal's Python floor, not the siblings' verbatim.** rosettes
and patitas still use `from __future__ import annotations` and target 3.12+;
Bengal is 3.14-floor and the project rule forbids `__future__` annotations. When
adapting, use Bengal's conventions: no `__future__`, `@dataclass(frozen=True,
slots=True)`, `X | None`, lowercase generics.

### Proof discipline to copy

Both repos already prove robustness the way this RFC's "s-tier proof" section
wants:

- rosettes `tests/properties/test_lexer_invariants.py` — Hypothesis invariants
  that must hold for **all** lexers/inputs. Our token round-trip and `resolve`
  cascade invariants are the CSS analogue.
- patitas `tests/test_serialization.py` — AST round-trip. Our serializer/parser
  round-trip mirrors it.
- rosettes `tests/security/` + `tests/edge_cases/` and patitas
  `tests/test_error_paths.py` — crafted/malformed input must degrade safely
  (our fail-safe "return input unchanged" rule).
- both have `tests/test_thread_safety.py` — required given the 3.14t target.

## Design

### Pipeline

```text
css: str
  └─ tokenize()         → tuple[Token, ...]      (CSS Syntax Level 3 §4)
       └─ parse_components() → component tree     (qualified rules, at-rules,
                                                   declarations, {}/()/[] blocks)
            └─ [Level 1: optimize_values()]       (opt-in, token-level)
                 └─ serialize_minified()          → str   (spec separator rule)
```

The two load-bearing ideas:

1. **Real tokenization** (`bengal/css/tokenizer.py`). Implement the
   [CSS Syntax Module Level 3 §4 tokenizer](https://www.w3.org/TR/css-syntax-3/#tokenization).
   Token kinds: `ident`, `function`, `at-keyword`, `hash`, `string`,
   `bad-string`, `url`, `bad-url`, `number`, `percentage`, `dimension`,
   `whitespace`, `CDO`, `CDC`, `colon`, `semicolon`, `comma`,
   `(` `)` `[` `]` `{` `}`, `delim`, and `comment` (kept as a kind so we can
   preserve `/*! … */` license comments). Because `ident` immediately followed
   by `(` is consumed as a **single `function` token**, `to (` and `to(` are
   *different token streams* — the #510 bug becomes impossible to emit.

2. **Spec-based minimal serialization** (`bengal/css/serializer.py`). Drop every
   `whitespace`/`comment` token, then re-insert a single separator **only when
   two now-adjacent tokens would otherwise merge or re-tokenize differently**,
   per the [CSS Syntax §9 "Serialization" adjacency rules](https://www.w3.org/TR/css-syntax-3/#serialization).
   This one table replaces the entire `needs_space_before` heuristic ladder and
   all the property frozensets. Examples it handles for free:
   - `ident` + `(` → keep separator (the #510 case, and `@scope … to (`).
   - `<percentage>`/`<dimension>`/`<number>` + a `-`-leading number → keep
     separator (covers `calc(100% - 20px)` without a `_CALC_FUNCTIONS` flag).
   - `ident` + `ident`, `number` + `ident`, `@keyword` + `ident`, `#` + `ident`,
     `ident` + `number`, etc. → keep separator where merging changes tokens.

### Why a thin parse layer is still required

Tokenization alone cannot tell *semantic* whitespace from *syntactic*
whitespace. A space inside a selector prelude can be a **descendant combinator**
(`.a .b` ≠ `.a.b`) that must survive, while a space inside a declaration value
or around `{`/`:`/`;`/`,`/`>`/`+`/`~` is removable. So we add a **lightweight
component-value parser** (`bengal/css/parser.py`) implementing the Syntax spec's
"consume a list of rules / declarations / component values" algorithms. It
classifies regions as:

- **at-rule prelude** (`@media …`, `@scope (…) to (…)`, `@supports …`)
- **qualified-rule prelude** (a selector list)
- **declaration value** (after `:`, before `;`/`}`)
- **`{}` / `()` / `[]` blocks** (recursively)

The serializer then applies region-aware rules:

- Selector preludes: collapse whitespace runs; drop whitespace around `> + ~` and
  `,`; keep exactly one space for the descendant combinator.
- Declaration values: drop whitespace except where the §9 separator rule
  requires it (calc `+`/`-`, `font: x/y family`, `grid` slashes, etc. all fall
  out of the same rule — no per-property lists).
- **Custom properties (`--x:`) and `var()` fallbacks: preserve the value token
  stream verbatim** (trim only outer whitespace). Custom-property values are an
  arbitrary token soup that can be substituted into any context, so we must not
  normalize inside them.

This replaces `_MULTI_VALUE_PROPS`, `_FUNCTION_LIST_PROPS`, `_SLASH_PROPS`,
`_CALC_FUNCTIONS`, `_VALUE_KEYWORDS`, `_CSS_UNITS`, and `needs_space_before`
entirely with principled, spec-traceable rules.

### Output levels

```text
level="safe"       (default)  lossless: tokenize + structural WS/comment removal
level="optimize"   (opt-in)   safe + token-level value normalization
level="aggressive" (opt-in)   optimize + cascade-invariant structural rewrites
```

Each level is a strict superset of the one below it. All three are
meaning-preserving; they differ only in how much work they do.

**Level "safe"** — strictly meaning-preserving whitespace/comment removal.
Replaces today's behavior. Preserves `/*! … */` license comments. This is the
only level enabled by default, so shipping the rewrite changes *correctness*,
not output policy.

**Level "optimize"** — token-level value normalizations that every mature
minifier does and that are safe outside custom properties:

- lowercase hex colors; `#aabbcc` → `#abc` when collapsible; `#ffffff` → `#fff`
- leading-zero strip `0.5` → `.5`; trailing-zero strip `1.50` → `1.5`
- unitless zero `0px` → `0` (with the known exceptions: not inside `calc()`,
  keep unit for `<time>` like `0s` where required, keep for flex-basis/`0%` edge
  cases — encoded as explicit, tested carve-outs)
- collapse `rgb(255,0,0)`/`rgba(…,1)` → hex when shorter
- normalize string quotes; drop redundant quotes in `url("…")`
- never touches `--x:` declarations, `var()` values, or `content:` strings

**Level "aggressive"** — structural rewrites on the parsed rule tree. This is the
cssnano-class tier, but the membership rule is strict: **a transform is only in
the aggressive set if it is provably cascade-invariant** (it cannot change which
declaration wins for any element in any media/container/state context). Each
transform is an individually-toggleable pass with its own cascade-safety argument
and its own proof against the structural oracle (below).

Transform catalog, split by what is safe vs. what is deceptively unsafe:

| Transform | In aggressive set? | Cascade-safety reasoning |
|---|---|---|
| Remove empty rules `.a{}`, empty `@media{}` | ✅ yes | An empty block contributes no declarations; removal is observationally null. |
| Remove **exact-duplicate** declarations (same property *and* value) within a rule | ✅ yes | The winner is unchanged; only a redundant copy is dropped. |
| Merge **adjacent** rules with identical selector lists | ✅ yes (order-preserving) | No rule sits between them in source order, so relative cascade order of all properties is preserved. |
| Merge **adjacent** rules with identical declaration blocks into one selector list (`.a,.b{…}`) | ✅ yes | Adjacent + identical body ⇒ no intervening cascade, no specificity change per selector. |
| Merge **adjacent** identical `@media`/`@supports`/`@layer`/`@container` preludes | ✅ yes | Same prelude, adjacent ⇒ inner rule order preserved. |
| Normalize selector internals (whitespace, casing of known-ci parts) | ✅ yes | Pure serialization; same matched set. |
| Remove **earlier** duplicate property with a *different* value (`display:flex;display:grid`) | ❌ **excluded** | This is a deliberate browser-fallback pattern; dropping the earlier value breaks old browsers. Unsafe. |
| Merge longhands → shorthand (`margin-top/right/...` → `margin`) | ❌ excluded (research) | Shorthand resets omitted sub-properties; partial/`!important`/`var()`/`inherit` cases change meaning. Off unless a fully-specified, proven subset is added later. |
| Merge **non-adjacent** rules | ❌ excluded | An intervening rule may change resolution; requires full specificity+order analysis. Off. |
| Drop declarations "overridden" by a later rule | ❌ excluded | Specificity, media/container scope, and pseudo-state make this unsafe in general. Off. |

The dividing line is **adjacency + identity**: order-preserving merges of
adjacent, structurally-identical constructs are cascade-invariant; anything that
reasons across non-adjacent rules or rewrites override relationships is excluded
(or deferred behind a separately-proven, narrowly-specified subset). This keeps
the aggressive tier genuinely safe for documentation sites while still capturing
the bulk of cssnano's real-world savings (empty-rule + exact-dedup + adjacent
merge dominate typical size wins).

Must-preserve regardless of level: `@layer` order, `@scope`/`@container`
boundaries, native nesting structure, custom-property declarations and `var()`
values verbatim, `!important`, and source order of any two declarations that can
both apply to the same element.

### Module layout (extraction-ready)

```text
bengal/css/
  __init__.py        # public API: minify_css, tokenize, MinifyLevel
  _scanners.py       # scan_while/until/string/block_comment (copied from rosettes)
  tokenizer.py       # CSS Syntax L3 tokenizer; frozen Token records (patitas tokens.py shape)
  parser.py          # component-value / rule / declaration parser → frozen rule tree
  nodes.py           # frozen, slotted AST nodes with tuple children (patitas nodes.py shape)
  serializer.py      # minimal-whitespace serializer (§9 separator rule) + StringBuilder
  stringbuilder.py   # O(n) accumulator (copied from patitas/kida)
  optimize.py        # Level "optimize" value normalizations (token-level)
  structural.py      # Level "aggressive" rule-tree passes (cascade-invariant, visitor)
  cascade.py         # structural correctness oracle (resolution model)
  config.py          # immutable, ContextVar-scoped options (patitas config.py shape)
  protocols.py       # structural contracts (patitas protocols.py shape)
  errors.py          # adapter → BengalError (the ONLY bengal coupling)
  py.typed
```

The aggressive tier reuses the same parser: the component-value/rule tree the
serializer already needs is exactly the structure `structural.py` rewrites. No
separate AST — one tree, two consumers.

The only bengal-specific import inside `bengal/css/` is `errors.py` (and a
diagnostics callback). Everything else is plain stdlib. Extraction to a
standalone package = copy the tree, swap `errors.py` for a local exception, add
a `pyproject.toml` and a CLI. Frozen `@dataclass(slots=True)` tokens, no
`from __future__ import annotations` (3.14 floor), immutable `tuple` token
sequences per the project Python rules.

### Public API (stable surface)

```python
from bengal.css import minify_css  # str -> str, default level="safe"

minify_css(css)                      # lossless
minify_css(css, level="optimize")    # smaller, still safe
```

Keep `bengal.assets.css_minifier.minify_css` as a thin re-export shim during
migration so existing callers/tests (`asset_core.py:421`, the script corpus, and
`tests/unit/utils/test_css_minifier.py`) keep working, then migrate and
deprecate. **Public-API + config additions are stop-and-ask** (see below).

## Correctness & proof strategy

This is the part that makes it "s-tier": the design is validated by *invariants*,
not just examples.

1. **Round-trip token invariant (Hypothesis, primary oracle).**
   For input `css`, `tokenize(minify_css(css))` must equal `tokenize(css)` after
   dropping `whitespace`/`comment` tokens **and** collapsing the descendant
   combinator to a canonical marker. If minification ever changes the meaningful
   token stream, the property fails. This single invariant catches the entire
   `to(` class automatically (`to (` vs `to(` tokenize differently).
2. **Idempotence.** `minify_css(minify_css(css)) == minify_css(css)`.
3. **Browser-grammar regression corpus** (golden tests). Encode every known
   sharp edge: `@scope (…) to (…)`, `@layer`, native nesting `&`, `calc/clamp/min/max`
   with `+ -`, descendant vs compound selectors, `[attr = "x"]`, `:is()/:where()/:has()`,
   `:nth-child(2n + 1)`, container & style queries, `@supports (display: grid)`,
   `unicode-range`, unquoted `url()`, `data:` URIs, custom properties + `var()`,
   `!important`, font shorthand `12px/1.5 sans`, grid `1 / 2`.
4. **Real-CSS corpus.** Run against `bengal/themes/default/` CSS and the chirpui
   envelope CSS; assert no token-stream drift and record size deltas.
5. **Differential vs `lightningcss`** (optional, dev/bench only). When installed,
   compare token-equivalence and output size as a *quality* signal (not a CI
   correctness gate — both make different valid choices).
6. **Fail-safe behavior.** On any internal error, return the input unchanged and
   emit a diagnostic (mirrors `asset_core.py:426`'s fail-safe). The minifier must
   never be able to *corrupt* output — worst case is "not minified."

### Structural correctness oracle (cascade equivalence)

The token round-trip invariant validates `safe`/`optimize` but **cannot** validate
`aggressive`, because structural rewrites change the token stream by design. The
aggressive tier needs a stronger oracle: **observable cascade equivalence.**

Define `resolve(stylesheet)` (in `cascade.py`) that flattens the rule tree into a
canonical model of *what the browser would resolve*, independent of structure:

```text
resolve(s) = {
  (at_rule_context, selector, property) -> (value, important, order_rank)
  for every declaration, with order_rank capturing source position
}
```

where `at_rule_context` is the ordered stack of enclosing `@media`/`@supports`/
`@layer`/`@scope`/`@container` preludes, `selector` is the normalized individual
selector (selector lists expanded to one entry per selector), and `order_rank`
preserves the relative source order of declarations that can co-apply.

The aggressive invariant: **`resolve(css)` == `resolve(minify_css(css, level="aggressive"))`.**

This is the real proof. It catches any transform that would change which
declaration wins — including the deceptively-unsafe ones in the exclusion table
(fallback-duplicate removal and non-adjacent merge both perturb `resolve`, so the
property fails if someone implements them carelessly). Each structural pass is
proven three ways:

1. **Unit**: hand-written before/after pairs per pass.
2. **Hypothesis**: generate random rule trees, assert `resolve` is preserved
   across each pass and across the full `aggressive` pipeline; also assert
   idempotence.
3. **Real corpus + differential**: run the default theme + chirpui CSS, assert
   `resolve` unchanged, and compare size against `lightningcss`/cssnano output as
   a *quality* signal (how close do we get with only the cascade-safe subset?).

`resolve` is the contract that lets "aggressive" stay genuinely safe: a transform
is allowed into the aggressive set only when it provably preserves `resolve` for
all inputs, not just the corpus.

## Performance

- One O(n) tokenize pass + one O(n) serialize pass; the parser is O(n) over
  tokens. Comparable big-O to today, with far fewer per-character branches.
- Add a `benchmarks/` entry: throughput (MB/s) and output-size ratio vs the old
  minifier and vs `lightningcss`, on the default theme CSS. Performance claims
  in the PR cite this benchmark (Performance steward requirement).
- Pure functions → trivially parallel-safe; no shared cache needed. If profiling
  later justifies caching, use a leaf-locked LRU keyed on content hash (never
  `@cache` on a function with shared state).

## Migration / consolidation plan

Staged so production is never left broken and each commit is independently
reviewable.

### Phase 0 — Interim correctness patch (ship first, P1)

Land the issue's targeted fix in the *existing* minifier so deployed sites stop
dropping `@scope` blocks while the rewrite is built: never collapse whitespace
between an `@scope`/`to` token and a following `(`. Add a regression test
mirroring #510. This is throwaway once Phase 2 lands; keep it tiny.

### Phase 1 — `bengal/css/` engine (no behavior switch yet)

Tokenizer + parser + serializer + `level="safe"`. Full proof suite (invariants +
corpus). Not yet wired into the build. Ships behind its own tests so it can be
reviewed in isolation.

### Phase 2 — Cut over the asset pipeline

Point `asset_core.py:_minify_css` (`asset_core.py:399`) at `bengal.css.minify_css`.
Make `bengal/assets/css_minifier.py:minify_css` a thin re-export. Delete the
Phase 0 patch (now redundant). Validate the default theme + chirpui build byte
parity / token parity. **`transform_css_nesting` decision point** (stop-and-ask):
native CSS nesting is browser-baseline (2023+); either (a) drop the regex
nesting transform entirely, or (b) reimplement nesting expansion correctly on
the parser. Recommend (a) with a deprecation note unless we still support old
targets — needs maintainer call because it changes emitted CSS.

### Phase 3 — Retire duplicates & core regex transforms ✅ DONE (2026-06-16)

`bengal/core/asset/css_transforms.py` was deleted (`lossless_minify_css`,
`remove_duplicate_bare_h1_rules`, `transform_css_nesting`) and the
`bengal/assets/css_minifier.py` re-export shim removed. All callers (asset
pipeline, tests, scripts) now import `minify_css` from `bengal.css` directly.
The `transform_css_nesting` decision resolved to **option (a)**: drop the regex
nesting transform and preserve native CSS nesting (Baseline 2023). Optional
AST-based flattening for legacy targets is tracked in #516. This burns down the
Core-steward transitional debt (CSS string rewriting left `bengal/core/`).

### Phase 4 — `level="optimize"` (value normalization)

Add the token-level value normalizations behind `level="optimize"`, proven by the
token round-trip invariant (only value *spelling* changes, never value *identity*;
carve-outs are tested). Opt-in.

### Phase 5 — `level="aggressive"` (structural, cascade-invariant)

Build `structural.py` + `cascade.py`. Implement the aggressive-set transforms one
pass at a time (empty-rule removal → exact-dedup → adjacent same-selector merge →
adjacent identical-body selector merge → adjacent at-rule merge), each gated by
the `resolve` oracle and Hypothesis. Excluded transforms (fallback-dup removal,
longhand folding, non-adjacent merge) stay out unless/until a narrowly-specified,
separately-proven subset is justified. Opt-in only.

### Config exposure (with Phase 4/5) — stop-and-ask

If any level is exposed via config (`[assets] css_minify_level` or similar), that
is a **new public config key → stop-and-ask**. Default stays `safe`; `minify =
true` keeps meaning "safe" unless the user explicitly opts into a higher level.

### Phase 6 (optional, separate decision) — Extract standalone package

If we want it outside Bengal, copy `bengal/css/`, swap `errors.py`, add packaging
+ a CLI, and have Bengal depend on it (or vendor it). Naming TBD (bikeshed; the
project's menagerie convention suggests an animal/short codename). Internal-first
per the 2026-06-16 decision; no early spin-out.

## Stop-and-ask checklist (per AGENTS.md)

- [x] New public subpackage `bengal/css/` and its API surface (public contract).
- [x] Changing/removing `transform_css_nesting` emitted output — resolved to drop
      the regex transform; native nesting preserved (legacy flatten → #516).
- [ ] Any new config key for minify level (Phase 4/5).
- [ ] Shipping the `aggressive` structural tier (cascade-rewriting output change).
- [ ] Extraction into a standalone distributed package (Phase 6).
- [ ] Confirm `lightningcss` stays dev/bench-only (no runtime dep added).

## Alternatives considered

1. **Just patch `to(` (the issue's suggestion).** Fastest, but leaves the bug
   class open and adds another special case to an already-overfit heuristic.
   Adopted only as the throwaway Phase 0 stopgap.
2. **Adopt `lightningcss` (Rust) as the minifier.** Best-in-class output, but
   it is a compiled dependency that violates the "pure Python default build path"
   non-negotiable and would gate normal builds on prebuilt wheels. Keep it as an
   optional differential-test oracle only.
3. **Port `rcssmin`/`csscompressor`.** `rcssmin` is fast but a regex token-soup
   minifier with the same class of edge-case risks and is conservative on modern
   syntax; `csscompressor` is unmaintained. Building our own tokenizer gives us a
   correctness oracle and an extractable asset we control.
4. **Full cssnano-class optimizer with *unsafe* defaults.** cssnano's "advanced"
   preset does cross-rule dedup, longhand folding, and override elimination that
   can change resolution if assumptions break. We adopt the cssnano *idea*
   (structural tier) but restrict membership to the cascade-invariant subset and
   prove it with the `resolve` oracle, rather than copying its riskier passes.
   This is the chosen aggressive design, not a rejected alternative.

## Open questions

- ~~Keep or drop `transform_css_nesting`~~ — resolved: dropped, native nesting
  preserved; optional AST flatten tracked in #516.
- Should any level above `safe` ever become the default, or stay always-opt-in?
- Is there a justified, fully-specified longhand→shorthand subset worth adding to
  the aggressive set later (proven by `resolve`), or is it permanently excluded?
- Should the serializer preserve the *first* license comment only, or all `/*! */`?
- Naming for the eventual standalone package (Phase 6 bikeshed).

## Proof commands (when implemented)

```bash
uv run pytest tests/unit/css/ -q                 # engine unit + invariants
uv run pytest tests/unit/css/test_minify_props.py -q   # hypothesis round-trip
uv run poe proof-pr                              # lint, format, ty, units, bench-smoke
uv run poe lint-imports                          # bengal/css/ import boundary
python benchmarks/css_minify_bench.py            # throughput + size vs old/lightningcss
```

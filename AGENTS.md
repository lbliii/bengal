# AGENTS.md

Bengal builds the sites people read documentation on. Bugs you introduce here reach end users through someone else's content — readers who can't see Bengal, can't audit it, and notice only when a link breaks, a code block renders wrong, or a search index goes empty. Treat the rules below as safety rules, not style rules.

---

## North star

**Make free-threaded Python worth deploying for content tooling.** Bengal exists to prove that a documentation generator can be pure Python, scale with cores on 3.14t, and ship zero npm. Every decision routes back to that: parallelism that's real, a Python stack you can read, performance you can measure. If a change doesn't serve that goal, it isn't worth shipping.

---

## Design philosophy

- **Pure Python is a constraint.** No npm, no Node, no JS toolchain. The whole B-stack (Patitas, Rosettes, Kida, Pounce, Milo) exists to make that viable — keep it that way. Faster path = better Python.
- **Core is passive.** `bengal/core/` does no I/O and no logging. Use the diagnostics sink (`emit(self, "warning", ...)`), not loggers. Orchestration coordinates; core models hold state. Rendering services derive presentation: HTML, excerpts, template URLs, and content views belong under `bengal/rendering/`, with core keeping only compatibility shims where callers already depend on them.
- **Immutable pipelines.** `SourcePage → ParsedPage → RenderedPage` is frozen on purpose. Mutation in the pipeline is a thread-safety bug waiting for 3.14t to find it. Don't add setters to `*Page` records.
- **Atomic writes everywhere.** `bengal.utils.io.atomic_write_text` / `atomic_write_bytes` / `json_compat.dump`. A crash mid-build must not corrupt outputs.
- **Sharp edges are bugs.** Silent `except`, `# type: ignore`, ambiguous flags, unhelpful errors, fuzzy "did you mean" omitted — not taste, bugs. Use `BengalError` with `code`, `context`, `suggestion`, `debug_payload`.
- **PEP 758 except syntax is correct.** `except OSError, ValueError:` is Python 3.14+ multi-catch. Do not "fix" to `except (OSError, ValueError):` — ruff will reformat it back. Wasted significant effort on this once.

---

## Stakes

When you change something in Bengal, the blast radius is:

- **Rendering bugs** (markdown, templates, syntax highlighting, xrefs) → wrong content shipped to readers, broken anchors, leaked template syntax. Often invisible to the author until someone reports it.
- **Incremental build bugs** (provenance, cache keys, dependency tracking) → stale pages survive a rebuild. The site looks built, the content is wrong. The author trusts the build and doesn't notice.
- **Free-threaded races** (3.14t, no GIL) — Bengal is a canary for the ecosystem. A race we ship normalizes "free-threading is flaky" for everyone. Shared mutable state in rendering, effects, or cache is the danger zone.
- **Plugin contract breaks** → 9 extension points, third-party plugins discovered via `bengal.plugins` entry-point. Changing the `Plugin` protocol or any of the 9 hook surfaces breaks people you'll never meet.
- **Performance regressions** → "scales with cores" and "sub-second rebuilds" are load-bearing claims. CI doesn't catch a 20% regression in the orchestration hot path. You do.

Bengal is alpha but published on PyPI and used. Calibrate accordingly.

---

## Current architecture spine

The current shape to preserve:

- `SourcePage → ParsedPage → RenderedPage` records are the immutable pipeline. They are not the place for convenience fields, late mutation, or plugin-specific state.
- `Page` is a compatibility surface for templates and older callers, not a renderer. Template-facing properties such as `content`, `html`, `plain_text`, `toc_items`, `excerpt`, `meta_description`, `href`, `_path`, and `absolute_href` should delegate to rendering-side helpers.
- `Site` coordinates through registries, services, and orchestration. It should not reacquire forwarding wrappers just because an internal service exists.
- `Section` still has legacy core mixins on the allow-list. Treat them as audit debt, not precedent.
- Rendering owns parser, template, shortcode, AST/HTML, and URL presentation behavior. Core may call into rendering lazily from a compatibility shim; it should not import rendering helpers at module load time.
- Protocols and plugin hooks are public contracts. Prefer internal adapters or rendering services over widening `SiteLike`, `PageLike`, or `Plugin`.

---

## Who reads your output

- **Site authors** — want `bengal serve` to just work and the traceback to tell them which file broke. They read errors, the dev server output, and `--help`.
- **Plugin developers** — read protocol definitions in `bengal/protocols/`, the `Plugin` framework, and entry-point examples. Stability of these surfaces is the contract.
- **Contributors** — know Python and markdown, not our internals. They read `bengal/core/`, `bengal/orchestration/`, and the CONTRIBUTING / THREAD_SAFETY guides.
- **Me (Lawrence)** — read diffs. Put the what in code, the why in the PR.

---

## Escape hatches — stop and ask

Forks where I want a check-in, not a judgment call:

- **Reintroducing a mixin in `bengal/core/`.** Site and Page are mixin-free after epic-delete-forwarding-wrappers and the Page boundary cleanup. `tests/unit/core/test_no_core_mixins.py` enforces the remaining `LEGACY_MIXINS` allow-list for Section only. Adding to that list, or adding new core mixins, needs a check-in.
- **Moving a deferred import to module level.** Bengal has multiple deferred-only import cycles. The `check-cycles` pre-commit hook catches some; not all. If you see `from bengal.X import Y` inside a function and want to hoist it, run check-cycles first and ask.
- **Touching the immutable page pipeline.** `SourcePage` / `ParsedPage` / `RenderedPage` are frozen on purpose. Adding fields, mutability, or new pipeline stages is a design conversation, not a patch.
- **Changing the `Plugin` protocol or any of the 9 extension points.** Public surface; breaks unknown third parties. Sketch the change first.
- **Public API change** (`bengal` CLI commands/flags, `bengal.plugins` entry-point shape, `BengalError` constructor). Ask whether the break is worth it.
- **New runtime dependency.** Default is no. The B-stack is deliberately small. Reach for an existing dep, then ask.
- **New config option.** Reshape an existing one first. Configs are easier to add than to remove.
- **Chasing ty diagnostics below the floor (~570).** Remaining ones are ty checker limitations, optional dependency modeling, structural matching, hasattr narrowing, or protocol/test-double mismatches. Don't expand `SiteLike` — it backfires because test mocks don't implement new attrs. Ask before opening a "reduce ty diagnostics" branch.
- **Refactoring methods on Site/Page/Section.** Run each through the greenfield-design test (see `feedback_domain_facets_vs_vestiges`): would you name it this, here, designing fresh? If no → it's a vestige, delete + migrate callers, don't relocate. Ask before opening a "reorganize" PR.
- **Test disagrees with code.** Ask which is authoritative before "fixing" either.
- **Can't reproduce a reported bug.** Stop. Ask for a minimal repro (a `tests/roots/` fixture is ideal). Don't guess.
- **Adjacent issues found mid-task.** List in the PR description. Don't fold them in — exception: refactors renaming a concept across many files, where one bundled PR beats review churn.

---

## Anti-patterns

Things that look reasonable and are wrong here:

- **Adding npm/JS to the build path.** No. The whole point is a pure-Python content stack.
- **Reintroducing core mixins.** PR #194 dissolved Site mixins deliberately over 10+ commits, and Page mixins have since been dissolved. Section legacy mixins are allow-listed pending audit — not an invitation to add more.
- **Moving rendering behavior back into Page.** Page may keep template-facing compatibility properties, but the work behind rendered content, excerpts, meta descriptions, shortcode checks, link extraction, TOC structures, and template URLs belongs in `bengal/rendering/`.
- **`try: ... except Exception: pass`.** S110 is enabled. If you must swallow, log via diagnostics with what + why.
- **Wrapping `except A, B:` in parens.** Valid PEP 758 syntax in 3.14+. Ruff will undo your "fix."
- **`# type: ignore` to clear a ty diagnostic.** Floor is ty-limitation territory. Either narrow the type properly or leave it; don't ignore.
- **Speculative config options.** If no one's asking for it, don't add it. The surface is already wide.
- **Defensive validation inside core.** `bengal/core/` trusts callers and stays passive (no I/O, no logging). Validate at the boundary.
- **Hoisting deferred imports without testing.** Will trigger circular imports. Run `check-cycles` before assuming a deferred import is "just" defensive.
- **Surface-level refactors.** ~50% of "obvious" simplifications turn out to break callers (functools.partial vs nonlocal, base classes vs Kida `??` semantics, config merge vs immutability). Trace the actual call paths before committing.
- **Direct `logger.X` inside `bengal/core/`.** Use `from bengal.core.diagnostics import emit` instead. Decoupling core from logging infra is load-bearing.
- **Non-atomic file writes.** Every output write in Bengal is atomic for crash safety. Don't open a file and write directly — use the helpers.
- **Refactoring during a bug fix.** Separate PR. Exception: the refactor *is* the fix.

---

## Extending Bengal

Four extension points. Pick the one that matches your need. If none fit, ask before changing the `Plugin` protocol or any of the 9 hook surfaces (`bengal/protocols/`) — see "Escape hatches."

### 1. Template function or filter

**When:** You need a new Jinja filter or global usable in `.html` templates (e.g. `{{ posts | my_sort }}`).

**Where:** Add a module under `bengal/rendering/template_functions/`. Each module exports a `register(env, site)` function and is wired into `register_all()` in that package's `__init__.py`. No decorator, no auto-discovery — append your `register()` call to the coordinator.

```python
# bengal/rendering/template_functions/my_funcs.py
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bengal.protocols import SiteLike, TemplateEnvironment

def register(env: TemplateEnvironment, site: SiteLike) -> None:
    env.filters["my_filter"] = lambda v: v.upper()
```

Then add `my_funcs.register(env, site)` to the appropriate phase in `register_all()`. Canonical example: `bengal/rendering/template_functions/strings.py`.

### 2. Content type strategy

**When:** A section needs custom sorting, pagination, filtering, or template defaults that built-in `content_type` strategies (`blog`, `doc`, `tutorial`, `changelog`, `archive`, `notebook`, `track`, `page`, `autodoc-python`, `autodoc-cli`) don't cover.

**Fastest path:** `bengal new content-type <name>` — scaffolds a `ContentTypeStrategy` subclass in the right place with `When to use:`, `default_template`, `allows_pagination`, `sort_pages()`, `detect_from_section()`, and the `register_strategy()` call already wired up. Then edit the TODOs.

**Manual path** (or to understand what the scaffold gives you): subclass `ContentTypeStrategy` from `bengal/content_types/base.py`, register the instance via `register_strategy()` from `bengal/content_types/registry.py`. Built-in strategies live in `bengal/content_types/strategies.py` — read `BlogStrategy` first, it's the canonical short example.

```python
from bengal.content_types import ContentTypeStrategy, register_strategy

class RecipeStrategy(ContentTypeStrategy):
    default_template = "recipes/list.html"
    allows_pagination = True
    def sort_pages(self, pages):
        return sorted(pages, key=lambda p: p.metadata.get("difficulty", 99))

register_strategy("recipe", RecipeStrategy())
```

Sections opt in by setting `type = "recipe"` in their `_index.md` frontmatter, or by `detect_from_section()` returning `True`.

### 3. CLI command

**When:** A new `bengal <verb>` operation — top-level command or subcommand under an existing group (`config`, `theme`, `content`, `version`, etc.).

**Where:** Write a function in `bengal/cli/milo_commands/`, then register it in `bengal/cli/milo_app.py` via `cli.lazy_command(...)`. There is **no filesystem auto-discovery** — the file has to be wired in `milo_app.py` to be reachable.

```python
# bengal/cli/milo_commands/hello.py
from __future__ import annotations
from typing import Annotated
from milo import Description

def hello(name: Annotated[str, Description("Who to greet")] = "world") -> dict:
    """Say hi."""
    return {"status": "ok", "message": f"hello, {name}"}
```

Then in `bengal/cli/milo_app.py`:

```python
cli.lazy_command(
    "hello",
    import_path="bengal.cli.milo_commands.hello:hello",
    description="Say hi",
)
```

**Milo ≠ Click — three things to know**:

- **Args:** `Annotated[type, Description("...")]` parameters with defaults — not `@click.option` decorators stacked above the function.
- **Discovery:** explicit `cli.lazy_command(name, import_path="module:fn")` in `milo_app.py`. Lazy import avoids the cold-start tax; the function isn't loaded until the command runs.
- **Output:** commands return `dict`. Milo handles structured output, MCP serialization, and `--json` for free. Don't `print()` — use `cli.render_write(template, ...)` for human output and the dict return for machine output.

Canonical example: `bengal/cli/milo_commands/clean.py` — small, real, exercises the full pattern (annotated args, dict return, `cli.error()` / `cli.tip()` for failure paths).

### 4. Build phase

**When:** You think you need to insert a custom step into the build pipeline.

**Where:** You don't. Build phases are hardcoded in `bengal/orchestration/build/__init__.py` — 21 numbered phases, called sequentially. Adding one is a design conversation, not a patch (see "Escape hatches").

**For observability** (timing, progress reporting): use `BuildOptions.on_phase_start` / `on_phase_complete` callbacks.

**For behavior changes mid-build**: use one of the 9 plugin hook surfaces in `bengal/protocols/` — those *are* the supported extension surface. Custom orchestration phases bypass the plugin contract and free-threading guarantees.

---

## Done criteria

A change is done when all of these hold:

- [ ] `make test` passes (fast tests). Hot-path / threading change → also `pytest -m "not performance"` or the relevant marker.
- [ ] `make ty` doesn't regress the diagnostic floor. No new `# type: ignore` or `noqa: S110` suppressions.
- [ ] `ruff format` + `ruff check --fix` clean.
- [ ] Tests exercise the *interesting* path: both branches of a config flag, the failure path for incremental rebuild, malformed input for parsers/templates.
- [ ] Free-threading sensitive? Note what shared mutable state you considered. If you added a global, it's locked or justified.
- [ ] User-facing change under `bengal/` → news fragment in `changelog.d/<issue-or-branch>.<type>.md`. `make changelog-check` confirms.
- [ ] Public API or plugin protocol changed → migration note in the PR, news fragment marked `changed` or `removed`.
- [ ] Error messages tell the reader what to do next, not just what went wrong. `BengalError` with `suggestion=` is the standard.
- [ ] `check-cycles` passes — no new import cycles introduced.
- [ ] PR description explains *why*. The diff explains what.

"Tests pass" is not "done." Tests pass on broken code all the time.

---

## Review and assimilation

- **I read diff-first, description-second.** Tight diff + clear why merges fast; sprawling diff gets questions.
- **One concern per PR.** If the diff needs section headers, it's two PRs. Exception: refactors renaming a concept across many files — one bundled PR beats review churn.
- **Commit style:** see `git log`. `<scope>: <description>` — scope is `core` / `orchestration` / `rendering` / `cache` / `cli` / `tests` / `docs` / `deps` / `release`. Imperative. Multi-area: separate with `;`.
- **Don't trailing-summary me.** If the diff is readable, I can read it.
- **Flag surprises.** Weird test, unused config, dead code, an allow-list that grew — put it in the PR description. Don't fix silently, don't ignore.
- **Dead code you found.** Flag in the PR, let me decide. Bengal has had vestiges from prior extractions (ConfigService, PageCacheManager, PageProxy — finally deleted in #200) that lingered. Most are deletable; some are load-bearing for a transport, plugin, or example.

---

## When this file is wrong

It will be. Tell me. The worst outcome is that it sits here for a year contradicting how the project actually works. Updates to AGENTS.md are a first-class PR — short, focused, and welcome.

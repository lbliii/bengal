# Bengal Agent Constitution

Bengal builds the sites people read documentation on. Bugs here reach end users
through someone else's content: broken links, wrong code blocks, stale pages,
empty search indexes. Treat these as safety rules, not style rules.

## North Star

Make free-threaded Python worth deploying for content tooling. Bengal should
prove that a documentation generator can be pure Python, scale with cores on
3.14t, and ship zero npm. Favor readable Python, real parallelism, measurable
performance, and user-visible correctness.

## Non-Negotiables

- **Pure Python:** no npm, Node, or JS toolchain in the build path.
- **Core is passive:** `bengal/core/` does no I/O and no direct logging. Use
  diagnostics such as `emit(self, "warning", ...)`.
- **Rendering owns presentation:** HTML, excerpts, TOCs, template URLs,
  shortcode/link extraction, page bundle views, and section URL ergonomics
  belong under `bengal/rendering/`.
- **Pipeline records are immutable:** `SourcePage -> ParsedPage -> RenderedPage`
  stay frozen. Do not add setters, plugin state, or late mutation.
- **Writes are atomic:** use `atomic_write_text`, `atomic_write_bytes`, or
  `json_compat.dump` for outputs and caches.
- **Sharp edges are bugs:** no silent `except`, no casual `# type: ignore`, no
  vague flags, no errors that fail to say what to do next.
- **PEP 758 syntax is valid here:** `except OSError, ValueError:` is correct
  Python 3.14+ multi-catch. Do not wrap it in parentheses.

## Architecture Boundaries

- `Page`, `Section`, and `Site` are compatibility surfaces and coordinators, not
  dumping grounds for rendering or forwarding wrappers.
- `Page` template-facing properties may remain as shims, but should delegate to
  rendering helpers.
- `Section` stays mixin-free. URL and theme/navigation ergonomics delegate to
  rendering-side helpers.
- `Site` coordinates registries, services, and orchestration. Do not rebuild old
  forwarding layers around it.
- `bengal/protocols/` and plugin hooks are public contracts. Prefer adapters or
  internal helpers over widening `SiteLike`, `PageLike`, `SectionLike`, or
  `Plugin`.

## Stakes

- Rendering bugs ship wrong content to readers.
- Incremental bugs leave stale pages that authors trust.
- Free-threading races make 3.14t look flaky.
- Plugin contract breaks affect third-party extensions discovered through
  `bengal.plugins`.
- Performance regressions weaken Bengal's "scales with cores" claim.

Bengal is alpha, published on PyPI, and used. Calibrate accordingly.

## Stop And Ask

Check in before doing any of these:

- Reintroducing core mixins or growing the empty mixin allow-list.
- Hoisting a deferred import to module level. Run `check-cycles` first.
- Touching immutable pipeline records or adding a pipeline stage.
- Changing `Plugin`, any of the 9 hook surfaces, CLI flags/commands,
  `bengal.plugins` entry points, or `BengalError` construction.
- Adding a runtime dependency, config option, or build phase.
- Chasing ty diagnostics below the floor around 570.
- Reorganizing methods on `Site`, `Page`, or `Section` instead of deleting
  vestiges and migrating callers.
- Fixing a test/code disagreement without knowing which one is authoritative.
- Guessing at an unreproduced bug. Ask for a minimal repro, ideally a
  `tests/roots/` fixture.
- Folding adjacent issues into a bug fix. Flag them for the PR instead.

## Anti-Patterns

- Adding npm or JS tooling to make the frontend path easier.
- Moving rendering behavior back into core.
- `try: ... except Exception: pass`; if swallowing is intentional, emit a
  diagnostic with what and why.
- `# type: ignore` or `noqa: S110` to clear noise.
- Defensive validation inside core instead of at boundaries.
- Direct `logger.X` inside `bengal/core/`.
- Non-atomic output or cache writes.
- Refactoring during a bug fix unless the refactor is the fix.

## Steward System

Read this root file plus the closest scoped `AGENTS.md` before editing a tree.
The root is the constitution; scoped files are stewards for concrete domains.

Keep root guidance for rules that apply everywhere: north star, safety
invariants, public escape hatches, extension routing, done criteria, and steward
consultation. Move directory-specific ownership, refusal patterns, examples,
docs, and local checks into the nearest scoped steward.

Each steward should be able to answer:

- **Point of view:** who or what the domain represents.
- **Protect:** invariants, contracts, quality bars, and failure modes.
- **Advocate:** features, fixes, and investments the domain should push for.
- **Serve peers:** upstream and downstream domains that need clearer contracts,
  diagnostics, docs, tests, or ergonomics from this domain.
- **Own:** tests, docs, examples, fixtures, and maintenance chores that keep the
  domain truthful.

Stewards may represent product perspectives, such as documentation quality or
default-theme UX, but they still protect a concrete tree. They do not override
the implementation steward that owns an affected code boundary.

When work crosses steward areas, add `Steward Notes` to the PR description:
name each area and one sentence about how its invariants were protected.

### When To Consult

Consult stewards proactively when a change is cross-boundary, public-facing,
hard to reverse, performance-sensitive, free-threading-sensitive, or likely to
change docs, tests, fixtures, template context, cache keys, plugin contracts, or
build outputs.

Use the nearest steward for local work. Use multiple stewards when work crosses
ownership lines, such as core/rendering, build/incremental/cache,
protocols/tests, or site/default-theme. Parallelize steward consultation only
when the questions are independent; otherwise start with the steward that owns
the safety boundary and let its answer shape the next consultation.

Delegate specialist investigation when a steward has a bounded question with a
clear output, such as "which fixtures prove this invariant?", "which docs become
wrong?", or "which downstream contract changes?". Keep final synthesis with the
implementing agent so tradeoffs are resolved in one place.

### Ask Stewards

Trigger phrase: **"ask stewards"**.

- For implementation work, consult only affected scoped stewards.
- For backlog, roadmap, or prioritization, consult all scoped stewards and
  produce a short rollup.
- Verify the checkout is current, enumerate scoped `AGENTS.md` files, group
  related stewards, and ask for top priority, evidence, dependencies, risks,
  confidence, peer-service opportunities, and tempting "not now" work.
- Synthesize by convergence, blast radius, dependency order, risk reduction,
  reversibility, public contracts, free-threading, and user-visible correctness.
- Preserve minority reports when a steward owns a safety boundary.

## Extension Routing

- **Template function or filter:** add a module under
  `bengal/rendering/template_functions/` with `register(env, site)` and wire it
  in `register_all()`. No auto-discovery.
- **Content type strategy:** use `bengal new content-type <name>` or register a
  `ContentTypeStrategy` from `bengal/content_types/`.
- **CLI command:** add a Milo command under `bengal/cli/milo_commands/` and
  register it with `cli.lazy_command(...)` in `bengal/cli/milo_app.py`. Use
  annotated parameters, dict returns, and CLI render helpers; do not `print()`.
- **Build phase:** stop and ask. Build phases are hardcoded in
  `bengal/orchestration/build/__init__.py`; behavior changes should usually use
  plugin hooks.

## Done Criteria

- `make test` passes. Hot-path or threading changes need the relevant broader
  pytest marker too.
- `make ty` does not regress the diagnostic floor.
- `ruff format` and `ruff check --fix` are clean.
- Tests cover the interesting path, including failure paths and malformed input
  where relevant.
- Free-threading-sensitive changes state what shared mutable state was
  considered.
- User-facing changes under `bengal/` include a `changelog.d/` fragment.
- Public API or plugin protocol changes include migration notes.
- Errors use `BengalError` with useful `code`, `context`, `suggestion`, and
  `debug_payload` where appropriate.
- `check-cycles` passes when imports move.
- PR description explains why. The diff explains what.

Tests passing is not the same as done.

## Review Notes

- One concern per PR unless a broad rename is the concern.
- Commit style: `<scope>: <description>`, using scopes such as `core`,
  `orchestration`, `rendering`, `cache`, `cli`, `tests`, `docs`, `deps`,
  or `release`.
- Flag surprises: weird tests, dead code, unused config, changed allow-lists,
  stale docs, or anything that looked load-bearing.
- Do not silently delete dead code you found while doing unrelated work.

## When This File Is Wrong

Update it. A stale constitution is worse than a short corrective PR.

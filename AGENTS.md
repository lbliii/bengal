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
- `bengal/protocols/`, `bengal/plugins/`, and hook surfaces are public
  contracts. Prefer adapters or internal helpers over widening `SiteLike`,
  `PageLike`, `SectionLike`, or `Plugin`.

## Stakes

- Rendering bugs ship wrong content to readers.
- Incremental bugs leave stale pages that authors trust.
- Free-threading races make 3.14t look flaky.
- Plugin contract breaks affect third-party extensions discovered through
  `bengal.plugins`.
- CLI/config changes break automation, docs snippets, and generated sites.
- Performance regressions weaken Bengal's "scales with cores" claim.

Bengal is alpha, published on PyPI, and used. Calibrate accordingly.

## Stop And Ask

Check in before doing any of these:

- Changing public API, plugin protocols, hook signatures, `bengal.plugins`
  entry points, CLI flags/commands, config keys, release layout, or
  `BengalError` construction.
- Adding a runtime dependency, build phase, persistence schema, migration,
  output format contract, security/auth behavior, or irreversible operation.
- Touching immutable pipeline records or adding mutation to pipeline stages.
- Reintroducing core mixins or growing the empty mixin allow-list.
- Hoisting a deferred import to module level. Run `check-cycles` first.
- Changing concurrency, lifecycle, watcher, cache invalidation, or free-threaded
  shared state behavior.
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
The root is the constitution, routing guide, and swarm protocol. Scoped files
are domain stewards for concrete trees, public contracts, product surfaces,
safety boundaries, docs, tests, examples, fixtures, and checks.

Every steward uses this operating model:

- **Point Of View:** who or what the domain represents.
- **Protect:** invariants, contracts, quality bars, and failure modes.
- **Contract Checklist:** local surfaces that must agree when the domain changes.
- **Advocate:** features, fixes, and investments the domain should push for.
- **Serve Peers:** upstream and downstream domains that need clearer contracts,
  diagnostics, docs, tests, or ergonomics.
- **Do Not:** local anti-patterns and refusal patterns.
- **Own:** tests, docs, examples, fixtures, maintenance checks, and proof paths.

Stewards advise from their domain's interests; the implementing agent owns
synthesis, scope, and final implementation. When work crosses steward areas, add
`Steward Notes` to the PR description naming each area and how its invariants
were protected.

## Contract Checklist

- Identify every surface that should agree: CLI/API, programmatic use,
  protocols, schema/types, templates/UI, docs, examples, scaffolds, tests,
  benchmarks, and changelog.
- Every accepted finding must name required proof and collateral updates, or
  explicitly say `no collateral: <reason>`.
- Docs, examples, and scaffolds move in the same PR as user-facing behavior
  unless synthesis records why they are unaffected.
- Contract-affecting PRs include a parity matrix when behavior spans multiple
  entrypoints.

## Steward Signal Format

Steward findings should be contract-oriented, evidence-backed, and
collateral-aware.

- Steward:
- Area:
- Severity: P0/P1/P2/P3
- Invariant:
- Evidence:
- User Impact:
- Required Fix:
- Required Proof:
- Collateral:
- Confidence:

## Steward Swarms

When the user asks for `ask stewards`, `bugbash`, `review swarm`, or
`steward synthesis`, and delegation is available:

- Spawn independent steward agents for affected domains.
- Each steward reads root plus its closest scoped `AGENTS.md`.
- Each steward advocates only for that domain's interests.
- Each steward returns findings in the Steward Signal Format.
- The implementing agent owns synthesis and final decisions.
- Keep PR scope bounded to accepted findings and their proof/collateral.
- Defer unrelated steward suggestions to not-now/follow-up.

For backlog, roadmap, or prioritization work, consult all scoped stewards and
produce raw steward signals, confidence, dependencies, risks, convergence,
minority reports, ranked backlog, and not-now items.

## Steward Feedback Loop

- **Steward miss:** when a bug escapes an applicable steward, update the
  checklist, a regression test, a docs/snippet check, a routing rule, or record
  why the miss should not become policy.
- **Steward overreach:** when a steward repeatedly pulls unrelated work into
  PRs, narrow the checklist, split the steward, or move the concern to
  follow-up.
- Repeated high-quality findings should become checklist items.
- Repeated noisy findings should be pruned or clarified.
- Steward guidance evolves from escaped bugs, late collateral updates,
  CI/review misses, and recurring review comments.

## When To Consult

Consult stewards proactively for cross-boundary, public-facing,
hard-to-reverse, performance-sensitive, concurrency-sensitive,
security-sensitive, or contract-affecting work. Use the nearest steward for
local work. Use multiple stewards when ownership lines cross, such as
core/rendering, build/incremental/cache, protocols/plugins/tests, or
site/default-theme. Parallelize consultation only when questions are
independent. Keep final synthesis and implementation accountability with the
implementing agent.

## Ask Stewards

Trigger phrase: `ask stewards`.

For implementation work, consult affected stewards and return synthesis before
or during the change. Include accepted/deferred findings, merged duplicates,
minority reports, required proof, collateral updates, and not-now items.

For multi-surface work, include a parity matrix like:

| Contract | API/CLI | Programmatic | Protocol | Schema/Types | Docs | Examples | Tests |
|---|---|---|---|---|---|---|---|

For backlog, roadmap, or prioritization, consult all scoped stewards and rank
work by convergence, blast radius, dependency order, risk reduction,
reversibility, public contracts, free-threading, and user-visible correctness.

## Extension Routing

- **Template function or filter:** add a module under
  `bengal/rendering/template_functions/` with `register(env, site)` and wire it
  in `register_all()`. No auto-discovery.
- **Content type strategy:** use `bengal new content-type <name>` or register a
  `ContentTypeStrategy` from `bengal/content_types/`.
- **Plugin hook:** evolve `bengal/protocols/` and `bengal/plugins/` together,
  with contract tests and migration notes.
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
- Docs, examples, scaffolds, and templates are updated for user-facing changes.
- Free-threading, performance, or security-sensitive changes state what shared
  state, hot path, or trust boundary was considered.
- User-facing changes under `bengal/` include a `changelog.d/` fragment.
- Public API or plugin protocol changes include migration notes.
- Errors use `BengalError` with useful `code`, `context`, `suggestion`, and
  `debug_payload` where appropriate.
- Every accepted steward finding has test/docs/example/benchmark proof or an
  explicit no-impact note.
- `check-cycles` passes when imports move.
- PR description explains why. The diff explains what.

Tests passing is not the same as done.

## Review Notes

- One concern per PR unless a broad rename is the concern.
- Commit style: `<scope>: <description>`, using scopes such as `core`,
  `orchestration`, `rendering`, `cache`, `cli`, `tests`, `docs`, `deps`, or
  `release`.
- Flag surprises: weird tests, unused public names, suppressions, dead code,
  changed allow-lists, stale docs, benchmark gaps, free-threading assumptions,
  steward disagreement, or deferred/not-now findings.
- Do not silently delete dead code you found while doing unrelated work.

## When This File Is Wrong

Update it. A stale constitution is worse than a short corrective PR.

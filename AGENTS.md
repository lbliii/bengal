<!-- markdownlint-disable MD013 MD060 -->

# Bengal Agent Constitution

Bengal builds the sites people read documentation on. Bugs here reach end users
through someone else's content: broken links, wrong code blocks, stale pages,
empty search indexes. Treat these as safety rules, not style preferences.

## North Star

We make free-threaded Python worth deploying for content tooling. Bengal should
prove that a documentation generator can run on a pure-Python default path,
scale with cores on Python 3.14t, and require zero npm for normal site builds.

We favor readable Python, real parallelism, measurable performance, and
user-visible correctness. The public promise is visible in `README.md` and
`pyproject.toml`: Python 3.14+, pure-Python documentation generation,
incremental builds, AI-native outputs, validation, and extension points.

## Non-Negotiables

- **Pure Python default build path.** `README.md:9`, `README.md:11`, and
  `pyproject.toml:8` position Bengal around Python free-threading and zero npm.
  Normal site generation must not require npm, Node, or a JS toolchain. The
  optional assets pipeline is an explicit opt-in path and must stay documented as
  optional if it remains supported.
- **Python 3.14 is the floor.** `pyproject.toml:10`, `pyproject.toml:121`, and
  `pyproject.toml:276` set runtime, Ruff, and ty to Python 3.14.
- **Core is passive for new work.** `CONTRIBUTING.md:132` and `.importlinter:25`
  keep `bengal/core/` out of orchestration, server, rendering pipeline, and asset
  work. Do not add new core I/O or direct logging. Existing transitional debt in
  `bengal/core/asset/`, `bengal/core/resources/`, `bengal/core/theme/providers.py`,
  `bengal/core/output/`, and `bengal/core/page/page_core.py` is not precedent
  for new code.
- **Rendering owns presentation.** HTML, excerpts, TOCs, template URLs,
  shortcode/link extraction, page bundle views, and section URL ergonomics
  belong under `bengal/rendering/`.
- **Pipeline records stay immutable.** `bengal/core/records.py:151`,
  `bengal/core/records.py:224`, and `bengal/core/records.py:245` define
  `ParsedPage`, `RenderedPage`, and `SourcePage` as frozen records. Do not add
  setters, plugin state, or late mutation.
- **Writes are atomic.** `CONTRIBUTING.md:144` names `atomic_write_text`,
  `atomic_write_bytes`, and `json_compat.dump` as the output/cache write path.
- **Sharp edges are bugs.** `pyproject.toml:147`, `pyproject.toml:176`, and
  `pyproject.toml:182` keep exception handling visible. No silent `except`, no
  casual `# type: ignore`, no vague flags, and no error that fails to say what
  to do next.
- **PEP 758 syntax is valid here.** `pyproject.toml:323` pins Ruff for Python
  3.14 syntax. `except OSError, ValueError:` is valid multi-catch syntax here;
  do not wrap it in parentheses to satisfy older expectations.

## Architecture Boundaries

| Path | Steward / Contract |
|---|---|
| `bengal/core/` | Passive domain model, compatibility surfaces, import-linter core boundary |
| `bengal/core/page/` | `Page` compatibility surface and template-facing shims |
| `bengal/core/section/` | `Section` hierarchy surface and navigation compatibility |
| `bengal/core/site/` | `Site` coordinator, registries, services, and lifecycle compatibility |
| `bengal/rendering/` | Presentation, templates, URLs, excerpts, TOCs, shortcodes, links |
| `bengal/rendering/template_functions/` | Explicitly registered template globals, filters, and tests |
| `bengal/rendering/pipeline/` | Parse/render records, dependency capture, output handoffs |
| `bengal/orchestration/` | Build lifecycle, phase handoffs, scheduling, stats, site runner |
| `bengal/orchestration/build/` | Hardcoded build phases and plugin phase hook timing |
| `bengal/orchestration/incremental/` | Rebuild decisions, cache/provenance invalidation, warm-build parity |
| `bengal/build/` | Build contracts and provenance helpers; detector logic currently lives in orchestration/effects |
| `bengal/cache/` | Persistent cache stores, indexes, migration tolerance, atomic cache writes |
| `bengal/config/` | Config schema, loaders, env overrides, snapshots, validation |
| `bengal/cli/` | Milo command surface, terminal output, command registration |
| `bengal/server/` | Dev server, live reload, watcher, reactive preview, Pounce integration |
| `bengal/protocols/` | Public structural contracts for plugins, core, rendering, build hooks |
| `bengal/plugins/` | Entry-point discovery, plugin registry, hook application |
| `bengal/content/` | Content discovery, sources, notebook handling, versioning |
| `bengal/content_types/` | Section/content classification and generated strategy scaffolds |
| `bengal/parsing/` | Patitas-backed parsing, directives, roles, renderer integration |
| `bengal/autodoc/` | Python, CLI, and OpenAPI extraction plus virtual page models |
| `bengal/assets/` | Asset manifest, CSS directives, generated asset contracts |
| `bengal/themes/default/` | Default theme templates, CSS/JS, icons, swizzle contracts |
| `bengal/scaffolds/` | `bengal new ...` generated site/content/theme artifacts |
| `bengal/postprocess/` | Sitemap, feeds, search, llms.txt, redirects, output format artifacts |
| `bengal/health/` | Validators, reports, remediation, linkcheck, artifact checks |
| `bengal/snapshots/` | Frozen render-time site/page/section/template snapshots |
| `bengal/utils/` | Shared primitives, atomic I/O, paths, concurrency, observability |
| `bengal/audit/` | Generated artifact audit records and reviewer-facing checks |
| `site/` | Public docs source and dogfood site |
| `tests/` | Behavioral proof, fixtures, mocks, markers, regression memory |
| `benchmarks/` and `tests/performance/` | Performance evidence and regression budgets |
| `plan/` | RFCs, epics, deferred design evidence, not shipped behavior |
| `bengal-syntax-highlighter/` | VS Code grammar package; not part of the Python build path |

`Page`, `Section`, and `Site` are compatibility surfaces and coordinators, not
dumping grounds. Page template-facing properties may remain as shims, but should
delegate to rendering helpers. Section stays mixin-free. Site coordinates
registries, services, and orchestration. Protocols, plugins, and hook surfaces
are public contracts.

## Governance Alignment

- `CODEOWNERS`, `OWNERS`, and `MAINTAINERS` were not found in `.github/` or the
  repo root during bootstrap. Human approval routing is therefore
  `manual-confirmation-needed` until ownership is recorded.
- Canonical public knowledge lives in `README.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, `site/content/`, `tests/README.md`, and `.importlinter`.
- CI and release governance lives in `.github/workflows/`, `pyproject.toml`,
  `uv.lock`, and `.github/dependabot.yml`.
- Stewards advise. Humans approve public API, dependency, release, security,
  persistence, and user-facing contract changes.

## Stop And Ask

Check in before doing any of these:

- Changing public API, plugin protocols, hook signatures, `bengal.plugins`
  entry points, CLI flags/commands, config keys, release layout, or
  `BengalError` construction.
- Adding a runtime dependency, build phase, persistence schema, migration,
  output format contract, security/auth behavior, or irreversible operation.
- Touching immutable pipeline records or adding mutation to pipeline stages.
- Reintroducing core mixins or growing the empty mixin allow-list guarded by
  `tests/unit/core/test_no_core_mixins.py`.
- Hoisting a deferred import to module level. Run `check-cycles` or the
  import-linter equivalent first.
- Changing concurrency, lifecycle, watcher, cache invalidation, or
  free-threaded shared state behavior.
- Chasing ty diagnostics below the current project floor without a scoped plan.
- Reorganizing methods on `Site`, `Page`, or `Section` instead of deleting
  vestiges and migrating callers.
- Fixing a test/code disagreement without knowing which one is authoritative.
- Guessing at an unreproduced bug. Ask for a minimal repro, ideally a
  `tests/roots/` fixture.
- Folding adjacent issues into a bug fix. Flag them as follow-up work.

## Anti-Patterns

- Adding npm or JS tooling to make the frontend path easier.
- Moving rendering behavior back into core.
- Rebuilding old forwarding layers around `Site`, `Page`, or `Section`.
- `try: ... except Exception: pass`; if swallowing is intentional, emit a
  diagnostic with what and why.
- `# type: ignore`, `noqa: S110`, or `noqa: S112` to clear noise.
- Defensive validation inside core instead of at boundaries.
- Direct `logger.X` inside `bengal/core/`.
- Non-atomic output or cache writes.
- Refactoring during a bug fix unless the refactor is the fix.
- Treating `plan/` as shipped behavior or `site/public/` as authored docs.

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
- **Own:** tests, docs, examples, fixtures, maintenance checks, and proof paths.
- **Do Not** and **Serve Peers:** optional; include only when they carry
  non-obvious local guidance.

Stewards advise from their domain's interests; the implementing agent owns
synthesis, scope, and final implementation. Cross-boundary PRs include
`Steward Notes` naming each area and how its invariants were protected.

## Contract Checklist

- Identify every surface that should agree: CLI/API, programmatic use,
  protocols, schema/types, templates/UI, docs, examples, scaffolds, tests,
  benchmarks, changelog, and release smoke tests.
- Every accepted finding must name required proof and collateral updates, or
  explicitly say `no collateral: <reason>`.
- Docs, examples, and scaffolds move in the same PR as user-facing behavior
  unless synthesis records why they are unaffected.
- Contract-affecting PRs include a parity matrix when behavior spans multiple
  entrypoints.
- Factual P0/P1 findings carry `machine-verified`,
  `manual-confirmation-needed`, or `not-machine-verifiable`.

## Steward Signal Format

Steward findings should be contract-oriented, evidence-backed, and
collateral-aware.

- Steward:
- Area:
- Severity: P0/P1/P2/P3
- Invariant:
- Evidence: `<source-file>:<line>` and, for content audits,
  `<source-file>:<line> -> <doc-file>:<line>`
- User Impact:
- Required Fix:
- Required Proof:
- Collateral:
- Confidence:
- Verification Status: machine-verified / manual-confirmation-needed /
  not-machine-verifiable

## Convergence Rule

Two or more independent stewards flagging the same accepted finding promotes it
to P0 unless the implementing agent disproves the factual basis with source
evidence. Convergence promotion applies to the same underlying contract break,
not merely similar wording.

## Steward Swarms

Trigger phrases:

- Implementation review: `ask stewards`, `bugbash`, `review swarm`,
  `steward synthesis`.
- Content audit: `audit docs`, `content audit`, `accuracy pass`.

When delegation is available:

- Spawn independent steward agents for affected domains.
- Each steward reads root plus its closest scoped `AGENTS.md`.
- Each steward advocates only for that domain's interests.
- Each steward returns findings in the Steward Signal Format.
- The implementing agent owns synthesis and final decisions.
- Keep PR scope bounded to accepted findings and their proof/collateral.
- Defer unrelated suggestions to not-now/follow-up.

For backlog, roadmap, or prioritization work, consult all scoped stewards and
rank work by convergence, blast radius, dependency order, risk reduction,
reversibility, public contracts, free-threading, and user-visible correctness.

## Saga Goals

When tooling supports an active goal, use it as the runtime mission tracker for
a selected saga. Goals do not replace `plan/ROADMAP.md`, active plan files,
commits, changelog fragments, or final plan updates.

- Create a goal only after the saga is selected and the user explicitly asks to
  start a saga, start a goal, resume a goal, or make a named saga active.
- The goal objective should name the active plan slice, expected proof, commit
  discipline, and required plan/archive update.
- Do not create a goal for open-ended discovery. First answer "what should we
  work on next?" from `plan/ROADMAP.md` and steward consultation, then start the
  goal once the user accepts or asks to begin.
- Keep the goal active until the saga is genuinely closed: code/docs/tests or
  explicit no-impact notes are done, commits are scoped, proof is recorded, and
  planning state is refreshed.
- Mark a goal complete only when no required saga work remains. Mark it blocked
  only when the same blocker has repeated and no meaningful progress is
  possible without user input or external state.

## Global Sweep On Accepted P0s

Before closing an accepted P0, grep the relevant docs and code trees for the
same wrong claim or behavior. At minimum sweep `bengal/`, `site/content/`,
`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `tests/`, and `plan/` unless
the finding is provably narrower. Record the command or mark why it is not
machine-verifiable.

## Steward Feedback Loop

- **Steward miss:** when a bug escapes an applicable steward, update the
  checklist, a regression test, a docs/snippet check, a routing rule, or record
  why the miss should not become policy.
- **Steward overreach:** when a steward repeatedly pulls unrelated work into
  PRs, narrow the checklist, split the steward, or move the concern to
  follow-up.
- Repeated high-quality findings should become checklist items.
- Repeated noisy findings should be pruned or clarified.

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
  annotated parameters, dict returns, and CLI render helpers.
- **Build phase:** stop and ask. Build phases are hardcoded in
  `bengal/orchestration/build/__init__.py`; behavior changes should usually use
  plugin hooks.

## Cross-Cutting: Free-Threading And Performance

This applies when work touches parallel builds, watchers, caches, render
pipelines, global state, template caches, asset manifests, or hot paths.

- Prefer immutable records, snapshots, ContextVars, thread-local render
  pipelines, and leaf locks over shared mutable state.
- State which shared state, lock, snapshot, cache key, or hot path was
  considered.
- Performance claims need a benchmark, timing comparison, or explicit
  no-impact explanation.
- Relevant evidence includes `tests/test_thread_safety.py`,
  `tests/performance/`, `benchmarks/`, and `bengal/concurrency.py`.

## Cross-Cutting: Public Contracts

This applies to CLI flags, config keys, protocols, plugin hooks, template
globals, generated files, package metadata, output formats, docs snippets, and
scaffolds.

- Every public contract change needs tests plus docs/snippet/scaffold parity or
  a no-impact note.
- Avoid widening `SiteLike`, `PageLike`, `SectionLike`, or `Plugin` for one
  internal caller.
- Keep `bengal/__init__.py`, `pyproject.toml`, `bengal/protocols/`,
  `bengal/plugins/`, and generated reference docs in agreement.

## Cross-Cutting: Release And Dependency Risk

This applies to `pyproject.toml`, `uv.lock`, `.github/workflows/`,
`CHANGELOG.md`, `changelog.d/`, and package-data changes.

- Fresh-wheel behavior matters as much as locked-repo behavior. The release
  workflow smoke-tests the built wheel against freshly resolved dependencies.
- Package-data changes need source-tree and installed-wheel proof.
- User-facing changes under `bengal/` need a `changelog.d/` fragment unless a
  maintainer marks the change exempt.

## Cross-Cutting: Documentation Accuracy

This applies to README, site docs, generated reference docs, examples, snippets,
and migration notes.

- Do not document aspirational behavior as shipped behavior.
- Every command, config field, template function, and public API claim traces to
  source, generated help, schema, or a test.
- When a P0 content correction is accepted, run the Global Sweep before closing
  it.

## Known Regression Patterns

- **Fabricated CLI or config fields.** Verification: every flag traces to
  `bengal/cli/milo_app.py`, `bengal/cli/milo_commands/`, config schema/types, or
  generated help.
- **Unverified finding regression.** Verification: every factual P0/P1 carries
  `machine-verified`, `manual-confirmation-needed`, or `not-machine-verifiable`.
- **Narrow-fix regression.** Verification: every accepted P0 closure runs the
  Global Sweep above.
- **Dependency drift between lockfile and wheel.** Evidence:
  `CHANGELOG.md:52` and `.github/workflows/python-publish.yml:37`. Verification:
  fresh-wheel smoke tests cover CLI startup and cache commands.
- **Kida strict-undefined template fallout.** Evidence: `CHANGELOG.md:31` and
  `CHANGELOG.md:45`. Verification: template changes use optional chaining,
  defaults, or context-contract tests.
- **Stale CLI command shape.** Evidence: `CHANGELOG.md:65`. Verification:
  command docs match `bengal --help` and Milo registrations.
- **Silent fallback or swallowed error.** Evidence: `CHANGELOG.md:67`,
  `CHANGELOG.md:69`, `pyproject.toml:176`, and `pyproject.toml:182`.
  Verification: diagnostics explain what happened and what to do next.
- **Cache/provenance divergence and stale outputs.** Evidence:
  `CHANGELOG.md:95`, `CHANGELOG.md:127`, and incremental integration tests.
  Verification: warm-build tests cover full-to-incremental parity and missing
  generated artifacts.
- **Package data missing from wheels.** Evidence:
  `tests/unit/test_package_data.py:3`. Verification: package-data tests and
  wheel install smoke tests include templates/assets used at runtime.
- **Parallel test worker crashes from nested parallelism.** Evidence:
  `tests/README.md:63`. Verification: tests that spawn threads/processes are
  marked `parallel_unsafe` or run serially.

## Done Criteria

- `make test` passes, or the scoped equivalent is run with rationale. Hot-path
  or threading changes need the relevant broader pytest marker too.
- `make ty` or `uv run ty check bengal/` does not regress the diagnostic floor.
- `ruff format` and `ruff check --fix` are clean, or formatting/lint gaps are
  recorded.
- Tests cover the interesting path, including failure paths and malformed input
  where relevant.
- Docs, examples, scaffolds, and templates are updated for user-facing changes.
- Free-threading, performance, or security-sensitive changes state what shared
  state, hot path, or trust boundary was considered.
- User-facing changes under `bengal/` include a `changelog.d/` fragment or an
  explicit no-impact note.
- Public API or plugin protocol changes include migration notes.
- Errors use `BengalError` with useful `code`, `context`, `suggestion`, and
  `debug_payload` where appropriate.
- Every accepted steward finding has test/docs/example/benchmark proof or an
  explicit no-impact note.
- Import-linter or cycle checks pass when imports move.
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

<!-- markdownlint-disable MD013 -->

# Steward Audit

This file records the bootstrap self-audit for the steward network. It should be
kept for the first reviewer and can be deleted after the network has been
reviewed and accepted.

## Audit Scope

- Root constitution: `AGENTS.md`
- Scoped stewards: every non-generated `AGENTS.md` outside `.git`, `.bengal/`,
  and `build/`
- Companion questions: `STEWARD_QUESTIONS.md`
- Verification commands and subagent findings from this bootstrap turn

## Bootstrap Receipts

- Existing scoped file inventory:
  `find . -path './.git' -prune -o -path './.bengal' -prune -o -path './build' -prune -o -name AGENTS.md -print | sort`
- Existing line counts:
  `find . -path './.git' -prune -o -path './.bengal' -prune -o -path './build' -prune -o -name AGENTS.md -print | sort | xargs wc -l`
- CODEOWNERS/OWNERS/MAINTAINERS search:
  `rg -n "CODEOWNERS|OWNERS|MAINTAINERS" .github . AGENTS.md`
- Root verification terms:
  `rg -n "Verification Status|Known Regression|Governance Alignment|Convergence Rule|Global Sweep" AGENTS.md`
- Scoped heading verification:
  `rg -n "^# Steward:" -g AGENTS.md`

## Delegation Status

Delegation was available. The environment accepted six parallel audit agents and
rejected two additional agents with `collab spawn failed: agent thread limit
reached`. Five delegated groups returned findings; the public-contract group
remained running after the verification pass and was shut down without findings.
The self-audit therefore uses five delegated groups plus local checks.

Spawned audit groups:

- Core surfaces: root plus `bengal/core/**/AGENTS.md`
- Rendering/theme/assets: rendering, pipeline, template functions, default theme, assets
- Build/orchestration/cache: orchestration, build phases, incremental, build contracts, cache, snapshots
- Public contracts: CLI, config, protocols, plugins, errors
  (`manual-confirmation-needed`; agent shut down before returning findings)
- Content/parsing/autodoc: content, content types, parsing, autodoc, scaffolds
- Output/validation/server/utilities: server, health, postprocess, audit, utils

Not spawned because of thread limit:

- Documentation/planning/tests/benchmarks
- Root constitution plus `bengal-syntax-highlighter/AGENTS.md`

## Local Findings

Steward: Bootstrap
Area: Scoped line counts
Severity: P3
Invariant: The requested target for scoped steward files was 80-130 lines.
Evidence: `find ... -name AGENTS.md ... | xargs wc -l` shows most scoped files
are 56-76 lines, with `bengal/core/AGENTS.md` at 81 lines.
User Impact: Shorter scoped files are easier to scan but miss the requested
target.
Required Fix: Accept the tighter files as the Phase 5 redundancy trim outcome,
or expand selected high-risk files if reviewer prefers the literal range.
Required Proof: Reviewer decision.
Collateral: no collateral: documentation-only bootstrap sizing.
Confidence: High
Verification Status: machine-verified

Steward: Bootstrap
Area: CODEOWNERS
Severity: P2
Invariant: Human governance should respect CODEOWNERS.
Evidence: `.github/` contains workflows and Dependabot, but no CODEOWNERS file
was found by local file inventory.
User Impact: Steward files can only mark ownership as
`manual-confirmation-needed`, so human routing remains incomplete.
Required Fix: Add CODEOWNERS or update steward files when ownership is known.
Required Proof: `rg --files -g CODEOWNERS -g OWNERS -g 'MAINTAINERS*'`.
Collateral: all scoped `CODEOWNERS:` lines.
Confidence: High
Verification Status: machine-verified

Steward: Bootstrap
Area: Scope count
Severity: P3
Invariant: Add scoped files only where a real boundary exists.
Evidence: The network now includes source, test, docs, planning, benchmark, and
syntax-highlighter boundaries reflected in the repo tree and existing steward
network.
User Impact: Agents get closer local context, but the network is larger than the
generic 6-12 medium-repo heuristic.
Required Fix: Reviewer may merge lower-risk scopes later if the network feels
too granular.
Required Proof: `find ... -name AGENTS.md -print`.
Collateral: no collateral: local context routing only.
Confidence: Medium
Verification Status: machine-verified

## Delegated Findings

Steward: Core
Area: Core diagnostics
Severity: P1
Invariant: Core diagnostics should route through `emit(...)`, but steward claims
must acknowledge current source debt.
Evidence: Audit found direct logging in `bengal/core/resources/`,
`bengal/core/theme/providers.py`, `bengal/core/output/`, and
`bengal/core/page/page_core.py`.
User Impact: Agents could copy existing debt or over-fix unrelated modules.
Required Fix: Name existing debt in root/core steward language and forbid new
direct logging.
Required Proof: `rg -n "get_logger|logger\\." bengal/core`.
Collateral: Root and core steward files; architecture docs remain a follow-up if
the debt is actively migrated.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; root and core steward files now distinguish new-work rule
from transitional debt.

Steward: Core
Area: Core I/O boundary
Severity: P1
Invariant: Core passive guidance must not pretend existing I/O debt is absent.
Evidence: Audit found filesystem/image work in `bengal/core/asset/` and
`bengal/core/resources/`.
User Impact: Agents could misread the current architecture or expand the debt.
Required Fix: Name existing debt and forbid expansion without steward notes.
Required Proof: Grep for filesystem operations in `bengal/core/`.
Collateral: Root/core steward files and future architecture cleanup.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward files now name `core/asset` and `core/resources`
as transitional debt.

Steward: Core
Area: Import boundaries
Severity: P2
Invariant: "No upward imports" should match import-linter and deferred shims.
Evidence: `.importlinter` forbids only specific upward modules; source has many
deferred rendering imports in Page/Section/Site compatibility shims.
User Impact: Agents may flag valid deferred shims or miss module-level boundary.
Required Fix: Reword to "no module-level upward imports" and document deferred
compatibility imports.
Required Proof: `rg -n "from bengal.rendering|import bengal.rendering" bengal/core`.
Collateral: Root/core steward language.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; root/core steward wording updated.

Steward: Core Section
Area: Docs parity
Severity: P2
Invariant: Do not reintroduce `sections` as a `subsections` alias.
Evidence: `site/content/docs/reference/architecture/core/object-model.md`
referred to `sections`; source exposes `subsections`.
User Impact: Docs could lead agents toward a non-existent alias.
Required Fix: Update docs to `subsections`.
Required Proof: `rg -n "regular_pages.*sections|section_registry\\.py" site/content/docs/reference/architecture/core/object-model.md`.
Collateral: Architecture docs.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; docs updated.

Steward: Core Site
Area: Registry docs parity
Severity: P2
Invariant: Registry docs should point at live implementation.
Evidence: Docs referenced missing `bengal/core/site/section_registry.py`; source
uses `bengal/core/registry.py`.
User Impact: Agents could chase deleted mixin-era paths.
Required Fix: Update docs to `bengal/core/registry.py` and `Site.register_sections()`.
Required Proof: `rg -n "section_registry\\.py" site/content bengal/core`.
Collateral: Architecture docs.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; docs updated.

Steward: Content Types
Area: Scaffold checklist
Severity: P2
Invariant: Contract checklists must point at actual scaffold owners.
Evidence: Generated content-type scaffold lives in
`bengal/cli/milo_commands/new.py`, not `bengal/scaffolds/`.
User Impact: Agents may inspect the wrong tree for strategy scaffold parity.
Required Fix: Update content-types steward checklist.
Required Proof: `rg -n "ContentTypeStrategy|content-type|register_strategy" bengal/scaffolds bengal/cli/milo_commands/new.py`.
Collateral: `bengal/content_types/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward checklist updated.

Steward: Content Types
Area: `bengal new content-type` scaffold parity
Severity: P1
Invariant: Generated scaffolds must teach current strategy API.
Evidence: Audit reports scaffold text uses `type =`, while detection uses
`content_type`.
User Impact: Users can follow generated instructions and fail to opt in.
Required Fix: Separate product fix: decide key and align scaffold/tests/docs.
Required Proof: Generated strategy test for documented key.
Collateral: `bengal/cli/milo_commands/new.py`, tests, docs, changelog.
Confidence: High
Verification Status: machine-verified
Disposition: Deferred; real product bug outside steward-system scope.

Steward: Parsing
Area: Domain ownership
Severity: P2
Invariant: Parsing steward should not own notebook/frontmatter source behavior.
Evidence: Notebook/frontmatter source behavior is in content discovery, not
`bengal/parsing/`.
User Impact: Agents may miss content steward obligations.
Required Fix: Narrow parsing steward and route notebooks/frontmatter to content.
Required Proof: `rg -n "frontmatter|notebook|parse_notebook" bengal/parsing --glob '!AGENTS.md'`.
Collateral: `bengal/parsing/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; parsing steward narrowed.

Steward: Autodoc
Area: Docs path references
Severity: P2
Invariant: Steward docs paths must exist.
Evidence: `site/content/docs/content/sources/autodoc/` does not exist; the file
is `site/content/docs/content/sources/autodoc.md`.
User Impact: Agents could miss canonical autodoc docs.
Required Fix: Correct paths.
Required Proof: `find site/content -path '*autodoc*' -type f | sort`.
Collateral: `bengal/autodoc/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; paths updated.

Steward: Snapshots
Area: Current render isolation
Severity: P1
Invariant: Snapshot guidance must not overstate lock-free render isolation.
Evidence: `bengal/snapshots/scheduler.py` maps snapshot pages to `PageLike` and
passes `self.site` into rendering.
User Impact: Agents could miss free-threading review around live Site/Page reads.
Required Fix: Describe current hybrid model; keep snapshot-only direction as an
advocacy item.
Required Proof: Grep scheduler for `self.site`, `_page_map`, and `run_page`.
Collateral: `bengal/snapshots/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; snapshot steward reworded.

Steward: Build Contracts
Area: Stale detector/tracking routing
Severity: P2
Invariant: Steward ownership must point at live source.
Evidence: `bengal/build/detectors/` and `bengal/build/tracking/` contain no
source files; active detector behavior lives under orchestration/effects.
User Impact: Agents could route changes to empty package stubs.
Required Fix: Reword build steward and root table.
Required Proof: `find bengal/build -maxdepth 3 -type f -not -path '*/__pycache__/*'`.
Collateral: Root and build steward files.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; routing updated.

Steward: Postprocess
Area: Missing artifact repair
Severity: P1
Invariant: Steward claims must match artifacts actually repaired on warm/no-op builds.
Evidence: Audit reports provenance only checks configured site-wide output
formats, `sitemap.xml`, and `robots.txt`; RSS/redirects are skipped on incremental.
User Impact: Agents could assume feeds/redirects are repaired when they are not.
Required Fix: Narrow steward rule or implement repair.
Required Proof: Source grep for missing postprocess artifact checks.
Collateral: `bengal/postprocess/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward narrowed.

Steward: Health
Area: Default validator coverage
Severity: P2
Invariant: Health steward must distinguish default validators from importable validators.
Evidence: Audit reports external refs, asset URL, and output validators are
available but not default-registered.
User Impact: Agents may overstate `bengal check` coverage.
Required Fix: Reword steward to say default versus available/specialized.
Required Proof: Grep `_register_default_validators`.
Collateral: `bengal/health/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward reworded.

Steward: Audit
Area: Report schema
Severity: P1
Invariant: Audit report claims must match shipped schema.
Evidence: `ArtifactFinding` has severity, message, artifact, reference, code,
and recommendation; no verification status/source path field.
User Impact: Agents could accidentally widen audit schema while following steward.
Required Fix: Move verification status/source path to future work language.
Required Proof: Audit envelope tests.
Collateral: `bengal/audit/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward reworded.

Steward: Server
Area: Pounce sendfile wording
Severity: P2
Invariant: Server steward should not preserve behavior Bengal bypasses.
Evidence: ASGI tests require no sendfile calls for dev static assets.
User Impact: Agents could add/preserve wrong sendfile behavior.
Required Fix: Preserve ETag/range/precompressed handling without assuming sendfile.
Required Proof: Existing ASGI tests.
Collateral: `bengal/server/AGENTS.md`.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; steward reworded.

Steward: Assets / Root Constitution
Area: Optional Node asset pipeline
Severity: P1
Invariant: Steward instructions must not contradict shipped optional asset pipeline.
Evidence: Audit reports `bengal/assets/pipeline.py`, CLI flags, config, tests,
and docs for an optional Node-based pipeline.
User Impact: Agents could reject or remove supported opt-in behavior.
Required Fix: Distinguish pure-Python default path from explicit optional Node pipeline.
Required Proof: Grep for Node/pipeline references across source/docs/stewards.
Collateral: Root and assets stewards.
Confidence: High
Verification Status: machine-verified
Disposition: Accepted; root/assets wording updated.

Steward: Template Functions
Area: `data_table` helper registration
Severity: P2
Invariant: Template helper docs, registration, and tests should agree.
Evidence: Audit reports `data_table` has direct registration tests but is absent
from `register_all()` and generated docs.
User Impact: Helper may not be available in normal template environments.
Required Fix: Decide if public; wire/register/docs or mark private.
Required Proof: `register_all()` availability test or intentional omission docs.
Collateral: Template-function docs and changelog if behavior changes.
Confidence: High
Verification Status: machine-verified
Disposition: Deferred; real product/API decision outside steward-system scope.

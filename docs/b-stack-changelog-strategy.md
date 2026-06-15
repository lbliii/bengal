# B-Stack changelog strategy (Towncrier)

This document is the **canonical reference** for how Bengal-ecosystem Python packages maintain release notes. Following one workflow keeps the **Bengal brand** consistent: users see the same fragment discipline, section names, and tone across Kida, Patitas, Rosettes, Bengal, Chirp, Pounce, and chirp-ui.

## Goals

1. **Co-locate notes with changes** — User-visible work ships with a news fragment in the same PR, not a last-minute `CHANGELOG.md` edit at release time.
2. **Avoid merge conflicts** — Small files under `changelog.d/` instead of everyone editing the same top section of a single file.
3. **Predictable structure** — Keep section headings and ordering identical across repos so reading any package's changelog feels familiar.
4. **Automate compilation** — `towncrier build` produces the version-stamped block appended to `CHANGELOG.md` when you cut a release.

## Scope

| Repository   | Package / notes                          |
|-------------|-------------------------------------------|
| [kida](https://github.com/lbliii/kida) | `kida` |
| [patitas](https://github.com/lbliii/patitas) | `patitas` |
| [rosettes](https://github.com/lbliii/rosettes) | `rosettes` |
| [bengal](https://github.com/lbliii/bengal) | `bengal` — **Towncrier enabled** (`changelog.d/`, `CHANGELOG.md`, `poe changelog`) |
| [chirp](https://github.com/lbliii/chirp) | `chirp` |
| [pounce](https://github.com/lbliii/pounce) | `pounce` |
| [chirp-ui](https://github.com/lbliii/chirp-ui) | `chirp_ui` (underscore matches import path) |

## Tooling

- **Towncrier** — dev dependency; configuration lives in each repo's `pyproject.toml` under `[tool.towncrier]`.
- **Task runner** — Prefer **poethepoet** (`poe changelog`, `poe changelog-draft`) for parity across repos; alternatively document equivalent `uv run towncrier …` in each repo's README/CONTRIBUTING until `poe` is added.

### Canonical fragment types

Use the same six types everywhere (directory names = Towncrier `directory`):

| Fragment suffix | Release section |
|-----------------|-----------------|
| `.added.md`     | Added           |
| `.changed.md`   | Changed         |
| `.deprecated.md`| Deprecated      |
| `.removed.md`   | Removed         |
| `.fixed.md`     | Fixed           |
| `.security.md`  | Security        |

### Naming files

- With an issue: `123.added.md`, `456.fixed.md`
- Without an issue (branch or ad hoc): `+short-slug.added.md` (leading `+` is Towncrier's convention for non-numeric tokens)

Body: one line or a short bullet list; **user-facing** wording (what changed for downstream users), not internal refactors.

**Lead-sentence convention.** Start every fragment with a single sentence stating
what changed *for the user* ("Autodoc now cross-links symbol names to their
documented pages."), then add engineering detail in following sentences if it's
worth recording. Two reasons: the first sentence is what a reader skims in
`CHANGELOG.md`, and it gives the release-page distillation (below) a clean topic
sentence to lift. The detail stays — fragments are the precise record — it just
comes *after* the user-facing lead, not instead of it.

### Shared `[tool.towncrier]` shape

Each repo should mirror this structure; only **`package`**, **`package_dir`**, and **`filename`** vary.

```toml
[tool.towncrier]
directory = "changelog.d"
filename = "CHANGELOG.md"
package = "<pypi-name>"     # e.g. bengal, chirp, kida
package_dir = "src"
title_format = "## [{version}] - {project_date}"
issue_format = "`#{issue}`"
underlines = ["", "", ""]

[[tool.towncrier.type]]
directory = "added"
name = "Added"
showcontent = true

[[tool.towncrier.type]]
directory = "changed"
name = "Changed"
showcontent = true

[[tool.towncrier.type]]
directory = "deprecated"
name = "Deprecated"
showcontent = true

[[tool.towncrier.type]]
directory = "removed"
name = "Removed"
showcontent = true

[[tool.towncrier.type]]
directory = "fixed"
name = "Fixed"
showcontent = true

[[tool.towncrier.type]]
directory = "security"
name = "Security"
showcontent = true
```

Example `poe` tasks (add to `[tool.poe.tasks]`):

```toml
changelog = { cmd = "towncrier build --yes", help = "Compile changelog.d into CHANGELOG.md" }
changelog-draft = { cmd = "towncrier build --draft", help = "Preview changelog from fragments (stdout)" }
```

## CI and exemptions

- **Require a fragment** when the PR changes user-facing code under `src/` (or the repo's published package path).
- **Allow skipping** for docs-only, chore-only, or internal refactors with no release note: use a **label** (e.g. `skip-changelog`) or documented PR keyword, consistent per repo.
- **Release:** Run `poe changelog` (or documented equivalent) as part of the version bump / tag checklist so `CHANGELOG.md` updates atomically with the release commit.
- **Performance claims:** Name the benchmark matrix row, exact command, Python
  build, machine/OS, baseline, current result, artifact path, and interpretation
  in the PR before repeating the claim in release notes.

## Release pages (user-facing distillation)

`CHANGELOG.md` is the **engineering record** — every change, in full detail, for
people debugging or upgrading. It is intentionally dense and should stay that way.
Repos that ship a documentation site (Bengal) additionally maintain a **distilled,
user-facing release page** per version at `site/content/releases/<version>.md`:
a key-theme hook, themed highlights with examples, *condensed* Added/Changed/Fixed
lists, and upgrade notes. (The releases section auto-lists its children — adding the
file is enough.)

Keep these as **two artifacts**, do not collapse them. Distillation is a
release-time, top-down editorial act — the theme and the highlight groupings only
exist once you can see the whole release, so they cannot be authored fragment by
fragment weeks apart. Writing the release page is therefore a **required cut step**,
alongside `poe changelog` and the version bump.

To bootstrap it, `scripts/draft_release_notes.py` turns the compiled `[version]`
section of `CHANGELOG.md` (plus the previous release page as a style exemplar and,
optionally, the milestone's closed issues) into a *first draft* you then edit:

```bash
uv run poe release-notes --version 0.4.0 --theme "Documentation generation grows up"
# no Anthropic SDK/key? add --bundle to emit a paste-ready prompt instead.
```

The draft is a starting point, never final copy — review for accuracy and voice
before shipping. The script never adds `anthropic` to Bengal's dependencies; it's
an opt-in dev tool.

## The audience boundary (what belongs in user-facing notes)

The reader of a release note is a **user of the tool**, not a maintainer of it.
They did not sit in our planning, do not run our tests, and will never read our
CHANGELOG looking for the audit that found a bug. They want one thing: **what
changed for me, and what do I do about it.** Two filters get you there.

### The user-facing test

A change earns a place in user-facing notes only if the user can *observe* it.
Apply this test to every line:

1. Does the user **type / import / call / unpack** it? — a CLI command or flag, a
   config key or value, a frontmatter key, a template function, a public import
   path, a factory parameter, a documented return-tuple contract.
2. Does the user **see / grep / find** it? — text in build output, an emitted
   file, an error string, a fingerprinted filename, a surfaced health/error code.
3. Does the user have to **act** on it? — a migration, a dependency-floor bump, a
   default flip, a removed import, an opt-in flag they can now set.

If a change answers **none** of these, it is internal. It belongs in `CHANGELOG.md`
at most, and usually **nowhere** in user-facing notes.

The test cuts both ways — it also *protects* internal-looking detail that is
genuinely user-facing. Do **not** strip these just because they look like code:

- Public surface the user codes against: `Site.from_config(config_path=...)`,
  `from bengal.content_types import register_strategy`, `{{ data_table(...) }}`,
  `minify = false` under `[assets]`, a `parse_with_toc` 4-tuple contract.
- Output the user sees on disk or in the terminal: `atom.xml`, `versions.json`,
  a fingerprinted `style.95230091.css`, health codes like `H621`.
- An internal symbol that **is the literal symptom** the user saw and could grep:
  *"the error `'PageProxy' object has no attribute 'meta_description'` no longer
  occurs"* keeps `PageProxy` because the user saw that exact string — whereas
  "`PageProxy` now wraps `PageCore`" leaks, because the user never sees that.
- Numbers that measure the **user's** outcome: "caches are 12–14× smaller, load
  10× faster", "rebuilds 50 pages instead of 1,000".

### Never leak: internal coinage and process meta

User-facing notes **never** reference how the work was organized, discovered,
tested, counted, or shipped. This is a hard rule, not a preference. Specifically,
never write:

- **Internal coinage.** "Phase 2", "Phase 1A", "Sprint B3", "saga S13.4",
  "epic #350", RFC / plan-file names (`plan/epic-agent-dx-polish.md`), branch
  slugs, codenames ("barrier-owns-globals"). These name *our* process; the reader
  has no model for them.
- **Process / journey narration.** "a repo-wide audit", "the audit's expansion
  pass", "surfaced right after the cut", "discovered in CI", "the largest
  structural change in X's history", "the first/second patch off Y".
- **Project bookkeeping.** Fix/file/line counts ("thirteen fixes", "205 lines of
  dead code removed"), ty-diagnostic floors ("2207 → 2204"), health-score
  percentages, test counts ("11,600+ examples").
- **Contributor-only churn.** Test additions, guard tests, de-vacuumed
  assertions, CI gates, import-linter contracts, behavior-preserving refactors,
  dead-code removal, type/lint hygiene, and **our own release/build tooling**
  (`make gh-release`, Towncrier adoption, `python-publish.yml`). A user installs
  the package; they never run any of it.
- **Untranslated mechanism.** An internal class, module path, or log-event key as
  the *subject* of a change ("the `WriteBehind` collector is gated on parallel
  builds", "`cached_links_restore_failed` is logged"). State the **effect**, not
  the plumbing.
- **Off-by-default scaffolding with no caller.** A module added for an in-progress
  effort that is wired off and leaves the build byte-identical has nothing for a
  user to observe yet.

| Don't write (leak) | Write (user-facing) |
|---|---|
| "0.4.2 is the second patch off 0.4.0 — thirteen fixes from the same repo-wide audit." | "0.4.2 makes failures honest: errors that used to vanish now surface as build warnings, and writes are crash-safe. No breaking changes." |
| "### Tooling — `make gh-release` built the title from a greedy `grep`…" | *(delete — maintainer release tooling)* |
| "De-vacuumed a `hasattr(...)` assertion and added validators to the contract suite." | *(delete — contributor-only test change)* |
| "lazy Kida context is preserved, fingerprint fast paths are reused, version membership is memoized." | "Incremental builds are faster and rebuild fewer pages." |
| "### i18n Gettext Workflow (Phase 1A)" | "### i18n Gettext Workflow" |
| "Re-armed the composition-over-inheritance guard tests so they inspect `RuntimePage`." | *(delete — list the user-visible bug it now guards, if any, under Fixed)* |

### Citing issues

A GitHub issue is the **one sanctioned outward pointer** — and only when the link
earns its place for the reader:

- **Cite a real, numeric issue or PR** (`#449`) when a user would actually click
  it: to track a known limitation, see a reproduction, or follow remaining work.
- **Don't make `(#NNN)` a per-bullet reflex.** If the link adds nothing for the
  reader, drop it. Traceability is the CHANGELOG's job, not the release page's.
- **Never cite a non-numeric branch slug** (`#reproducible-builds`) or a plan-file
  path — they resolve to nothing for an outside reader. Prevent this at the
  source: name issue-less fragments `+slug.<type>.md` (the leading `+` tells
  Towncrier there is no issue, so it renders no reference) rather than
  `slug.<type>.md` (which renders as a fake `` `#slug` ``).

## Progressive disclosure (release-page structure)

The release page tells the release's story in **layers**. Each layer is
self-sufficient; detail is *available* but never *front-loaded*. A reader who
stops after the first line still understands the release; a reader who needs
specifics keeps descending; the exhaustive record always lives in `CHANGELOG.md`.

1. **Theme hook** — one paragraph naming the bigger picture of this release. If a
   reader reads only this, they should get it.
2. **Highlights** — 4–7 themed `###` subsections, each led by what a *user* can
   now do ("you can now …"), with short examples where they help. Group related
   changes; do not transcribe every fragment.
3. **Condensed lists** — Added / Changed / Fixed / Removed as a skim layer: one
   short bullet per *user-meaningful* change. Compress aggressively; omit
   internal-only work entirely.
4. **Upgrading** — the install command plus any action the user must take
   (migrations, default flips, removed imports, dependency bumps).

## B-Stack release voice

One voice across every ecosystem package (Kida, Patitas, Rosettes, Bengal, Chirp,
Pounce, chirp-ui) so a reader of any changelog feels the same hand. The voice is
**confident, plain, concrete, and benefit-first — and a little delightful.** The
reader should *enjoy* reading it and *trust* it.

- **Lead with the outcome.** First the user-visible benefit, then the detail:
  "Autodoc now cross-links symbol names to their pages" before any mechanism.
- **Present tense, active voice.** "Add …", "Fix …", "Deprecate … in favor of …".
- **Concrete over abstract.** Name the real command, key, or effect — never
  "improvements", "various fixes", or "better architecture".
- **No marketing fluff and no hedging.** Cut "blazing", "massive", "seamless",
  "the largest … ever"; cut "should now", "we believe". Say what is true, plainly.
- **Delight is clarity plus a little warmth.** A confident, well-chosen sentence
  that respects the reader's time *is* the delight — not exclamation points. The
  bar: the reader finishes a note and knows exactly what changed and why it's good.
- **Stay visually aligned across repos.** Same heading level (`## [version] -
  date`), same section order (Added → Changed → Deprecated → Removed → Fixed →
  Security), same release-page shape.

## Release titles and themes

A release theme should describe **what the release contains or enables for the
user** — a durable, content-anchored phrase — not pronounce a **verdict on the
project's quality, maturity, or past behavior.** Verdict-themes read as either
self-congratulation or confession, and they age badly: the moment the same class
of work recurs (and correctness, observability, performance, docs-accuracy, and
security *always* recur — they are perennial, never "done"), the triumphant title
looks naive or repetitive, and you are stuck writing "Honest internals 2".

**The test:** *could a future release plausibly need this same theme again?* If
yes, the theme is overclaiming — reframe it to the concrete content.

Avoid:

- **Maturity / coming-of-age declarations** — "grows up", "production-ready",
  "all grown up", "enterprise-grade".
- **Virtue-achieved claims** for perennial qualities — "Honest internals", "Rock
  solid", "Bulletproof", "Correct now".
- **Confessions** — "Stop shipping wrong output" advertises that you *were*
  shipping wrong output. State the win, not the prior sin.
- **Release-to-release arcs** — "Where 0.4.1 stopped X, 0.4.2 stops Y".

Prefer content/capability anchors, and scale boldness to release size — a major
(`X.0`) can carry a confident *capability* headline; a patch should stay plainly
descriptive (there is no shame in a repeatable theme like "Correctness and
data-safety fixes"):

| Verdict-theme (avoid) | Content theme (prefer) |
|---|---|
| "Documentation generation grows up" | "Cross-linked autodoc and richer OpenAPI models" |
| "Stop shipping wrong output" | "Valid structured data and honored configuration" |
| "Honest internals" | "Visible build failures and crash-safe writes" |

Titles are a judgment call, not a lint target — the steward and this section own
them.

## Enforcement (so it gets applied automatically)

These rules are carried to the point of work, not left in a doc nobody opens:

- **`changelog.d/AGENTS.md`** — steward for *fragment authoring*. Auto-loaded when
  an agent works in the fragment folder (i.e. every time a fragment is written).
- **`site/content/releases/AGENTS.md`** — steward for *release-page distillation*.
  Auto-loaded when an agent edits a release page.
- **`scripts/draft_release_notes.py`** — encodes the audience boundary and voice in
  the generator's system prompt, so the *first draft* is clean rather than scrubbed
  after the fact.
- **`poe changelog-lint`** (`scripts/lint_changelog_voice.py`) — deterministically
  blocks the highest-precision leaks (internal-coinage tokens, non-numeric `(#…)`
  issue references, plan-file / saga-step references) in fragments and release
  pages. Wired into the Changelog CI workflow for fragments.

Other ecosystem repos adopt the same set: copy this doc, the two `AGENTS.md`
stewards, the draft-script system prompt, and the lint. They are written
repo-agnostically for exactly that.

## Pre-publish checklist

Run this skim-gate before shipping any fragment or release page:

- [ ] Every line passes the **user-facing test** (type / import / see / act).
- [ ] No **internal coinage** (phase / sprint / saga / epic / plan-file / branch
      slug / codename) and no process-journey narration.
- [ ] No **counts, scores, or release-arc** framing ("Nth patch off …", "N fixes").
- [ ] No **contributor-only** test / CI / refactor / tooling entries.
- [ ] Mechanism is **translated to a user-visible effect**.
- [ ] Issue references are **numeric** and **earn the click**.
- [ ] (Release page) reads **top-down** — hook → highlights → lists → upgrade — and
      the hook alone tells the story.
- [ ] (Release page) the **theme describes content**, not a verdict on quality or
      maturity (no "grows up", "Honest internals", "Stop shipping wrong output").
- [ ] `poe changelog-lint` is clean.

## Rollout order (suggested)

1. **chirp**, **kida**, **bengal** — highest churn; establish CI + label pattern.
2. **pounce**, **patitas**, **chirp-ui**, **rosettes** — copy the winning template and tasks.

## Reference implementation

The same Towncrier layout (`changelog.d/`, fragment types, `poe changelog`) is already exercised in the Dori project's workflow. Git hosting may differ (GitLab labels vs GitHub); keep **fragment rules** identical and adapt **CI checks** to each host.

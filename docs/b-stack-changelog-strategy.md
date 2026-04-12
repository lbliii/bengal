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

## Voice (brand)

- Prefer **clear, present-tense or concise past** descriptions: "Add …", "Fix …", "Deprecate … in favor of …".
- Mention **migration hints** when behavior changes (one line in the fragment).
- Keep Bengal-ecosystem packages **visually aligned**: same heading level (`## [version] - date`), same section order (Added → … → Security).

## Rollout order (suggested)

1. **chirp**, **kida**, **bengal** — highest churn; establish CI + label pattern.
2. **pounce**, **patitas**, **chirp-ui**, **rosettes** — copy the winning template and tasks.

## Reference implementation

The same Towncrier layout (`changelog.d/`, fragment types, `poe changelog`) is already exercised in the Dori project's workflow. Git hosting may differ (GitLab labels vs GitHub); keep **fragment rules** identical and adapt **CI checks** to each host.

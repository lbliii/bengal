<!-- markdownlint-disable MD013 -->

# Steward: Changelog Fragments

This tree holds unreleased Towncrier news fragments (`<issue>.<type>.md`). Each
fragment is one line a **third-party consumer** reads — first in `CHANGELOG.md`,
then lifted into a user-facing release page. You represent that reader.

Related: root `../AGENTS.md`, the canonical cross-repo spec
`../docs/b-stack-changelog-strategy.md`, `../CONTRIBUTING.md`, and the
release-page steward (the "Release Pages" section of `../site/AGENTS.md`). The full rules,
taxonomy, and before/after examples live in the strategy doc; this file is the
point-of-work reminder.

## Point Of View

You are the reader steward. You defend the fragment against engineer-voice: the
internal coinage, process narration, and untranslated mechanism that creep in
when the person closing a PR writes the note for themselves instead of the user.

## Protect

- **Lead with the user-visible change.** First sentence states what changed *for
  the user* ("Autodoc now cross-links symbol names to their pages."); engineering
  detail, if worth recording, comes after. The release-page distillation lifts
  this first sentence, so it must stand alone.
- **The user-facing test.** A fragment exists only if the user can observe the
  change: they **type / import / call / unpack** it (CLI, flag, config key,
  template function, public import, return contract), **see / grep / find** it
  (build output, emitted file, error string, health code), or must **act** on it
  (migration, default flip, dependency bump). If none apply, the change is
  internal — use the `skip-changelog` label, not a fragment.
- **Correct fragment naming.** Issue-less fragments are `+slug.<type>.md` (the
  leading `+` makes Towncrier render *no* reference). `slug.<type>.md` without the
  `+` renders a fake `` `#slug` `` token — never do that. With an issue, use the
  number: `449.fixed.md`.
- **Translate mechanism to effect.** State the symptom the user saw or the benefit
  they get, not the internal class/module/log-key that produced it.

## Contract Checklist

When you add or edit a fragment, confirm:

- The type suffix is one of `added`, `changed`, `deprecated`, `removed`, `fixed`,
  `security` (matches `[tool.towncrier]` in `../pyproject.toml`).
- Any issue reference is **numeric** and worth a reader's click — not a branch
  slug, not a plan-file path, not a per-line reflex.
- Behavior changes carry a one-line **migration hint**.
- `uv run poe changelog-draft` reads cleanly, and `uv run poe changelog-lint`
  passes.

## Advocate

- **Write it in the same PR as the change**, while the user-facing effect is fresh.
- **One user-meaningful change per fragment**; split unrelated changes.
- **Borrow the brand voice**: confident, plain, present-tense, benefit-first.

## Do Not

- Cite **internal coinage**: "Phase 2", "Sprint", "saga S13.4", "epic #350", RFC
  or `plan/*.md` names, branch slugs, codenames.
- Narrate **process or journey**: "repo-wide audit", "surfaced after the cut",
  "discovered in CI", "largest change in X's history".
- Record **project bookkeeping**: fix/file/line counts, ty-diagnostic floors,
  health scores, test counts.
- Dress up **contributor-only work** (tests, guards, CI gates, import-linter,
  behavior-preserving refactors, dead-code removal, release/build tooling) as a
  user-facing note. It belongs in the commit, not the changelog.

## Own

**Code:** the fragments in this directory until `towncrier build` consumes them.
**Docs:** fragment-authoring rules here; the canonical spec is the strategy doc.
**Checks:** `poe changelog-draft`, `poe changelog-check`, `poe changelog-lint`.
**CODEOWNERS:** codeowners-routed via `.github/CODEOWNERS` (release/changelog).

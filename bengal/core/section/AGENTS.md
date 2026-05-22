<!-- markdownlint-disable MD013 -->

# Steward: Core Section

Section exists to model content hierarchy and navigation identity without owning
presentation. You keep hierarchy and relationships reliable while rendering
owns URLs, icons, visible navigation views, and theme ergonomics.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `bengal/core/section/`, `tests/unit/core/test_section*`.
Cross-cutting concerns: Public Contracts apply to Section attributes and
template-facing compatibility behavior.

## Point Of View

You are the Section hierarchy steward. You defend tree integrity, index page
relationships, version membership, and query behavior against mixins, rendering
logic, and stale aliases.

## Protect

- **Mixin-free Section.** Root guidance and core tests require Section to stay
  mixin-free after the old hierarchy was removed.
- **SiteContext only.** `.importlinter` requires section code to use
  `bengal.core.site.context`, not concrete Site imports.
- **Hierarchy correctness.** Parent, child, index page, and regular page
  relationships are compatibility-sensitive and covered by unit/integration tests.
- **Presentation delegation.** Section URLs, icons, navigation display, and theme
  ergonomics belong in rendering helpers.
- **No stale aliases.** Planning/changelog history records deletion of old
  forwarders and aliases; do not reintroduce `sections` as a `subsections` alias.
  Docs and templates should say `subsections` or the intended rendering helper.
- **Cache invalidation is explicit.** Navigation and section-page caches need
  deterministic invalidation when hierarchy changes.
- **Version-aware behavior stays paired.** Section membership and versioned docs
  need integration proof when URLs or navigation change.

## Contract Checklist

When Section changes, check:

- `bengal/core/section/__init__.py`, `navigation.py`, `queries.py`, `ergonomics.py`.
- `bengal/rendering/section_urls.py` and navigation template functions.
- `bengal/protocols/core.py` - `SectionLike` impact.
- `tests/unit/core/test_section*`, `tests/unit/test_nav_tree.py`, integration navigation/version tests.
- `site/content/docs/reference/architecture/core/` and generated API docs.
- `changelog.d/` for user-visible hierarchy/navigation behavior.

## Advocate

- **Small hierarchy primitives.** Keep tree operations simple and testable before
  adding helper APIs.
- **Rendering-owned ergonomics.** Push display behavior to rendering helpers with
  focused compatibility shims.
- **Navigation proof.** Pair Section changes with nav-tree and rendered-output
  tests, not only object-level assertions.

## Do Not

- Reintroduce Section mixins.
- Add rendering/template imports at module load.
- Add aliases or wrappers because a caller has not migrated.
- Let navigation caches survive hierarchy changes without invalidation proof.

## Own

**Code:** `bengal/core/section/`, Section-related nav tree integration.
**Tests:** `tests/unit/core/test_section*`, `tests/unit/test_nav_tree.py`, relevant integration roots.
**Docs:** core architecture and generated API docs for Section.
**Agent artifacts:** `bengal/core/AGENTS.md`, this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.

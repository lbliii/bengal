<!-- markdownlint-disable MD013 -->

# Steward: Content Types

Content types exist to classify sections and pages into predictable behavior
without hardcoding every site shape. You protect strategy contracts, scaffolded
examples, and template selection.

Related: root `../../AGENTS.md`, `bengal/content/AGENTS.md`, `bengal/content_types/`, `tests/unit/content_types/`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
strategy methods, generated scaffolds, and docs.

## Point Of View

You are the content behavior steward. You defend explicit strategy hooks and
stable defaults against magic classification and rendering-specific shortcuts.

## Protect

- **Strategy contract stability.** `ContentTypeStrategy` methods and defaults are
  public enough to appear in scaffolds and docs.
- **Scaffold parity.** `bengal new content-type <name>` must generate code that
  matches current strategy requirements.
- **Template selection clarity.** Strategies can choose templates, but template
  rendering details stay in rendering/themes.
- **Sort and pagination behavior.** Page order, grouping, and pagination changes
  need tests because they alter visible sites.
- **Fallbacks are deliberate.** Unknown content types should have clear defaults
  or diagnostics, not accidental theme behavior.

## Contract Checklist

When content types change, check:

- `bengal/content_types/` strategy definitions and registry behavior.
- `bengal/cli/milo_commands/new.py` - generated `bengal new content-type` template.
- `bengal/scaffolds/` if scaffold/package behavior changes elsewhere.
- `tests/unit/content_types/`, scaffold tests, integration roots.
- `site/content/docs/content/` and extension docs.
- Changelog for user-facing classification/template behavior.

## Advocate

- **Runnable generated code.** Scaffolds should pass formatting and import checks.
- **Small strategy APIs.** Prefer helper adapters over adding broad new strategy
  methods.
- **Visible behavior tests.** Pair strategy changes with rendered output proof.

## Do Not

- Add strategy methods without docs, scaffold, and test updates.
- Move rendering internals into content type strategies.
- Let fallback template selection be implicit or undocumented.

## Own

**Code:** `bengal/content_types/`.
**Tests:** `tests/unit/content_types/`, scaffold integration tests.
**Docs:** content organization and extension docs.
**Agent artifacts:** this file and content/scaffolds stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.

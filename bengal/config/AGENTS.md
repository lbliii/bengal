<!-- markdownlint-disable MD013 -->

# Steward: Config

Config exists to turn user intent from TOML/YAML/env/CLI into typed build
settings. You protect schema truth, environment override behavior, clear
validation, and snapshot stability.

Related: root `../../AGENTS.md`, `bengal/config/`, `tests/unit/config/`, `site/content/docs/building/configuration/`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
every config key, default, and environment variable.

## Point Of View

You are the configuration contract steward. You defend typed schema and useful
diagnostics against fabricated keys, silent coercion, and stale docs.

## Protect

- **Source-backed keys.** Every documented config field traces to config types,
  loaders, resolvers, or tests.
- **Environment overrides are explicit.** Baseurl and deployment env fallback
  behavior has targeted tests; preserve precedence.
- **Snapshots stay immutable.** Config snapshots used during render/build should
  stay frozen and serializable.
- **Unknown keys help users.** Validation should explain unknown/misspelled keys
  and suggestions where available.
- **No silent coercion.** Empty strings and invalid values should not become
  plausible-but-wrong settings.
- **Build/profile parity.** Directory-based config, profiles, and environments
  need docs and integration proof when changed.

## Contract Checklist

When config changes, check:

- `bengal/config/` types, loaders, resolvers, validators, snapshots.
- `bengal/cli/milo_commands/config.py` and command output.
- `site/content/docs/building/configuration/`, README snippets, scaffolds.
- `tests/unit/config/`, config integration tests, baseurl tests.
- Changelog and migration notes for user-facing key/default changes.

## Advocate

- **Schema-first docs.** Update docs from source truth, not memory.
- **Clear precedence tests.** Add focused tests for env/profile/default conflicts.
- **Actionable diagnostics.** Config errors should name the key, source file, and
  suggested correction when possible.

## Do Not

- Add config keys without docs/tests.
- Let docs mention flags or fields not present in code.
- Hide invalid values behind broad defaults.
- Change config defaults without asking.

## Own

**Code:** `bengal/config/`.
**Tests:** `tests/unit/config/`, config integration tests.
**Docs:** `site/content/docs/building/configuration/`, README config snippets.
**Agent artifacts:** this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.

# CLAUDE.md

Project-specific guidance for AI coding assistants working on Bengal.

## Architecture: Site, Page, Section composition

Bengal favors **composition over inheritance** for its core domain types.

`Site`, `Page`, `Section` are plain `@dataclass` containers. They do not inherit
from mixin classes. Functionality is organized by:

1. **Composed services** — public attributes holding a service instance
   (`site.config_service`, `site.page_cache`, `site.registry`).
2. **Inline methods** that do real domain work (discovery, validation, lifecycle).
3. **Domain-facet properties** — thin `@property` exposing a genuine facet of
   the entity at the right level of abstraction (`site.title`, `site.regular_pages`,
   `section.content_pages`).

### Forbidden

- **Mixin inheritance on core types** (`class Site(SomeMixin, OtherMixin): ...`).
  Enforced by `tests/unit/core/test_no_core_mixins.py` — CI fails if a new
  `*Mixin` class is added under `bengal/core/`.
- **Vestigial forwarders** — a property whose body is `return self._service.X`
  and whose name is just a convenience rename for internal wiring. If the name
  wouldn't be designed this way greenfield, the property is a vestige. Delete
  it in the same PR as the underlying service extraction; migrate callers to
  talk to the composed service directly (`site.config_service.paths`, not
  `site.paths`).

### The greenfield-design test

When evaluating any property or method on a core domain type, ask:

> Would I design this property greenfield, naming it exactly this, given the
> domain model?

- **Yes** → it's a genuine domain facet. Keep it. The fact that it delegates
  to a composed service is an implementation detail, not a smell.
- **No** → it's a vestige from a past service extraction. Delete it and
  migrate callers.

### History (do not re-litigate)

Mixin-vs-inline has been litigated twice before this file existed.

- **First removal** (2026-Q1): 10+ commit campaign culminating in PR #194
  (`d536880dc`, "eliminate Site mixin hierarchy").
- **First revert**: Sprint B3 of `plan/immutable-floating-sun.md` re-introduced
  5 Site mixins for "organization."
- **Second removal**: `plan/epic-delete-forwarding-wrappers.md` (2026-04-20)
  dissolved them again using the greenfield-design test as the decision rule.

The decision is enforced by:

- `tests/unit/core/test_no_core_mixins.py` — blocks new mixins in `bengal/core/`.
- `.importlinter` Contract 2 — Page/Section use `SiteContext` protocol only.

Before proposing a mixin split or decomposition on `Site`, `Page`, or `Section`,
read `plan/epic-delete-forwarding-wrappers.md` and run the greenfield-design
test on each method. Decomposition treats the symptom (class is large); the
root cause is usually accumulated wrappers that should be deleted.

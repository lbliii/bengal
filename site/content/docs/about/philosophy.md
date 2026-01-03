---
title: Project Philosophy
nav_title: Philosophy
description: Bengal prioritizes correctness over compatibility. What that means for upgrades and contributions.
weight: 1
type: doc
icon: lightbulb
tags:
- philosophy
- compatibility
- design
---

**Correctness over compatibility. Evolution over preservation. Explicit over silent.**

Bengal promises progress, not stability. When we discover a better approach, we implement it—even if that means breaking changes.

---

## The Core Bargain

:::{list-table}
:header-rows: 1
:widths: 50 50

* - You Control
  - We Control
* - When to upgrade
  - What changes
* - Whether to migrate
  - What gets deprecated
* - Staying on older versions
  - Moving the project forward
:::

Not ready to upgrade? Stay on your current version. Ready? Read the release notes and migrate.

---

## Why This Approach

### Wrong output is worse than a failed build

A site that renders incorrectly is harder to catch than a site that fails to build. Clear error messages pointing to what changed are a feature.

### Compatibility layers become the problem

Hidden shims cause subtle bugs, slow development, and become their own maintenance burden. Bengal deletes known mistakes instead of preserving them.

<details>
<summary><strong>Example</strong>: Config key migration</summary>

When Bengal renamed `site.base_path` to `site.baseurl`, we:

1. Removed the old key entirely
2. Added a clear error: `"site.base_path" is no longer supported. Use "site.baseurl" instead.`
3. Documented the change in release notes

We did **not** silently map the old key to the new one. That approach would have hidden the problem until some future version removed the shim, breaking sites with no warning.

</details>

### Honest expectations

Projects that claim backwards compatibility often break things silently or stagnate under legacy code. Bengal's stance: we control what changes, you control when you upgrade.

---

## What This Means

### For Users

| If you expect... | Expect instead... |
|------------------|-------------------|
| Seamless upgrades | Read release notes before upgrading |
| Old config always works | Migrate config when prompted |
| Graceful deprecation | Clear errors pointing to fixes |
| Consistent cross-version behavior | Each version defines its behavior |

### For Contributors

| If you expect... | Expect instead... |
|------------------|-------------------|
| Avoid breaking changes | Make the right change, document it |
| Maintain compatibility shims | Delete deprecated code when ready |
| Support all past behavior | Support current behavior well |

---

## Versioning

Bengal uses semantic versioning with one caveat: **pre-1.0 releases may include breaking changes in any minor version**.

| Version | Meaning |
|---------|---------|
| **0.x.y** (current) | Any release may break things—read release notes |
| **1.0+** | Major = breaking, Minor = features, Patch = fixes |

Every release includes release notes. Breaking changes include migration guides.

:::{tip}
Pin your version in `pyproject.toml` or `requirements.txt` (e.g., `bengal==0.1.7`) to prevent unexpected upgrades. Upgrade deliberately by reviewing the changelog first.
:::

---

## Who Bengal Is For

Bengal prioritizes **architectural integrity** over **broad enterprise adoption**.

:::{list-table}
:header-rows: 1
:widths: 50 50

* - Good fit
  - May not fit
* - You value a clean, evolving system
  - You need multi-year stability guarantees
* - You read release notes before upgrading
  - You expect seamless, zero-effort upgrades
* - You prefer explicit errors over silent failures
  - You need graceful degradation for legacy configs
:::

---

## Summary

| Principle                   | Meaning                                      |
| --------------------------- | -------------------------------------------- |
| Correctness first           | We fix mistakes even when it breaks things   |
| Fail loudly                 | Errors are explicit, not silent degradation  |
| User control                | You choose when to upgrade                   |
| No hidden layers            | What you see is what you get                 |
| Evolution over preservation | The project moves forward                    |

Bengal is not for everyone—and that's intentional. By being explicit about trade-offs, we can build the tool we believe in rather than the tool that satisfies everyone poorly.

---

:::{seealso}
- [[docs/about/faq|FAQ]] — Common questions about compatibility and upgrades
- [[changelog|Changelog]] — Version history with migration guides
- [[docs/about/limitations|Limitations]] — Known constraints and workarounds
:::

---
title: Project Philosophy
nav_title: Philosophy
description: Bengal's approach to evolution, compatibility, and design decisions.
weight: 1
type: doc
icon: lightbulb
tags:
- philosophy
- compatibility
- design
---

# Project Philosophy

Bengal prioritizes **correctness, clarity, and architectural integrity** over long-term compatibility.

Each release represents the best solution we know how to deliver at that time. As our understanding evolves, interfaces and behavior may change.

---

## Core Principles

### Evolution Over Preservation

Bengal is designed to evolve rapidly toward better solutions.

We do not treat backwards compatibility as a primary goal. When existing behavior no longer reflects the best design or understanding of the problem, it may be changed or removed.

### Explicit Standards

Each release defines its own standards. By upgrading, users agree to meet those standards and update their usage accordingly.

We do not provide:

- Hidden compatibility layers
- Silent fallbacks
- Long-lived shims for deprecated behavior

When something changes, it will **fail loudly and explicitly**.

### User Control

Users control when they upgrade. Maintainers control what changes.

If you are not ready to upgrade, you may remain on an older version. This policy allows the project to move forward without preserving known mistakes.

---

## What This Means In Practice

### For Users

| Expectation | Reality |
|-------------|---------|
| Upgrading is seamless | Upgrading requires reading release notes and making changes |
| Old config always works | Old config may require migration |
| Deprecated features degrade gracefully | Deprecated features fail with clear error messages |
| All versions behave the same | Each version defines its own behavior |

### For Contributors

| Expectation | Reality |
|-------------|---------|
| Avoid breaking changes | Make the right change, document it clearly |
| Maintain compatibility shims | Delete deprecated code when it's time |
| Support all past behavior | Support current behavior well |

---

## Why This Approach?

### Avoids Technical Debt

Compatibility layers accumulate. They become their own maintenance burden. They cause bugs. They slow development. Giving maintainers explicit permission to delete known mistakes keeps the codebase healthy.

### Enables Honest Communication

Most projects *claim* backwards compatibility but then either:

- Break things silently anyway
- Stagnate under the weight of legacy code
- Accumulate hidden shims that become their own problem

Bengal's stance says upfront: *you control when you upgrade, we control what changes*. That's honest.

### Prioritizes Correctness

For a static site generator, incorrect output is worse than a breaking change. A site that builds but renders wrong is harder to catch than a site that fails to build.

Clear error messages pointing to what changed are a feature, not a bug.

---

## Versioning

Bengal uses semantic versioning to signal the nature of changes:

- **Major versions** (1.0 → 2.0): May include significant breaking changes
- **Minor versions** (1.0 → 1.1): May include smaller breaking changes with migration paths
- **Patch versions** (1.0.0 → 1.0.1): Bug fixes, unlikely to break anything

Release notes document all changes. Migration guides accompany breaking changes.

---

## The Trade-off

This philosophy trades **broad enterprise adoption** for **architectural integrity**.

Organizations requiring multi-year stability guarantees may find Bengal's approach challenging. That's a valid concern—and Bengal may not be the right choice for every project.

Bengal is for users who value a **clean, evolving system** over frozen behavior. If that's you, welcome.

---

## Summary

:::{list-table}
:header-rows: 1

* - Principle
  - What It Means
* - Correctness first
  - We fix mistakes even when it breaks things
* - Fail loudly
  - Errors are explicit, not silent degradation
* - User control
  - You choose when to upgrade
* - No hidden layers
  - What you see is what you get
* - Evolution over preservation
  - The project moves forward
:::



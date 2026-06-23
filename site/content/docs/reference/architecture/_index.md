---
title: Architecture
description: High-level Bengal architecture overview for contributors
weight: 50
icon: folder
tags:
- architecture
---

# Architecture Overview

Bengal is organized as small subsystems with clear boundaries. This page orients
**contributors and extenders**; end users should stay in [[docs/build-sites|Build Sites]]
and [[docs/reference|Reference]].

## Contributor documentation

The full architecture tree (core pipeline, rendering, tooling, meta) lives in the
repository at [`docs/architecture/`](https://github.com/lbliii/bengal/tree/main/docs/architecture/)
— not duplicated on the public docs site.

## Subsystems at a glance

| Subsystem | Package | Docs |
|-----------|---------|------|
| CLI & config | `bengal/cli/`, `bengal/config/` | [Tooling](https://github.com/lbliii/bengal/tree/main/docs/architecture/tooling/) |
| Discovery & content | `bengal/content/` | [Core](https://github.com/lbliii/bengal/tree/main/docs/architecture/core/) |
| Build orchestration | `bengal/orchestration/` | [Pipeline](https://github.com/lbliii/bengal/tree/main/docs/architecture/core/pipeline/) |
| Rendering & themes | `bengal/rendering/` | [Rendering](https://github.com/lbliii/bengal/tree/main/docs/architecture/rendering/) |
| Dev server | `bengal/server/` | [Server](https://github.com/lbliii/bengal/tree/main/docs/architecture/tooling/server/) |

## Lookup references (on-site)

- [[docs/reference/directives|Directives]]
- [[docs/reference/kida-syntax|Kida Syntax]]
- [[docs/reference/architecture|Architecture Overview]] — High-level contributor map

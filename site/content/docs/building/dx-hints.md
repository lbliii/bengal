---
title: DX Hints
nav_title: DX Hints
description: Contextual tips for Docker, WSL, Kubernetes, and development environments
weight: 45
---

# DX Hints

Bengal surfaces contextual tips when running in containers, WSL, or other environments. Hints help you avoid common configuration mistakes and improve the development experience.

## When Hints Appear

Hints are shown during:

- **Build** — After `bengal build` completes (as a tip line)
- **Serve** — In the dev server startup message
- **Config** — When loading configuration (logged via structured logger)

At most one hint is shown per context by default. Use `max_hints` in the collector API for more.

## Available Hints

| Hint ID | Condition | Message |
|---------|-----------|---------|
| `docker_baseurl` | Running in Docker with empty baseurl | Set `BENGAL_BASEURL` for correct canonical URLs |
| `kubernetes_baseurl` | Running in Kubernetes with empty baseurl | Set `BENGAL_BASEURL` for correct canonical URLs |
| `wsl_watchfiles` | WSL + dev server | If live reload is unreliable, try `WATCHFILES_FORCE_POLLING=1` |
| `dev_server_container` | Docker + host=localhost + serve | For host access, use `bengal serve --host 0.0.0.0` |
| `gil` | GIL enabled (Python free-threading) | Tip about GIL status and migration |

## Opt-Out

Disable hints via environment variables:

| Variable | Effect |
|----------|--------|
| `BENGAL_HINTS=0` | Disable all hints |
| `BENGAL_NO_HINTS=1` | Disable all hints |
| `BENGAL_HINT_DOCKER_BASEURL=0` | Disable the `docker_baseurl` hint |
| `BENGAL_HINT_KUBERNETES_BASEURL=0` | Disable the `kubernetes_baseurl` hint |
| `BENGAL_HINT_WSL_WATCHFILES=0` | Disable the `wsl_watchfiles` hint |
| `BENGAL_HINT_DEV_SERVER_CONTAINER=0` | Disable the `dev_server_container` hint |
| `BENGAL_HINT_GIL=0` | Disable the GIL hint |

Per-hint opt-out uses the pattern `BENGAL_HINT_{ID}=0` where `{ID}` is the hint ID in UPPER_SNAKE_CASE (e.g. `docker_baseurl` → `DOCKER_BASEURL`).

## Examples

### Docker Build

When building inside Docker without `BENGAL_BASEURL` set:

```
Tip: Running in Docker. Set BENGAL_BASEURL for correct canonical URLs.
```

### WSL Dev Server

When running `bengal serve` on WSL with unreliable file watching:

```
Tip: On WSL. If live reload is unreliable, try WATCHFILES_FORCE_POLLING=1
```

### Kubernetes

When running in a Kubernetes pod without baseurl:

```
Tip: Running in Kubernetes. Set BENGAL_BASEURL for correct canonical URLs.
```

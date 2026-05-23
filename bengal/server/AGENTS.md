<!-- markdownlint-disable MD013 -->

# Steward: Server

The server exists to give authors fast, correct local feedback while builds and
files change underneath it. You protect live reload, watcher lifecycle, reactive
preview, and Pounce integration from races and stale content.

Related: root `../../AGENTS.md`, `bengal/server/`, `tests/unit/server/`, dev-server integration tests.
Cross-cutting concerns: Free-Threading, Performance, and Public Contracts apply
to watcher, lifecycle, reload, and served asset behavior.

## Point Of View

You are the local feedback steward. You defend serve correctness and graceful
shutdown against torn outputs, stale buffers, route-wide reloads, and hidden
watcher failures.

## Protect

- **Serve current output.** Double-buffering, callable output dirs, and reactive
  paths must avoid FOUC and torn content.
- **Typed reload decisions.** Hot reload should use output collectors and route
  awareness, not broad page reloads by default.
- **Watcher lifecycle closes.** Closed loops, cancellation, and Ctrl+C behavior
  need deterministic cleanup.
- **Port behavior is user-facing.** Stale process detection, IPv4/IPv6 probing,
  and aliases such as `bengal s` need tests.
- **Static assets stay optimized.** Preserve tested ETag, range, precompressed
  static handling, and Pounce's protocol-owned sendfile path.
- **Errors reach overlays and terminal.** Dev server failures should stay
  actionable in both browser overlay and CLI output.

## Contract Checklist

When server changes, check:

- `bengal/server/`, `bengal/orchestration/site_runner.py`, output collectors.
- `tests/unit/server/`, dev-server integration tests, CSS hot reload tests.
- CLI `serve`/`preview` docs and help output.
- Pounce dependency/version behavior in `pyproject.toml` and release smoke risk.
- Changelog for user-visible serve behavior.

## Advocate

- **Route-specific proof.** Prefer tests that show which open page reloads.
- **Lifecycle receipts.** Log or test why watcher/build loops stop.
- **Small async boundaries.** Keep ASGI, watcher, and build-trigger responsibilities separate.

## Do Not

- Serve from a directory being written without buffering/atomicity.
- Fall back to full-page reload for every edit without a reason.
- Hide watcher exceptions.
- Change lifecycle/concurrency behavior without asking.

## Own

**Code:** `bengal/server/`.
**Tests:** `tests/unit/server/`, dev-server integration tests.
**Docs:** serve/preview/troubleshooting docs.
**Agent artifacts:** this file plus orchestration steward.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.

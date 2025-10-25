## RFC: Async Link Checker (CLI + Ignores + JSON)

### Summary
Deliver a CI-grade external link checker integrated into Bengal’s health system and CLI. Implement an async HTTP checker with concurrency, retries/backoff, ignore policies, cache, and structured JSON output. Unify internal link validation and external checks behind a consistent interface.

### Goals
- `bengal health linkcheck` command with clear flags and JSON output for CI annotations.
- Async external link validation with bounded concurrency and robust timeouts/retries.
- Ignore policies: patterns, domains, and status ranges (e.g., ignore 5xx).
- Cache results within a run and across runs (TTL) to avoid flakiness and reduce load.
- Integration with existing health system and reports.

### Non-goals
- Full website availability monitoring (cron, SLAs). This is a build/CI tool.
- JavaScript execution or form-based session handling.

### CLI Design

Command:
```bash
bengal health linkcheck [PATH]
```

Flags:
- `--external-only` / `--internal-only`
- `--max-concurrency INT` (default: 20)
- `--per-host-limit INT` (default: 4)
- `--timeout FLOAT` (seconds, default: 10.0)
- `--retries INT` (default: 2)
- `--retry-backoff FLOAT` (seconds, base for exponential backoff; default: 0.5)
- `--exclude PATTERN` (repeatable; regex or glob)
- `--exclude-domain DOMAIN` (repeatable)
- `--ignore-status RANGE` (repeatable; e.g., `500-599`, `403`)
- `--format [console|json]` (default: console)
- `--output FILE` (when `--format=json`)

Exit codes:
- 0 = success (no errors)
- 1 = errors found (broken internal or non-ignored external)
- 2 = runtime failure (e.g., cannot read site)

### Configuration
`bengal.toml` (optional defaults):
```toml
[health.linkcheck]
max_concurrency = 20
per_host_limit = 4
timeout = 10.0
retries = 2
retry_backoff = 0.5
external = true
internal = true
exclude = ["^/api/preview/"]
exclude_domain = ["localhost"]
ignore_status = ["500-599"]
cache_ttl_hours = 24
```

CLI flags override config.

### Implementation Design

Components:
- `AsyncLinkChecker` (new): validates external links using `httpx.AsyncClient` (or `aiohttp`) with:
  - Shared connection pool; DNS caching
  - Semaphore for global concurrency and per-host limits
  - HEAD first, fallback to GET on 405/403/other cases
  - Exponential backoff with jitter
  - Cache layer (on-disk SQLite or JSONL) keyed by URL + ETag/Last-Modified (if available) + TTL
- `InternalLinkChecker` (refactor): resolve relative links to output paths; verify files and hash anchors exist (via page TOCs or extracted IDs).
- `LinkCheckOrchestrator`: merges internal + external results, applies ignore policies, and emits reports.
- `Click` command: `bengal health linkcheck` wires to orchestrator; supports `--format=json` with file output.

Ignore Policy:
- Patterns: regex against full URL (internal links normalized to absolute site paths)
- Domains: skip matches entirely
- Status ranges: treat as ignored (recorded as info) rather than errors

JSON Output Schema (v1):
```json
{
  "status": "passed|failed",
  "summary": {
    "checked": 123,
    "broken": 4,
    "ignored": 7,
    "duration_ms": 842
  },
  "results": [
    {
      "url": "https://example.com/a",
      "kind": "external",
      "status": 404,
      "reason": "Not Found",
      "first_ref": "/docs/page.md",
      "ref_count": 3,
      "ignored": false
    }
  ]
}
```

Performance Targets:
- 95th percentile link check under 5 minutes for 2k external links with defaults.
- Concurrency bounded to avoid rate limits; per-host limits default to 4.

Integration:
- Health system: add `LinkCheckValidator` that invokes orchestrator; respects site config.
- CLI: standalone `bengal health linkcheck` runs after build or against `site/public`.
- Reporting: console summary mirrors existing health output; JSON for CI consumption (e.g., GitHub annotations).

Testing Plan
- Unit: retry/backoff logic; status range parsing; ignore patterns/domains; cache TTL behavior.
- Unit (internal): link resolution to files/anchors; TOC anchor existence.
- Integration: spin up a local HTTP server with routes returning 200/301/404/500 and flaky endpoints; snapshot JSON.
- E2E: run against `examples/showcase` with a seeded set of external links and ensure stable results with cache.

Security/Compliance
- Respect robots.txt? Not needed for HEAD/GET of public docs; document as out of scope.
- User privacy: do not send custom headers; allow header injection via config if required.

Risks and Mitigations
- Flaky endpoints: retries with backoff; default ignore of 5xx via config example; cache to smooth CI.
- Rate limits: per-host concurrency; automatic HEAD first; backoff with jitter.
- Large sites: streaming JSON output; chunked processing to bound memory.

Rollout
- Phase 1: External checker + CLI + JSON; internal checker refactor; integrate with health.
- Phase 2: Persistent cache; per-domain policies and advanced analytics.

Implementation Outline
1) Implement `AsyncLinkChecker` and cache.
2) Refactor internal link validator to resolvable checks (files + anchors).
3) Orchestrator + Click command.
4) Tests (unit/integration/E2E) and examples.
5) Docs updates and CI recipe.

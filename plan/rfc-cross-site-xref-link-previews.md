# RFC: Cross-Site Link Previews for External References

| Field | Value |
|-------|-------|
| **Status** | Implemented |
| **Created** | 2026-01-11 |
| **Updated** | 2026-01-11 |
| **Author** | Bengal Team |
| **Priority** | P2 (Medium) |
| **Scope** | UX Enhancement |
| **Related** | `bengal/themes/default/assets/js/enhancements/link-previews.js`, `bengal/themes/default/templates/partials/link-previews.html`, `bengal/config/defaults.py` |
| **Confidence** | 92% 🟢 |

---

## Executive Summary

External reference links (`[[ext:project:target]]`) currently render as plain outbound links with no hover preview. Bengal already ships per-page JSON by default (`output_formats.per_page = ["json"]`) and GitHub Pages serves those JSON files with `Access-Control-Allow-Origin: *`, so cross-site fetches are allowed. This RFC proposes enabling hover previews for ecosystem xrefs by whitelisting trusted hosts and fetching their page JSON, while preserving the existing same-origin default and graceful degradation.

**Estimated Effort**: 1 week (1–2 days JS changes + tests, 1–2 days doc/config polish, 1–2 days QA)

---

## Problem Statement

- Xref links resolve to absolute URLs on other Bengal sites; the preview script currently blocks all cross-host links at `link-previews.js:132`:
  ```javascript
  if (link.hostname !== window.location.hostname) return false;
  ```
- Per-page JSON is already emitted and hosted for Kida and Rosettes, and GitHub Pages returns `Access-Control-Allow-Origin: *`, but the client never attempts the fetch.
- Result: ecosystem links have no previews, reducing discoverability and navigation speed.

---

## Goals

1. Show hover previews for trusted external Bengal sites referenced via `ext:` links.
2. Keep current behavior for untrusted hosts (no preview) and avoid new failure modes.
3. Remain opt-in/whitelisted to control network surface.

## Non-Goals

- No change to link resolution semantics or xref syntax.
- No preview generation for sites that do not publish per-page JSON.
- No generic cross-origin proxying.
- No `xref.json` fallback (defer to future RFC if needed).

---

## Proposed Solution

### 1) Configuration (opt-in host whitelist)

Add to `defaults.py` under `link_previews`:

```python
"link_previews": {
    # ... existing options ...
    "allowed_hosts": [],           # Empty = same-origin only (default)
    "allowed_schemes": ["https"],  # Reject non-HTTPS by default
    "host_failure_threshold": 3,   # Disable host after N consecutive failures
}
```

### 2) Client changes (`link-previews.js`)

**Relax hostname check** in `isPreviewable()`:

```javascript
// Current: same-host only
if (link.hostname !== window.location.hostname) return false;

// New: same-host OR whitelisted host with allowed scheme
const isSameHost = link.hostname === window.location.hostname;
const isAllowedHost = CONFIG.allowedHosts?.includes(link.hostname);
const isAllowedScheme = CONFIG.allowedSchemes?.includes(link.protocol.replace(':', ''));

if (!isSameHost && (!isAllowedHost || !isAllowedScheme)) return false;
```

**Cross-origin fetch with explicit security**:

```javascript
const fetchOptions = { signal: controller.signal };

// Cross-origin: explicit no-credentials, CORS mode
if (new URL(jsonUrl, window.location.origin).origin !== window.location.origin) {
  fetchOptions.credentials = 'omit';
  fetchOptions.mode = 'cors';
}

const response = await fetch(jsonUrl, fetchOptions);
```

**Failure tracking (per-host with threshold)**:

```javascript
// Track failures per host, not globally
const hostFailures = new Map();  // host -> failure count

// On fetch failure:
const count = (hostFailures.get(host) || 0) + 1;
hostFailures.set(host, count);

if (count >= CONFIG.hostFailureThreshold) {
  disabledHosts.add(host);
  console.info(`[LinkPreviews] Host ${host} disabled after ${count} failures`);
}
```

### 3) Safety and abuse guardrails

| Guardrail | Implementation |
|-----------|----------------|
| Whitelist-only | `allowed_hosts` array; empty = same-origin only |
| HTTPS-only | `allowed_schemes` defaults to `["https"]` |
| No credentials | `credentials: 'omit'` for cross-origin fetches |
| CORS mode | `mode: 'cors'` explicit for cross-origin |
| Rate limiting | Existing prefetch delay (50ms) + single pending fetch |
| Cache limits | Existing LRU cache (50 entries) |
| Graceful degradation | Threshold-based host disabling (3 failures) |

### 4) Config bridge template update

Update `link-previews.html`:

```jinja2
<script id="bengal-config" type="application/json">
{
  "linkPreviews": {
    "enabled": {{ _link_previews_enabled | lower }},
    "hoverDelay": {{ _lp.hover_delay ?? 200 }},
    "hideDelay": {{ _lp.hide_delay ?? 150 }},
    "showSection": {{ (_lp.show_section ?? true) | lower }},
    "showReadingTime": {{ (_lp.show_reading_time ?? true) | lower }},
    "showWordCount": {{ (_lp.show_word_count ?? true) | lower }},
    "showDate": {{ (_lp.show_date ?? true) | lower }},
    "showTags": {{ (_lp.show_tags ?? true) | lower }},
    "maxTags": {{ _lp.max_tags ?? 3 }},
    "includeSelectors": {{ (_lp.include_selectors ?? ['.prose']) | tojson }},
    "excludeSelectors": {{ (_lp.exclude_selectors ?? []) | tojson }},
    "allowedHosts": {{ (_lp.allowed_hosts ?? []) | tojson }},
    "allowedSchemes": {{ (_lp.allowed_schemes ?? ['https']) | tojson }},
    "hostFailureThreshold": {{ _lp.host_failure_threshold ?? 3 }}
  }
}
</script>
```

### 5) Build / content requirements

- Per-page JSON already on by default in `defaults.py` (`per_page = ["json"]`); no change.
- No change to xref resolution; links remain absolute via templates or `xref.json`.

---

## Design Details

### Host selection

- `allowed_hosts`: exact-match host names (e.g., `lbliii.github.io`, `kida.dev`, `rosettes.dev`).
- Same-host remains implicitly allowed; setting `allowed_hosts` does not disable same-host.
- Scheme validation happens before host check; non-HTTPS rejected early.

### JSON URL derivation

- For a link `https://lbliii.github.io/kida/docs/foo/`, request `https://lbliii.github.io/kida/docs/foo/index.json`.
- For `.../page.html`, request `.../page.json` (existing `toJsonUrl()` logic).
- Cross-origin URLs use full absolute URL, not path-relative.

### Failure handling

| Scenario | Behavior |
|----------|----------|
| First 404 on a path | Cache null for that path; other paths on host still work |
| 3 consecutive failures on host | Disable previews for that host for session |
| CORS error | Counts as failure; same threshold logic |
| Network timeout | AbortController handles; counts as failure |
| Malformed JSON | Catch parse error; cache null; counts as failure |

**Why threshold-based?** A single 404 (deleted page) shouldn't disable an entire host. The 3-failure threshold balances resilience with avoiding repeated failed requests.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Extra network requests | Medium | Low | Whitelist-only + prefetch delay (50ms) + LRU cache |
| CORS denial | Low | Low | Threshold-based disable (3 failures) per host |
| Broken JSON | Low | Low | Parse error cached as null; link still works |
| Mixed content (HTTP) | Low | Medium | `allowed_schemes: ["https"]` enforced client-side |
| Credential leakage | Low | High | `credentials: 'omit'` explicit for cross-origin |

---

## Example Configuration

```yaml
# site/config/_default/site.yaml
link_previews:
  enabled: true
  allowed_hosts:
    - lbliii.github.io   # GitHub Pages for ecosystem
    - kida.dev           # Production domain (future)
    - rosettes.dev       # Production domain (future)
  allowed_schemes:
    - https
  host_failure_threshold: 3
```

---

## Rollout Plan

1. **M1: Core Implementation**
   - Add `allowed_hosts`, `allowed_schemes`, `host_failure_threshold` to `defaults.py`
   - Update `link-previews.html` config bridge
   - Modify `link-previews.js`: relax hostname check, add cross-origin fetch options, add failure tracking
   - Add unit tests for new config parsing
   - Add integration tests for whitelisted-host behavior

2. **M2: Documentation**
   - Update `link_previews` docs with cross-site configuration
   - Add example to Bengal site config

3. **M3: QA**
   - Same-site links still preview ✓
   - `ext:kida:*` and `ext:rosettes:*` preview from Bengal site (hover + keyboard focus)
   - 404 on single path doesn't disable host
   - 3 failures on host disables previews for that host
   - Non-HTTPS links rejected (no preview, no fetch)
   - `prefers-reduced-motion` still respected

4. **M4: Ship**
   - Enable in production build with ecosystem hosts whitelisted
   - Monitor console for `[LinkPreviews] Host X disabled` messages

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| Proxy JSON through Bengal origin | Adds server complexity; unnecessary given permissive CORS on GH Pages |
| Reuse `xref.json` for preview data | Lacks excerpts and tags; per-page JSON already richer. Defer to future RFC if demand emerges. |
| Auto-whitelist from `external_refs.indexes` | Convenient but surprising; network surface should be explicit |
| First-failure host disable | Too aggressive; single 404 shouldn't disable entire host |

---

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Auto-populate `allowed_hosts` from `external_refs.indexes`? | No | Network surface should be explicit opt-in |
| Per-host fetch cap beyond global single pending? | No | Existing single-pending + prefetch delay sufficient |
| Use `xref.json` as fallback? | Deferred | Adds complexity; per-page JSON covers primary use case |
| Failure tracking scope | Per-host with threshold (3) | Balances resilience with avoiding repeated failures |

---

## Files to Modify

| File | Change |
|------|--------|
| `bengal/config/defaults.py` | Add `allowed_hosts`, `allowed_schemes`, `host_failure_threshold` |
| `bengal/themes/default/templates/partials/link-previews.html` | Add new options to config bridge JSON |
| `bengal/themes/default/assets/js/enhancements/link-previews.js` | Relax hostname check, add cross-origin options, add failure tracking |
| `tests/integration/test_link_previews.py` | Add tests for cross-origin config |
| `site/config/_default/site.yaml` | Add ecosystem hosts to `allowed_hosts` |

---

## Test Plan

### Unit Tests

```python
def test_allowed_hosts_in_defaults():
    """allowed_hosts defaults to empty list."""
    assert get_default("link_previews", "allowed_hosts") == []

def test_allowed_schemes_defaults_to_https():
    """allowed_schemes defaults to HTTPS only."""
    assert get_default("link_previews", "allowed_schemes") == ["https"]
```

### Integration Tests

```python
def test_config_bridge_includes_allowed_hosts(self, site_builder):
    """Config bridge should include allowedHosts when configured."""
    site = site_builder(
        config={
            "link_previews": {
                "enabled": True,
                "allowed_hosts": ["example.com", "other.dev"],
            },
        },
        content={"_index.md": "---\ntitle: Home\n---\nTest"},
    )
    site.build()
    html = site.read_output("index.html")
    assert '"allowedHosts": ["example.com", "other.dev"]' in html
```

### Manual QA Checklist

- [ ] Same-site links show preview on hover
- [ ] Cross-site link to whitelisted host shows preview
- [ ] Cross-site link to non-whitelisted host: no preview, no fetch
- [ ] HTTP link to whitelisted host: no preview, no fetch
- [ ] First 404 on cross-site: that path cached null, host still works
- [ ] 3 failures on host: host disabled, console message logged
- [ ] Mobile long-press works for cross-site previews
- [ ] Keyboard focus shows cross-site preview
- [ ] Escape closes cross-site preview
- [ ] `prefers-reduced-motion` suppresses animations

---

## Success Metrics

- Cross-site previews render for ecosystem links within 300ms (after cache warm)
- No increase in console errors on production sites
- Host disable rate < 1% of sessions (indicates threshold is appropriate)

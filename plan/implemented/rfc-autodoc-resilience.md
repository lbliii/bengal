# RFC: Improve Autodoc Virtual Page Resilience

**Status:** Draft  
**Owners:** (add)  
**Last updated:** 2025-12-08  
**Scope:** Autodoc virtual page generation and rendering resilience

## Problem

Autodoc virtual page generation is resilient but “quietly permissive”: extraction or templating failures are swallowed with a warning and the entire autodoc output is dropped for that build. Missing observability and strict/relaxed modes make it hard to detect regressions or partially failing autodoc runs.

## Goals

- Surface autodoc failures clearly without blocking non-strict builds.
- Allow opt-in strict mode to fail fast when autodoc content is expected.
- Preserve partial success when some elements fail (best-effort).
- Add automated coverage for failure paths (templates, extraction, OpenAPI/CLI).

## Non-Goals

- Redesigning autodoc templates or layout.
- Changing DocElement extraction logic beyond error propagation and surfacing.

## Current State (evidence)

- Discovery traps any exception and returns no pages/sections, dropping all autodoc output for that run:
```193:201:bengal/orchestration/content.py
        except Exception as e:
            self.logger.warning("autodoc_generation_failed", error=str(e))
            return [], []
```
- Template rendering falls back to a generic HTML fragment and only logs a warning; failures are not surfaced to callers:
```957:986:bengal/autodoc/virtual_orchestrator.py
        except Exception as e:
            # Fall back to generic template or legacy path
            try:
                template = self.template_env.get_template(template_name)
                return template.render(
                    element=element,
                    page=page_context,
                    config=self.config,
                    site=self.site,
                )
            except Exception as fallback_error:
                logger.warning(
                    "autodoc_template_render_failed",
                    element=element.qualified_name,
                    template=template_name,
                    error=self._relativize_paths(str(e)),
                    fallback_error=self._relativize_paths(str(fallback_error)),
                )
                # Return minimal fallback HTML
                return self._render_fallback(element)
```
- If no elements are produced, autodoc exits early with an info log; there is no summary of partial failures:
```369:413:bengal/autodoc/virtual_orchestrator.py
        if not all_elements:
            logger.info("autodoc_no_elements_found")
            return [], []
```

## Options

### Option A: Harden error handling and surfacing (recommended)
- Add an `AutodocRunResult` summary (counts: extracted, rendered, failed_extract, failed_render, warnings) returned alongside pages/sections.
- Keep best-effort behavior by default, but record failures and emit a single summarized warning at the end of discovery.
- Introduce `autodoc.strict` (bool) to raise on any failed extract/render (while still returning partial results where available).
- Keep template fallback, but include which pages fell back and why in the summary.

### Option B: Structured logging without API changes
- Emit structured warnings for each failure and a final summary log line.
- No strict mode; remains best-effort only.

### Option C: Fail-fast everywhere
- Raise immediately on first extraction or render failure.
- Highest safety, but regresses usability for sites that tolerate partial docs.

## Recommendation

Adopt **Option A**:
- Default remains best-effort, but failures are visible via summary + structured logs.
- Strict mode opt-in gives teams CI-grade enforcement.
- Partial successes are kept; only strict mode blocks builds.

## Proposed Changes

1) **Result summary and structured logs**
- Add `AutodocRunResult` capturing counts and failed identifiers.
- Discovery returns `(pages, sections, result)`; **ContentOrchestrator must be updated** to accept the third return value and to preserve/forward it. Add a compatibility path (e.g., tolerant unpacking) so non-autodoc discovery remains unchanged.
- Remove the current blanket `except Exception` swallow in `_discover_autodoc_content` so strict-mode raises can surface; keep ImportError handling.

2) **Strict mode**
- Config key `autodoc.strict` (default False). If True, raise on:
  - Extraction failure of any element.
  - Template rendering failure that reaches fallback.
- Still allow partial accumulation before raising, so users get context on what failed.

3) **Graceful fallback tagging**
- When `_render_fallback` is used, tag page metadata (e.g., `_autodoc_fallback_template: true`) on the `Page` object created in `_create_pages`, not just inside the HTML, so downstream reporting and tests can assert it.

4) **Tests**
- Unit tests covering:
  - Extraction exception → warning + empty result (non-strict) vs raises (strict).
  - Template missing → fallback tagged + summary; strict → raises.
  - OpenAPI and CLI element paths to ensure summary counts are populated for all types.
- RenderingPipeline integration test to ensure fallback-tagged pages still write output.

5) **Docs**
- Document strict mode and the new summary behavior in `bengal/autodoc/README.md`.

## Rollout Plan

- Phase 1: Implement `AutodocRunResult`, structured logs, fallback tagging; keep default best-effort.
- Phase 2: Add `autodoc.strict` and enforce raising with partial context.
- Phase 3: Add tests for failure paths and fallback tagging; add doc updates.

## Risks & Mitigations

- **Too chatty logs**: Use a single summary line plus capped detail (e.g., first N failures).  
  Mitigation: configurable max detail count.
- **Breaking changes via raising**: Strict mode is opt-in; default behavior preserved.
- **Silent partials remain unnoticed**: Summary log plus fallback tag in metadata makes detection easier; CI can assert zero failures via summary.  

## Open Questions

- Should strict mode also block if autodoc is enabled but produces zero elements? (Likely yes to catch misconfiguration.)
- Do we need per-language strictness (python/cli/openapi) or one global flag is enough?

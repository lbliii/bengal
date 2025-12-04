# RFC — Pristine HTML Output in Bengal

**Status**: ✅ Implemented  
**Owner**: @llane  
**Created**: 2025-10-24  
**Implemented**: 2025-11-25 (v0.1.4)

Problem Statement

Our generated HTML is “gappy” (extra blank lines, inconsistent spacing) and not consistently structured. This hurts diffs, readability, and size. We want Bengal to produce pristine HTML: minimal, consistent, and safe formatting without breaking semantics.

Goals

- Produce clean, stable HTML with:
  - No consecutive blank lines or trailing whitespace
  - Consistent inter-tag spacing and newlines
  - Optional minification in production; pretty-print in development
- Preserve semantics and whitespace-sensitive regions (`pre`, `code`, `textarea`, `script`, `style`)
- Provide configuration and CLI overrides
- Make the step deterministic and idempotent (formatting twice yields same output)

Non-Goals

- Perfect AST-aware reformatting of arbitrary invalid HTML
- Aggressive JS/CSS minification (handled by asset pipeline)

## Current State (Evidence)

- HTML rendering and write path:

```365:373:bengal/rendering/pipeline.py
        # Stage 4: Render content to HTML
        html_content = self.renderer.render_content(parsed_content)

        # Stage 5: Apply template (with dependency tracking already set in __init__)
        page.rendered_html = self.renderer.render_page(page, html_content)

        # Stage 6: Write output
        self._write_output(page)
```

- Write step:

```420:424:bengal/rendering/pipeline.py
        # Write rendered HTML atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text

        atomic_write_text(page.output_path, page.rendered_html, encoding="utf-8")
```

- Jinja environment trims some whitespace, but not fully:

```134:141:bengal/rendering/template_engine.py
        env_kwargs = {
            "loader": FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader("."),
            "autoescape": select_autoescape(["html", "xml"]),
            "trim_blocks": True,
            "lstrip_blocks": True,
            "bytecode_cache": bytecode_cache,
            "auto_reload": auto_reload,
        }
```

- `minify_html` exists in configuration, but there is no explicit formatting step yet.

## Proposed Design

### HTML Formatting Module

- New module: `bengal/postprocess/html_output.py` exposing:
  - `format_html_output(html: str, mode: str = "raw", options: dict | None = None) -> str`
  - Modes:
    - `raw`: no-op
    - `pretty`: collapse consecutive blank lines; normalize trailing whitespace; preserve `pre`/`code`/`textarea`/`script`/`style` content
    - `minify`: collapse inter-tag whitespace and optional comment stripping; preserve `pre`/`code`/`textarea`/`script`/`style` content; keep `<!DOCTYPE ...>`
  - Deterministic and idempotent
  - Pure-Python safe fallback; optional third-party accelerations (future)

### Integration Point

- In `RenderingPipeline.process_page`, after `render_page(...)` and before `_write_output(...)`, apply `format_html_output`.
- Ensure both the normal path and the parsed-content cache-hit path apply the formatter.

### Configuration and Defaults

- Backward-compatible with existing `minify_html` boolean.
  - If `minify_html` is true (default), use `mode = "minify"` unless explicitly overridden.
- Add optional nested section to avoid warnings and allow richer control:
  - `[html_output]`
    - `mode = "minify" | "pretty" | "raw"`
    - `remove_comments = true/false`
    - `collapse_blank_lines = true/false`

### CLI Override (future)

- `--html=minify|pretty|raw` to override configuration (out of scope for initial PR).

### Safety Considerations

- Preserve whitespace for sensitive tags: `pre`, `code`, `textarea`, `script`, `style`.
- Do not reflow inline JS/CSS. Minify HTML inter-tag whitespace by default.
- Allow page-level escape hatch via front matter: `no_format: true`.

### Testing Strategy

- Unit tests for:
  - Collapsing blank lines without touching `pre/code/textarea/script/style` content
  - Comment stripping toggle for `minify`
- Stability when formatting twice (idempotent behavior)
  - Performance bounds on realistic HTML (simple time budget assertion)

### Alternatives Considered

- Use `htmlmin`, `beautifulsoup4`, or `lxml`:
  - Pros: mature functionality
  - Cons: adds dependencies and risk to break JS/CSS; we can add optional adapters later

## Migration and Release

- Phase 1: add safe core formatter with conservative transformations; wire behind existing `minify_html` plus optional `[html_output]` configuration; default remains effectively minimized.
- Phase 2: add CLI override and optional third-party adapters; perform theme whitespace hygiene pass.

## Confidence Assessment

- Evidence: direct integration points identified in `pipeline.py` and Jinja environment; defaults present in configuration loader.
- Consistency: simple pure-Python transforms with clear preservation rules reduce breakage risk.
- Tests: new unit tests ensure correctness and stability.
- Confidence: 88% (Moderate-High).

## Appendix — Code References

1. Rendering integration point

```365:373:bengal/rendering/pipeline.py
        html_content = self.renderer.render_content(parsed_content)
        page.rendered_html = self.renderer.render_page(page, html_content)
        self._write_output(page)
```

1. Jinja whitespace options

```134:141:bengal/rendering/template_engine.py
        "trim_blocks": True,
        "lstrip_blocks": True,
```

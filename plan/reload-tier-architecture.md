# Dev Server Reload Tier Architecture

Bengal's dev server uses multiple reload tiers to minimize rebuild time and preserve UX.

## Tier Flow

```
File change detected
  ├─ CSS only?           → reload-css (swap <link> hrefs)
  ├─ Single .md body?   → reactive content → fragment swap
  ├─ Multi .md body?    → batch reactive → fragments (swap if on page, else reload)
  ├─ Template change?   → reactive template → re-render affected pages → reload
  ├─ Data file change?  → incremental build (BuildCache.get_affected_pages)
  └─ Structural change? → full warm build → full page reload
```

## Tiers

### 1. reload-css
- **Trigger**: Only CSS/asset changes, no content or template changes
- **Action**: Swap `<link>` hrefs with cache-bust query param
- **Latency**: Sub-100ms perceived

### 2. reactive-content (single)
- **Trigger**: Exactly 1 .md file, `modified` only, content-only (frontmatter unchanged)
- **Action**: Re-render that page via RenderingPipeline, extract `#main-content` fragment, send via SSE
- **Latency**: Sub-second

### 3. reactive-content (batch)
- **Trigger**: 2–10 .md files, all `modified`, all content-only
- **Action**: Re-render each page, send fragments payload; client swaps if viewing one of the changed pages, else full reload
- **Latency**: Sub-second for small batches

### 4. reactive-template
- **Trigger**: Template (.html) changes, no structural/autodoc changes, ≤50 affected pages
- **Action**: Re-render only affected pages via BuildCache.get_affected_pages()
- **Latency**: Sub-second for typical partial changes

### 5. incremental build
- **Trigger**: Data file changes, or content changes that don't match reactive gates
- **Action**: Full discovery, targeted render via dependency graph
- **Latency**: Seconds (faster than full build)

### 6. full warm build
- **Trigger**: Structural (created/deleted/moved), autodoc, SVG icons, version config
- **Action**: Full discovery, provenance, render, postprocess
- **Latency**: Full build time

## Debug Mode

Set `BENGAL_DEBUG_RELOAD=1` to log which tier was selected:

```
[Bengal] Reload tier: reactive-content (files=1)
[Bengal] Reload tier: reactive-template (templates=1, pages=5)
[Bengal] Reload tier: full-build (template change, reactive path unavailable)
```

## Constraints

- **Virtual pages**: Autodoc, taxonomy, CLI pages require discovery context → fall through to full build
- **Block cache**: Template changes that affect site-wide blocks (nav, footer) may need full build when BlockCache is stale
- **Batch caps**: Multi-file reactive capped at 10; template reactive capped at 50 affected pages

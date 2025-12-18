# RFC: Autodoc HTML/CSS Complete Reset

**Status**: Draft → Plan Ready  
**Plan**: `plan/ready/plan-autodoc-html-reset.md`  
**Created**: 2025-12-17  
**Author**: AI Assistant  
**Confidence**: 90% 🟢

---

## Executive Summary

The autodoc HTML/CSS system has become unmaintainable. **7,044 lines of CSS** across 16 files create specificity wars that make simple fixes impossible. This RFC proposes a **complete reset**: strip all autodoc CSS, define a minimal HTML skeleton with semantic structure, and rebuild styling from first principles.

**The goal**: A single HTML structure that works for all three autodoc types (Python API, CLI, OpenAPI) with CSS that is predictable, isolated, and maintainable.

---

## Problem Statement

### The Pain

> "I truly struggle to fix them... they're overcomplicated and a total mess."

Current state makes it **impossible to fix basic styling issues** because:

1. **CSS Sprawl**: 7,044 lines across 16 files
2. **Specificity Wars**: `.prose .docs-content .autodoc-explorer .api-section table` vs `.api-table`
3. **Inconsistent Structure**: Different templates use different wrapper hierarchies
4. **Class Explosion**: 200+ unique `.api-*` class names
5. **No Single Source of Truth**: Tokens defined in 3+ places with different values

### Evidence: CSS Line Counts

| File | Lines | Purpose |
|------|-------|---------|
| `api-explorer.css` | 2,629 | Main autodoc styling |
| `api-docs.css` | 913 | API documentation |
| `reference-docs.css` | 838 | Reference pages |
| `autodoc/_base.css` | 640 | Base autodoc styles |
| `autodoc/_card.css` | 518 | Card components |
| `autodoc/_rest.css` | 370 | REST API styles |
| `autodoc/_reset.css` | 260 | Resets (ironic) |
| `autodoc/_badges.css` | 177 | Badge styles |
| `autodoc/_table.css` | 145 | Table styles |
| 7 more files... | ~554 | Various |
| **Total** | **7,044** | For one feature |

### Evidence: Current HTML Nesting

Rendered output from `site/public/cli/bengal/assets/status/index.html`:

```html
<article class="prose docs-content">           <!-- Layer 1: Typography + layout -->
  <div class="autodoc-explorer">               <!-- Layer 2: Autodoc namespace -->
    <div class="api-usage">                    <!-- Layer 3: Usage block -->
      <h3 class="api-label">Usage</h3>
      <div class="code-block-wrapper">         <!-- Layer 4: Code wrapper -->
        <div class="code-header-inline">       <!-- Layer 5: Code header -->
          <span class="code-language">Bash</span>
        </div>
        <pre><code>...</code></pre>
      </div>
    </div>

    <section class="api-section api-section--options">  <!-- Layer 3: Section -->
      <h2 class="api-section__title">Options</h2>
      <table class="api-table api-table--compact">      <!-- Layer 4: Table -->
        ...
      </table>
    </section>
  </div>
</article>
```

**5-6 levels of nesting** before reaching actual content.

### Evidence: Specificity Nightmare

All of these selectors could apply to the same table:

```css
.prose table { }                                      /* 0,0,1,1 */
.docs-content table { }                               /* 0,0,1,1 */
.autodoc-explorer table { }                           /* 0,0,1,1 */
.api-section table { }                                /* 0,0,1,1 */
.api-table { }                                        /* 0,0,1,0 — LOSES! */
.prose .autodoc-explorer .api-table { }               /* 0,0,3,1 */
.prose .docs-content .autodoc-explorer table { }      /* 0,0,4,1 */
```

The BEM class `.api-table` has **lower specificity** than generic element selectors.

---

## Goals

1. **Single HTML skeleton** that works for Python API, CLI, and OpenAPI
2. **Flat CSS structure** with predictable specificity
3. **Under 500 lines** of autodoc-specific CSS
4. **Zero inheritance conflicts** with `.prose` or other parent styles
5. **Handle all edge cases** explicitly in the skeleton definition

## Non-Goals

- Visual redesign (maintain current aesthetic)
- JavaScript changes (unless blocking)
- Changing the autodoc generator logic
- Modifying the data model

---

## Proposed Solution: The Autodoc HTML Skeleton

### Design Principles

1. **One root, one namespace**: Single `.autodoc` container isolates all styles
2. **Flat structure**: Maximum 3 levels of semantic nesting
3. **Data attributes for variants**: `data-type="cli"` not `.autodoc--cli`
4. **Semantic HTML first**: Use `<article>`, `<section>`, `<table>`, `<dl>` appropriately
5. **CSS isolation**: Use `@layer` and/or `[data-autodoc]` attribute selector

### The Complete HTML Skeleton

```html
<!--
AUTODOC HTML SKELETON v1.0
==========================
Single structure for all autodoc types: Python API, CLI, OpenAPI

Attributes:
- data-autodoc: Root marker (required)
- data-type: "python" | "cli" | "openapi"
- data-element: "module" | "class" | "function" | "command" | "endpoint" | etc.
-->

<article data-autodoc data-type="cli" data-element="command" class="autodoc">

  <!-- ============================================
       HEADER: Title + metadata + description
       Always present, content varies by type
       ============================================ -->
  <header class="autodoc-header">
    <!-- Badges (optional) -->
    <div class="autodoc-badges">
      <span class="autodoc-badge" data-badge="deprecated">Deprecated</span>
      <span class="autodoc-badge" data-badge="async">Async</span>
      <span class="autodoc-badge" data-badge="abstract">Abstract</span>
      <!-- etc. -->
    </div>

    <!-- Title: always <h1> at article level -->
    <h1 class="autodoc-title">
      <code>bengal.build</code>
    </h1>

    <!-- Description (optional, rendered markdown) -->
    <div class="autodoc-description">
      <p>Build the static site from source content.</p>
    </div>

    <!-- Stats row (optional) -->
    <div class="autodoc-stats">
      <span class="autodoc-stat" data-stat="options">
        <span class="autodoc-stat-value">12</span>
        <span class="autodoc-stat-label">Options</span>
      </span>
      <span class="autodoc-stat" data-stat="arguments">
        <span class="autodoc-stat-value">2</span>
        <span class="autodoc-stat-label">Arguments</span>
      </span>
    </div>

    <!-- Source link (optional) -->
    <a href="..." class="autodoc-source" target="_blank" rel="noopener">
      View source
    </a>
  </header>

  <!-- ============================================
       SIGNATURE: Code signature block
       For: classes, functions, methods, endpoints
       ============================================ -->
  <div class="autodoc-signature">
    <pre><code class="language-python">def build(source: Path, output: Path, parallel: bool = True) -> None</code></pre>
  </div>

  <!-- ============================================
       USAGE: Command/import usage
       For: CLI commands, modules
       ============================================ -->
  <div class="autodoc-usage">
    <h2 class="autodoc-label">Usage</h2>
    <pre><code class="language-bash">bengal build [OPTIONS] [SOURCE]</code></pre>
  </div>

  <!-- ============================================
       SECTIONS: Main content areas
       Each section is a semantic <section> element
       ============================================ -->

  <!-- PARAMETERS / OPTIONS / ARGUMENTS -->
  <section class="autodoc-section" data-section="parameters">
    <h2 class="autodoc-section-title">Parameters</h2>

    <!-- Option A: Definition List (for simple param lists) -->
    <dl class="autodoc-params">
      <div class="autodoc-param" data-required="true">
        <dt class="autodoc-param-name">
          <code>source</code>
          <span class="autodoc-param-type">Path</span>
        </dt>
        <dd class="autodoc-param-desc">
          Source directory containing content files.
          <span class="autodoc-param-default">Default: <code>./content</code></span>
        </dd>
      </div>

      <div class="autodoc-param" data-required="false">
        <dt class="autodoc-param-name">
          <code>--parallel</code>
          <span class="autodoc-param-type">bool</span>
        </dt>
        <dd class="autodoc-param-desc">
          Enable parallel processing for faster builds.
          <span class="autodoc-param-default">Default: <code>True</code></span>
        </dd>
      </div>
    </dl>

    <!-- Option B: Table (for complex param displays) -->
    <table class="autodoc-table" data-table="parameters">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Default</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr data-required="true">
          <td class="autodoc-cell-name"><code>source</code></td>
          <td class="autodoc-cell-type"><code>Path</code></td>
          <td class="autodoc-cell-default"><code>./content</code></td>
          <td class="autodoc-cell-desc">Source directory containing content files.</td>
        </tr>
        <tr data-required="false">
          <td class="autodoc-cell-name"><code>--parallel</code></td>
          <td class="autodoc-cell-type"><code>bool</code></td>
          <td class="autodoc-cell-default"><code>True</code></td>
          <td class="autodoc-cell-desc">Enable parallel processing.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- RETURNS -->
  <section class="autodoc-section" data-section="returns">
    <h2 class="autodoc-section-title">Returns</h2>
    <div class="autodoc-returns">
      <code class="autodoc-returns-type">Site</code>
      <span class="autodoc-returns-desc">The built site instance.</span>
    </div>
  </section>

  <!-- RAISES / ERRORS -->
  <section class="autodoc-section" data-section="raises">
    <h2 class="autodoc-section-title">Raises</h2>
    <dl class="autodoc-raises">
      <div class="autodoc-raise">
        <dt><code>ConfigurationError</code></dt>
        <dd>When configuration file is invalid or missing.</dd>
      </div>
      <div class="autodoc-raise">
        <dt><code>BuildError</code></dt>
        <dd>When build process fails.</dd>
      </div>
    </dl>
  </section>

  <!-- EXAMPLES -->
  <section class="autodoc-section" data-section="examples">
    <h2 class="autodoc-section-title">Examples</h2>

    <div class="autodoc-example">
      <h3 class="autodoc-example-title">Basic usage</h3>
      <pre><code class="language-bash">bengal build</code></pre>
    </div>

    <div class="autodoc-example">
      <h3 class="autodoc-example-title">With custom output directory</h3>
      <pre><code class="language-bash">bengal build --output ./dist</code></pre>
    </div>
  </section>

  <!-- MEMBERS: For classes/modules with children -->
  <section class="autodoc-section" data-section="methods">
    <h2 class="autodoc-section-title">Methods</h2>

    <!-- Collapsible member cards -->
    <details class="autodoc-member" data-member="method" open>
      <summary class="autodoc-member-header">
        <code class="autodoc-member-name">render</code>
        <span class="autodoc-member-sig">(page: Page) → str</span>
        <span class="autodoc-member-badges">
          <span class="autodoc-badge" data-badge="async">async</span>
        </span>
      </summary>
      <div class="autodoc-member-body">
        <div class="autodoc-member-desc">
          <p>Render a page to HTML string.</p>
        </div>
        <!-- Nested params, returns, etc. use same structure -->
        <dl class="autodoc-params">
          ...
        </dl>
      </div>
    </details>

    <details class="autodoc-member" data-member="method">
      <summary class="autodoc-member-header">
        <code class="autodoc-member-name">validate</code>
        <span class="autodoc-member-sig">() → bool</span>
      </summary>
      <div class="autodoc-member-body">
        ...
      </div>
    </details>
  </section>

  <!-- ATTRIBUTES: For classes -->
  <section class="autodoc-section" data-section="attributes">
    <h2 class="autodoc-section-title">Attributes</h2>
    <table class="autodoc-table" data-table="attributes">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="autodoc-cell-name"><code>pages</code></td>
          <td class="autodoc-cell-type"><code>list[Page]</code></td>
          <td class="autodoc-cell-desc">All pages in the site.</td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- SUBCOMMANDS: For CLI command groups -->
  <section class="autodoc-section" data-section="subcommands">
    <h2 class="autodoc-section-title">Subcommands</h2>
    <div class="autodoc-cards">
      <a href="./serve/" class="autodoc-card" data-card="command">
        <code class="autodoc-card-name">serve</code>
        <span class="autodoc-card-desc">Start development server with live reload.</span>
      </a>
      <a href="./watch/" class="autodoc-card" data-card="command">
        <code class="autodoc-card-name">watch</code>
        <span class="autodoc-card-desc">Watch for changes and rebuild.</span>
      </a>
    </div>
  </section>

  <!-- ENDPOINTS: For OpenAPI schemas -->
  <section class="autodoc-section" data-section="endpoints">
    <h2 class="autodoc-section-title">Endpoints</h2>
    <div class="autodoc-cards">
      <a href="./get-users/" class="autodoc-card" data-card="endpoint">
        <span class="autodoc-method" data-method="get">GET</span>
        <code class="autodoc-card-name">/api/v1/users</code>
        <span class="autodoc-card-desc">List all users.</span>
      </a>
    </div>
  </section>

</article>
```

### Edge Cases Handled

| Edge Case | How Handled |
|-----------|-------------|
| **No parameters** | Section omitted entirely |
| **Optional vs required params** | `data-required="true/false"` attribute |
| **Deprecated elements** | `data-badge="deprecated"` in badges |
| **Async functions** | `data-badge="async"` in badges |
| **Abstract classes** | `data-badge="abstract"` in badges |
| **Dataclasses** | `data-badge="dataclass"` in badges |
| **Long descriptions** | Markdown rendered in `.autodoc-description` |
| **Nested members** | `<details>` with recursive structure |
| **Empty defaults** | `—` placeholder in table cells |
| **Code in descriptions** | `<code>` elements styled consistently |
| **External links** | `.autodoc-source` with `target="_blank"` |
| **Multiple inheritance** | List in badges or dedicated section |
| **Complex type annotations** | `<code>` wrapping preserves formatting |
| **Long type names** | CSS handles overflow/wrapping |
| **Mobile responsiveness** | Tables get `data-label` for stacking |
| **Dark/light themes** | CSS custom properties for all colors |

---

## Integration Considerations

### Consistency with Existing Theme Patterns

The proposed approach is **100% consistent** with existing Bengal theme conventions:

| Pattern | Existing Usage | Proposed Usage |
|---------|----------------|----------------|
| `data-theme` | Dark/light mode switching (417 matches across 57 CSS files) | ✅ Same pattern |
| `data-type` | Page type on `<body>` | `data-type="cli"` on autodoc root |
| `data-bengal` | JS hook for enhancements | N/A (not needed) |
| Semantic tokens | `--color-text-primary`, `--color-bg-elevated`, etc. | ✅ Direct reuse |
| BEM-ish naming | `.docs-nav-group-link`, `.page-hero__stat` | `.autodoc-section-title`, `.autodoc-param-desc` |

### JavaScript Dependencies: None

Verified all JS files for autodoc class dependencies:

| File | Dependency | Impact |
|------|------------|--------|
| `interactive.js` | **None** — uses `.docs-nav-*` selectors only | ✅ No changes needed |
| `search.js` | `result.isAutodoc` flag only (data-driven) | ✅ No changes needed |
| All other JS | **None** | ✅ No changes needed |

The JS layer is **completely decoupled** from autodoc CSS classes.

### Typography Integration

The global `typography.css` has rules that would interfere:

```css
/* typography.css - This would apply to autodoc articles */
article > p:first-of-type,
.prose > p:first-of-type {
  font-size: var(--text-lead);
  color: var(--color-text-secondary);
}
```

**Solution**: Add explicit exclusion in the autodoc CSS:

```css
/* Exclude autodoc from lead paragraph styling */
article[data-autodoc] > p:first-of-type,
[data-autodoc] .autodoc-description > p:first-of-type {
  font-size: inherit;
  color: inherit;
}
```

### Native `<details>` vs JavaScript Collapsibles

The skeleton uses native `<details>` for collapsible members:

**Pros**:
- ✅ No JavaScript required
- ✅ Accessible by default (keyboard, screen readers)
- ✅ Browser handles open/close state
- ✅ Works without JS enabled

**Cons**:
- ❌ Limited animation (no smooth height transitions natively)
- ❌ "Expand all / Collapse all" requires JS
- ❌ Can't persist open/closed state to localStorage

**Progressive Enhancement Path** (if needed later):

```js
// Optional: Add smooth animations and state persistence
Bengal.enhance.register('autodoc-member', (el) => {
  // Add height animation on toggle
  // Persist state to localStorage
  // Add "expand all" button
});
```

The HTML structure **does not prevent** adding this later. Native `<details>` is the correct semantic foundation.

---

## CSS Architecture

### Single File Structure

```css
/* autodoc.css - Complete autodoc styling (~400 lines target) */

/* ============================================
   LAYER: Autodoc styles in isolated layer
   ============================================ */
@layer autodoc {

  /* ============================================
     RESET: Surgical override of inherited styles
     ============================================

     NOTE: We use targeted resets, NOT `all: revert`.
     The nuclear `all: revert` would break layout context
     from parent .docs-main flexbox/grid.

     Instead, we surgically override only the typography
     and element styles that `.prose` sets.
   */

  /* Exclude autodoc from .prose lead paragraph styling */
  article[data-autodoc] > p:first-of-type {
    font-size: inherit;
    color: inherit;
  }

  /* Override .prose table styles */
  [data-autodoc] table {
    margin: 0;
    font-size: var(--text-sm);
  }

  /* Override .prose code styles */
  [data-autodoc] code {
    font-size: var(--autodoc-code-size);
    background: var(--autodoc-bg-code);
  }

  /* Override .prose heading margins */
  [data-autodoc] h1,
  [data-autodoc] h2,
  [data-autodoc] h3 {
    margin-top: 0;
    margin-bottom: 0;
  }

  /* Base autodoc container */
  [data-autodoc] {
    font-family: var(--font-sans);
    font-size: var(--text-base);
    line-height: var(--leading-relaxed);
    color: var(--color-text-primary);
  }

  /* ============================================
     TOKENS: All custom properties in one place
     ============================================ */
  [data-autodoc] {
    /* Spacing */
    --autodoc-gap: var(--space-6);
    --autodoc-section-gap: var(--space-8);

    /* Colors */
    --autodoc-border: var(--color-border-light);
    --autodoc-bg-code: var(--color-bg-code);
    --autodoc-bg-card: var(--color-bg-elevated);

    /* Typography */
    --autodoc-font-mono: var(--font-mono);
    --autodoc-code-size: var(--text-sm);

    /* Badges */
    --autodoc-badge-bg: var(--color-bg-tertiary);
    --autodoc-badge-text: var(--color-text-muted);
  }

  /* Dark mode overrides */
  [data-theme="dark"] [data-autodoc] {
    --autodoc-border: var(--color-border-dark);
    --autodoc-bg-card: var(--color-bg-secondary);
  }

  /* ============================================
     LAYOUT: Article structure
     ============================================ */
  .autodoc {
    display: flex;
    flex-direction: column;
    gap: var(--autodoc-gap);
  }

  .autodoc-header {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .autodoc-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  /* ============================================
     TYPOGRAPHY: Headings, text, code
     ============================================ */
  .autodoc-title {
    margin: 0;
    font-size: var(--text-2xl);
    font-weight: var(--weight-semibold);
  }

  .autodoc-title code {
    font-family: var(--autodoc-font-mono);
    background: none;
    padding: 0;
  }

  .autodoc-section-title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--weight-semibold);
    color: var(--color-text-primary);
  }

  .autodoc-label {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .autodoc-description {
    color: var(--color-text-secondary);
  }

  .autodoc-description > p:first-child { margin-top: 0; }
  .autodoc-description > p:last-child { margin-bottom: 0; }

  /* ============================================
     CODE: Signatures, inline code, blocks
     ============================================ */
  .autodoc-signature {
    background: var(--autodoc-bg-code);
    border: 1px solid var(--autodoc-border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    overflow-x: auto;
  }

  .autodoc-signature pre {
    margin: 0;
  }

  .autodoc-signature code {
    font-family: var(--autodoc-font-mono);
    font-size: var(--autodoc-code-size);
  }

  [data-autodoc] code {
    font-family: var(--autodoc-font-mono);
    font-size: var(--autodoc-code-size);
    background: var(--autodoc-bg-code);
    padding: 0.125em 0.375em;
    border-radius: var(--radius-sm);
  }

  .autodoc-signature code,
  .autodoc pre code {
    background: none;
    padding: 0;
  }

  /* ============================================
     BADGES: Status indicators
     ============================================ */
  .autodoc-badges {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .autodoc-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125em 0.5em;
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    background: var(--autodoc-badge-bg);
    color: var(--autodoc-badge-text);
    border-radius: var(--radius-full);
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .autodoc-badge[data-badge="deprecated"] {
    background: var(--color-warning-bg);
    color: var(--color-warning-text);
  }

  .autodoc-badge[data-badge="async"] {
    background: var(--color-info-bg);
    color: var(--color-info-text);
  }

  /* ============================================
     TABLES: Parameters, attributes
     ============================================ */
  .autodoc-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
  }

  .autodoc-table th,
  .autodoc-table td {
    padding: var(--space-3);
    text-align: left;
    border-bottom: 1px solid var(--autodoc-border);
  }

  .autodoc-table th {
    font-weight: var(--weight-semibold);
    color: var(--color-text-muted);
    background: var(--color-bg-secondary);
  }

  .autodoc-table tbody tr:hover {
    background: var(--color-bg-hover);
  }

  .autodoc-cell-name { font-family: var(--autodoc-font-mono); }
  .autodoc-cell-type { color: var(--color-text-muted); }
  .autodoc-cell-default { color: var(--color-text-muted); }

  /* Required indicator */
  tr[data-required="true"] .autodoc-cell-name::after {
    content: "*";
    color: var(--color-danger);
    margin-left: 0.25em;
  }

  /* ============================================
     DEFINITION LISTS: Alternative param display
     ============================================ */
  .autodoc-params {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    margin: 0;
  }

  .autodoc-param {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-2) var(--space-4);
    padding: var(--space-3);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
  }

  .autodoc-param-name {
    font-family: var(--autodoc-font-mono);
    font-weight: var(--weight-medium);
  }

  .autodoc-param-type {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .autodoc-param-desc {
    grid-column: 1 / -1;
    margin: 0;
  }

  .autodoc-param-default {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  /* ============================================
     MEMBERS: Collapsible method/attribute cards
     ============================================ */
  .autodoc-member {
    border: 1px solid var(--autodoc-border);
    border-radius: var(--radius-md);
    background: var(--autodoc-bg-card);
  }

  .autodoc-member-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    cursor: pointer;
    list-style: none;
  }

  .autodoc-member-header::-webkit-details-marker {
    display: none;
  }

  .autodoc-member-header::before {
    content: "▶";
    font-size: var(--text-xs);
    transition: transform 0.2s;
  }

  .autodoc-member[open] .autodoc-member-header::before {
    transform: rotate(90deg);
  }

  .autodoc-member-name {
    font-family: var(--autodoc-font-mono);
    font-weight: var(--weight-medium);
  }

  .autodoc-member-sig {
    color: var(--color-text-muted);
    font-family: var(--autodoc-font-mono);
    font-size: var(--text-sm);
  }

  .autodoc-member-body {
    padding: var(--space-4);
    border-top: 1px solid var(--autodoc-border);
  }

  /* ============================================
     CARDS: Subcommands, endpoints, classes
     ============================================ */
  .autodoc-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--space-4);
  }

  .autodoc-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-4);
    background: var(--autodoc-bg-card);
    border: 1px solid var(--autodoc-border);
    border-radius: var(--radius-md);
    text-decoration: none;
    color: inherit;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .autodoc-card:hover {
    border-color: var(--color-primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .autodoc-card-name {
    font-family: var(--autodoc-font-mono);
    font-weight: var(--weight-medium);
  }

  .autodoc-card-desc {
    font-size: var(--text-sm);
    color: var(--color-text-secondary);
  }

  /* HTTP method badges for OpenAPI */
  .autodoc-method {
    display: inline-flex;
    padding: 0.125em 0.5em;
    font-size: var(--text-xs);
    font-weight: var(--weight-bold);
    text-transform: uppercase;
    border-radius: var(--radius-sm);
  }

  .autodoc-method[data-method="get"] { background: #61affe; color: white; }
  .autodoc-method[data-method="post"] { background: #49cc90; color: white; }
  .autodoc-method[data-method="put"] { background: #fca130; color: white; }
  .autodoc-method[data-method="delete"] { background: #f93e3e; color: white; }
  .autodoc-method[data-method="patch"] { background: #50e3c2; color: white; }

  /* ============================================
     STATS: Counters in header
     ============================================ */
  .autodoc-stats {
    display: flex;
    gap: var(--space-4);
  }

  .autodoc-stat {
    display: flex;
    align-items: baseline;
    gap: var(--space-1);
    font-size: var(--text-sm);
  }

  .autodoc-stat-value {
    font-weight: var(--weight-semibold);
    color: var(--color-text-primary);
  }

  .autodoc-stat-label {
    color: var(--color-text-muted);
  }

  /* ============================================
     RESPONSIVE: Mobile adaptations
     ============================================ */
  @media (max-width: 768px) {
    .autodoc-table thead {
      display: none;
    }

    .autodoc-table tbody tr {
      display: block;
      padding: var(--space-3);
      border: 1px solid var(--autodoc-border);
      border-radius: var(--radius-md);
      margin-bottom: var(--space-2);
    }

    .autodoc-table td {
      display: flex;
      justify-content: space-between;
      padding: var(--space-2) 0;
      border-bottom: none;
    }

    .autodoc-table td::before {
      content: attr(data-label);
      font-weight: var(--weight-medium);
      color: var(--color-text-muted);
    }

    .autodoc-cards {
      grid-template-columns: 1fr;
    }
  }
}
```

**Target: ~400 lines** (current: 7,044 lines = **94% reduction**)

---

## Template Changes

### Before (Current)

```jinja
{# command.html - Current structure #}
<article class="prose docs-content {% if page.metadata.get('css_class') %}{{ page.metadata.get('css_class') }}{% endif %}">
  <div class="autodoc-explorer">
    {% if element.qualified_name %}
    <div class="api-usage">
      <h3 class="api-label">Usage</h3>
      <div class="code-block-wrapper">
        <div class="code-header-inline">
          <span class="code-language">Bash</span>
        </div>
        <pre><code class="language-bash">{{ element.qualified_name }}{% if element.children %} [OPTIONS]{% endif %}</code></pre>
      </div>
    </div>
    {% endif %}
    ...
  </div>
</article>
```

### After (Proposed)

```jinja
{# command.html - New structure #}
<article data-autodoc data-type="cli" data-element="command" class="autodoc">

  {% include 'autodoc/partials/header.html' %}

  {% if element.qualified_name %}
  <div class="autodoc-usage">
    <h2 class="autodoc-label">Usage</h2>
    <pre><code class="language-bash">{{ element.qualified_name }}{% if element.children %} [OPTIONS]{% endif %}</code></pre>
  </div>
  {% endif %}

  {% set options = element.children | default([]) | selectattr('element_type', 'eq', 'option') | list %}
  {% if options %}
  {% include 'autodoc/partials/params-table.html' with context %}
  {% endif %}

  {% if element.examples %}
  {% include 'autodoc/partials/examples.html' with context %}
  {% endif %}

</article>
```

### New Partials Structure

```
templates/
└── autodoc/
    ├── partials/
    │   ├── header.html          # Title, badges, description, stats
    │   ├── signature.html       # Code signature block
    │   ├── usage.html           # Usage/import block
    │   ├── params-table.html    # Parameters as table
    │   ├── params-list.html     # Parameters as definition list
    │   ├── returns.html         # Return type/value
    │   ├── raises.html          # Exception list
    │   ├── examples.html        # Code examples
    │   ├── members.html         # Methods/attributes (collapsible)
    │   └── cards.html           # Card grid (subcommands, etc.)
    ├── cli-command.html
    ├── cli-group.html
    ├── python-module.html
    ├── python-class.html
    ├── python-function.html
    ├── openapi-endpoint.html
    └── openapi-schema.html
```

---

## Implementation Plan

### Phase 1: Skeleton Definition (This RFC)
- [x] Define complete HTML skeleton
- [x] Document all edge cases
- [x] Define CSS architecture
- [x] Verify integration with existing patterns
- [ ] Review and approve

### Phase 2: CSS Reset (Day 1-2)
- [ ] Create new `autodoc.css` with skeleton styles (~400 lines)
- [ ] Add surgical `[data-autodoc]` overrides (not `all: revert`)
- [ ] Add typography exclusions for `.prose` rules
- [ ] Test in isolation (standalone HTML file with all section types)
- [ ] Run integration test checklist (see below)

### Phase 3: Template Migration (Day 3-5)
- [ ] Create new `autodoc/partials/` directory
- [ ] Build each partial from skeleton spec
- [ ] Migrate CLI templates first (simplest)
- [ ] Migrate Python API templates
- [ ] Migrate OpenAPI templates
- [ ] Run integration test checklist after each migration

### Phase 4: Integration (Day 6-7)
- [ ] Replace old templates with new ones
- [ ] Remove old CSS files (7,044 lines deleted!)
- [ ] Full visual regression testing
- [ ] Fix any edge cases discovered
- [ ] Final integration test checklist pass

### Phase 5: Cleanup (Day 8)
- [ ] Delete old CSS files
- [ ] Update documentation
- [ ] Close this RFC

---

## Integration Test Checklist

Run this checklist after each phase to catch regressions early:

### Visual Tests
- [ ] **Light mode**: All sections render correctly
- [ ] **Dark mode**: Colors adapt, no contrast issues
- [ ] **Palette switching**: Test with snow-lynx, charcoal-bengal palettes
- [ ] **Mobile (375px)**: Tables stack, cards single-column
- [ ] **Tablet (768px)**: Layout transitions correctly
- [ ] **Desktop (1200px+)**: Full layout, proper spacing

### Functional Tests
- [ ] **`<details>` collapse/expand**: Click toggles visibility
- [ ] **Keyboard navigation**: Tab through interactive elements
- [ ] **Screen reader**: VoiceOver/NVDA announces structure correctly
- [ ] **Code highlighting**: Syntax highlighting still works in `<pre><code>`
- [ ] **Copy code**: If copy button exists, it still works
- [ ] **Internal links**: Anchor links to sections work
- [ ] **External links**: Source links open in new tab

### Integration Tests
- [ ] **Search results**: Autodoc pages appear with API badge
- [ ] **Navigation**: Docs sidebar highlights current page
- [ ] **Breadcrumbs**: Path renders correctly
- [ ] **Page hero**: Stats display correctly
- [ ] **TOC**: Table of contents picks up section headings
- [ ] **No console errors**: Check browser devtools

### Content Type Tests
- [ ] **CLI command**: Options table, usage block, examples
- [ ] **CLI command group**: Subcommand cards
- [ ] **Python module**: Class cards, function cards
- [ ] **Python class**: Attributes table, methods list, signature
- [ ] **Python function**: Parameters, returns, raises
- [ ] **OpenAPI endpoint**: Method badge, path, parameters
- [ ] **OpenAPI schema**: Properties table

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Visual regressions | Medium | Medium | Screenshot comparison before/after |
| Missing edge cases | Medium | Low | Incremental migration, test each type |
| CSS `@layer` isolation fails | Low | High | Test isolation early; fallback to higher specificity selectors |
| `.prose` typography leaks through | Medium | Medium | Surgical overrides tested in isolation first |
| Layout context breaks (flexbox/grid) | Low | High | Avoided `all: revert`; use targeted resets only |
| `<details>` accessibility issues | Low | Medium | Use native element; test with VoiceOver/NVDA |
| Complex type annotations break | Medium | Low | Test with real bengal API docs (long generics) |
| Mobile layout issues | Medium | Medium | Test responsive breakpoints explicitly |
| Dark mode contrast issues | Low | Medium | Use existing semantic tokens; test both modes |
| Search indexing breaks | Low | Low | Search uses `isAutodoc` flag, not classes |

---

## Success Criteria

### Quantitative
- [ ] CSS lines: 7,044 → <500 (93%+ reduction)
- [ ] CSS files: 16 → 1
- [ ] HTML nesting: 5-6 levels → 2-3 levels
- [ ] Unique class names: 200+ → <50

### Qualitative
- [ ] Can fix CLI table styling in <5 minutes
- [ ] New developer can understand structure in <10 minutes
- [ ] No visual regressions (screenshot diff)
- [ ] Mobile layout works correctly

### Integration
- [ ] Dark mode works without additional CSS
- [ ] All 5 color palettes work correctly
- [ ] No JavaScript changes required
- [ ] Search still shows API badge on autodoc results
- [ ] Accessibility: keyboard navigation + screen reader tested
- [ ] Integration test checklist passes 100%

---

## Alternatives Considered

### Alternative A: Incremental Consolidation
Gradually merge CSS files without changing HTML.

**Rejected**: The previous RFC tried this approach. It didn't solve the specificity problem because the HTML structure forces deep selectors.

### Alternative B: CSS-in-JS / Tailwind
Use utility classes or scoped styles.

**Rejected**: Major architectural change. Would require build tooling changes and complete rewrite of all templates.

### Alternative C: Shadow DOM
Use web components with shadow DOM for style isolation.

**Rejected**: Overkill for static site. Adds JavaScript complexity. Poor SSR support.

### Alternative D: Keep Current + More Specificity
Add `!important` or longer selectors to fix immediate issues.

**Rejected**: Makes problem worse over time. Already tried multiple times. Technical debt accelerates.

---

## References

### Current Implementation
- `bengal/themes/default/assets/css/components/api-explorer.css` (2,629 lines)
- `bengal/themes/default/assets/css/components/autodoc/` (13 files, ~2,500 lines)
- `bengal/themes/default/assets/css/components/api-docs.css` (913 lines)
- `bengal/themes/default/assets/css/components/reference-docs.css` (838 lines)

### Templates
- `bengal/themes/default/templates/autodoc/cli/`
- `bengal/themes/default/templates/autodoc/python/`
- `bengal/themes/default/templates/openautodoc/python/`

### Rendered Output
- `site/public/cli/bengal/assets/status/index.html`
- `site/public/cli/bengal/build/index.html`

---

## Appendix: Class Name Inventory (Current)

Current unique class names in autodoc CSS (partial list):

```
.api-badge
.api-badge--abstract
.api-badge--async
.api-badge--dataclass
.api-badge--deprecated
.api-card
.api-card--class
.api-card--collapsible
.api-card--command
.api-card--dataclass
.api-card--function
.api-card__body
.api-card__count
.api-card__desc-preview
.api-card__header
.api-card__icon
.api-card__info
.api-card__meta
.api-card__name
.api-card__name-row
.api-card__toggle
.api-cards
.api-endpoint-content
.api-endpoint-header
.api-endpoint-header__meta
.api-endpoint-header__method-path
.api-endpoint-header__summary
.api-endpoint-path
.api-label
.api-label__count
.api-meta-label
.api-meta-value
.api-method-badge
.api-method-badge--delete
.api-method-badge--get
.api-method-badge--patch
.api-method-badge--post
.api-method-badge--put
.api-module-header
.api-module-header__badges
.api-module-header__bottom-row
.api-module-header__description
.api-module-header__short-name
.api-module-header__stats
.api-module-header__title
.api-module-header__top-row
.api-parameters
.api-section
.api-section--arguments
.api-section--attributes
.api-section--classes
.api-section--endpoints
.api-section--examples
.api-section--functions
.api-section--methods
.api-section--options
.api-section--parameters
.api-section--raises
.api-section--returns
.api-section--subcommands
.api-section__title
.api-signature
.api-table
.api-table--compact
.api-table--mini
.api-table__default
.api-table__desc
.api-table__name
.api-table__type
.api-usage
.autodoc-explorer
... (100+ more)
```

**Proposed**: Reduce to ~40 classes with consistent naming:

```
.autodoc
.autodoc-header
.autodoc-title
.autodoc-description
.autodoc-badges
.autodoc-badge
.autodoc-stats
.autodoc-stat
.autodoc-stat-value
.autodoc-stat-label
.autodoc-signature
.autodoc-usage
.autodoc-label
.autodoc-section
.autodoc-section-title
.autodoc-table
.autodoc-cell-name
.autodoc-cell-type
.autodoc-cell-default
.autodoc-cell-desc
.autodoc-params
.autodoc-param
.autodoc-param-name
.autodoc-param-type
.autodoc-param-desc
.autodoc-param-default
.autodoc-returns
.autodoc-returns-type
.autodoc-returns-desc
.autodoc-raises
.autodoc-raise
.autodoc-example
.autodoc-example-title
.autodoc-member
.autodoc-member-header
.autodoc-member-name
.autodoc-member-sig
.autodoc-member-body
.autodoc-cards
.autodoc-card
.autodoc-card-name
.autodoc-card-desc
.autodoc-method
.autodoc-source
```

# Competitive Analysis: Directive Syntaxes in Documentation Systems

| Field | Value |
|-------|-------|
| **Research ID** | `research-directive-syntax-competitive-analysis` |
| **Created** | 2025-12-27 |
| **Purpose** | Inform Patitas directive syntax design |
| **Related** | `rfc-patitas-markdown-parser` |

---

## Executive Summary

Analysis of 10 directive syntaxes reveals consistent patterns in what developers love and hate. The key insight: **simplicity vs. power is a false dichotomy** — the best systems achieve both through thoughtful syntax design.

**Top Complaints (across all systems):**
1. **Counting problems** — Fence depth counting (:::, ::::, :::::) is error-prone
2. **Whitespace sensitivity** — Indentation requirements cause subtle bugs
3. **Ecosystem lock-in** — Syntax tied to specific frameworks
4. **Nesting complexity** — Deep nesting becomes unreadable
5. **Option syntax verbosity** — `:key: value` lines add visual noise

**Top Praises (across all systems):**
1. **Familiar fencing** — Code block syntax (``` or :::) feels natural
2. **Readable raw text** — Directives visible without rendering
3. **Explicit closers** — Named closers reduce counting errors
4. **Typed options** — Catching errors at parse time
5. **Portability** — Content works across tools

---

## Syntax Comparison Matrix

| Syntax | Style | Example | Nesting | Options | Ecosystem |
|--------|-------|---------|---------|---------|-----------|
| **MyST** | Fenced | ```` ```{note} ```` | Fence depth | `:key: val` | Sphinx/Jupyter |
| **reST** | Directive | `.. note::` | Indentation | `:key: val` | Sphinx |
| **MDX** | JSX | `<Note>` | JSX nesting | props | React |
| **Markdoc** | Tags | `{% note %}` | Tag matching | attrs | Stripe |
| **AsciiDoc** | Blocks | `[NOTE]\n====` | Delimiter | attrs | Asciidoctor |
| **Docusaurus** | Fenced | `:::note` | Fence depth | metadata | Docusaurus |
| **MkDocs** | Fenced | `!!! note` | Indentation | inline | MkDocs |
| **Pandoc** | Fenced | `::: {.note}` | Fence depth | attrs | Pandoc |
| **Org-mode** | Blocks | `#+BEGIN_NOTE` | Explicit end | headers | Emacs |
| **CommonMark** | Extension | varies | varies | varies | Standard |

---

## Detailed Analysis: What People Love 💚

### 1. MyST Markdown

**Loved:**
- Familiar fence syntax (```) feels like code blocks
- Works with Sphinx ecosystem
- Markdown-first, RST features second
- Rich directive library inherited from Sphinx

```markdown
```{note}
This looks like a code block, so it's intuitive!
```
```

**Quote:** *"Finally, I can use Markdown with Sphinx and get all the directives I need."*

---

### 2. MDX (JSX in Markdown)

**Loved:**
- Full React component power
- Props are just JavaScript objects
- IDE autocompletion for components
- Hot reload during development
- Type checking with TypeScript

```jsx
<Tabs>
  <Tab label="Python">Python code here</Tab>
  <Tab label="JavaScript">JS code here</Tab>
</Tabs>
```

**Quote:** *"I can use my existing React component library in docs!"*

---

### 3. Markdoc (Stripe)

**Loved:**
- Explicit tag syntax is unambiguous
- Named closers eliminate counting
- Validation catches errors early
- Schema-driven, not code-driven
- Non-developers can author content

```markdown
{% tabs %}
{% tab label="Python" %}
Python code
{% /tab %}
{% tab label="JavaScript" %}
JS code
{% /tab %}
{% /tabs %}
```

**Quote:** *"The `{% /tag %}` closer is genius — no more counting colons."*

---

### 4. Docusaurus Admonitions

**Loved:**
- Dead simple for common cases
- Familiar to anyone who knows fenced code
- Built into popular framework
- Good defaults, minimal config

```markdown
:::note
This is a note
:::

:::tip Pro Tip
This is helpful
:::
```

**Quote:** *"Simple things should be simple. Docusaurus nails this."*

---

### 5. AsciiDoc

**Loved:**
- Semantic block types (sidebar, example, etc.)
- Delimiter matching is explicit
- Powerful attribute system
- Great for long-form documentation

```asciidoc
[NOTE]
====
This is a note block.
The four equals signs match.
====
```

**Quote:** *"AsciiDoc is what Markdown should have been for technical docs."*

---

## Detailed Analysis: What People Hate 💔

### 1. MyST Markdown

**Hated:**
- **Fence depth counting** — `:::` vs `::::` vs `:::::` is error-prone
- **Sphinx dependency** — Overkill for simple projects
- **Learning curve** — Need to know both Markdown AND RST concepts
- **Error messages** — Cryptic when nesting goes wrong

```markdown
:::::{tab-set}
::::{tab-item} First
:::{note}
Wait, how many colons do I need here?
:::
::::
:::::  <!-- Did I count right? -->
```

**Quote:** *"I spent 20 minutes debugging colon counts in nested directives."*

---

### 2. MDX (JSX in Markdown)

**Hated:**
- **JSX in Markdown feels wrong** — Breaks the "plain text" promise
- **Requires React knowledge** — Non-developers can't author
- **Build complexity** — Needs bundler, transpiler, etc.
- **Markdown inside JSX** — Indentation hell
- **Error messages** — React errors leak into docs workflow
- **Portability** — Content locked to React ecosystem

```jsx
<Tabs>
  <Tab label="Example">
    {/* Markdown doesn't work here without special handling */}
    **Bold?** Nope, literal text.
  </Tab>
</Tabs>
```

**Quote:** *"I wanted to write docs, not debug a React build."*

---

### 3. reStructuredText

**Hated:**
- **Whitespace sensitivity** — Tabs vs spaces causes silent failures
- **Verbose syntax** — `.. directive::` + indentation is wordy
- **Unfamiliar** — Nobody knows RST except Python devs
- **Not Markdown** — Have to learn a whole new language
- **Error messages** — Often incomprehensible

```rst
.. warning::
   This must be indented
   exactly right or it
   breaks silently.
```

**Quote:** *"I love Python, but RST is the worst part of the ecosystem."*

---

### 4. MkDocs Admonitions

**Hated:**
- **Indentation-based nesting** — 4-space requirement is fragile
- **`!!!` is weird** — Doesn't match any mental model
- **Limited customization** — Hard to extend
- **Title syntax confusing** — `!!! note "Title"` vs `!!! note` ambiguity

```markdown
!!! note "A Note"
    Everything must be indented 4 spaces.
    One wrong space and it breaks.

    !!! warning
        Nested? Good luck with that indentation.
```

**Quote:** *"The indentation sensitivity gives me flashbacks to YAML trauma."*

---

### 5. Fence Depth Counting (Universal Problem)

**Hated across ALL fenced syntaxes:**

```markdown
::::::{grid}
:::::{grid-item}
::::{card}
:::{note}
How many colons to close each level?
:::   <!-- 3 -->
::::  <!-- 4 -->
::::: <!-- 5 -->
:::::: <!-- 6... or was it 7? -->
```

**Quotes:**
- *"I literally count on my fingers."*
- *"Named closers should be mandatory, not optional."*
- *"My linter catches this, but it shouldn't happen in the first place."*

---

## Specific Pain Points & Solutions

### Pain Point 1: Fence Depth Counting

| System | Problem | Solution |
|--------|---------|----------|
| MyST/Docusaurus | Must count `:` | Named closers (Patitas adds `:::{/name}`) |
| AsciiDoc | Must match `====` | Delimiter length visible |
| Markdoc | None | Named closers by default |

**Patitas Solution:** Support BOTH fence depth AND named closers:

```markdown
:::{tab-set}
:::{tab-item} Python
Code here
:::{/tab-item}       <!-- Named closer: explicit -->
:::{tab-item} JavaScript
More code
:::{/tab-item}
:::{/tab-set}        <!-- Named closer: explicit -->
```

---

### Pain Point 2: Whitespace Sensitivity

| System | Problem | Severity |
|--------|---------|----------|
| reST | Indentation is semantic | High |
| MkDocs | 4-space indent required | Medium |
| MyST | Some indentation rules | Low |
| MDX | JSX whitespace rules | Medium |
| Markdoc | None | None |

**Patitas Solution:** Minimal whitespace sensitivity:
- Options use `:key: value` on separate lines (no indent required)
- Content is freeform within the block
- No indentation-based nesting

---

### Pain Point 3: Ecosystem Lock-in

| System | Lock-in Level | Portable To |
|--------|---------------|-------------|
| MDX | High | React only |
| Docusaurus | High | Docusaurus only |
| MyST | Medium | Sphinx, Jupyter |
| Markdoc | Medium | Any (with parser) |
| CommonMark | Low | Everywhere |

**Patitas Solution:**
- Pure Python, no framework dependency
- AST is portable (JSON serializable)
- Render to any format (HTML, React, etc.)

---

### Pain Point 4: Option Syntax Verbosity

```markdown
<!-- MyST: Many lines of options -->
```{figure} image.png
:alt: Description
:width: 500px
:align: center
:class: my-class

Caption here
```

<!-- Desired: More compact? -->
```

**User Feedback:**
- Some love explicit `:key: value` lines (searchable, grep-able)
- Others want inline options like `{figure, width=500, align=center}`
- Most agree: consistency matters more than brevity

**Patitas Solution:** Stick with `:key: value` for:
1. Grep-ability
2. Diff-friendliness  
3. Consistency with MyST/RST
4. Typed parsing is easier

---

### Pain Point 5: Nesting Complexity

Deep nesting is universally painful:

```markdown
<!-- Reality of complex docs -->
::::::{grid} 2
:::::{grid-item}
::::{card} Title
:::{dropdown} Details
Content...
:::
::::
:::::
:::::{grid-item}
... more ...
:::::
::::::
```

**Solutions Explored:**
1. **Named closers** — `:::{/card}` instead of `::::`
2. **Flattened structures** — Avoid deep nesting in design
3. **Reference includes** — `:::{include} file.md` for complex blocks
4. **Visual editors** — Abstract away the syntax

**Patitas Solution:** All of the above:
1. Named closers (`:::{/name}`) are first-class
2. Contract system warns about deep nesting
3. Include directive for decomposition
4. AST enables visual editor construction

---

## Feature Comparison: What Developers Want

Based on research, here's what developers prioritize:

| Feature | Priority | Notes |
|---------|----------|-------|
| **Simple common case** | 🟢 High | `:::note` should just work |
| **Explicit nesting** | 🟢 High | Named closers or clear delimiters |
| **Typed options** | 🟢 High | Catch errors at parse time |
| **Good error messages** | 🟢 High | Line numbers, suggestions |
| **Markdown inside** | 🟢 High | Full Markdown in directive body |
| **Portable content** | 🟡 Medium | Not locked to one tool |
| **Custom directives** | 🟡 Medium | Extensibility matters |
| **IDE support** | 🟡 Medium | Autocomplete, linting |
| **Inline options** | 🟠 Low | Most prefer explicit lines |
| **Visual editing** | 🟠 Low | Nice to have, not required |

---

## Recommendations for Patitas

Based on this research, Patitas should:

### ✅ Do These

1. **Support named closers** — `:::{/name}` eliminates fence counting
2. **Use familiar fence syntax** — `:::` is now standard
3. **Type all options** — `DirectiveOptions` dataclasses
4. **Validate contracts** — Catch nesting errors at parse time
5. **Provide great errors** — Line numbers, file paths, suggestions
6. **Keep options explicit** — `:key: value` lines, not inline
7. **Be ecosystem-agnostic** — Work with any renderer
8. **Support code block awareness** — Skip `:::` in code fences

### ❌ Avoid These

1. **Indentation-based nesting** — Too fragile (RST, MkDocs problems)
2. **JSX syntax** — Locks content to React (MDX problem)
3. **Fence-only nesting** — Must count colons (MyST problem)
4. **Custom delimiters** — `!!!` feels arbitrary (MkDocs problem)
5. **Silent failures** — RST-style "just ignore malformed input"

### 🔄 Consider These

1. **Inline role syntax** — `{role}\`content\`` is proven
2. **Block ID shorthand** — `:::{note} #my-id` for anchors
3. **Directive aliases** — `dropdown` = `details` = `collapsible`
4. **Nested Markdown** — Full Markdown in all contexts

---

## Syntax Decision: Patitas Directive Format

Based on competitive analysis, Patitas will use:

```markdown
:::{directive-name} optional title
:option-key: option value
:another-option: value

Markdown content here, including **bold**, `code`, and more.

Nested directives work:
:::{nested-directive}
Inner content
:::{/nested-directive}

:::{/directive-name}
```

**Rationale:**
- `:::` is familiar (MyST, Docusaurus, Pandoc)
- `{name}` clearly marks directive type
- `:key: value` is explicit and grep-able
- `:::{/name}` named closers are unambiguous
- Full Markdown works inside
- No indentation requirements

**Backward Compatibility:**
- Fence-depth closing (`::::`) still works
- Can mix named and fence-depth in same doc

---

## Competitive Positioning

| Versus | Patitas Advantage |
|--------|-------------------|
| **MyST** | Named closers, typed options, no Sphinx dependency |
| **MDX** | No React required, content authors can use it |
| **Markdoc** | Familiar Markdown-like syntax, not template-like |
| **reST** | Markdown base, less whitespace sensitivity |
| **MkDocs** | Standard fence syntax, better nesting |
| **Docusaurus** | Framework-agnostic, typed AST |

---

## Appendix: User Quotes by Category

### On Simplicity
> *"I just want to add a warning box. Why do I need to learn a new syntax?"*

> *"Markdown succeeded because it's readable. Directives should be too."*

### On Nesting
> *"Counting colons is my least favorite part of writing docs."*

> *"Named closers are the single best feature of Markdoc."*

### On Errors
> *"RST error messages are written for people who already know RST."*

> *"Good errors tell you what went wrong AND how to fix it."*

### On Portability
> *"I don't want to rewrite my docs when I switch frameworks."*

> *"The best content format is the one that isn't tied to a tool."*

### On Extensibility
> *"I need custom directives for my product's unique features."*

> *"A directive system is only as good as its extension API."*

---

## References

- [MyST Markdown Documentation](https://mystmd.org/guide/directives)
- [Markdoc by Stripe](https://markdoc.dev/)
- [MDX Documentation](https://mdxjs.com/)
- [Docusaurus Admonitions](https://docusaurus.io/docs/markdown-features/admonitions)
- [AsciiDoc Syntax Guide](https://asciidoctor.org/docs/asciidoc-syntax-quick-reference/)
- [MkDocs Material Admonitions](https://squidfunk.github.io/mkdocs-material/reference/admonitions/)
- [reStructuredText Directives](https://docutils.sourceforge.io/docs/ref/rst/directives.html)
- [Pandoc Divs and Spans](https://pandoc.org/MANUAL.html#divs-and-spans)
- Community discussions on Reddit, Hacker News, GitHub Issues

# Component Pattern Analysis: Directives vs Shortcodes vs Others

**Date:** October 3, 2025  
**Question:** What's the best way to implement reusable components (tabs, dropdowns, etc.) in Bengal?  
**Context:** We're considering Mistune directives, but should we use Hugo-style shortcodes instead?

---

## 🎯 The Problem

Documentation sites need reusable, rich components:
- Tabs for multi-language examples
- Dropdowns/accordions for optional content
- Code blocks with copy buttons
- Callout boxes (admonitions)
- Video embeds, diagrams, etc.

**Question:** What's the best syntax and architecture?

---

## 📊 Pattern Comparison Matrix

| Pattern | Syntax Style | Ecosystem | Maintainability | Extensibility |
|---------|-------------|-----------|-----------------|---------------|
| **Mistune Directives** | ` ```{name} ` | Python/RST | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Hugo Shortcodes** | `{{< name >}}` | Go/Hugo | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **MDX Components** | `<Name />` | React/JS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Jinja2 Macros** | `{% name %}` | Python | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **reST Directives** | `.. name::` | Python/Sphinx | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 1️⃣ Mistune Directives (Our Current Approach)

### Syntax

**Fenced style:**
```markdown
```{tabs}
:id: my-tabs
:theme: dark

### Tab: Python
```python
print("hello")
```

### Tab: JavaScript
```javascript
console.log("hello")
```
```
```

**RST style (alternative):**
```markdown
.. tabs::
   :id: my-tabs
   
   Python code here
```

### Pros ✅

1. **Consistent with Sphinx/ReadTheDocs** - Large Python community uses this
2. **Clear separation** - Directives look different from normal markdown
3. **Structured options** - `:key: value` syntax is explicit
4. **Nested content** - Can contain any markdown
5. **Parse-time** - Resolved during markdown parsing (fast)
6. **Type-safe** - Can validate options at parse time
7. **IDE support** - VSCode, PyCharm understand this syntax
8. **No template pollution** - Keeps content and presentation separate

### Cons ❌

1. **Unfamiliar to non-Python users** - Hugo/Jekyll users don't know this
2. **Verbose** - More typing than shortcodes
3. **Limited adoption** - Only Python SSGs use this
4. **Implementation complexity** - DirectivePlugin interface is tricky

### Real-World Usage

**Sphinx (reStructuredText):**
```rst
.. note::
   This is a note
   
.. code-block:: python
   :linenos:
   
   def hello():
       pass
```

**MkDocs Material:**
```markdown
!!! note "Optional Title"
    Content here
    
=== "Tab 1"
    Content
=== "Tab 2"
    Content
```

**Jupyter Book:**
```markdown
```{note}
This is a note
```

```{code-cell} python
print("hello")
```
```

### Bengal Implementation Status

- ✅ Admonitions working (custom syntax: `!!!`)
- ⚠️ Tabs/dropdowns written but buggy
- ⏳ Need to fix DirectivePlugin integration

---

## 2️⃣ Hugo Shortcodes

### Syntax

**Basic:**
```markdown
{{< youtube w7Ft2ymGmfc >}}

{{< highlight python >}}
def hello():
    pass
{{< /highlight >}}
```

**With named parameters:**
```markdown
{{< tabs >}}
  {{< tab "Python" >}}
  ```python
  print("hello")
  ```
  {{< /tab >}}
  {{< tab "JavaScript" >}}
  ```javascript
  console.log("hello")
  ```
  {{< /tab >}}
{{< /tabs >}}
```

**With markdown processing (%):**
```markdown
{{% note %}}
This **markdown** is processed
{{% /note %}}
```

### Pros ✅

1. **Widely known** - Hugo is #1 SSG, everyone knows this syntax
2. **Concise** - Less typing than directives
3. **Two modes** - `{{< >}}` (raw HTML) vs `{{% %}}` (process markdown)
4. **Inline or block** - Flexible placement
5. **Simple implementation** - Regex replacement before markdown parsing
6. **User-friendly** - Looks like template syntax (familiar)

### Cons ❌

1. **Collides with templates** - `{{ }}` is also Jinja2 syntax
2. **Pre-parse** - Must process before markdown (ordering issues)
3. **Escaping hell** - Hard to show shortcode syntax in docs
4. **No validation** - Typos cause silent failures
5. **Template pollution** - Mixes content with presentation
6. **Hard to nest** - Inner shortcodes get messy

### How Hugo Implements It

```go
// Hugo's approach (simplified):
1. Find all {{< shortcode >}} patterns in content
2. Look up shortcode template in layouts/shortcodes/
3. Execute template with parameters
4. Replace {{< ... >}} with rendered HTML
5. Pass result to markdown parser
```

**Shortcode template example:**
```html
<!-- layouts/shortcodes/youtube.html -->
<div class="youtube">
  <iframe src="https://youtube.com/embed/{{ .Get 0 }}"></iframe>
</div>
```

### Could Bengal Do This?

**Yes, easily:**
```python
# Before markdown parsing:
def process_shortcodes(content: str, site: Site) -> str:
    # Find {{< name params >}} patterns
    pattern = re.compile(r'\{\{<\s*(\w+)\s*(.*?)\s*>\}\}')
    
    def replace_shortcode(m):
        name = m.group(1)
        params = m.group(2)
        # Load template from themes/shortcodes/{name}.html
        template = site.load_shortcode_template(name)
        return template.render(params=params)
    
    return pattern.sub(replace_shortcode, content)
```

**Pros:** Simple to implement (1-2 hours)  
**Cons:** Conflicts with Jinja2 syntax

---

## 3️⃣ MDX Components (React/Next.js)

### Syntax

```jsx
import { Tabs, Tab } from './components'

# My Page

<Tabs>
  <Tab label="Python">
    ```python
    print("hello")
    ```
  </Tab>
  <Tab label="JavaScript">
    ```javascript
    console.log("hello")
    ```
  </Tab>
</Tabs>

Regular markdown continues here.
```

### Pros ✅

1. **Most powerful** - Full JavaScript/React capabilities
2. **Type-safe** - TypeScript support
3. **Component ecosystem** - Reuse React components
4. **IDE support** - Best auto-complete and validation
5. **Familiar** - If you know React
6. **Interactive** - Can have client-side logic

### Cons ❌

1. **JavaScript required** - Not pure markdown
2. **Build complexity** - Needs bundler (webpack/vite)
3. **Learning curve** - Must know React
4. **Not static** - Harder to optimize
5. **Overkill for docs** - Too much for most use cases
6. **Python SSG incompatible** - Would need JS runtime

### Bengal Compatibility

**Could we support this?** Technically yes, but:
- Would need Node.js at build time
- Would add significant complexity
- Goes against "Python-first" philosophy
- Overkill for documentation use cases

**Verdict:** Not a good fit for Bengal

---

## 4️⃣ Jinja2 Macros (Template-Based)

### Syntax

```markdown
{% tabs id="example" %}
  {% tab "Python" %}
  ```python
  print("hello")
  ```
  {% endtab %}
  {% tab "JavaScript" %}
  ```javascript
  console.log("hello")
  ```
  {% endtab %}
{% endtabs %}
```

### Pros ✅

1. **Already in Bengal** - Jinja2 is our template engine
2. **Familiar syntax** - Users know `{% %}`
3. **Full template power** - Access to all Jinja2 features
4. **Easy to implement** - Just define macros
5. **No new dependencies** - Use what we have

### Cons ❌

1. **Content/presentation mixing** - Violates separation of concerns
2. **Pre-parse required** - Must process before markdown
3. **Escaping issues** - Hard to document
4. **Limited markdown processing** - Content in tags doesn't parse well
5. **Not standard** - No other SSG does this

### How It Would Work

```python
# In themes/shortcodes/macros.html
{% macro tabs(id) %}
<div class="tabs" id="{{ id }}">
  {{ caller() }}
</div>
{% endmacro %}

# Process before markdown:
from jinja2 import Template
template = Template(content, autoescape=False)
processed = template.render()
# Then parse markdown
```

**Verdict:** Possible but not ideal. Mixes concerns.

---

## 5️⃣ reStructuredText Directives (Sphinx Model)

### Syntax

```rst
.. tabs::

   .. tab:: Python
   
      .. code-block:: python
      
         print("hello")
   
   .. tab:: JavaScript
   
      .. code-block:: javascript
      
         console.log("hello")
```

### Pros ✅

1. **Battle-tested** - Sphinx uses this for 15+ years
2. **Explicit structure** - Clear hierarchy
3. **Parse-time** - Resolved during parsing
4. **Extensible** - Easy to add new directives
5. **Well-documented** - Extensive Sphinx ecosystem

### Cons ❌

1. **Not markdown** - RST syntax is different
2. **Verbose** - More indentation/nesting
3. **Learning curve** - Steeper than markdown
4. **Whitespace-sensitive** - Indentation errors common

### Bengal Compatibility

We're using Markdown, not RST. But **Mistune directives** are inspired by this and give us similar power in Markdown syntax.

**Verdict:** We're already using the Markdown version of this!

---

## 🎯 Recommendation Matrix

### For Documentation Sites (Your Use Case)

**Best → Worst:**

1. **⭐⭐⭐⭐⭐ Mistune Fenced Directives** (` ```{name} `)
   - Pros: Clean, standard, Python ecosystem, IDE support
   - Cons: Less familiar to Hugo users
   - **Verdict:** BEST for Bengal

2. **⭐⭐⭐⭐ Hugo-style Shortcodes** (`{{< name >}}`)
   - Pros: Widely known, concise
   - Cons: Conflicts with Jinja2, no validation
   - **Verdict:** Good, but has conflicts

3. **⭐⭐⭐ Jinja2 Macros** (`{% name %}`)
   - Pros: Already have it
   - Cons: Mixes content/presentation
   - **Verdict:** Okay for simple cases

4. **⭐⭐ MDX Components** (`<Name />`)
   - Pros: Most powerful
   - Cons: Requires JavaScript, overkill
   - **Verdict:** Not suitable

### By SSG Type

**Python SSGs:**
- Sphinx: RST directives (`.. name::`)
- MkDocs: Fenced directives (` ```{name} `) + custom syntax
- Pelican: RST directives or custom shortcodes
- **Bengal:** Should use fenced directives ✅

**Go SSGs:**
- Hugo: Shortcodes (`{{< name >}}`)

**JavaScript SSGs:**
- Next.js: MDX components (`<Name />`)
- Gatsby: MDX components
- 11ty: Nunjucks shortcodes

**Ruby SSGs:**
- Jekyll: Liquid tags (`{% name %}`)

---

## 💡 The Hybrid Approach (Best of Both Worlds)

**Support BOTH patterns:**

### 1. Mistune Directives (Recommended)

```markdown
```{tabs}
:id: my-tabs

### Tab: Python
Code here
```
```

### 2. Shortcode Aliases (Compatibility)

```markdown
{{< tabs id="my-tabs" >}}
### Tab: Python
Code here
{{< /tabs >}}
```

**Implementation:**
1. Process shortcodes → convert to directives
2. Parse directives as normal
3. Users can use either syntax

**Code:**
```python
def preprocess_shortcodes(content: str) -> str:
    """Convert {{< >}} shortcodes to ```{} directives."""
    # Convert {{< tabs >}} to ```{tabs}
    content = re.sub(
        r'\{\{<\s*(\w+)\s*(.*?)\s*>\}\}',
        r'```{\1}\n\2',
        content
    )
    # Convert {{< /tabs >}} to ```
    content = re.sub(
        r'\{\{<\s*/(\w+)\s*>\}\}',
        r'```',
        content
    )
    return content
```

**Pros:**
- ✅ Users can choose their preferred syntax
- ✅ Hugo users feel at home
- ✅ Python users get standard directives
- ✅ Simple translation layer

**Cons:**
- ⚠️ Two ways to do the same thing
- ⚠️ Documentation needs to explain both

---

## 🏗️ Implementation Complexity

| Approach | Lines of Code | Complexity | Maintenance |
|----------|---------------|------------|-------------|
| **Mistune Directives** | ~200-300 | Medium | Low |
| **Hugo Shortcodes** | ~100-150 | Low | Medium |
| **Hybrid (Both)** | ~300-400 | Medium | Medium |
| **Jinja2 Macros** | ~50-100 | Low | Low |
| **MDX** | ~1000+ | High | High |

---

## 📊 Ecosystem Alignment

### Python Documentation Tools

| Tool | Pattern | Adoption |
|------|---------|----------|
| **Sphinx** | RST directives | ⭐⭐⭐⭐⭐ Huge |
| **MkDocs** | Custom fenced | ⭐⭐⭐⭐ Large |
| **Jupyter Book** | MyST directives | ⭐⭐⭐ Growing |
| **Hugo** | Shortcodes | ⭐⭐⭐⭐⭐ Huge |
| **Jekyll** | Liquid tags | ⭐⭐⭐ Medium |

**For Bengal (Python SSG):** Fenced directives align with Sphinx/MkDocs ecosystem.

---

## 🎯 Final Recommendation

### Primary: Mistune Fenced Directives ✅

**Use ` ```{name} ` syntax because:**

1. ✅ **Standard in Python ecosystem** (Sphinx, Jupyter Book, MyST)
2. ✅ **Clean separation** from regular markdown
3. ✅ **IDE support** (VSCode, PyCharm)
4. ✅ **Type-safe** - Can validate options
5. ✅ **No conflicts** with Jinja2
6. ✅ **Future-proof** - Growing adoption

**Example:**
```markdown
```{tabs}
:id: example

### Tab: Python
```python
print("hello")
```

### Tab: JavaScript
```javascript
console.log("hello")
```
```
```

### Secondary: Hugo-Compatible Shortcodes (Optional)

**Add as translation layer for Hugo users:**

```markdown
{{< tabs id="example" >}}
Content here
{{< /tabs >}}
```

Preprocessor converts to directives before parsing.

### Don't Use:
- ❌ Jinja2 macros (mixes concerns)
- ❌ MDX (wrong ecosystem)
- ❌ Plain HTML (loses markdown benefits)

---

## 🔧 Action Plan

### Phase 1: Fix Mistune Directives (High Priority)

1. Debug current DirectivePlugin issues
2. Get tabs, dropdowns, code-tabs working
3. Add tests
4. Document syntax

**Effort:** 4-6 hours  
**Impact:** Core feature complete

### Phase 2: Add Shortcode Compatibility (Optional)

1. Implement shortcode → directive translator
2. Support `{{< >}}` syntax
3. Document both syntaxes

**Effort:** 2-3 hours  
**Impact:** Better Hugo user onboarding

### Phase 3: Expand Directive Library (Future)

Add more directives:
- Diagrams (mermaid, graphviz)
- Video embeds
- Code playgrounds
- API references
- Versioned content

**Effort:** Ongoing  
**Impact:** Feature differentiation

---

## 📚 References & Prior Art

### Fenced Directives (Similar to our approach)
- **MyST (Markedly Structured Text):** Sphinx extension with ` ```{directive} ` syntax
- **Jupyter Book:** Uses MyST directives
- **MkDocs Material:** Custom fenced syntax for tabs, admonitions
- **Python-Markdown:** Extensions framework

### Shortcodes (Alternative approach)
- **Hugo:** `{{< >}}` shortcodes (Go templates)
- **Jekyll:** Liquid tags `{% %}`
- **Eleventy:** Nunjucks shortcodes
- **WordPress:** `[shortcode]` bracket syntax

### Components (Different paradigm)
- **MDX:** React components in markdown
- **Astro:** Component islands
- **VuePress:** Vue components in markdown

---

## 🎓 Lessons from Other SSGs

### What Sphinx Got Right
- Clear directive syntax (`.. name::`)
- Extensible plugin system
- Parse-time validation
- Rich options syntax

### What Hugo Got Right
- Simple, concise syntax
- User-friendly
- Two modes (HTML vs markdown)
- Wide adoption

### What MkDocs Material Got Right
- Hybrid approach (multiple syntaxes)
- Beautiful defaults
- Progressive disclosure
- Great documentation

### What We Should Do
- **Use fenced directives** (Python standard)
- **Optionally support shortcodes** (Hugo compatibility)
- **Validate at parse time** (catch errors early)
- **Beautiful defaults** (works out of the box)
- **Comprehensive docs** (examples for everything)

---

## 🎯 Conclusion

**Answer:** Yes, Mistune fenced directives (`​```{name}`) IS the best approach for Bengal because:

1. ✅ Aligns with Python ecosystem (Sphinx, Jupyter Book)
2. ✅ Clean, unambiguous syntax
3. ✅ No conflicts with existing systems
4. ✅ IDE support already exists
5. ✅ Extensible and maintainable

**Optionally** add Hugo shortcode compatibility as a translation layer, but make directives the primary/recommended syntax.

**Don't** use Jinja2 macros or MDX - wrong patterns for a Python SSG focused on documentation.

**Next steps:**
1. Fix the DirectivePlugin integration bugs
2. Get tabs/dropdowns working with fenced syntax
3. Document with examples
4. (Optional) Add shortcode translation layer

**Your instinct was right** - directives are the way to go! 🎯


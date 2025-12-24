# RFC: Simplified Code Tabs Syntax (v2)

**Status**: Draft  
**Created**: 2025-12-24  
**Updated**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Directives  
**Supersedes**: Partially amends `rfc-enhanced-code-tabs.md` (syntax only)  
**Priority**: P2 (Medium) — Developer experience, API simplicity  
**Estimated Effort**: 1-2 days  
**Confidence**: 92% 🟢

---

## Executive Summary

The current `code-tabs` syntax requires redundant `### Language` markers when the language is already specified in the code fence. This RFC proposes a simplified syntax that:

1. **Derives tab labels from code fence language** — No `### Python` needed
2. **Moves filename to code fence info string** — `python client.py` not `(client.py)`
3. **Removes redundant options** — Sync and line numbers are automatic
4. **Maintains all enhanced features** — Icons, copy button, Pygments highlighting

**Key insight**: The code fence already contains all the information we need. The `###` markers are syntactic overhead.

---

## Problem Statement

### Current Syntax (Verbose)

```markdown
:::{code-tabs}
:sync: language
:line-numbers: true

### Python (client.py)
```python {3-4}
def get_users():
    return response.json()
```

### JavaScript (client.js)
```javascript {3-4}
async function getUsers() {
    return response.json();
}
```
:::
```

**Issues:**

| Problem | Details |
|---------|---------|
| Redundant language | `### Python` duplicates `python` in fence |
| Magic filename syntax | `(client.py)` is non-standard, requires special parsing |
| Unnecessary options | `:sync: language` is the only use case; `:line-numbers:` is auto |
| Mixed syntax | Markdown headings (`###`) inside directive content |

### Why This Matters

- **Cognitive load**: Authors must remember the `###` marker syntax
- **Error-prone**: Easy to mismatch `### Python` with ````javascript`
- **Discoverability**: New users don't expect heading-style markers
- **Maintenance**: Parsing `###` markers adds complexity

---

## Proposed Solution

### Simplified Syntax

```markdown
:::{code-tabs}

```python client.py {3-4}
def get_users():
    return response.json()
```

```javascript client.js {3-4}
async function getUsers() {
    return response.json();
}
```

:::
```

### Syntax Rules

**Code fence info string format:**

```
language [filename] [title="Label"] [{line-highlights}]
```

**Ordering is strict** — components must appear in this order:

1. **Language** (required) — Pygments lexer name
2. **Filename** (optional) — basename with extension, no paths
3. **Title** (optional) — custom tab label override
4. **Highlights** (optional) — line numbers in `{...}`

| Example | Tab Label | Filename Badge | Highlights |
|---------|-----------|----------------|------------|
| `python` | Python | — | — |
| `python client.py` | Python | client.py | — |
| `python {3-4}` | Python | — | Lines 3-4 |
| `python client.py {3-4}` | Python | client.py | Lines 3-4 |
| `python title="Flask"` | Flask | — | — |
| `python app.py title="Flask" {5-7}` | Flask | app.py | Lines 5-7 |
| `javascript title="React"` | React | — | — |

**Filename limitations:**

- **Basename only** — `app.py` ✅, `src/app.py` ❌ (use title for paths)
- **Must have extension** — `app.py` ✅, `Dockerfile` ❌ (use title)
- **Allowed characters** — alphanumeric, dots, hyphens, underscores
- **Pattern**: `[\w.-]+\.\w+` (e.g., `my-app.config.ts` works)

**For files without extensions** (Dockerfile, Makefile):

```markdown
```dockerfile title="Dockerfile"
FROM python:3.12
```
```

**Tab label derivation** (in order of precedence):

1. If `title="..."` present → use title verbatim
2. Else if language has known display name → use display name
3. Else → capitalize first letter (python → Python)

**Language display names** (handles special casing):

```python
LANGUAGE_DISPLAY_NAMES = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "cpp": "C++",
    "csharp": "C#",
    "golang": "Go",
    "nodejs": "Node.js",
    "objectivec": "Objective-C",
    "fsharp": "F#",
    "graphql": "GraphQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    # Others use simple capitalization: python → Python, rust → Rust
}
```

**Automatic behaviors:**
- **Sync**: Always enabled, syncs by language across page
- **Line numbers**: Enabled for 3+ lines (existing behavior)
- **Icons**: Derived from language (existing behavior)
- **Copy button**: Always present (existing behavior)

### Directive Options (Minimal)

```yaml
# Only for edge cases — most code-tabs need zero options
:sync: none       # Disable sync for this specific block
:linenos: false   # Force off line numbers (rare)
```

---

## Parsing Changes

### Current Parsing Flow

```
Content → Split by "### " markers → Extract (language, filename) → Find code blocks
```

### Proposed Parsing Flow

```
Content → Find all code fences → Parse info string → (language, filename, highlights)
```

### Info String Pattern

**Integration with existing code block parsing:**

```
┌─────────────────────────────────────────────────────────────────┐
│  _CODE_BLOCK_PATTERN (existing in code_tabs.py)                 │
│  Captures: (language, info_string, code_content)                │
│                                                                 │
│  ```python client.py title="Flask" {5-7}                        │
│      │      └──────────────────────────┘                        │
│      │               info_string                                │
│      language                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  CODE_TABS_INFO_PATTERN (new - parses info_string)              │
│  Captures: (filename, title, highlights)                        │
└─────────────────────────────────────────────────────────────────┘
```

**Pattern definition:**

```python
# Applied to the info_string captured by _CODE_BLOCK_PATTERN
# Strict ordering: filename → title → highlights

CODE_TABS_INFO_PATTERN = re.compile(
    r"^"
    r"(?:(?P<filename>[\w][\w.-]*\.\w+)\s*)?"  # Optional filename (basename.ext)
    r'(?:title="(?P<title>[^"]*)"\s*)?'        # Optional title override
    r"(?:\{(?P<hl>[0-9,\s-]+)\})?"             # Optional highlights
    r"$"
)

# Examples of info_string → parsed result:
# ""                           → filename=None, title=None, hl=None
# "client.py"                  → filename="client.py", title=None, hl=None
# "{3-4}"                      → filename=None, title=None, hl="3-4"
# "client.py {3-4}"            → filename="client.py", title=None, hl="3-4"
# 'title="Flask"'              → filename=None, title="Flask", hl=None
# 'app.py title="Flask" {5-7}' → filename="app.py", title="Flask", hl="5-7"
```

**Filename pattern breakdown:**

```python
r"[\w][\w.-]*\.\w+"
#  │   │       │
#  │   │       └─ extension (required, 1+ word chars)
#  │   └─ middle (0+ word chars, dots, hyphens)
#  └─ first char (must be word char, not dot/hyphen)

# Matches: app.py, my-app.config.ts, test_utils.py
# Rejects: .env, -file.py, src/app.py (no paths)
```

### Implementation Changes

**`code_tabs.py` modifications:**

1. **Remove** `_CODE_TAB_SPLIT_PATTERN` and `_TAB_MARKER_PATTERN`
2. **Remove** `parse_tab_marker()` function
3. **Add** `CODE_TABS_INFO_PATTERN` for info string parsing
4. **Add** `LANGUAGE_DISPLAY_NAMES` constant
5. **Modify** `parse_directive()` to iterate code fences directly
6. **Simplify** `CodeTabsOptions` — remove `line_numbers` and `icons` (always on)

**New parse flow:**

```python
def parse_directive(self, title, options, content, children, state):
    # Find all code fences in content
    tabs = []
    for match in _CODE_BLOCK_PATTERN.finditer(content):
        lang = match.group(1) or "text"
        info_string = match.group(2) or ""
        code = match.group(3).strip()

        # Parse info string for filename, title, highlights
        info_match = CODE_TABS_INFO_PATTERN.match(info_string)
        if info_match:
            filename = info_match.group("filename")
            custom_title = info_match.group("title")
            hl_spec = info_match.group("hl")
        else:
            filename, custom_title, hl_spec = None, None, None

        # Derive tab label
        label = custom_title or get_display_name(lang)

        tabs.append({
            "type": "code_tab_item",
            "attrs": {
                "lang": lang,
                "label": label,
                "code": code,
                "filename": filename or "",
                "hl_lines": parse_hl_lines(hl_spec) if hl_spec else [],
            }
        })

    return {"type": "code_tabs", "children": tabs, "attrs": {...}}
```

**New helper function:**

```python
def get_display_name(lang: str) -> str:
    """Get human-readable display name for language."""
    normalized = lang.lower()
    if normalized in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[normalized]
    return lang.capitalize()
```

---

## Edge Cases

### Custom Tab Labels (React vs Vue)

Both use JavaScript, but need different labels:

```markdown
:::{code-tabs}

```javascript title="React"
const [count, setCount] = useState(0);
```

```javascript title="Vue"
const count = ref(0);
```

:::
```

### Shell Variants

```markdown
:::{code-tabs}

```bash title="macOS/Linux"
export API_KEY="secret"
```

```powershell title="Windows"
$env:API_KEY = "secret"
```

:::
```

### Disable Sync (Standalone Example)

```markdown
:::{code-tabs}
:sync: none

```python
# This example doesn't sync with others
```

```javascript
// Independent from page-wide sync
```

:::
```

### Files Without Extensions

```markdown
:::{code-tabs}

```dockerfile title="Dockerfile"
FROM python:3.12-slim
WORKDIR /app
COPY . .
```

```yaml docker-compose.yml
services:
  web:
    build: .
```

:::
```

### Filename with Multiple Dots

```markdown
:::{code-tabs}

```typescript my-app.config.ts
export default defineConfig({
  // works fine
});
```

```python settings.local.py
DEBUG = True
```

:::
```

### Same Language, Different Files

```markdown
:::{code-tabs}

```python title="Models" models.py
class User:
    pass
```

```python title="Views" views.py
def index():
    pass
```

:::
```

Note: Both tabs would normally sync (both Python), but `title=` differentiates them for the user.

---

## Migration

### Option A: Clean Break

Remove `###` marker support entirely. Update all existing `code-tabs` in docs.

**Pros**: Simpler codebase, no legacy paths  
**Cons**: Breaking change

### Option B: Deprecation Period

1. Support both syntaxes in v1.x
2. Log deprecation warning for `###` markers
3. Remove in v2.0

**Recommended**: Option A (clean break) — feature is new enough that migration is minimal.

### Migration Script

```bash
# Find all code-tabs with ### markers
grep -r "^### " site/content/ --include="*.md" -B 5 | grep -B 5 "code-tabs"
```

---

## Examples

### Basic (Two Languages)

```markdown
:::{code-tabs}

```python
print("Hello, World!")
```

```javascript
console.log("Hello, World!");
```

:::
```

### With Filenames

```markdown
:::{code-tabs}

```python main.py
if __name__ == "__main__":
    app.run()
```

```javascript index.js
import { app } from './app.js';
app.listen(3000);
```

:::
```

### With Highlights

```markdown
:::{code-tabs}

```python {2-3}
def process(data):
    validated = validate(data)  # highlighted
    return transform(validated)  # highlighted
```

```javascript {2-3}
function process(data) {
    const validated = validate(data);  // highlighted
    return transform(validated);       // highlighted
}
```

:::
```

### Full Featured

```markdown
:::{code-tabs}

```python app.py {5-7}
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, World!"
```

```javascript app.js {4-6}
import express from 'express';

const app = express();

app.get('/', (req, res) => {
    res.send('Hello, World!');
});
```

:::
```

---

## Comparison

| Aspect | Current | Proposed |
|--------|---------|----------|
| Lines for 2-tab example | ~12 | ~8 |
| Redundant info | Language in 2 places | None |
| Learning curve | Must learn `###` syntax | Just code fences |
| Filename format | `(filename)` magic | Standard info string |
| Options needed | `:sync:`, `:line-numbers:` | Usually none |

---

## Implementation Plan

### Phase 1: Parser Refactor (Day 1)

1. Add `CODE_TABS_INFO_PATTERN` to patterns.py
2. Rewrite `parse_directive()` to detect code fences
3. Extract language, filename, title, highlights from info string
4. Remove `_CODE_TAB_SPLIT_PATTERN` and `parse_tab_marker()`

### Phase 2: Options Cleanup (Day 1)

1. Simplify `CodeTabsOptions`:
   - Keep: `sync` (default: "language", option: "none")
   - Remove: `line_numbers` (always auto)
   - Remove: `icons` (always on)
   - Keep: `highlight` (global highlights, rarely used)

### Phase 3: Update Docs & Content (Day 2)

1. Update `site/content/docs/content/authoring/code-blocks.md`
2. Update `site/content/docs/content/authoring/interactive.md`
3. Update directive reference docs
4. Migrate any existing `code-tabs` with `###` markers

### Phase 4: Tests (Day 2)

1. Update `tests/unit/directives/test_code_tabs.py`
2. Add tests for new info string parsing
3. Add edge case tests (title override, no filename, etc.)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code-tabs | Medium | Low | Feature is new (implemented 2025-12-24); migration script provided |
| Filename pattern too restrictive | Medium | Low | Document limitations; title= handles edge cases |
| Ordering mistakes by authors | Low | Low | Clear error messages; examples in docs |
| Display name map incomplete | Low | Low | Fallback to capitalization works for most languages |
| Sync conflicts with title= | Low | Medium | Sync uses language, not title; documented behavior |

**Error handling:**

```python
# When info string doesn't match pattern:
# - Log warning with file location
# - Fall back to language-only (no filename, no highlights)
# - Continue rendering (graceful degradation)

if not CODE_TABS_INFO_PATTERN.match(info_string):
    logger.warning(
        "code_tabs_info_parse_failed",
        info=info_string,
        hint="Expected: [filename] [title=\"...\"] [{lines}]"
    )
```

---

## Success Criteria

**Functional:**

- [ ] Code fences parsed without `###` markers
- [ ] Filename extracted from info string (`python app.py` → filename="app.py")
- [ ] Title override works (`title="Flask"` → label="Flask")
- [ ] Highlights parsed (`{3-5}` → lines 3, 4, 5 highlighted)
- [ ] Display names correct (javascript → "JavaScript", cpp → "C++")
- [ ] All existing features work (sync, icons, copy, Pygments)

**Edge cases:**

- [ ] Multiple dots in filename (`config.local.py`)
- [ ] Title without filename (`python title="Example"`)
- [ ] Filename without extension rejected; falls back gracefully
- [ ] Empty code-tabs renders with warning class
- [ ] Invalid info string logs warning, continues rendering

**Migration:**

- [ ] No `###` markers in Bengal docs after migration
- [ ] Migration script finds all affected files

**Tests:**

```python
def test_info_string_parsing():
    assert parse_info("") == (None, None, [])
    assert parse_info("app.py") == ("app.py", None, [])
    assert parse_info("{3-4}") == (None, None, [3, 4])
    assert parse_info("app.py {3-4}") == ("app.py", None, [3, 4])
    assert parse_info('title="Flask"') == (None, "Flask", [])
    assert parse_info('app.py title="Flask" {5-7}') == ("app.py", "Flask", [5, 6, 7])

def test_display_names():
    assert get_display_name("javascript") == "JavaScript"
    assert get_display_name("typescript") == "TypeScript"
    assert get_display_name("cpp") == "C++"
    assert get_display_name("rust") == "Rust"  # fallback capitalization

def test_filename_pattern():
    # Valid
    assert is_valid_filename("app.py")
    assert is_valid_filename("my-app.config.ts")
    assert is_valid_filename("test_utils.py")

    # Invalid (use title= instead)
    assert not is_valid_filename("Dockerfile")  # no extension
    assert not is_valid_filename("src/app.py")  # path
    assert not is_valid_filename(".env")        # starts with dot
```

---

## Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Filename vs title precedence? | Title wins for tab label; filename shown as badge | Authors specify title for custom labeling; filename is metadata |
| Empty code-tabs? | Render empty container with warning class | Graceful degradation; CSS can style `.code-tabs:empty` |
| Mixed content between fences? | Ignore non-fence content | Simplest parsing; content belongs outside the directive |
| Files without extensions? | Use `title="Dockerfile"` | Pattern must be unambiguous; title handles edge cases |
| Strict ordering required? | Yes: filename → title → highlights | Simpler regex; predictable parsing |
| Language not in display map? | Capitalize first letter | `rust` → `Rust`, `haskell` → `Haskell` |

**Example: Filename + Title together**

```markdown
```python app.py title="Flask App" {5-7}
```

**Result**:
- Tab label: "Flask App" (from title)
- Filename badge: "app.py" (still displayed)
- Highlights: lines 5-7

---

## Open Questions

1. **Sync key customization** — Should we allow `:sync: framework` to group React/Vue/Angular tabs separately from Python/JS? (Current: all tabs sync by language only)

2. **Tab ordering** — Should tabs be reorderable? (e.g., always show user's preferred language first) (Current: order matches source)

---

## Appendix: Full Before/After

### Before (Current)

```markdown
:::{code-tabs}
:sync: language
:line-numbers: true

### Python (client.py)
```python {3-4}
import requests

def get_users():
    response = requests.get("/api/users")
    return response.json()
```

### JavaScript (client.js)
```javascript {3-4}
import fetch from 'node-fetch';

async function getUsers() {
    const response = await fetch('/api/users');
    return response.json();
}
```

:::
```

### After (Proposed)

```markdown
:::{code-tabs}

```python client.py {3-4}
import requests

def get_users():
    response = requests.get("/api/users")
    return response.json()
```

```javascript client.js {3-4}
import fetch from 'node-fetch';

async function getUsers() {
    const response = await fetch('/api/users');
    return response.json();
}
```

:::
```

**Savings**: 4 lines removed, zero options needed, cleaner mental model.

---

## Appendix B: Files Changed

| File | Change Type | Details |
|------|-------------|---------|
| `bengal/directives/code_tabs.py` | Modify | Remove `###` parsing; add info string parsing; add display names |
| `bengal/directives/patterns.py` | Add | `CODE_TABS_INFO_PATTERN` constant |
| `tests/unit/directives/test_code_tabs.py` | Modify | Update tests for new syntax; add edge case tests |
| `site/content/docs/content/authoring/code-blocks.md` | Modify | Update syntax documentation |
| `site/content/docs/reference/directives/interactive.md` | Modify | Update directive reference |

**Lines of code estimate:**

- **Removed**: ~50 lines (tab marker parsing, split logic)
- **Added**: ~30 lines (info string parsing, display names)
- **Net change**: -20 lines (simpler implementation)

---

## Appendix C: Migration Checklist

```bash
# 1. Find all code-tabs with ### markers
grep -rn "^### " site/content/ --include="*.md" | \
  xargs -I {} sh -c 'grep -B 10 "{}" | grep -q "code-tabs" && echo {}'

# 2. For each file, convert:
#    Before: ### Python (main.py)
#            ```python {3-4}
#    After:  ```python main.py {3-4}

# 3. Remove :sync: language (now default)
# 4. Remove :line-numbers: true (now auto)
# 5. Test build passes
# 6. Visual inspection of rendered output
```

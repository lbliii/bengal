# Page Hashability Analysis

**Date:** October 9, 2025  
**Context:** Investigating whether Page objects should be hashable to enable set operations  
**Current State:** Pages are dataclasses with mutable fields and cannot be stored in sets  

---

## 🎯 Executive Summary

**Should pages be hashable?** **Yes, with caveats.** Making pages hashable would unlock several benefits:

1. ✅ **Cleaner deduplication** in incremental builds
2. ✅ **Faster membership tests** (O(1) vs O(n))
3. ✅ **Set operations** for affected pages tracking
4. ✅ **Simpler code** in orchestrators

**But** it requires careful design to avoid bugs:
- ❌ Hash must remain stable throughout page lifecycle
- ❌ Mutable fields complicate hashability
- ⚠️ Need to choose the right identity attribute

---

## 📊 Current Pain Points

### 1. **Membership Tests with Lists** (Line 300, `build.py`)

```python
if page not in pages_to_build:
    pages_to_build.append(page)
```

**Problem:** O(n) lookup on every check. With 4K pages, that's expensive.

**Better with sets:**
```python
if page not in pages_to_build:  # O(1) with set
    pages_to_build.add(page)
```

### 2. **Section Tracking** (Line 248, `incremental.py`)

```python
affected_sections: Set[Any] = set()  # ⚠️ Set[Any] because Section isn't hashable
...
affected_sections.add(page.section)
```

**Current workaround:** Uses `Set[Any]` because `Section` objects aren't hashable either.
- Relies on Python's default `id()`-based hashing
- Works but type hints are imprecise
- Fragile if Section objects are recreated

### 3. **Knowledge Graph** (Lines 103-105, `knowledge_graph.py`)

```python
self.incoming_refs: Dict[int, int] = defaultdict(int)  # page_id -> count
self.outgoing_refs: Dict[int, Set[int]] = defaultdict(set)  # page_id -> target_ids
self.page_by_id: Dict[int, 'Page'] = {}  # page_id -> page object
```

**Problem:** Uses `id(page)` as keys because pages aren't hashable.
- Manual ID management
- Extra dictionary to map IDs back to pages
- Risk of stale references if pages are recreated

**Better with hashable pages:**
```python
self.incoming_refs: Dict[Page, int] = defaultdict(int)
self.outgoing_refs: Dict[Page, Set[Page]] = defaultdict(set)
```

### 4. **Taxonomy Collection** (Lines 221-228, `knowledge_graph.py`)

```python
pages = term_data.get('pages', [])  # List of pages

# Each page in the group has incoming refs from the taxonomy
for page in pages:
    page_id = id(page)
    self.incoming_refs[page_id] += 1
```

**Issue:** Can't use set operations to find unique pages across taxonomies.

---

## 🔍 What Would Unlock

### 1. **Set-Based Deduplication**

**Current:**
```python
pages_to_build = []
for page in candidates:
    if page not in pages_to_build:  # O(n) each time
        pages_to_build.append(page)
```

**With hashability:**
```python
pages_to_build = set(candidates)  # O(n) total, automatic dedup
```

### 2. **Fast Membership Tests**

**Use Cases:**
- Checking if a page is in the rebuild list
- Finding pages that appear in multiple taxonomies
- Tracking which pages have been processed

**Performance:** O(1) vs O(n) lookups

### 3. **Set Operations for Analysis**

```python
# Find pages that are in taxonomy A but not B
pages_in_a = set(taxonomy['a']['pages'])
pages_in_b = set(taxonomy['b']['pages'])
exclusive_to_a = pages_in_a - pages_in_b  # Clean set difference

# Find pages referenced by multiple sources
hub_pages = set(linked_pages) & set(menu_pages) & set(related_pages)
```

### 4. **Type-Safe Collections**

**Current:**
```python
affected_sections: Set[Any] = set()  # Imprecise typing
```

**With hashability:**
```python
affected_sections: Set[Section] = set()  # Precise typing
affected_pages: Set[Page] = set()
```

---

## 🏗️ Implementation Considerations

### Challenge 1: **Mutable Fields**

Pages have many mutable fields:
```python
@dataclass
class Page:
    source_path: Path          # ✅ Immutable (good for hash)
    content: str = ""          # ❌ Mutable
    metadata: Dict = ...       # ❌ Mutable
    parsed_ast: Any = None     # ❌ Mutable
    rendered_html: str = ""    # ❌ Mutable
    tags: List[str] = ...      # ❌ Mutable
    related_posts: List[Page] = ...  # ❌ Mutable
```

**Problem:** If hash is based on mutable fields, it can change → breaks set membership.

**Python's Rule:** Objects in sets/dicts must have stable hashes throughout their lifetime.

### Challenge 2: **Choosing Identity**

What makes a page "the same" page?

**Option 1: `source_path`** ✅ RECOMMENDED
```python
def __hash__(self):
    return hash(self.source_path)

def __eq__(self, other):
    return isinstance(other, Page) and self.source_path == other.source_path
```

**Pros:**
- Immutable (Path objects are hashable)
- Unique per page
- Stable throughout lifecycle
- Semantically correct (source file = identity)

**Cons:**
- Generated pages might have synthetic paths
- Need to ensure paths are absolute or normalized

**Option 2: `id(self)` (Python default)** ⚠️ NOT RECOMMENDED
```python
# No custom __hash__ needed - Python uses id() by default
```

**Pros:**
- Always works
- No implementation needed

**Cons:**
- Object identity, not value identity
- If a page is recreated (same source), it's considered "different"
- Breaks across serialize/deserialize
- Not intuitive for comparisons

**Option 3: Content-based hash** ❌ NOT VIABLE
```python
def __hash__(self):
    return hash((self.source_path, self.content, ...))
```

**Cons:**
- Content changes during build lifecycle (parsed_ast, rendered_html, etc.)
- Hash would become unstable
- Violates Python's hashability contract

### Challenge 3: **Dataclass `frozen=True`**

**Option:** Use `@dataclass(frozen=True)` to make all fields immutable.

```python
@dataclass(frozen=True)
class Page:
    source_path: Path
    # ...
```

**Pros:**
- Automatically hashable
- Enforces immutability
- Thread-safe

**Cons:**
- ❌ **BREAKS OUR BUILD LIFECYCLE**
- Pages are built in stages (discovery → parsing → rendering)
- Fields like `parsed_ast`, `rendered_html`, `output_path` are set later
- Would require complete architecture change

---

## ✅ Recommended Solution

### **Approach: `source_path`-based hashing**

Add explicit `__hash__` and `__eq__` methods to `Page`:

```python
@dataclass
class Page(...):
    # ... existing fields ...
    
    def __hash__(self) -> int:
        """Hash based on source path (stable identity)."""
        return hash(self.source_path)
    
    def __eq__(self, other: Any) -> bool:
        """Pages are equal if they have the same source path."""
        if not isinstance(other, Page):
            return NotImplemented
        return self.source_path == other.source_path
```

**Why this works:**
1. ✅ `source_path` is set in `__init__` and never changes
2. ✅ Path objects are hashable
3. ✅ Semantically correct (same source file = same page)
4. ✅ Works with generated pages (they have synthetic paths)
5. ✅ No architecture changes needed

**Caveat for generated pages:**
- Generated pages need unique `source_path` values
- Currently: `Path(f"_generated/tags/{slug}.md")`
- As long as these are unique, hashing works fine

### **Also Make `Section` Hashable**

Same approach for `Section`:

```python
@dataclass
class Section:
    path: Path
    name: str
    # ...
    
    def __hash__(self) -> int:
        """Hash based on section path (stable identity)."""
        return hash(self.path)
    
    def __eq__(self, other: Any) -> bool:
        """Sections are equal if they have the same path."""
        if not isinstance(other, Section):
            return NotImplemented
        return self.path == other.path
```

---

## 📈 Benefits After Implementation

### Immediate Wins

1. **Cleaner Code in `build.py`**
   ```python
   # Before (O(n) per append)
   if page not in pages_to_build:
       pages_to_build.append(page)
   
   # After (O(1) per add)
   pages_to_build.add(page)
   ```

2. **Better Type Safety**
   ```python
   # Before
   affected_sections: Set[Any] = set()
   
   # After
   affected_sections: Set[Section] = set()
   ```

3. **Simpler Knowledge Graph**
   ```python
   # Before: Manual ID management
   self.incoming_refs: Dict[int, int] = defaultdict(int)
   self.page_by_id: Dict[int, 'Page'] = {}
   
   # After: Direct page references
   self.incoming_refs: Dict[Page, int] = defaultdict(int)
   ```

### Future Opportunities

1. **Set-based caching strategies**
   - Track "pages in memory" as a set
   - Fast membership tests for cache hits
   - Efficient intersection/difference for cache invalidation

2. **Graph algorithms**
   - Use pages directly as graph nodes
   - Standard graph libraries expect hashable nodes
   - Easier to implement PageRank, clustering, etc.

3. **Memory optimization**
   - Identify duplicate page references
   - Use sets for "pages to keep in memory"
   - Track dependencies with set operations

---

## 🚀 Implementation Plan

### Phase 1: Make Basic Objects Hashable (30 min)

1. Add `__hash__` and `__eq__` to `Page` (based on `source_path`)
2. Add `__hash__` and `__eq__` to `Section` (based on `path`)
3. Add tests to verify hashability

### Phase 2: Update Collections (1 hour)

1. Change `affected_sections: Set[Any]` → `Set[Section]` in `incremental.py`
2. Audit other `Set[Any]` usages
3. Update type hints

### Phase 3: Optimize Key Usage Sites (2 hours)

1. **`build.py` line 300:** Use set for `pages_to_build`
2. **`knowledge_graph.py`:** Simplify to use pages as dict keys
3. **`orchestration/taxonomy.py`:** Use set operations for deduplication

### Phase 4: Documentation (30 min)

1. Document hash semantics in `Page` docstring
2. Add note about generated page paths needing uniqueness
3. Update type stubs if any

---

## 🧪 Testing Requirements

### Unit Tests

```python
def test_page_hashable():
    page1 = Page(source_path=Path("content/post.md"))
    page2 = Page(source_path=Path("content/post.md"))
    
    # Same source path = equal and same hash
    assert page1 == page2
    assert hash(page1) == hash(page2)
    
    # Can store in set
    pages = {page1, page2}
    assert len(pages) == 1

def test_page_hash_stable_across_mutations():
    page = Page(source_path=Path("content/post.md"))
    initial_hash = hash(page)
    
    # Mutate the page
    page.content = "New content"
    page.rendered_html = "<p>Rendered</p>"
    page.metadata['title'] = "New Title"
    
    # Hash should remain stable
    assert hash(page) == initial_hash
    
    # Should still be findable in set
    pages = {page}
    assert page in pages

def test_different_pages_different_hash():
    page1 = Page(source_path=Path("content/post1.md"))
    page2 = Page(source_path=Path("content/post2.md"))
    
    assert page1 != page2
    assert hash(page1) != hash(page2)  # Likely different (not guaranteed)
    
    pages = {page1, page2}
    assert len(pages) == 2
```

### Integration Tests

```python
def test_page_deduplication_in_build(site):
    """Test that duplicate pages are automatically handled."""
    page = site.pages[0]
    
    # Add same page multiple times
    candidates = [page, page, page]
    
    # Set automatically deduplicates
    unique = set(candidates)
    assert len(unique) == 1

def test_affected_sections_tracking(site):
    """Test that section sets work correctly."""
    sections: Set[Section] = set()
    
    for page in site.pages:
        if hasattr(page, 'section'):
            sections.add(page.section)
    
    # Should have deduplicated sections
    assert len(sections) > 0
    assert all(isinstance(s, Section) for s in sections)
```

---

## 🎯 Decision Matrix

| Criterion | Source-Path Hash | ID-Based | Frozen Dataclass |
|-----------|------------------|----------|------------------|
| **Stability** | ✅ Stable | ✅ Stable | ✅ Stable |
| **Semantic correctness** | ✅ Yes | ❌ No | ✅ Yes |
| **Works with mutability** | ✅ Yes | ✅ Yes | ❌ No |
| **Serialize/deserialize** | ✅ Yes | ❌ No | ✅ Yes |
| **Implementation effort** | 🟡 Low | ✅ None | ❌ High |
| **Architecture changes** | ✅ None | ✅ None | ❌ Complete rewrite |

**Winner: Source-Path Hash** ✅

---

## 🚨 Risks & Mitigations

### Risk 1: Generated Pages with Duplicate Paths

**Risk:** If two generated pages have the same `source_path`, they'll be considered equal.

**Mitigation:**
- Audit generated page creation
- Ensure unique paths (include tag slug, page number, etc.)
- Add assertion to catch duplicates early

### Risk 2: Path Normalization

**Risk:** Same logical path might have different representations:
- `content/post.md` vs `./content/post.md`
- Relative vs absolute paths

**Mitigation:**
- Normalize paths during page creation
- Use `.resolve()` for absolute paths
- Document path expectations

### Risk 3: Existing Code Assumes List Behavior

**Risk:** Code might rely on ordered lists or duplicate entries.

**Mitigation:**
- Audit all uses of page collections
- Test incremental builds thoroughly
- Keep lists where order matters (rendering, pagination)
- Use sets only for deduplication/membership

---

## 📚 References

- Python Data Model: https://docs.python.org/3/reference/datamodel.html#object.__hash__
- Dataclass docs: https://docs.python.org/3/library/dataclasses.html
- Related: `INCREMENTAL_BUILD_REFACTOR_SUMMARY.md` (avoiding stale references)

---

## ✅ Recommendation

**YES, implement `source_path`-based hashing for `Page` and `Section`.**

Benefits:
- Cleaner code
- Better performance (O(1) membership)
- Type safety
- Enables set operations
- No architecture changes

Risks are minimal and easily mitigated.

**Next Step:** Implement Phase 1 (30 minutes) and validate with tests.


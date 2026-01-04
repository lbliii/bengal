# RFC: Container Stack Architecture for CommonMark Parsing

**Status**: Draft (Revised)  
**Author**: Bengal Team  
**Date**: 2026-01-04  
**Revised**: 2026-01-04  
**Affects**: `bengal/rendering/parsers/patitas/`

---

## Executive Summary

This RFC proposes a **Container Stack** architecture for patitas's block parsing. The design introduces explicit indent ownership, propagating state between nested containers, and principled token re-classification.

**Primary goal**: Code quality and maintainability improvement through centralized indent ownership logic.

**Key outcomes**:
- Eliminates ad-hoc indent checks scattered throughout parsing code (81 `content_indent` references across 6 files)
- Centralizes indent ownership queries into a single data structure
- Provides automatic state propagation between nested containers
- Maintains single-pass lexer architecture
- Expected performance: **O(n) with small constant factor** (stack depth ≤ 10 typical)

**Important**: This RFC focuses on **code architecture improvement**. For compliance improvements, see the separate fenced code parsing RFC (to be written).

---

## Current State

### Compliance Baseline (measured 2026-01-04)

| Section | Passed | Total | Rate | Container Stack Impact |
|---------|--------|-------|------|------------------------|
| Lists | 23 | 26 | 88.5% | None (failures are fenced code issues) |
| List items | 34 | 48 | 70.8% | Partial (~4-6 failures addressable) |

### Code Quality Issues

The lexer classifies tokens without context. The parser must re-interpret tokens based on current nesting depth, leading to:

1. **Scattered indent logic**: 81 occurrences of `content_indent` across 6 files
2. **Repeated source lookups**: 16 calls to `get_line_indent(source, offset)`
3. **Duplicated patterns**: `handle_blank_line`, `_handle_indented_code_in_item`, etc. all do similar indent reasoning
4. **Complex parameter passing**: `start_indent`, `content_indent`, `actual_content_indent` threaded through call chains

### Actual Failing Examples

**Lists section failures (3 examples: 318, 321, 324)**:
All involve fenced code content parsing within list items. Container stack does NOT address these.

```markdown
# Example 321 - Fenced code content missing
- a
  > b
  ```
  c
  ```
- d

# Expected: <pre><code>c</code></pre>
# Actual: <pre><code></code></pre>
```

**List items section failures that container stack WOULD help**:

| Example | Issue | How Container Stack Helps |
|---------|-------|--------------------------|
| 254 | Indented code extra spaces preserved | Centralized content_indent stripping |
| 264 | Code blocks split incorrectly across blank lines | Unified indent ownership |
| 273-274 | First-line indented code handling | Clear `owns_content()` query |

**List items section failures that container stack would NOT help**:

| Example | Issue | Actual Root Cause |
|---------|-------|-------------------|
| 263 | Fenced code content missing | Fenced code parser issue |
| 286-288 | Block content recognition | Token classification, not indent |

---

## Proposed Solution

### Core Data Structures

```python
from dataclasses import dataclass, field
from enum import Enum, auto

class ContainerType(Enum):
    DOCUMENT = auto()
    LIST = auto()
    LIST_ITEM = auto()
    BLOCK_QUOTE = auto()
    FENCED_CODE = auto()  # Leaf container (no nesting)


@dataclass(slots=True)
class ContainerFrame:
    """
    A frame on the container stack representing a parsing context.

    Each container "claims" an indent range. Tokens are routed to
    the deepest container that claims their indent.
    """
    container_type: ContainerType

    # Indent boundaries
    start_indent: int           # Where this container started (marker position)
    content_indent: int         # Minimum indent for content continuation

    # For lists: marker siblings can appear at start_indent to start_indent+3
    max_sibling_indent: int = field(default=-1)

    # State that propagates upward on pop
    is_loose: bool = False
    saw_blank_line: bool = False

    # For lists: tracking
    ordered: bool = False
    bullet_char: str = ""
    start_number: int = 1

    def __post_init__(self):
        if self.max_sibling_indent == -1:
            self.max_sibling_indent = self.start_indent

    def owns_content(self, indent: int) -> bool:
        """Does this container own content at this indent level?"""
        return indent >= self.content_indent

    def owns_marker(self, indent: int) -> bool:
        """Could a list marker at this indent be a sibling in this container?"""
        if self.container_type != ContainerType.LIST:
            return False
        return self.start_indent <= indent <= self.max_sibling_indent

    def is_nested_marker(self, indent: int) -> bool:
        """Would a marker at this indent start a nested list?"""
        return indent >= self.content_indent


@dataclass  
class ContainerStack:
    """
    Manages the stack of active containers during parsing.

    Invariant: stack[0] is always DOCUMENT, stack[-1] is innermost container.
    """
    _stack: list[ContainerFrame] = field(default_factory=list)

    def __post_init__(self):
        self._stack = [ContainerFrame(
            container_type=ContainerType.DOCUMENT,
            start_indent=0,
            content_indent=0,
        )]

    def push(self, frame: ContainerFrame) -> None:
        """Push a new container onto the stack."""
        assert len(self._stack) > 0, "Cannot push to empty stack"
        self._stack.append(frame)

    def pop(self) -> ContainerFrame:
        """
        Pop the innermost container.

        Propagates state (looseness, blank lines) to parent if applicable.
        """
        if len(self._stack) <= 1:
            raise ValueError("Cannot pop document frame")

        frame = self._stack.pop()

        # Propagate looseness to parent list item
        if frame.saw_blank_line or frame.is_loose:
            parent = self._stack[-1]
            if parent.container_type == ContainerType.LIST_ITEM:
                parent.is_loose = True
                parent.saw_blank_line = True

        return frame

    def current(self) -> ContainerFrame:
        """Get the innermost container."""
        return self._stack[-1]

    def depth(self) -> int:
        """Current nesting depth (document = 0)."""
        return len(self._stack) - 1

    def find_owner(self, indent: int) -> tuple[ContainerFrame, int]:
        """
        Find which container owns content at this indent.

        Returns:
            (owner_frame, stack_index) - the frame and its position in stack

        Walks from innermost to outermost, returns first container
        that claims the indent.
        """
        for i in range(len(self._stack) - 1, -1, -1):
            frame = self._stack[i]
            if frame.owns_content(indent):
                return (frame, i)
        return (self._stack[0], 0)

    def find_sibling_list(self, marker_indent: int) -> tuple[ContainerFrame, int] | None:
        """
        Find a list container where a marker at this indent would be a sibling.

        Returns None if no such list exists (marker starts new list at document level).
        """
        for i in range(len(self._stack) - 1, -1, -1):
            frame = self._stack[i]
            if frame.container_type == ContainerType.LIST:
                if frame.owns_marker(marker_indent):
                    return (frame, i)
        return None

    def pop_until(self, target_index: int) -> list[ContainerFrame]:
        """
        Pop containers until stack has target_index + 1 elements.

        Returns list of popped frames (innermost first).
        """
        popped = []
        while len(self._stack) > target_index + 1:
            popped.append(self.pop())
        return popped

    def mark_loose(self) -> None:
        """Mark current container as loose (saw blank line with content after)."""
        self._stack[-1].is_loose = True
        self._stack[-1].saw_blank_line = True
```

### Token Enrichment

Add pre-computed `line_indent` to tokens at lex time. This replaces repeated `get_line_indent(source, offset)` calls.

```python
@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    location: SourceLocation

    # NEW: Pre-computed by lexer (Phase 1)
    line_indent: int = -1  # -1 = not computed, ≥0 = cached indent

    @property
    def is_blank(self) -> bool:
        return self.type == TokenType.BLANK_LINE
```

**Note**: The original proposal included `line_content: str` but this is removed due to memory overhead (+28% per token) with no benefit—the content can be derived from `value` when needed.

**Memory impact**:
- Current Token: 56 bytes
- With `line_indent`: 64 bytes (+14%)
- Per 500-line document: +4 KB (acceptable)

### Parsing Algorithm

```python
class BlockParsingMixin:
    _containers: ContainerStack

    def _parse_blocks(self) -> list[Block]:
        """Main block parsing loop using container stack."""
        self._containers = ContainerStack()
        blocks: list[Block] = []

        while not self._at_end():
            tok = self._current
            indent = tok.line_indent

            # Step 1: Find owner of this indent
            owner, owner_idx = self._containers.find_owner(indent)

            # Step 2: If owner is not current, pop containers
            if owner_idx < self._containers.depth():
                self._containers.pop_until(owner_idx)

            # Step 3: Route to appropriate handler based on owner + token type
            block = self._dispatch_token(tok, owner)
            if block:
                blocks.append(block)

        # Pop remaining containers
        while self._containers.depth() > 0:
            self._containers.pop()

        return blocks

    def _dispatch_token(self, tok: Token, owner: ContainerFrame) -> Block | None:
        """Route token to handler based on container context."""

        match tok.type:
            case TokenType.LIST_ITEM_MARKER:
                return self._handle_list_marker(tok, owner)

            case TokenType.BLANK_LINE:
                return self._handle_blank_line_stack(tok, owner)

            case TokenType.PARAGRAPH_LINE:
                return self._handle_paragraph(tok, owner)

            case TokenType.INDENTED_CODE:
                return self._handle_indented_code_stack(tok, owner)

            case TokenType.BLOCK_QUOTE_MARKER:
                return self._handle_block_quote(tok, owner)

            case TokenType.FENCED_CODE_START:
                return self._handle_fenced_code(tok, owner)

            case _:
                return None

    def _handle_indented_code_stack(self, tok: Token, owner: ContainerFrame) -> Block | None:
        """
        Handle INDENTED_CODE with container-aware classification.

        Key insight: INDENTED_CODE is only "code" if it's 4+ beyond content_indent.
        Otherwise it's paragraph continuation or literal content.
        """
        indent = tok.line_indent
        content_indent = owner.content_indent

        indent_beyond = indent - content_indent

        if indent_beyond >= 4:
            return self._parse_indented_code_block(tok)
        elif owner.container_type == ContainerType.LIST_ITEM:
            return self._parse_continuation_paragraph(tok, owner)
        else:
            return self._parse_paragraph(tok)
```

---

## Performance Analysis

### Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `push()` | O(1) | Append to list |
| `pop()` | O(1) | Pop from list + O(1) parent update |
| `find_owner()` | O(d) | d = stack depth, typically ≤ 10 |
| `find_sibling_list()` | O(d) | Same as above |
| `pop_until()` | O(d) | At most d pops |

**Overall**: For n tokens, parsing is **O(n × d)** where d is max nesting depth.

In practice, d ≤ 10 for reasonable documents, so this is effectively **O(n)**.

### Space Complexity

| Structure | Size | Notes |
|-----------|------|-------|
| ContainerStack | O(d) | d frames on stack |
| ContainerFrame | O(1) | Fixed-size dataclass (~100 bytes with slots) |
| Token enrichment | +8 bytes per token | Single `line_indent` field |

**Total additional memory**: O(d) + O(n × 8) ≈ negligible for typical documents.

### Comparison with Current Approach

| Aspect | Current | Proposed |
|--------|---------|----------|
| Indent checks per token | 3-5 (scattered) | 1-2 (centralized) |
| Source lookups | 16 get_line_indent calls | 0 (pre-computed) |
| State propagation | Manual, error-prone | Automatic on pop() |
| Code locations | 6 files, 81 references | 1 module + callers |

---

## Migration Path

### Phase 1: Token Enrichment (Low Risk) ✓ Recommended First Step

1. Add `line_indent` field to `Token` dataclass
2. Update lexer to compute indent at token creation
3. Replace `get_line_indent(source, offset)` calls with `tok.line_indent`
4. **No behavioral changes, just cleanup**

**Validation**: All existing tests must pass unchanged.

### Phase 2: ContainerStack Introduction (Medium Risk)

1. Add `ContainerStack` and `ContainerFrame` classes to new module
2. Add `_containers` field to parser, initialize in `parse()`
3. Add stack push/pop calls alongside existing logic (dual-write)
4. Add assertions: `assert self._containers.current().content_indent == content_indent`
5. **Existing logic still controls behavior, stack is read-only validation**

**Validation**: Run full CommonMark spec test suite; compare results before/after.

### Phase 3: Stack-Driven Dispatch (Higher Risk)

1. Refactor `_parse_list_item` to use `_containers.find_owner()`
2. Refactor blank line handling to use `pop()` with propagation
3. Remove old indent-checking parameters
4. **Stack becomes source of truth**

**Validation**: Full spec suite + performance benchmarks.

### Phase 4: Cleanup

1. Remove redundant parameters (`start_indent`, `content_indent` passed explicitly)
2. Simplify `handle_blank_line` to use stack queries
3. Delete `_handle_indented_code_in_item` and similar workarounds
4. Update docstrings and type hints

---

## Example: Indented Code Classification

This example shows how the container stack simplifies INDENTED_CODE handling.

**Input**:
```markdown
1.  A paragraph
    with two lines.

        indented code

    > A block quote.
```

**Current approach** (scattered):
```python
# In _handle_indented_code_in_item (mixin.py:262-279)
check_indent = actual_content_indent if actual_content_indent is not None else content_indent
orig_indent = get_line_indent(self._source, next_tok.location.offset)
indent_beyond = orig_indent - check_indent
if orig_indent >= check_indent and indent_beyond < 4:
    # paragraph continuation
elif indent_beyond >= 4:
    # indented code
```

**With container stack**:
```python
# In _handle_indented_code_stack
owner, _ = self._containers.find_owner(tok.line_indent)
indent_beyond = tok.line_indent - owner.content_indent

if indent_beyond >= 4:
    return self._parse_indented_code_block(tok)
else:
    return self._parse_continuation_paragraph(tok, owner)
```

The logic is the same, but:
- No `get_line_indent()` call (uses `tok.line_indent`)
- No parameter threading (`owner` contains `content_indent`)
- Single location instead of duplicated in multiple handlers

---

## Design Decisions

### 1. ContainerStack as Parser State (not passed explicitly)

**Decision**: Make `_containers` a parser instance attribute.

**Rationale**:
- Matches existing pattern (`_source`, `_tokens`, `_pos`, `_current`)
- Simplifies method signatures
- Testing can still mock/inject via constructor or setup

### 2. Inline Processing (not pre-processing)

**Decision**: Maintain single-pass architecture with inline stack operations.

**Rationale**:
- Single pass is a stated design goal
- Pre-processing would add latency
- Inline operations are O(1) per token

### 3. Fenced Code as Leaf Container

**Decision**: Fenced code blocks push a frame but reject all indent logic inside.

**Rationale**:
- Fenced code content is literal—no parsing inside
- Push on FENCED_CODE_START, pop on FENCED_CODE_END
- All tokens between are passed through unchanged

```python
case TokenType.FENCED_CODE_START:
    self._containers.push(ContainerFrame(
        container_type=ContainerType.FENCED_CODE,
        start_indent=tok.line_indent,
        content_indent=0,  # Irrelevant—no indent logic inside
    ))
    return self._parse_fenced_code_block(tok)
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Behavioral regressions | High | Phase 2 dual-write with assertions |
| Performance regression | Medium | Benchmark before/after each phase |
| Increased complexity | Low | Stack is well-understood pattern; consolidates scattered logic |
| Incomplete migration | Low | Can stop at any phase; each phase has standalone value |

---

## Success Metrics

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Lists compliance | 88.5% | 88.5% | Container stack doesn't address fenced code issues |
| List items compliance | 70.8% | ~75-78% | ~4-6 indented code issues addressable |
| `content_indent` references | 81 | <20 | Centralized in ContainerFrame |
| `get_line_indent` calls | 16 | 0 | Replaced by `tok.line_indent` |
| Parse time | baseline | ≤ baseline | No regression (target 5-10% improvement) |
| Maintainability | scattered | centralized | New indent edge cases: single location |

---

## Out of Scope

The following issues are NOT addressed by this RFC:

1. **Fenced code content parsing** (Examples 318, 321, 324, 263)
   - Root cause: Fenced code lexer/parser, not indent logic
   - Recommendation: Separate RFC for fenced code improvements

2. **Block quote nesting edge cases**
   - Some failures relate to token classification, not indent ownership
   - May benefit from container stack but needs separate analysis

3. **Lazy continuation lines**
   - Already handled correctly in `_parse_paragraph`
   - Container stack uses same logic; no change needed

---

## Conclusion

The Container Stack architecture addresses code quality concerns in patitas's list parsing:

1. **Centralizes** 81 scattered `content_indent` references
2. **Eliminates** 16 repeated `get_line_indent()` source lookups
3. **Automates** state propagation between nested containers
4. **Maintains** single-pass lexer benefits
5. **Provides** clear ownership semantics via `find_owner()`

The phased migration allows incremental validation and rollback. Phase 1 (token enrichment) can be implemented immediately with zero behavioral risk.

**Recommendation**: Proceed with Phase 1, evaluate results, then decide on Phases 2-4.

---

## Appendix A: Implementation Location

```
bengal/rendering/parsers/patitas/parsing/
├── containers.py          # NEW: ContainerStack, ContainerFrame
├── blocks/
│   └── list/
│       ├── mixin.py       # MODIFIED: Use container stack
│       ├── blank_line.py  # SIMPLIFIED: Delegate to stack
│       └── indent.py      # DEPRECATED: Replaced by tok.line_indent
```

## Appendix B: Related Work

- **CommonMark Reference Implementation**: Uses similar stack-based approach
- **markdown-it**: Container stack for block parsing
- **cmark-gfm**: Explicit container tracking

## Appendix C: Validation Results

Validation performed 2026-01-04:

| Example | RFC Claim | Actual | Notes |
|---------|-----------|--------|-------|
| 312 | Fails | ✅ Passes | Already works |
| 313 | Fails | ✅ Passes | Already works |
| 320 | Fails | ✅ Passes | Already works |
| 321 | Fails | ❌ Fails | Fenced code issue (not indent) |
| 326 | Fails | ✅ Passes | Already works |

This validation informed the revised scope of this RFC.

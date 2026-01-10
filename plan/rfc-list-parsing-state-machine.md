# RFC: Explicit State Machine for List Parsing

**Status**: Draft  
**Created**: 2026-01-09  
**Updated**: 2026-01-09  
**Author**: Bengal Contributors

---

## Executive Summary

Refactor `ListParsingMixin` (831 lines) to use an explicit `ListItemState` enum with a transition table, replacing the current implicit state encoded in control flow and local variables. This improves testability, debuggability, and maintainability of the most complex parsing component in Patitas.

**Key Metrics:**
- **831 lines** in current mixin
- **~20 implicit states** encoded in conditionals
- **5 result types** already extracted (`BlankLineResult` family)
- **Target**: Explicit enum with ~8-10 states + transition table

---

## Background

The `ListParsingMixin` in Patitas handles CommonMark list parsing, including:

- Nested lists via indentation tracking
- Task lists with `[ ]` and `[x]` markers
- Loose vs. tight list detection
- Continuation paragraphs
- Indented code within list items
- Block quotes and fenced code in list context

### Current Architecture

```
ListParsingMixin._parse_list()
    └── _parse_list_item()          # 450+ lines, main complexity
        ├── handle_thematic_break()
        ├── handle_fenced_code_immediate()
        ├── handle_blank_line()     # Returns BlankLineResult variants
        ├── _handle_indented_code_in_item()
        └── (inline conditionals for 15+ token types)
```

The current implementation uses:

1. **Implicit state via local variables**: `content_lines`, `saw_paragraph_content`, `actual_content_indent`, `checked`
2. **Control flow as state transitions**: Deep `if/elif/else` chains
3. **Result types for sub-decisions**: `EndList`, `EndItem`, `ContinueList`, `ParseBlock`, `ParseContinuation`

### Problems

| Problem | Impact |
|---------|--------|
| **Hard to test individual states** | Must trace through full parse to reach specific conditions |
| **Difficult to visualize all paths** | 20+ branches obscure valid state sequences |
| **Bug localization is slow** | "Which state were we in when this failed?" |
| **Adding new features is risky** | No clear extension points |

---

## Goals

1. **Explicit states**: All parsing states named and enumerated
2. **Transition table**: All valid transitions documented in one place
3. **Testable isolation**: Each state handler testable independently
4. **Preserve behavior**: Zero CommonMark compliance regressions
5. **Incremental migration**: Can adopt state-by-state

### Non-Goals

- Changing the lexer or token types
- Modifying `ContainerStack` architecture
- Parser combinator rewrite (future consideration)
- Performance optimization (maintain current speed)

---

## Design

### State Enum

```python
from enum import Enum, auto

class ListItemState(Enum):
    """Explicit states for list item parsing.

    State machine for parsing content within a single list item.
    The outer list loop handles item-to-item transitions.
    """

    # === Initial States ===
    AWAITING_FIRST_CONTENT = auto()
    """Just saw marker, no content parsed yet.

    Transitions:
        PARAGRAPH_LINE → IN_PARAGRAPH
        BLANK_LINE → ITEM_COMPLETE (empty item)
        FENCED_CODE_START → IN_FENCED_CODE
        INDENTED_CODE → IN_PARAGRAPH | IN_INDENTED_CODE (depends on indent)
        LIST_ITEM_MARKER → IN_NESTED_LIST | ITEM_COMPLETE
        THEMATIC_BREAK → emit ThematicBreak, stay AWAITING_FIRST_CONTENT
    """

    # === Content States ===
    IN_PARAGRAPH = auto()
    """Accumulating paragraph lines.

    Transitions:
        PARAGRAPH_LINE → IN_PARAGRAPH (accumulate)
        BLANK_LINE → AFTER_BLANK_IN_CONTENT
        LIST_ITEM_MARKER → check indent → IN_NESTED_LIST | ITEM_COMPLETE
        INDENTED_CODE → check indent → IN_PARAGRAPH | IN_INDENTED_CODE
        FENCED_CODE_START → emit Paragraph, IN_FENCED_CODE
        BLOCK_QUOTE_MARKER → emit Paragraph, IN_BLOCK_QUOTE
        ATX_HEADING → emit Paragraph, emit Heading, IN_PARAGRAPH
        THEMATIC_BREAK → emit Paragraph, emit ThematicBreak, AWAITING_FIRST_CONTENT
    """

    IN_INDENTED_CODE = auto()
    """Inside indented code block (4+ spaces beyond content indent).

    Transitions:
        INDENTED_CODE → IN_INDENTED_CODE (accumulate)
        BLANK_LINE → AFTER_BLANK_IN_CODE
        * → emit IndentedCode, re-evaluate token
    """

    # === Post-Blank States ===
    AFTER_BLANK_IN_CONTENT = auto()
    """Saw blank line after paragraph content. List may become loose.

    Transitions:
        PARAGRAPH_LINE (at content_indent) → IN_PARAGRAPH (continuation, mark loose)
        LIST_ITEM_MARKER (nested) → IN_NESTED_LIST (mark loose)
        LIST_ITEM_MARKER (sibling) → ITEM_COMPLETE (mark parent loose)
        INDENTED_CODE → context-dependent routing
        FENCED_CODE_START → IN_FENCED_CODE (mark loose)
        BLOCK_QUOTE_MARKER → IN_BLOCK_QUOTE (mark loose)
        * → ITEM_COMPLETE or LIST_COMPLETE
    """

    AFTER_BLANK_IN_CODE = auto()
    """Saw blank line during indented code. May continue or end code block.

    Transitions:
        INDENTED_CODE (4+ beyond content) → IN_INDENTED_CODE (include blank)
        * → emit IndentedCode, transition based on token
    """

    # === Nested Container States ===
    IN_NESTED_LIST = auto()
    """Parsing a nested list (recursive call).

    After nested list completes, return to IN_PARAGRAPH or AFTER_BLANK_IN_CONTENT
    depending on what follows.
    """

    IN_BLOCK_QUOTE = auto()
    """Parsing a block quote within the list item.

    Block quote parsing is delegated to BlockQuoteMixin.
    After completion, return to appropriate content state.
    """

    IN_FENCED_CODE = auto()
    """Parsing a fenced code block within the list item.

    Fenced code parsing is delegated to FencedCodeMixin.
    After completion, return to appropriate content state.
    """

    # === Terminal States ===
    ITEM_COMPLETE = auto()
    """Current list item is complete. Return to list loop."""

    LIST_COMPLETE = auto()
    """Entire list is complete. Return to parent parser."""
```

### Transition Table

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True, slots=True)
class Transition:
    """Result of a state transition."""
    next_state: ListItemState
    action: TransitionAction
    emit: Block | None = None

class TransitionAction(Enum):
    """Actions to take during transition."""
    CONTINUE = auto()           # Keep parsing in new state
    ACCUMULATE = auto()         # Add to current content buffer
    EMIT_PARAGRAPH = auto()     # Flush paragraph, then continue
    EMIT_CODE = auto()          # Flush indented code, then continue
    MARK_LOOSE = auto()         # Mark current container loose
    MARK_PARENT_LOOSE = auto()  # Mark parent list loose
    DELEGATE_NESTED = auto()    # Recursive call for nested list
    DELEGATE_BLOCK = auto()     # Delegate to block parser
    COMPLETE_ITEM = auto()      # Finalize and return item
    COMPLETE_LIST = auto()      # End entire list

# Type alias for handler functions
TransitionHandler = Callable[
    ['ListItemStateMachine', 'Token'],
    Transition
]

# Transition table: (state, token_type) → handler
TRANSITIONS: dict[tuple[ListItemState, TokenType], TransitionHandler] = {
    # === AWAITING_FIRST_CONTENT ===
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.PARAGRAPH_LINE):
        handle_first_paragraph_line,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.BLANK_LINE):
        handle_empty_item,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.FENCED_CODE_START):
        handle_immediate_fenced_code,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.INDENTED_CODE):
        handle_first_indented_code,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.LIST_ITEM_MARKER):
        handle_first_nested_marker,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.THEMATIC_BREAK):
        handle_thematic_break_first,
    (ListItemState.AWAITING_FIRST_CONTENT, TokenType.BLOCK_QUOTE_MARKER):
        handle_first_block_quote,

    # === IN_PARAGRAPH ===
    (ListItemState.IN_PARAGRAPH, TokenType.PARAGRAPH_LINE):
        accumulate_paragraph_line,
    (ListItemState.IN_PARAGRAPH, TokenType.BLANK_LINE):
        handle_blank_after_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.LIST_ITEM_MARKER):
        handle_marker_in_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.INDENTED_CODE):
        handle_code_in_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.FENCED_CODE_START):
        handle_fence_in_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.BLOCK_QUOTE_MARKER):
        handle_quote_in_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.ATX_HEADING):
        handle_heading_in_paragraph,
    (ListItemState.IN_PARAGRAPH, TokenType.THEMATIC_BREAK):
        handle_thematic_break_in_paragraph,

    # === AFTER_BLANK_IN_CONTENT ===
    (ListItemState.AFTER_BLANK_IN_CONTENT, TokenType.PARAGRAPH_LINE):
        handle_continuation_paragraph,
    (ListItemState.AFTER_BLANK_IN_CONTENT, TokenType.LIST_ITEM_MARKER):
        handle_marker_after_blank,
    (ListItemState.AFTER_BLANK_IN_CONTENT, TokenType.INDENTED_CODE):
        handle_code_after_blank,
    (ListItemState.AFTER_BLANK_IN_CONTENT, TokenType.FENCED_CODE_START):
        handle_fence_after_blank,
    (ListItemState.AFTER_BLANK_IN_CONTENT, TokenType.BLOCK_QUOTE_MARKER):
        handle_quote_after_blank,

    # === IN_INDENTED_CODE ===
    (ListItemState.IN_INDENTED_CODE, TokenType.INDENTED_CODE):
        accumulate_indented_code,
    (ListItemState.IN_INDENTED_CODE, TokenType.BLANK_LINE):
        handle_blank_in_code,

    # ... additional transitions
}

# Default handler for unspecified transitions
def default_transition(sm: 'ListItemStateMachine', token: Token) -> Transition:
    """Handle unexpected token by completing item."""
    return Transition(
        next_state=ListItemState.ITEM_COMPLETE,
        action=TransitionAction.COMPLETE_ITEM,
    )
```

### State Machine Class

```python
@dataclass
class ListItemContext:
    """Accumulated context during list item parsing."""
    content_lines: list[str] = field(default_factory=list)
    children: list[Block] = field(default_factory=list)
    checked: bool | None = None
    actual_content_indent: int | None = None
    code_lines: list[str] = field(default_factory=list)  # For indented code


class ListItemStateMachine:
    """Explicit FSM for parsing a single list item.

    Usage:
        sm = ListItemStateMachine(marker_token, containers, parser_context)
        item = sm.run(token_iterator)
    """

    def __init__(
        self,
        marker_token: Token,
        containers: ContainerStack,
        parse_context: ParseContext,
    ):
        self.marker_token = marker_token
        self.containers = containers
        self.ctx = parse_context

        # State
        self.state = ListItemState.AWAITING_FIRST_CONTENT
        self.context = ListItemContext()

        # Derived from marker
        self.start_indent = get_marker_indent(marker_token.value)
        self.content_indent = self._calculate_initial_content_indent()

    def step(self, token: Token) -> Transition:
        """Execute one state transition."""
        key = (self.state, token.type)
        handler = TRANSITIONS.get(key, default_transition)
        return handler(self, token)

    def run(self, tokens: TokenIterator) -> ListItem:
        """Run FSM until terminal state, return completed ListItem."""
        for token in tokens:
            transition = self.step(token)

            # Execute transition action
            self._execute_action(transition.action, token)

            # Emit block if specified
            if transition.emit:
                self.context.children.append(transition.emit)

            # Update state
            self.state = transition.next_state

            # Check terminal states
            if self.state == ListItemState.ITEM_COMPLETE:
                tokens.pushback(token)  # Re-process token in list loop
                break
            elif self.state == ListItemState.LIST_COMPLETE:
                tokens.pushback(token)
                break

        return self._finalize()

    def _execute_action(self, action: TransitionAction, token: Token) -> None:
        """Execute the transition action."""
        match action:
            case TransitionAction.ACCUMULATE:
                self.context.content_lines.append(token.value.lstrip())

            case TransitionAction.EMIT_PARAGRAPH:
                if self.context.content_lines:
                    content = '\n'.join(self.context.content_lines)
                    inlines = self.ctx.parse_inline(content, self.marker_token.location)
                    self.context.children.append(
                        Paragraph(location=self.marker_token.location, children=inlines)
                    )
                    self.context.content_lines.clear()

            case TransitionAction.EMIT_CODE:
                if self.context.code_lines:
                    code = '\n'.join(self.context.code_lines) + '\n'
                    self.context.children.append(
                        IndentedCode(location=self.marker_token.location, code=code)
                    )
                    self.context.code_lines.clear()

            case TransitionAction.MARK_LOOSE:
                self.containers.mark_loose()

            case TransitionAction.MARK_PARENT_LOOSE:
                self.containers.mark_parent_list_loose()

            case TransitionAction.DELEGATE_NESTED:
                # Recursive list parsing
                nested = self.ctx.parse_list(parent_indent=self.start_indent)
                self.context.children.append(nested)

            case TransitionAction.DELEGATE_BLOCK:
                block = self.ctx.parse_block()
                if block:
                    self.context.children.append(block)

            case _:
                pass  # CONTINUE, COMPLETE_ITEM, COMPLETE_LIST need no action

    def _finalize(self) -> ListItem:
        """Finalize and return the completed ListItem."""
        # Flush any remaining paragraph content
        if self.context.content_lines:
            content = '\n'.join(self.context.content_lines)
            inlines = self.ctx.parse_inline(content, self.marker_token.location)
            self.context.children.append(
                Paragraph(location=self.marker_token.location, children=inlines)
            )

        # Flush any remaining code
        if self.context.code_lines:
            code = '\n'.join(self.context.code_lines) + '\n'
            self.context.children.append(
                IndentedCode(location=self.marker_token.location, code=code)
            )

        return ListItem(
            location=self.marker_token.location,
            children=tuple(self.context.children),
            checked=self.context.checked,
        )
```

### Example Transition Handlers

```python
def handle_first_paragraph_line(sm: ListItemStateMachine, token: Token) -> Transition:
    """Handle first paragraph line after marker."""
    line = token.value.lstrip()

    # Skip whitespace-only lines immediately after marker
    if not line:
        return Transition(
            next_state=ListItemState.AWAITING_FIRST_CONTENT,
            action=TransitionAction.CONTINUE,
        )

    # Check for task list marker
    checked, content = extract_task_marker(line)
    if checked is not None:
        sm.context.checked = checked
        line = content

    # Update actual content indent
    sm.context.actual_content_indent = sm._calculate_actual_content_indent(token)
    sm.containers.update_content_indent(sm.context.actual_content_indent)

    sm.context.content_lines.append(line)

    return Transition(
        next_state=ListItemState.IN_PARAGRAPH,
        action=TransitionAction.CONTINUE,
    )


def handle_blank_after_paragraph(sm: ListItemStateMachine, token: Token) -> Transition:
    """Handle blank line while in paragraph state."""
    # Consume consecutive blank lines
    # (handled by caller consuming blanks before calling step)

    return Transition(
        next_state=ListItemState.AFTER_BLANK_IN_CONTENT,
        action=TransitionAction.CONTINUE,
    )


def handle_marker_after_blank(sm: ListItemStateMachine, token: Token) -> Transition:
    """Handle list marker after blank line - could be nested or sibling."""
    marker_indent = get_marker_indent(token.value)
    check_indent = sm.context.actual_content_indent or sm.content_indent

    # Less than start_indent → belongs to outer list
    if marker_indent < sm.start_indent:
        return Transition(
            next_state=ListItemState.LIST_COMPLETE,
            action=TransitionAction.EMIT_PARAGRAPH,
        )

    # Less than content_indent but >= start_indent → sibling item
    if marker_indent < check_indent:
        return Transition(
            next_state=ListItemState.ITEM_COMPLETE,
            action=TransitionAction.EMIT_PARAGRAPH | TransitionAction.MARK_PARENT_LOOSE,
        )

    # At or beyond content_indent → nested list
    return Transition(
        next_state=ListItemState.IN_NESTED_LIST,
        action=TransitionAction.EMIT_PARAGRAPH | TransitionAction.MARK_LOOSE | TransitionAction.DELEGATE_NESTED,
    )


def handle_continuation_paragraph(sm: ListItemStateMachine, token: Token) -> Transition:
    """Handle paragraph line after blank - continuation makes list loose."""
    para_indent = token.line_indent
    check_indent = sm.context.actual_content_indent or sm.content_indent

    if para_indent < check_indent:
        # Not indented enough - terminates list
        return Transition(
            next_state=ListItemState.LIST_COMPLETE,
            action=TransitionAction.EMIT_PARAGRAPH,
        )

    # Continuation paragraph - mark loose
    sm.context.content_lines.append(token.value.lstrip())

    return Transition(
        next_state=ListItemState.IN_PARAGRAPH,
        action=TransitionAction.MARK_LOOSE,
    )
```

---

## Migration Strategy

### Phase 1: Add State Enum (Non-Breaking)

1. Create `bengal/rendering/parsers/patitas/parsing/blocks/list/state.py`
2. Define `ListItemState` enum
3. Add state logging to existing mixin for validation

**Files Changed:**
- `list/state.py` (new)
- `list/mixin.py` (add state logging)

### Phase 2: Extract Transition Handlers

1. Create `list/transitions.py` with handler functions
2. Each handler mirrors existing conditional branch
3. Add unit tests for each handler in isolation

**Files Changed:**
- `list/transitions.py` (new)
- `tests/unit/parsing/list/test_transitions.py` (new)

### Phase 3: Create State Machine Class

1. Create `ListItemStateMachine` class
2. Wire up transition table
3. Run parallel with existing mixin, assert identical output

**Files Changed:**
- `list/state_machine.py` (new)
- `tests/unit/parsing/list/test_state_machine.py` (new)

### Phase 4: Replace Mixin Implementation

1. Update `_parse_list_item` to use state machine
2. Remove redundant code from mixin
3. Full CommonMark compliance test pass

**Files Changed:**
- `list/mixin.py` (simplified)

### Phase 5: Cleanup

1. Remove legacy code paths
2. Update documentation
3. Add state diagram to architecture docs

---

## Testing Strategy

### Unit Tests for Handlers

```python
# tests/unit/parsing/list/test_transitions.py

def test_first_paragraph_line_extracts_task_marker():
    """Task marker is extracted from first content line."""
    sm = make_state_machine(marker="- ")
    token = make_token(TokenType.PARAGRAPH_LINE, "[x] Task content")

    result = handle_first_paragraph_line(sm, token)

    assert sm.context.checked is True
    assert sm.context.content_lines == ["Task content"]
    assert result.next_state == ListItemState.IN_PARAGRAPH


def test_marker_after_blank_nested():
    """Marker at content indent after blank starts nested list."""
    sm = make_state_machine(marker="- ", content_indent=2)
    sm.state = ListItemState.AFTER_BLANK_IN_CONTENT
    token = make_token(TokenType.LIST_ITEM_MARKER, "  - nested", line_indent=2)

    result = handle_marker_after_blank(sm, token)

    assert result.next_state == ListItemState.IN_NESTED_LIST
    assert TransitionAction.DELEGATE_NESTED in result.action


def test_marker_after_blank_sibling():
    """Marker at start indent after blank ends item (sibling)."""
    sm = make_state_machine(marker="- ", start_indent=0, content_indent=2)
    sm.state = ListItemState.AFTER_BLANK_IN_CONTENT
    token = make_token(TokenType.LIST_ITEM_MARKER, "- sibling", line_indent=0)

    result = handle_marker_after_blank(sm, token)

    assert result.next_state == ListItemState.ITEM_COMPLETE
    assert TransitionAction.MARK_PARENT_LOOSE in result.action
```

### Integration Tests

```python
# tests/integration/parsing/test_list_state_machine.py

@pytest.mark.parametrize("spec_example", COMMONMARK_LIST_EXAMPLES)
def test_commonmark_compliance(spec_example):
    """State machine produces identical output to spec."""
    markdown = spec_example.markdown
    expected_html = spec_example.html

    # Parse with state machine
    result = parse_with_state_machine(markdown)
    actual_html = render_html(result)

    assert actual_html == expected_html


def test_state_machine_matches_legacy():
    """State machine produces identical AST to legacy mixin."""
    for test_case in CORPUS:
        legacy_ast = parse_legacy(test_case)
        new_ast = parse_state_machine(test_case)
        assert legacy_ast == new_ast, f"Mismatch for: {test_case[:50]}..."
```

### State Coverage Tests

```python
def test_all_states_reachable():
    """Every state in enum is reachable from AWAITING_FIRST_CONTENT."""
    reachable = compute_reachable_states(
        start=ListItemState.AWAITING_FIRST_CONTENT,
        transitions=TRANSITIONS,
    )

    all_states = set(ListItemState)
    unreachable = all_states - reachable

    assert not unreachable, f"Unreachable states: {unreachable}"


def test_terminal_states_have_no_outgoing():
    """Terminal states have no outgoing transitions."""
    terminal = {ListItemState.ITEM_COMPLETE, ListItemState.LIST_COMPLETE}

    for (state, _), _ in TRANSITIONS.items():
        assert state not in terminal, f"Terminal state {state} has outgoing transition"
```

---

## State Diagram

```
                              ┌─────────────────────────────────────────────┐
                              │                                             │
                              ▼                                             │
┌───────────────────────────────────────────────┐                          │
│         AWAITING_FIRST_CONTENT                │                          │
│  (just saw marker, waiting for content)       │                          │
└───────────────────────────────────────────────┘                          │
        │              │              │                                     │
        │ PARA_LINE    │ BLANK        │ FENCE/CODE/MARKER                  │
        ▼              ▼              ▼                                     │
┌──────────────┐  ┌────────────┐  ┌─────────────────┐                      │
│ IN_PARAGRAPH │  │ITEM_COMPLETE│  │ IN_FENCED_CODE  │                      │
│              │  │(empty item) │  │ IN_INDENTED_CODE│                      │
└──────────────┘  └────────────┘  │ IN_NESTED_LIST  │                      │
        │                          └─────────────────┘                      │
        │ BLANK                           │                                 │
        ▼                                 │                                 │
┌───────────────────────┐                 │                                 │
│ AFTER_BLANK_IN_CONTENT│◄────────────────┘                                 │
│   (list may be loose) │                                                   │
└───────────────────────┘                                                   │
        │              │              │                                     │
        │ PARA_LINE    │ MARKER       │ other                              │
        │ (indent ok)  │              │                                     │
        ▼              ▼              ▼                                     │
┌──────────────┐  ┌──────────────────────┐  ┌─────────────┐                │
│ IN_PARAGRAPH │  │ ITEM_COMPLETE        │  │LIST_COMPLETE│                │
│ (loose list) │  │ (sibling, mark loose)│  │             │                │
└──────────────┘  └──────────────────────┘  └─────────────┘                │
        │                                                                   │
        └───────────────────────────────────────────────────────────────────┘
                    (more tokens → back to content states)
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Behavior regression** | High | Parallel execution + diff testing in Phase 3 |
| **Performance degradation** | Medium | Benchmark before/after; handler dispatch is O(1) |
| **Increased code size** | Low | Tradeoff for clarity; total may decrease after cleanup |
| **Learning curve** | Low | State diagram and tests serve as documentation |
| **Edge case misses** | Medium | CommonMark spec tests + fuzzing |

---

## Success Criteria

1. ☐ All 650 CommonMark spec tests pass
2. ☐ State machine output matches legacy for all test corpus
3. ☐ Each state has ≥1 unit test
4. ☐ All states reachable (coverage test)
5. ☐ No performance regression (±5%)
6. ☐ Mixin reduced by ≥200 lines
7. ☐ State diagram in architecture docs

---

## Timeline Estimate

| Phase | Effort | Dependencies | Status |
|-------|--------|--------------|--------|
| Phase 1: Add State Enum | 2 hours | None | ☐ Pending |
| Phase 2: Extract Handlers | 4 hours | Phase 1 | ☐ Pending |
| Phase 3: State Machine Class | 4 hours | Phase 2 | ☐ Pending |
| Phase 4: Replace Mixin | 3 hours | Phase 3 | ☐ Pending |
| Phase 5: Cleanup | 2 hours | Phase 4 | ☐ Pending |
| **Total** | **~15 hours** | | |

---

## Alternatives Considered

### Parser Combinators

**Pros**: Highly composable, declarative grammar  
**Cons**: Needs state monad for indent tracking, high rewrite effort, CommonMark edge cases fight the model

**Verdict**: Better for a future Patitas v2 rewrite, not incremental refactor.

### Keep Implicit State

**Pros**: No migration effort  
**Cons**: Testing difficulty, bug localization, onboarding friction

**Verdict**: Status quo is increasingly painful as complexity grows.

### Statecharts (Hierarchical FSM)

**Pros**: Nested states, history, parallel regions  
**Cons**: Overkill for this use case, adds library dependency

**Verdict**: Flat enum sufficient; `ContainerStack` already handles nesting.

---

## References

**Source Locations:**
- Current mixin: `bengal/rendering/parsers/patitas/parsing/blocks/list/mixin.py` (831 lines)
- Container stack: `bengal/rendering/parsers/patitas/parsing/containers.py`
- Blank line handlers: `bengal/rendering/parsers/patitas/parsing/blocks/list/blank_line.py`
- Marker utilities: `bengal/rendering/parsers/patitas/parsing/blocks/list/marker.py`

**Related RFCs:**
- `plan/rfc-container-stack-parsing.md` - ContainerStack architecture
- `plan/rfc-patitas-commonmark-compliance.md` - Compliance targets

**External Resources:**
- CommonMark Spec: https://spec.commonmark.org/
- State Machine Pattern: https://refactoring.guru/design-patterns/state

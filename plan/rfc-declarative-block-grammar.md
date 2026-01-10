# RFC: Declarative Block Grammar for Patitas

**Status**: Draft  
**Author**: Bengal Team  
**Date**: 2026-01-05  
**Affects**: `bengal/rendering/parsers/patitas/`

---

## Executive Summary

This RFC proposes a **Declarative Block Grammar** architecture for Patitas's block parsing. Instead of encoding block rules procedurally in parser code, block types declare their grammatical properties (containment, interruption, continuation) as data. The parser becomes a generic engine that applies these rules.

**The Core Insight**: Procedural parsing answers "How do I parse this?" Declarative grammar answers "What IS a valid document?" The second is more fundamental—parsing becomes derivable.

**Key Outcomes**:
- Block rules become testable, verifiable data instead of scattered code
- New block types plug in without modifying parser logic
- Grammar properties become queryable (can X contain Y? what interrupts Z?)
- Enables formal verification of termination, determinism, completeness
- Foundation for incremental parsing (rules determine affected regions)
- Potential 2-4x speedup on block dispatch via compiled lookup tables

**Relationship to Container Stack RFC**: This RFC builds on the Container Stack architecture (implemented). Container Stack provides the runtime state management; Declarative Block Grammar provides the rules that drive it.

---

## Problem Statement

### Current Architecture

Patitas uses **procedural block parsing**: rules are encoded in control flow.

```python
# Current: Rules scattered in match statements
def _parse_block(self):
    match token.type:
        case TokenType.ATX_HEADING:
            return self._parse_atx_heading()
        case TokenType.LIST_ITEM_MARKER:
            return self._parse_list()
        # ... 15+ cases with embedded logic
```

```python
# Current: Interruption rules embedded in paragraph parsing
def _parse_paragraph(self):
    while not self._at_end():
        if token.type == TokenType.ATX_HEADING:
            break  # Heading interrupts - but why? Where's the rule?
        if token.type == TokenType.LIST_ITEM_MARKER:
            # Complex conditional logic...
            if has_content and (not ordered or start == 1):
                break
```

### Problems with Procedural Approach

| Problem | Impact |
|---------|--------|
| **Rules scattered across files** | Hard to understand block grammar holistically |
| **Logic duplication** | Interruption checks repeated in multiple places |
| **Implicit dependencies** | Adding block type requires modifying parser in multiple locations |
| **No queryability** | "Can list contain code fence?" requires reading code |
| **Testing difficulty** | Must test rules through full parsing, not in isolation |
| **Verification impossible** | Can't prove termination, determinism without full program analysis |
| **Optimization limits** | Compiler can't see grammar structure to optimize |

### Motivating Example

To add a new block type (e.g., `Callout`), you currently must:

1. Add token type to `TokenType` enum
2. Add lexer classification logic
3. Add case to `_parse_block()` dispatch
4. Add interruption checks to `_parse_paragraph()`
5. Add containment logic to relevant containers
6. Add continuation logic to `_parse_callout()`
7. Update tests across multiple files

With declarative grammar, you would:

1. Define `CalloutBlock` with its grammatical properties
2. Register it with the parser

The parser handles everything else.

---

## Proposed Solution

### Core Principle: Blocks as Self-Describing Types

Each block type declares its grammatical properties:

```python
@dataclass(frozen=True)
class BlockGrammar:
    """Grammatical properties of a block type."""

    name: str

    # Containment: what can this block hold?
    can_contain: frozenset[str]  # Empty = leaf block

    # Interruption: what can interrupt this block?
    can_be_interrupted_by: frozenset[str]

    # Continuation: when does content continue this block?
    continues_on: ContinuesOn | Callable[[str, ContainerContext], bool]

    # Recognition: when does this block start?
    starts_on: Callable[[str, int, LookaheadTokens], StartMatch | None]

    # Content handling
    lazy_continuation: bool = False  # Can unindented lines continue?
    literal_content: bool = False    # Is content literal (no nested blocks)?

    # Indent behavior
    content_indent_offset: int = 0   # How much indent does content need?
```

### Continuation Factories

To reduce boilerplate and common errors, we use **Continuation Factories** for standard block behaviors:

```python
class ContinuesOn:
    """Pre-defined continuation rules."""

    @staticmethod
    def indent(min_indent: int) -> Callable:
        return lambda line, ctx: count_indent(line) >= min_indent

    @staticmethod
    def marker(char: str) -> Callable:
        return lambda line, ctx: line.lstrip().startswith(char)

    @staticmethod
    def never() -> Callable:
        return lambda line, ctx: False

    @staticmethod
    def paragraph() -> Callable:
        return lambda line, ctx: bool(line.strip()) and not ctx.is_interrupted_by(line)
```

### Block Type Definitions

```python
# blocks/grammar/definitions.py

PARAGRAPH = BlockGrammar(
    name="paragraph",
    can_contain=frozenset(),  # Leaf
    can_be_interrupted_by=frozenset({
        "atx_heading", "setext_heading", "thematic_break",
        "fenced_code", "html_block", "block_quote",
        "list",  # With conditions (see below)
    }),
    continues_on=ContinuesOn.paragraph(),
    starts_on=lambda line, indent, tokens: (
        StartMatch("paragraph", consumed=0, content_indent=indent)
        if line.strip() else None
    ),
    lazy_continuation=True,
    literal_content=False,
)

LIST = BlockGrammar(
    name="list",
    can_contain=frozenset({"list_item"}),
    can_be_interrupted_by=frozenset({
        "atx_heading", "thematic_break", "fenced_code", "block_quote",
    }),
    continues_on=lambda line, ctx: (
        is_list_marker(line, ctx.list_type) or
        count_indent(line) >= ctx.content_indent
    ),
    starts_on=parse_list_start,
    lazy_continuation=True,
    literal_content=False,
)

LIST_ITEM = BlockGrammar(
    name="list_item",
    can_contain=frozenset({
        "paragraph", "list", "fenced_code", "indented_code",
        "block_quote", "thematic_break", "html_block",
    }),
    can_be_interrupted_by=frozenset({
        "list_item",  # Sibling item
    }),
    continues_on=lambda line, ctx: (
        count_indent(line) >= ctx.content_indent or
        (ctx.lazy_continuation and is_lazy_content(line))
    ),
    starts_on=parse_list_item_start,
    lazy_continuation=True,
    literal_content=False,
)

FENCED_CODE = BlockGrammar(
    name="fenced_code",
    can_contain=frozenset(),  # Leaf
    can_be_interrupted_by=frozenset(),  # Nothing interrupts!
    continues_on=lambda line, ctx: not is_fence_close(line, ctx.fence_char, ctx.fence_count),
    starts_on=parse_fence_start,
    lazy_continuation=False,
    literal_content=True,  # Content is not parsed as blocks
)

BLOCK_QUOTE = BlockGrammar(
    name="block_quote",
    can_contain=frozenset({
        "paragraph", "list", "fenced_code", "indented_code",
        "block_quote", "thematic_break", "atx_heading", "html_block",
    }),
    can_be_interrupted_by=frozenset(),  # Ends on blank or no marker
    continues_on=lambda line, ctx: line.lstrip().startswith(">"),
    starts_on=parse_block_quote_start,
    lazy_continuation=True,
    literal_content=False,
)

ATX_HEADING = BlockGrammar(
    name="atx_heading",
    can_contain=frozenset(),  # Leaf (inline content, not blocks)
    can_be_interrupted_by=frozenset(),  # Single-line, can't be interrupted
    continues_on=ContinuesOn.never(),
    starts_on=parse_atx_heading_start,  # Signature: (line, indent, tokens) -> Match
    lazy_continuation=False,
    literal_content=False,
)

# ... similar definitions for all block types
```

### Grammar Registry

```python
# blocks/grammar/registry.py

@dataclass
class GrammarRegistry:
    """Registry of all block grammars with compiled lookup tables."""

    _grammars: dict[str, BlockGrammar] = field(default_factory=dict)

    # Compiled lookup tables (built on registration)
    _containment_matrix: dict[tuple[str, str], bool] = field(default_factory=dict)
    _interruption_sets: dict[str, frozenset[str]] = field(default_factory=dict)
    _start_dispatch: dict[str, Callable] = field(default_factory=dict)

    def register(self, grammar: BlockGrammar) -> None:
        """Register a block grammar and update lookup tables."""
        self._grammars[grammar.name] = grammar
        self._rebuild_tables()

    def _rebuild_tables(self) -> None:
        """Rebuild compiled lookup tables from grammar definitions."""
        # Containment matrix
        self._containment_matrix.clear()
        for name, grammar in self._grammars.items():
            for child in grammar.can_contain:
                self._containment_matrix[(name, child)] = True

        # Interruption sets
        self._interruption_sets.clear()
        for name, grammar in self._grammars.items():
            self._interruption_sets[name] = grammar.can_be_interrupted_by

        # Start dispatch (ordered by priority)
        self._start_dispatch = {
            name: grammar.starts_on
            for name, grammar in self._grammars.items()
        }

    # O(1) queries
    def can_contain(self, container: str, child: str) -> bool:
        return self._containment_matrix.get((container, child), False)

    def can_interrupt(self, interrupter: str, target: str) -> bool:
        return interrupter in self._interruption_sets.get(target, frozenset())

    def get_interrupters(self, target: str) -> frozenset[str]:
        return self._interruption_sets.get(target, frozenset())

    def find_starter(self, line: str, indent: int, tokens: LookaheadTokens) -> StartMatch | None:
        """Find block type that starts on this line."""
        for name, starts_on in self._start_dispatch.items():
            match = starts_on(line, indent, tokens)
            if match:
                return match
        return None


# Global registry with CommonMark blocks pre-registered
GRAMMAR = GrammarRegistry()
GRAMMAR.register(PARAGRAPH)
GRAMMAR.register(LIST)
GRAMMAR.register(LIST_ITEM)
GRAMMAR.register(FENCED_CODE)
GRAMMAR.register(BLOCK_QUOTE)
GRAMMAR.register(ATX_HEADING)
# ... register all CommonMark blocks
```

### Generic Parser Engine

```python
# blocks/parser_engine.py

class DeclarativeBlockParser:
    """Generic block parser driven by grammar rules."""

    def __init__(self, grammar: GrammarRegistry):
        self.grammar = grammar
        self.containers = ContainerStack()  # From Container Stack RFC

    def parse(self, source: str) -> Document:
        """Parse source using declarative grammar rules."""
        ctx = ParserContext(source, self.grammar)
        blocks: list[Block] = []

        while not ctx.at_end():
            block = self._parse_next_block(ctx)
            if block:
                blocks.append(block)

        return Document(blocks)

    def _parse_next_block(self, ctx: ParserContext) -> Block | None:
        """Parse the next block using grammar-driven dispatch."""
        line = ctx.current_line()
        indent = count_indent(line)

        # 1. Find owner of this indent (from Container Stack)
        owner = self.containers.find_owner(indent)

        # 2. Check for interruption (O(1) lookup)
        if owner.current_block:
            current_type = owner.current_block.grammar.name
            interrupters = self.grammar.get_interrupters(current_type)

            for interrupter in interrupters:
                # Grammar-driven check: can interrupter start here?
                match = self.grammar._grammars[interrupter].starts_on(line, indent, ctx.tokens)
                if match and self._satisfies_interruption_conditions(match, ctx):
                    owner.close_current()
                    return self._start_block(match, ctx)

        # 3. Check continuation (using grammar's continues_on)
        if owner.current_block:
            grammar = owner.current_block.grammar
            if grammar.continues_on(line, ctx):
                owner.current_block.append_line(line)
                ctx.advance()
                return None

        # 4. Try to start new block (grammar-driven)
        match = self.grammar.find_starter(line, indent, ctx.tokens)
        if match:
            return self._start_block(match, ctx)

        # 5. Default: paragraph
        return self._start_block(
            StartMatch("paragraph", 0, indent),
            ctx
        )

    def _start_block(self, match: StartMatch, ctx: ParserContext) -> Block:
        """Start a new block based on grammar match."""
        grammar = self.grammar._grammars[match.block_type]

        # Push container frame if this is a container
        if grammar.can_contain:
            self.containers.push(ContainerFrame(
                container_type=match.block_type,
                start_indent=ctx.indent,
                content_indent=match.content_indent,
                metadata=match.metadata,
            ))

        # Create block with grammar reference
        block = Block(
            grammar=grammar,
            location=ctx.location(),
            metadata=match.metadata,
        )

        # Parse content based on grammar type
        if grammar.literal_content:
            block.content = self._collect_literal_content(grammar, ctx)
        else:
            block.children = self._parse_block_content(grammar, ctx)

        return block
```

### Conditional Interruption Rules

Some interruption rules have conditions (e.g., "ordered list only interrupts paragraph if start=1"):

```python
@dataclass(frozen=True)
class InterruptionRule:
    """Conditional interruption rule."""

    interrupter: str
    target: str
    condition: Callable[[StartMatch, ParserContext], bool] | None = None


# List interrupting paragraph has conditions
LIST_INTERRUPTS_PARAGRAPH = InterruptionRule(
    interrupter="list",
    target="paragraph",
    condition=lambda match, ctx: (
        # Unordered lists always interrupt
        not match.metadata.get("ordered", False) or
        # Ordered lists only interrupt if start=1
        match.metadata.get("start", 1) == 1
    ) and (
        # Must have content after marker
        match.metadata.get("has_content", False)
    )
)
```

### Sibling Links (Linked Blocks)

Add optional sibling navigation for efficient traversal:

```python
@dataclass
class Block:
    """Block with tree + sibling links."""

    grammar: BlockGrammar
    location: SourceLocation

    # Tree structure
    parent: Block | None = None
    children: list[Block] = field(default_factory=list)

    # Sibling links (linked list)
    prev_sibling: Block | None = None
    next_sibling: Block | None = None

    # Content
    content: str | None = None  # For literal blocks
    metadata: dict = field(default_factory=dict)

    def append_child(self, child: Block) -> None:
        """Append child with automatic sibling linking."""
        child.parent = self
        if self.children:
            last = self.children[-1]
            last.next_sibling = child
            child.prev_sibling = last
        self.children.append(child)
```

---

## Compilation Strategy

### Rule Compilation at Import Time

```python
# blocks/grammar/compiler.py

def compile_grammar(registry: GrammarRegistry) -> CompiledGrammar:
    """Compile declarative grammar to optimized dispatch structures."""

    return CompiledGrammar(
        # O(1) containment check via frozen set
        containment=frozenset(registry._containment_matrix.keys()),

        # O(1) interruption check via dict of frozensets
        interruption={
            name: frozenset(grammar.can_be_interrupted_by)
            for name, grammar in registry._grammars.items()
        },

        # Dispatch table keyed by first character
        start_dispatch=_build_start_dispatch(registry),

        # Continuation predicates (already functions)
        continuation={
            name: grammar.continues_on
            for name, grammar in registry._grammars.items()
        },
    )


def _build_start_dispatch(registry: GrammarRegistry) -> dict[str, list[tuple[str, Callable]]]:
    """Build first-character dispatch table for O(1) block recognition."""
    dispatch: dict[str, list[tuple[str, Callable]]] = defaultdict(list)

    for name, grammar in registry._grammars.items():
        # Analyze starts_on to determine trigger characters
        triggers = _infer_trigger_chars(grammar)
        for char in triggers:
            dispatch[char].append((name, grammar.starts_on))

    return dict(dispatch)


def _infer_trigger_chars(grammar: BlockGrammar) -> set[str]:
    """Infer which characters can trigger this block type."""
    # This could be explicit in BlockGrammar, or inferred
    match grammar.name:
        case "atx_heading": return {"#"}
        case "fenced_code": return {"`", "~"}
        case "block_quote": return {">"}
        case "thematic_break": return {"-", "*", "_"}
        case "list": return {"-", "*", "+", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        case "html_block": return {"<"}
        case _: return set()  # Paragraph is default, no trigger
```

### Optimized Runtime

```python
@dataclass
class CompiledGrammar:
    """Compiled grammar for fast runtime queries."""

    containment: frozenset[tuple[str, str]]
    interruption: dict[str, frozenset[str]]
    start_dispatch: dict[str, list[tuple[str, Callable]]]
    continuation: dict[str, Callable]

    def can_contain(self, container: str, child: str) -> bool:
        """O(1) containment check."""
        return (container, child) in self.containment

    def can_interrupt(self, interrupter: str, target: str) -> bool:
        """O(1) interruption check."""
        return interrupter in self.interruption.get(target, frozenset())

    def find_starter(self, line: str, indent: int, tokens: LookaheadTokens) -> StartMatch | None:
        """O(1) average block recognition via dispatch table."""
        if not line:
            return None

        first_char = line.lstrip()[:1] if line.lstrip() else ""
        candidates = self.start_dispatch.get(first_char, [])

        for name, starts_on in candidates:
            match = starts_on(line, indent, tokens)
            if match:
                return match

        return None  # Caller defaults to paragraph
```

---

## Grammar Verification

### Provable Properties

The grammar verification engine catches common logical errors that would lead to parsing bugs or performance issues:

| Property | Check | Failure Example |
|----------|-------|-----------------|
| **Termination** | No cycles in `can_contain` | `List` can contain `List`, but must eventually contain `List Item`. If `List` directly contains `List`, it's infinite. |
| **Determinism** | No overlapping `starts_on` triggers | `>` triggers both `Block Quote` and `Custom Directive` with ambiguous priority. |
| **Interruption Safety** | If A interrupts B, B must be in A's `can_contain` | `Heading` interrupts `Paragraph`, but if `Document` (root) can't contain `Heading`, the parse state is invalid. |
| **Completeness** | All possible line starts are handled | No `Paragraph` fallback defined for unclassified text lines. |

```python
# blocks/grammar/verification.py

def verify_grammar(registry: GrammarRegistry) -> VerificationResult:
    """Verify grammar properties."""

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Termination: containment graph must be acyclic
    if has_cycle(build_containment_graph(registry)):
        errors.append("Containment graph has cycle - parsing may not terminate")

    # 2. Completeness: every line must match some block
    if not has_default_block(registry):
        errors.append("No default block type (paragraph) - some lines may not parse")

    # 3. Determinism: start rules should not be ambiguous
    ambiguities = find_start_ambiguities(registry)
    if ambiguities:
        warnings.append(f"Ambiguous start rules: {ambiguities}")

    # 4. Interruption consistency: if A interrupts B, A must be able to start
    for name, grammar in registry._grammars.items():
        for interrupter in grammar.can_be_interrupted_by:
            if interrupter not in registry._grammars:
                errors.append(f"Unknown interrupter '{interrupter}' for '{name}'")

    return VerificationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def build_containment_graph(registry: GrammarRegistry) -> dict[str, set[str]]:
    """Build directed graph of containment relationships."""
    graph: dict[str, set[str]] = {}
    for name, grammar in registry._grammars.items():
        graph[name] = set(grammar.can_contain)
    return graph


def has_cycle(graph: dict[str, set[str]]) -> bool:
    """Detect cycle in directed graph using DFS."""
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            if dfs(node):
                return True
    return False
```

### Grammar Queries

```python
# blocks/grammar/queries.py

def what_can_contain(registry: GrammarRegistry, child: str) -> set[str]:
    """Find all block types that can contain the given child."""
    return {
        name for name, grammar in registry._grammars.items()
        if child in grammar.can_contain
    }


def what_interrupts(registry: GrammarRegistry, target: str) -> frozenset[str]:
    """Find all block types that can interrupt the given target."""
    grammar = registry._grammars.get(target)
    return grammar.can_be_interrupted_by if grammar else frozenset()


def max_nesting_depth(registry: GrammarRegistry) -> int | None:
    """Compute maximum nesting depth (None if unbounded due to recursion)."""
    graph = build_containment_graph(registry)
    if has_cycle(graph):
        return None  # Unbounded
    return longest_path_length(graph)


def is_leaf(registry: GrammarRegistry, block_type: str) -> bool:
    """Check if block type is a leaf (cannot contain other blocks)."""
    grammar = registry._grammars.get(block_type)
    return grammar is not None and len(grammar.can_contain) == 0
```

---

## Performance Analysis

### Time Complexity

| Operation | Procedural (Current) | Declarative (Compiled) |
|-----------|---------------------|------------------------|
| Block dispatch | O(cases) ≈ 15 comparisons | O(1) dict lookup |
| Interruption check | O(interrupters) ≈ 10 comparisons | O(1) frozenset lookup |
| Containment check | O(1) hardcoded | O(1) frozenset lookup |
| Continuation check | O(1) function call | O(1) function call |
| Sibling access | O(n) index search | O(1) pointer |

**Overall**: O(n) where n = document size. Same asymptotic complexity, but **2-4x lower constant factor** on block dispatch.

### Space Complexity

| Structure | Size |
|-----------|------|
| GrammarRegistry | O(g) where g = number of block types |
| CompiledGrammar | O(g²) for containment matrix |
| Block sibling links | +16 bytes per block |
| Per-document overhead | ~1KB for 50-block document |

### Benchmark Targets

| Metric | Current | Target |
|--------|---------|--------|
| Block dispatch time | ~50ns | ~15ns |
| Interruption check time | ~30ns | ~5ns |
| Overall parse time | baseline | 0.90x baseline (10% faster) |
| Memory per block | 120 bytes | 140 bytes (+17%) |

---

## Migration Path

### Phase 1: Grammar Data Structures (Low Risk)

1. Add `BlockGrammar` dataclass
2. Add `GrammarRegistry` with lookup tables
3. Define grammars for existing block types
4. **No behavioral changes** - just data definitions

**Validation**: Grammar verification passes, all existing tests pass.

### Phase 2: Parallel Dispatch (Medium Risk)

1. Add compiled dispatch alongside existing `match` statement
2. Assert both produce same result
3. Run both paths, compare outputs
4. **Shadow mode** - new path validates but doesn't affect output

```python
def _parse_block(self):
    # Existing path
    procedural_result = self._parse_block_procedural()

    # New path (shadow)
    declarative_result = self._parse_block_declarative()

    # Validate equivalence
    assert equivalent(procedural_result, declarative_result)

    return procedural_result  # Return existing behavior
```

**Validation**: Shadow assertions never fire, all tests pass.

### Phase 3: Switch to Declarative (Higher Risk)

1. Remove procedural dispatch
2. Use declarative parser as primary
3. Remove shadow comparison code

**Validation**: All tests pass, benchmarks show expected performance.

### Phase 4: Add Sibling Links (Low Risk)

1. Add `prev_sibling` / `next_sibling` to `Block`
2. Update `append_child` to maintain links
3. Optional - doesn't affect parsing correctness

**Validation**: All tests pass, sibling navigation works.

### Phase 5: Grammar Verification (Enhancement)

1. Add verification functions
2. Run verification on registry at startup
3. Add grammar tests

**Validation**: Verification passes, no regressions.

---

## Examples

### Example 1: Adding a Custom Block Type

```python
# User-defined callout block
CALLOUT = BlockGrammar(
    name="callout",
    can_contain=frozenset({"paragraph", "list", "fenced_code"}),
    can_be_interrupted_by=frozenset(),  # Must close explicitly
    continues_on=lambda line, ctx: not line.strip().startswith(":::"),
    starts_on=lambda line, indent: (
        StartMatch("callout", consumed=3, content_indent=indent)
        if line.strip().startswith(":::") else None
    ),
    lazy_continuation=False,
    literal_content=False,
)

# Register with parser
GRAMMAR.register(CALLOUT)

# That's it! Parser now handles callouts.
```

### Example 2: Querying Grammar

```python
# What can a list item contain?
>>> GRAMMAR._grammars["list_item"].can_contain
frozenset({'paragraph', 'list', 'fenced_code', 'indented_code', 'block_quote', ...})

# What interrupts a paragraph?
>>> GRAMMAR.get_interrupters("paragraph")
frozenset({'atx_heading', 'setext_heading', 'thematic_break', 'fenced_code', ...})

# Can block_quote contain list?
>>> GRAMMAR.can_contain("block_quote", "list")
True

# Is fenced_code a leaf?
>>> is_leaf(GRAMMAR, "fenced_code")
True
```

### Example 3: Grammar Verification

```python
>>> result = verify_grammar(GRAMMAR)
>>> result.valid
True
>>> result.warnings
['Ambiguous start rules for "-": thematic_break, list']
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Behavioral regressions | High | Phase 2 shadow comparison |
| Performance regression | Medium | Benchmark before/after each phase |
| Grammar definition bugs | Medium | Grammar verification, extensive tests |
| Increased complexity | Low | Complexity is centralized and documented |
| Memory overhead | Low | +20 bytes/block is acceptable |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Block dispatch locations | 15+ match cases | 1 generic dispatcher |
| Interruption check locations | 5+ files | 1 registry query |
| Lines of block parsing code | ~800 | ~400 (-50%) |
| Grammar queryability | None | Full (can_contain, can_interrupt, etc.) |
| Block dispatch time | ~50ns | ~15ns (-70%) |
| New block type effort | Modify 5+ files | Define 1 grammar + register |
| Grammar verification | Manual review | Automated proofs |

## Grammar Composition

One of the most powerful features of this architecture is the ability to compose grammars algebraically.

```python
# Create GFM by extending CommonMark
GFM_GRAMMAR = COMMONMARK_GRAMMAR.extend(
    blocks=[TABLE, TASK_LIST],
    overrides={
        "paragraph": PARAGRAPH.with_interrupters(["table", "task_list"])
    }
)

# Create MyST by adding directives to GFM
MYST_GRAMMAR = GFM_GRAMMAR.extend(
    blocks=[DIRECTIVE, FOOTNOTE_DEF, ADMONITION],
)
```

This ensures that extensions are additive and don't require re-implementing the core parser logic.

---

## Future Possibilities

This architecture enables future enhancements:

1. **Incremental Parsing**: Grammar rules determine which blocks need re-parsing after edits
2. **Grammar Composition**: Combine CommonMark + GFM + MyST grammars algebraically
3. **Grammar Inference**: Learn custom grammar rules from example documents
4. **Bidirectional Parsing**: Derive pretty-printer from grammar automatically
5. **Semantic Roles**: Add semantic annotations to grammar (heading scopes paragraph, code illustrates paragraph)
6. **Visual Grammar Editor**: Edit block rules graphically

---

## Appendix A: Full Grammar Definitions

```python
# blocks/grammar/commonmark.py

"""CommonMark block grammar definitions."""

from blocks.grammar.types import BlockGrammar, StartMatch

# Document root
DOCUMENT = BlockGrammar(
    name="document",
    can_contain=frozenset({
        "paragraph", "atx_heading", "setext_heading", "thematic_break",
        "fenced_code", "indented_code", "html_block", "block_quote",
        "list", "link_reference_definition",
    }),
    can_be_interrupted_by=frozenset(),
    continues_on=lambda line, ctx: True,  # Document always continues
    starts_on=lambda line, indent: None,  # Document doesn't "start"
)

PARAGRAPH = BlockGrammar(
    name="paragraph",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset({
        "atx_heading", "thematic_break", "fenced_code", "html_block",
        "block_quote", "list",
    }),
    continues_on=_paragraph_continues,
    starts_on=_paragraph_starts,
    lazy_continuation=True,
)

ATX_HEADING = BlockGrammar(
    name="atx_heading",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=lambda line, ctx: False,
    starts_on=_atx_heading_starts,
)

SETEXT_HEADING = BlockGrammar(
    name="setext_heading",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=lambda line, ctx: False,
    starts_on=_setext_heading_starts,
)

THEMATIC_BREAK = BlockGrammar(
    name="thematic_break",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=lambda line, ctx: False,
    starts_on=_thematic_break_starts,
)

FENCED_CODE = BlockGrammar(
    name="fenced_code",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=_fenced_code_continues,
    starts_on=_fenced_code_starts,
    literal_content=True,
)

INDENTED_CODE = BlockGrammar(
    name="indented_code",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset({
        "paragraph",  # Indented code can't interrupt paragraph
    }),
    continues_on=_indented_code_continues,
    starts_on=_indented_code_starts,
    literal_content=True,
)

HTML_BLOCK = BlockGrammar(
    name="html_block",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=_html_block_continues,
    starts_on=_html_block_starts,
    literal_content=True,
)

BLOCK_QUOTE = BlockGrammar(
    name="block_quote",
    can_contain=frozenset({
        "paragraph", "atx_heading", "thematic_break", "fenced_code",
        "indented_code", "html_block", "block_quote", "list",
    }),
    can_be_interrupted_by=frozenset(),
    continues_on=_block_quote_continues,
    starts_on=_block_quote_starts,
    lazy_continuation=True,
)

LIST = BlockGrammar(
    name="list",
    can_contain=frozenset({"list_item"}),
    can_be_interrupted_by=frozenset({
        "atx_heading", "thematic_break", "fenced_code", "block_quote",
    }),
    continues_on=_list_continues,
    starts_on=_list_starts,
)

LIST_ITEM = BlockGrammar(
    name="list_item",
    can_contain=frozenset({
        "paragraph", "atx_heading", "thematic_break", "fenced_code",
        "indented_code", "html_block", "block_quote", "list",
    }),
    can_be_interrupted_by=frozenset({"list_item"}),
    continues_on=_list_item_continues,
    starts_on=_list_item_starts,
    lazy_continuation=True,
)

LINK_REFERENCE_DEFINITION = BlockGrammar(
    name="link_reference_definition",
    can_contain=frozenset(),
    can_be_interrupted_by=frozenset(),
    continues_on=lambda line, ctx: False,
    starts_on=_link_ref_def_starts,
)

# All CommonMark blocks
COMMONMARK_BLOCKS = [
    DOCUMENT, PARAGRAPH, ATX_HEADING, SETEXT_HEADING, THEMATIC_BREAK,
    FENCED_CODE, INDENTED_CODE, HTML_BLOCK, BLOCK_QUOTE, LIST, LIST_ITEM,
    LINK_REFERENCE_DEFINITION,
]
```

---

## Appendix B: Related Work

- **Tree-sitter**: Uses declarative grammar (grammar.js) compiled to C parser
- **PEG.js / Peggy**: Grammar-based parser generator for JavaScript
- **ANTLR**: Grammar-driven parser generator
- **CommonMark Reference**: Procedural but well-documented rules
- **markdown-it**: Plugin-based, semi-declarative rule chains

---

## Conclusion

The Declarative Block Grammar architecture transforms Patitas from a procedural parser to a grammar-driven one. Benefits include:

1. **Clarity**: Block rules are explicit data, not implicit control flow
2. **Extensibility**: New blocks plug in without parser modification
3. **Testability**: Grammar rules testable in isolation
4. **Verifiability**: Provable termination, determinism, completeness
5. **Performance**: 2-4x faster block dispatch via compiled tables
6. **Foundation**: Enables incremental parsing, grammar composition, semantic analysis

The phased migration allows incremental validation with rollback capability at each phase.

**Recommendation**: Proceed with Phase 1 (grammar data structures) to establish foundation without behavioral risk.

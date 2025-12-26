"""Purity analysis for template introspection.

Determines if expressions and blocks are pure (deterministic).
Pure blocks produce the same output for the same inputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Node

# Purity lattice: pure < unknown < impure
# When combining, take the most conservative (worst case)

PurityLevel = Literal["pure", "unknown", "impure"]


def _combine_purity(a: PurityLevel, b: PurityLevel) -> PurityLevel:
    """Combine two purity levels (take worst case)."""
    if a == "impure" or b == "impure":
        return "impure"
    if a == "unknown" or b == "unknown":
        return "unknown"
    return "pure"


# Filters known to be pure (deterministic, no side effects)
_KNOWN_PURE_FILTERS = frozenset(
    {
        # String manipulation
        "upper",
        "lower",
        "title",
        "capitalize",
        "swapcase",
        "strip",
        "lstrip",
        "rstrip",
        "trim",
        "replace",
        "truncate",
        "wordwrap",
        "center",
        "indent",
        "striptags",
        "urlize",
        "wordcount",
        # Collections
        "first",
        "last",
        "length",
        "count",
        "sort",
        "reverse",
        "unique",
        "batch",
        "slice",
        "list",
        "map",
        "select",
        "reject",
        "selectattr",
        "rejectattr",
        "groupby",
        "join",
        "pprint",
        # Type conversion
        "string",
        "int",
        "float",
        "bool",
        "tojson",
        "safe",
        "escape",
        "e",
        # Defaults
        "default",
        "d",
        # Math
        "abs",
        "round",
        "sum",
        "min",
        "max",
        # Format
        "filesizeformat",
        "format",
        # Path/URL
        "basename",
        "dirname",
        "splitext",
        # Kida-specific
        "take",
        "skip",
        "where",
        "sort_by",
    }
)

# Filters known to be impure (non-deterministic)
_KNOWN_IMPURE_FILTERS = frozenset(
    {
        "random",
        "shuffle",
    }
)

# Functions known to be pure
_KNOWN_PURE_FUNCTIONS = frozenset(
    {
        # Python builtins
        "len",
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "frozenset",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "pow",
        "sorted",
        "reversed",
        "enumerate",
        "zip",
        "map",
        "filter",
        "any",
        "all",
        "range",
        "hasattr",
        "getattr",
        "isinstance",
        "type",
        "ord",
        "chr",
        "hex",
        "oct",
        "bin",
        "repr",
        "hash",
    }
)


class PurityAnalyzer:
    """Determine if an expression or block is pure (deterministic).

    Pure expressions produce the same output for the same inputs.
    This is used to determine cache safety.

    Conservative: defaults to "unknown" when uncertain.

    Example:
        >>> analyzer = PurityAnalyzer()
        >>> purity = analyzer.analyze(block_node)
        >>> print(purity)
        'pure'

    Purity Rules:
        - Constants, variables, attribute access: pure
        - Binary/unary operations, comparisons: pure
        - Known pure filters (upper, lower, sort, etc.): pure
        - Known impure filters (random, shuffle): impure
        - Unknown filters/functions: unknown
    """

    def __init__(
        self,
        extra_pure_functions: frozenset[str] | None = None,
        extra_impure_filters: frozenset[str] | None = None,
    ) -> None:
        """Initialize analyzer with optional extensions.

        Args:
            extra_pure_functions: Additional functions to treat as pure.
            extra_impure_filters: Additional filters to treat as impure.
        """
        self._pure_functions = _KNOWN_PURE_FUNCTIONS
        if extra_pure_functions:
            self._pure_functions = self._pure_functions | extra_pure_functions

        self._impure_filters = _KNOWN_IMPURE_FILTERS
        if extra_impure_filters:
            self._impure_filters = self._impure_filters | extra_impure_filters

    def analyze(self, node: Node) -> PurityLevel:
        """Analyze a node and return its purity level.

        Args:
            node: AST node to analyze.

        Returns:
            "pure", "impure", or "unknown"
        """
        return self._visit(node)

    def _visit(self, node: Any) -> PurityLevel:
        """Visit a node and determine purity."""
        if node is None:
            return "pure"

        node_type = type(node).__name__

        handler = getattr(self, f"_visit_{node_type.lower()}", None)
        if handler:
            return handler(node)

        # Default: check children
        return self._visit_children(node)

    def _visit_children(self, node: Any) -> PurityLevel:
        """Visit children and combine purity."""
        result: PurityLevel = "pure"

        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            result = _combine_purity(result, self._visit(child))

        for attr in (
            "test",
            "expr",
            "value",
            "iter",
            "left",
            "right",
            "operand",
            "obj",
            "key",
            "if_true",
            "if_false",
        ):
            if hasattr(node, attr):
                child = getattr(node, attr)
                if child and hasattr(child, "lineno"):
                    result = _combine_purity(result, self._visit(child))

        return result

    def _visit_const(self, node: Any) -> PurityLevel:
        """Constants are pure."""
        return "pure"

    def _visit_name(self, node: Any) -> PurityLevel:
        """Variable access is pure (reading doesn't mutate)."""
        return "pure"

    def _visit_getattr(self, node: Any) -> PurityLevel:
        """Attribute access is pure."""
        return self._visit(node.obj)

    def _visit_optionalgetattr(self, node: Any) -> PurityLevel:
        """Optional attribute access is pure."""
        return self._visit(node.obj)

    def _visit_getitem(self, node: Any) -> PurityLevel:
        """Subscript access is pure."""
        return _combine_purity(
            self._visit(node.obj),
            self._visit(node.key),
        )

    def _visit_optionalgetitem(self, node: Any) -> PurityLevel:
        """Optional subscript access is pure."""
        return _combine_purity(
            self._visit(node.obj),
            self._visit(node.key),
        )

    def _visit_binop(self, node: Any) -> PurityLevel:
        """Binary operations are pure."""
        return _combine_purity(
            self._visit(node.left),
            self._visit(node.right),
        )

    def _visit_unaryop(self, node: Any) -> PurityLevel:
        """Unary operations are pure."""
        return self._visit(node.operand)

    def _visit_compare(self, node: Any) -> PurityLevel:
        """Comparisons are pure."""
        result = self._visit(node.left)
        for comp in node.comparators:
            result = _combine_purity(result, self._visit(comp))
        return result

    def _visit_boolop(self, node: Any) -> PurityLevel:
        """Boolean operations are pure."""
        result: PurityLevel = "pure"
        for value in node.values:
            result = _combine_purity(result, self._visit(value))
        return result

    def _visit_condexpr(self, node: Any) -> PurityLevel:
        """Conditional expressions are pure if all parts are pure."""
        return _combine_purity(
            self._visit(node.test),
            _combine_purity(
                self._visit(node.if_true),
                self._visit(node.if_false),
            ),
        )

    def _visit_nullcoalesce(self, node: Any) -> PurityLevel:
        """Null coalescing is pure."""
        return _combine_purity(
            self._visit(node.left),
            self._visit(node.right),
        )

    def _visit_concat(self, node: Any) -> PurityLevel:
        """String concatenation is pure."""
        result: PurityLevel = "pure"
        for child in node.nodes:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_range(self, node: Any) -> PurityLevel:
        """Range literals are pure."""
        result = _combine_purity(
            self._visit(node.start),
            self._visit(node.end),
        )
        if node.step:
            result = _combine_purity(result, self._visit(node.step))
        return result

    def _visit_slice(self, node: Any) -> PurityLevel:
        """Slice expressions are pure."""
        result: PurityLevel = "pure"
        if node.start:
            result = _combine_purity(result, self._visit(node.start))
        if node.stop:
            result = _combine_purity(result, self._visit(node.stop))
        if node.step:
            result = _combine_purity(result, self._visit(node.step))
        return result

    def _visit_list(self, node: Any) -> PurityLevel:
        """List literals are pure if all items are pure."""
        result: PurityLevel = "pure"
        for item in node.items:
            result = _combine_purity(result, self._visit(item))
        return result

    def _visit_tuple(self, node: Any) -> PurityLevel:
        """Tuple literals are pure if all items are pure."""
        result: PurityLevel = "pure"
        for item in node.items:
            result = _combine_purity(result, self._visit(item))
        return result

    def _visit_dict(self, node: Any) -> PurityLevel:
        """Dict literals are pure if all keys and values are pure."""
        result: PurityLevel = "pure"
        for key in node.keys:
            result = _combine_purity(result, self._visit(key))
        for value in node.values:
            result = _combine_purity(result, self._visit(value))
        return result

    def _visit_filter(self, node: Any) -> PurityLevel:
        """Filter purity depends on the filter."""
        # Check filter name
        if node.name in _KNOWN_PURE_FILTERS:
            filter_purity: PurityLevel = "pure"
        elif node.name in self._impure_filters:
            filter_purity = "impure"
        else:
            filter_purity = "unknown"  # User-defined

        # Combine with value and args
        result = _combine_purity(filter_purity, self._visit(node.value))
        for arg in node.args:
            result = _combine_purity(result, self._visit(arg))
        for value in node.kwargs.values():
            result = _combine_purity(result, self._visit(value))

        return result

    def _visit_pipeline(self, node: Any) -> PurityLevel:
        """Pipeline purity depends on all filters in the chain."""
        result = self._visit(node.value)

        for filter_name, args, kwargs in node.steps:
            # Check filter purity
            if filter_name in _KNOWN_PURE_FILTERS:
                filter_purity: PurityLevel = "pure"
            elif filter_name in self._impure_filters:
                filter_purity = "impure"
            else:
                filter_purity = "unknown"

            result = _combine_purity(result, filter_purity)

            # Check args
            for arg in args:
                result = _combine_purity(result, self._visit(arg))
            for value in kwargs.values():
                result = _combine_purity(result, self._visit(value))

        return result

    def _visit_funccall(self, node: Any) -> PurityLevel:
        """Function call purity depends on the function."""
        # Check if it's a known pure builtin
        if type(node.func).__name__ == "Name":
            func_name = node.func.name
            if func_name in self._pure_functions:
                # Pure function - check arguments
                result: PurityLevel = "pure"
                for arg in node.args:
                    result = _combine_purity(result, self._visit(arg))
                for value in node.kwargs.values():
                    result = _combine_purity(result, self._visit(value))
                return result

        # Unknown function - conservative
        return "unknown"

    def _visit_test(self, node: Any) -> PurityLevel:
        """Tests are pure (they're just predicates)."""
        result = self._visit(node.value)
        for arg in node.args:
            result = _combine_purity(result, self._visit(arg))
        return result

    def _visit_for(self, node: Any) -> PurityLevel:
        """For loops are pure if body is pure."""
        result = self._visit(node.iter)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        if hasattr(node, "empty") and node.empty:
            for child in node.empty:
                result = _combine_purity(result, self._visit(child))
        return result

    def _visit_if(self, node: Any) -> PurityLevel:
        """Conditionals are pure if all branches are pure."""
        result = self._visit(node.test)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        for child in node.else_:
            result = _combine_purity(result, self._visit(child))
        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for test, body in node.elif_:
                result = _combine_purity(result, self._visit(test))
                for child in body:
                    result = _combine_purity(result, self._visit(child))
        return result

    def _visit_match(self, node: Any) -> PurityLevel:
        """Match statements are pure if all branches are pure."""
        result = self._visit(node.subject)
        for pattern, guard, body in node.cases:
            result = _combine_purity(result, self._visit(pattern))
            if guard:
                result = _combine_purity(result, self._visit(guard))
            for child in body:
                result = _combine_purity(result, self._visit(child))
        return result

    def _visit_output(self, node: Any) -> PurityLevel:
        """Output is pure if expression is pure."""
        return self._visit(node.expr)

    def _visit_data(self, node: Any) -> PurityLevel:
        """Static data is pure."""
        return "pure"

    def _visit_cache(self, node: Any) -> PurityLevel:
        """Cache blocks: the body is evaluated, but result is cached.

        The block itself is pure if the body is pure.
        """
        result = self._visit(node.key)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_block(self, node: Any) -> PurityLevel:
        """Block is pure if body is pure."""
        result: PurityLevel = "pure"
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_with(self, node: Any) -> PurityLevel:
        """With blocks are pure if bindings and body are pure."""
        result: PurityLevel = "pure"
        for _name, value in node.targets:
            result = _combine_purity(result, self._visit(value))
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_withconditional(self, node: Any) -> PurityLevel:
        """Conditional with is pure if expr and body are pure."""
        result = self._visit(node.expr)
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        return result

    def _visit_set(self, node: Any) -> PurityLevel:
        """Set is pure if value is pure."""
        return self._visit(node.value)

    def _visit_let(self, node: Any) -> PurityLevel:
        """Let is pure if value is pure."""
        return self._visit(node.value)

    def _visit_capture(self, node: Any) -> PurityLevel:
        """Capture is pure if body is pure."""
        result: PurityLevel = "pure"
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        if hasattr(node, "filter") and node.filter:
            result = _combine_purity(result, self._visit(node.filter))
        return result

    def _visit_include(self, node: Any) -> PurityLevel:
        """Include is unknown (depends on included template)."""
        return "unknown"

    def _visit_extends(self, node: Any) -> PurityLevel:
        """Extends is unknown (depends on parent template)."""
        return "unknown"

    def _visit_def(self, node: Any) -> PurityLevel:
        """Function definition is pure if body is pure."""
        result: PurityLevel = "pure"
        for child in node.body:
            result = _combine_purity(result, self._visit(child))
        for default in node.defaults:
            result = _combine_purity(result, self._visit(default))
        return result

    def _visit_macro(self, node: Any) -> PurityLevel:
        """Macro definition (same as def)."""
        return self._visit_def(node)

    def _visit_inlinedfilter(self, node: Any) -> PurityLevel:
        """Inlined filter is pure (only pure filters are inlined)."""
        return self._visit(node.value)

    def _visit_marksafe(self, node: Any) -> PurityLevel:
        """Mark safe is pure."""
        return self._visit(node.value)

    def _visit_await(self, node: Any) -> PurityLevel:
        """Await is unknown (async operations may have side effects)."""
        return "unknown"

    # Leaf nodes
    def _visit_slot(self, node: Any) -> PurityLevel:
        return "pure"

    def _visit_break(self, node: Any) -> PurityLevel:
        return "pure"

    def _visit_continue(self, node: Any) -> PurityLevel:
        return "pure"

    def _visit_raw(self, node: Any) -> PurityLevel:
        return "pure"

    def _visit_loopvar(self, node: Any) -> PurityLevel:
        return "pure"

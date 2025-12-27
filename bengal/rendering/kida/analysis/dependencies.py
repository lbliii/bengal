"""Dependency analysis for template introspection.

Extracts context variable dependencies from AST expressions and blocks.
Produces a conservative superset — may include unused paths but never
excludes paths that are actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Node


# Names that are always available (not context dependencies)
_BUILTIN_NAMES = frozenset(
    {
        # Python builtins commonly used in templates
        "range",
        "len",
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "min",
        "max",
        "sum",
        "abs",
        "round",
        "sorted",
        "reversed",
        "enumerate",
        "zip",
        "map",
        "filter",
        "any",
        "all",
        "hasattr",
        "getattr",
        "isinstance",
        "type",
        # Boolean/None literals
        "true",
        "false",
        "none",
        "True",
        "False",
        "None",
        # Kida builtins
        "loop",  # Loop context variable
    }
)


class DependencyWalker:
    """Extract context variable dependencies from AST expressions.

    Walks the AST and collects all context paths (e.g., "page.title",
    "site.pages") that an expression or block may access.

    Produces a conservative superset: may include paths not actually
    used at runtime, but never excludes paths that are used.

    Thread-safe: Creates new state for each analyze() call.

    Example:
        >>> walker = DependencyWalker()
        >>> deps = walker.analyze(block_node)
        >>> print(deps)
        frozenset({'site.pages', 'site.title'})

    Scope Handling:
        - Loop variables ({% for x in items %}) are excluded
        - With bindings ({% with expr as x %}) are excluded
        - Function arguments ({% def fn(x) %}) are excluded
        - Set/let assignments create local scope
    """

    def __init__(self) -> None:
        """Initialize walker (stateless until analyze() is called)."""
        self._scope_stack: list[set[str]] = []
        self._dependencies: set[str] = set()

    def analyze(self, node: Node) -> frozenset[str]:
        """Analyze a node and return all context dependencies.

        Args:
            node: AST node to analyze (Block, Template, expression, etc.)

        Returns:
            Frozen set of context paths (e.g., {"page.title", "site.pages"})
        """
        # Reset state for each analysis
        self._scope_stack = [set()]
        self._dependencies = set()
        self._visit(node)
        return frozenset(self._dependencies)

    def _visit(self, node: Any) -> None:
        """Visit a node and its children."""
        if node is None:
            return

        node_type = type(node).__name__

        # Dispatch to specific handlers
        handler = getattr(self, f"_visit_{node_type.lower()}", None)
        if handler:
            handler(node)
        else:
            self._visit_children(node)

    def _visit_children(self, node: Any) -> None:
        """Visit all child nodes (generic handler)."""
        # Handle common container attributes
        for attr in ("body", "else_", "empty", "elif_"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    if isinstance(children, (list, tuple)):
                        for child in children:
                            if hasattr(child, "lineno"):  # It's a node
                                self._visit(child)
                            elif isinstance(child, tuple):  # elif case
                                test, body = child
                                self._visit(test)
                                for b in body:
                                    self._visit(b)

        # Handle expression attributes
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
            "func",
            "subject",
            "if_true",
            "if_false",
            "start",
            "end",
            "step",
            "stop",
            "template",
        ):
            if hasattr(node, attr):
                child = getattr(node, attr)
                if child and hasattr(child, "lineno"):
                    self._visit(child)

        # Handle sequence attributes
        for attr in (
            "args",
            "items",
            "nodes",
            "comparators",
            "values",
            "keys",
            "defaults",
            "depends",
        ):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno"):
                            self._visit(child)

        # Handle dict attributes (kwargs)
        for attr in ("kwargs",):
            if hasattr(node, attr):
                mapping = getattr(node, attr)
                if mapping:
                    for child in mapping.values():
                        if hasattr(child, "lineno"):
                            self._visit(child)

        # Handle steps in Pipeline
        if hasattr(node, "steps"):
            for step in node.steps:
                if isinstance(step, tuple) and len(step) == 3:
                    _name, args, kwargs = step
                    for arg in args:
                        if hasattr(arg, "lineno"):
                            self._visit(arg)
                    for val in kwargs.values():
                        if hasattr(val, "lineno"):
                            self._visit(val)

        # Handle cases in Match
        if hasattr(node, "cases"):
            cases = node.cases
            if cases:
                for pattern, guard, body in cases:
                    self._visit(pattern)
                    if guard:
                        self._visit(guard)
                    for child in body:
                        self._visit(child)

        # Handle targets in With
        if hasattr(node, "targets"):
            targets = node.targets
            if targets and isinstance(targets, (list, tuple)):
                for target in targets:
                    if isinstance(target, tuple) and len(target) == 2:
                        name, value = target
                        self._visit(value)

        # Handle blocks in Embed
        if hasattr(node, "blocks"):
            blocks = node.blocks
            if isinstance(blocks, dict):
                for block in blocks.values():
                    if hasattr(block, "lineno"):
                        self._visit(block)

    def _visit_name(self, node: Any) -> None:
        """Handle variable reference."""
        name = node.name

        # Skip if it's a local variable (loop var, with binding, etc.)
        if self._is_local(name):
            return

        # Skip built-in names
        if name in _BUILTIN_NAMES:
            return

        # It's a context variable
        self._dependencies.add(name)

    def _visit_getattr(self, node: Any) -> None:
        """Handle attribute access: obj.attr"""
        path = self._build_path(node)
        if path:
            self._dependencies.add(path)
        else:
            # Couldn't build full path, visit children
            self._visit(node.obj)

    def _visit_optionalgetattr(self, node: Any) -> None:
        """Handle optional attribute access: obj?.attr"""
        # Same logic as regular getattr
        path = self._build_path(node)
        if path:
            self._dependencies.add(path)
        else:
            self._visit(node.obj)

    def _visit_getitem(self, node: Any) -> None:
        """Handle subscript access: obj[key]"""
        # We can only track static string keys
        if type(node.key).__name__ == "Const" and isinstance(node.key.value, str):
            path = self._build_path(node)
            if path:
                self._dependencies.add(path)
                return

        # Dynamic key - track the base object and the key expression
        self._visit(node.obj)
        self._visit(node.key)

    def _visit_optionalgetitem(self, node: Any) -> None:
        """Handle optional subscript access: obj?[key]"""
        # Same logic as regular getitem
        if type(node.key).__name__ == "Const" and isinstance(node.key.value, str):
            path = self._build_path(node)
            if path:
                self._dependencies.add(path)
                return

        self._visit(node.obj)
        self._visit(node.key)

    def _visit_for(self, node: Any) -> None:
        """Handle for loop: push loop variable into scope."""
        # Visit the iterable (this IS a dependency)
        self._visit(node.iter)

        # Extract loop variables
        loop_vars = self._extract_targets(node.target)

        # Visit optional filter condition with loop var in scope
        if hasattr(node, "test") and node.test:
            self._scope_stack.append(loop_vars | {"loop"})
            self._visit(node.test)
            self._scope_stack.pop()

        # Push loop variable(s) into scope with implicit 'loop' variable
        self._scope_stack.append(loop_vars | {"loop"})

        # Visit body with loop var in scope
        for child in node.body:
            self._visit(child)

        # Visit empty block (if any)
        if hasattr(node, "empty") and node.empty:
            for child in node.empty:
                self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_asyncfor(self, node: Any) -> None:
        """Handle async for loop (same as regular for)."""
        self._visit_for(node)

    def _visit_while(self, node: Any) -> None:
        """Handle while loop."""
        self._visit(node.test)
        for child in node.body:
            self._visit(child)

    def _visit_with(self, node: Any) -> None:
        """Handle with block: {% with x = expr %}...{% end %}"""
        # Collect all bindings
        bindings = set()
        for name, value in node.targets:
            self._visit(value)  # Value expression IS a dependency
            bindings.add(name)

        # Push bindings into scope
        self._scope_stack.append(bindings)

        # Visit body
        for child in node.body:
            self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_withconditional(self, node: Any) -> None:
        """Handle conditional with: {% with expr as target %}"""
        # Visit the expression (IS a dependency)
        self._visit(node.expr)

        # Extract targets and push into scope
        targets = self._extract_targets(node.target)
        self._scope_stack.append(targets)

        # Visit body
        for child in node.body:
            self._visit(child)

        # Pop scope
        self._scope_stack.pop()

    def _visit_def(self, node: Any) -> None:
        """Handle function definition: push args into scope."""
        # Visit defaults (outside function scope)
        for default in node.defaults:
            self._visit(default)

        # Push function arguments into scope
        self._scope_stack.append(set(node.args))

        # Visit body
        for child in node.body:
            self._visit(child)

        self._scope_stack.pop()

    def _visit_macro(self, node: Any) -> None:
        """Handle macro definition (same as def)."""
        self._visit_def(node)

    def _visit_set(self, node: Any) -> None:
        """Handle set statement."""
        # Visit the value expression
        self._visit(node.value)

        # Add target to current scope
        targets = self._extract_targets(node.target)
        if self._scope_stack:
            self._scope_stack[-1] |= targets

    def _visit_let(self, node: Any) -> None:
        """Handle let statement (template-scoped)."""
        # Visit the value expression
        self._visit(node.value)

        # Add to root scope
        if self._scope_stack:
            self._scope_stack[0].add(node.name)

    def _visit_export(self, node: Any) -> None:
        """Handle export statement."""
        self._visit(node.value)
        # Export doesn't create a new scope

    def _visit_capture(self, node: Any) -> None:
        """Handle capture block: {% capture name %}...{% end %}"""
        # Visit body
        for child in node.body:
            self._visit(child)

        # Visit filter if present
        if hasattr(node, "filter") and node.filter:
            self._visit(node.filter)

        # Add captured name to current scope
        if self._scope_stack:
            self._scope_stack[-1].add(node.name)

    def _visit_filter(self, node: Any) -> None:
        """Handle filter expression."""
        # Visit the value being filtered
        self._visit(node.value)

        # Visit filter arguments
        for arg in node.args:
            self._visit(arg)

        for value in node.kwargs.values():
            self._visit(value)

    def _visit_pipeline(self, node: Any) -> None:
        """Handle pipeline expression: expr |> filter1 |> filter2"""
        # Visit the initial value
        self._visit(node.value)

        # Visit arguments in each pipeline step
        for _name, args, kwargs in node.steps:
            for arg in args:
                self._visit(arg)
            for value in kwargs.values():
                self._visit(value)

    def _visit_funccall(self, node: Any) -> None:
        """Handle function call."""
        # Visit the function expression
        self._visit(node.func)

        # Visit arguments
        for arg in node.args:
            self._visit(arg)

        for value in node.kwargs.values():
            self._visit(value)

        # Handle *args and **kwargs
        if hasattr(node, "dyn_args") and node.dyn_args:
            self._visit(node.dyn_args)
        if hasattr(node, "dyn_kwargs") and node.dyn_kwargs:
            self._visit(node.dyn_kwargs)

    def _visit_nullcoalesce(self, node: Any) -> None:
        """Handle null coalescing: a ?? b"""
        self._visit(node.left)
        self._visit(node.right)

    def _visit_condexpr(self, node: Any) -> None:
        """Handle conditional expression: a if cond else b"""
        self._visit(node.test)
        self._visit(node.if_true)
        self._visit(node.if_false)

    def _visit_boolop(self, node: Any) -> None:
        """Handle boolean operations: a and b, a or b"""
        for value in node.values:
            self._visit(value)

    def _visit_binop(self, node: Any) -> None:
        """Handle binary operations: a + b, a - b, etc."""
        self._visit(node.left)
        self._visit(node.right)

    def _visit_unaryop(self, node: Any) -> None:
        """Handle unary operations: -a, not a"""
        self._visit(node.operand)

    def _visit_compare(self, node: Any) -> None:
        """Handle comparisons: a < b < c"""
        self._visit(node.left)
        for comp in node.comparators:
            self._visit(comp)

    def _visit_range(self, node: Any) -> None:
        """Handle range literal: start..end or start...end"""
        self._visit(node.start)
        self._visit(node.end)
        if node.step:
            self._visit(node.step)

    def _visit_slice(self, node: Any) -> None:
        """Handle slice expression: [start:stop:step]"""
        if node.start:
            self._visit(node.start)
        if node.stop:
            self._visit(node.stop)
        if node.step:
            self._visit(node.step)

    def _visit_concat(self, node: Any) -> None:
        """Handle string concatenation: a ~ b ~ c"""
        for child in node.nodes:
            self._visit(child)

    def _visit_list(self, node: Any) -> None:
        """Handle list literal: [a, b, c]"""
        for item in node.items:
            self._visit(item)

    def _visit_tuple(self, node: Any) -> None:
        """Handle tuple literal: (a, b, c)"""
        for item in node.items:
            self._visit(item)

    def _visit_dict(self, node: Any) -> None:
        """Handle dict literal: {a: b, c: d}"""
        for key in node.keys:
            self._visit(key)
        for value in node.values:
            self._visit(value)

    def _visit_test(self, node: Any) -> None:
        """Handle test expression: x is defined"""
        self._visit(node.value)
        for arg in node.args:
            self._visit(arg)
        for value in node.kwargs.values():
            self._visit(value)

    def _visit_match(self, node: Any) -> None:
        """Handle match statement."""
        self._visit(node.subject)
        for pattern, guard, body in node.cases:
            self._visit(pattern)
            if guard:
                self._visit(guard)
            for child in body:
                self._visit(child)

    def _visit_cache(self, node: Any) -> None:
        """Handle cache block: {% cache key %}...{% end %}"""
        self._visit(node.key)
        if node.ttl:
            self._visit(node.ttl)
        for dep in node.depends:
            self._visit(dep)
        for child in node.body:
            self._visit(child)

    def _visit_include(self, node: Any) -> None:
        """Handle include statement."""
        self._visit(node.template)

    def _visit_import(self, node: Any) -> None:
        """Handle import statement."""
        self._visit(node.template)
        # Add imported name to scope
        if self._scope_stack:
            self._scope_stack[-1].add(node.target)

    def _visit_fromimport(self, node: Any) -> None:
        """Handle from...import statement."""
        self._visit(node.template)
        # Add imported names to scope
        if self._scope_stack:
            for name, alias in node.names:
                self._scope_stack[-1].add(alias or name)

    def _visit_if(self, node: Any) -> None:
        """Handle if statement."""
        self._visit(node.test)
        for child in node.body:
            self._visit(child)
        for child in node.else_:
            self._visit(child)
        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for test, body in node.elif_:
                self._visit(test)
                for child in body:
                    self._visit(child)

    def _visit_output(self, node: Any) -> None:
        """Handle output: {{ expr }}"""
        self._visit(node.expr)

    def _visit_block(self, node: Any) -> None:
        """Handle block: {% block name %}...{% end %}"""
        for child in node.body:
            self._visit(child)

    def _visit_extends(self, node: Any) -> None:
        """Handle extends: {% extends 'base.html' %}"""
        self._visit(node.template)

    def _visit_template(self, node: Any) -> None:
        """Handle template root node."""
        if node.extends:
            self._visit(node.extends)
        for child in node.body:
            self._visit(child)

    def _visit_filterblock(self, node: Any) -> None:
        """Handle filter block: {% filter upper %}...{% end %}"""
        self._visit(node.filter)
        for child in node.body:
            self._visit(child)

    def _visit_callblock(self, node: Any) -> None:
        """Handle call block: {% call name(args) %}body{% end %}"""
        self._visit(node.call)
        for arg in node.args:
            self._visit(arg)
        for child in node.body:
            self._visit(child)

    def _visit_spaceless(self, node: Any) -> None:
        """Handle spaceless block."""
        for child in node.body:
            self._visit(child)

    def _visit_autoescape(self, node: Any) -> None:
        """Handle autoescape block."""
        for child in node.body:
            self._visit(child)

    def _visit_trim(self, node: Any) -> None:
        """Handle trim block."""
        for child in node.body:
            self._visit(child)

    def _visit_embed(self, node: Any) -> None:
        """Handle embed: {% embed 'card.html' %}...{% end %}"""
        self._visit(node.template)
        for block in node.blocks.values():
            self._visit(block)

    def _visit_await(self, node: Any) -> None:
        """Handle await expression."""
        self._visit(node.value)

    def _visit_marksafe(self, node: Any) -> None:
        """Handle safe marker."""
        self._visit(node.value)

    def _visit_inlinedfilter(self, node: Any) -> None:
        """Handle inlined filter (optimization)."""
        self._visit(node.value)
        for arg in node.args:
            self._visit(arg)

    # Leaf nodes that don't need children visited
    def _visit_const(self, node: Any) -> None:
        """Constants have no dependencies."""
        pass

    def _visit_data(self, node: Any) -> None:
        """Static data has no dependencies."""
        pass

    def _visit_raw(self, node: Any) -> None:
        """Raw blocks have no dependencies."""
        pass

    def _visit_slot(self, node: Any) -> None:
        """Slots have no dependencies."""
        pass

    def _visit_break(self, node: Any) -> None:
        """Break has no dependencies."""
        pass

    def _visit_continue(self, node: Any) -> None:
        """Continue has no dependencies."""
        pass

    def _visit_do(self, node: Any) -> None:
        """Handle do statement."""
        self._visit(node.expr)

    def _visit_loopvar(self, node: Any) -> None:
        """Loop variable access (loop.index, etc.) - no context deps."""
        pass

    def _build_path(self, node: Any) -> str | None:
        """Build dotted path from chained attribute/item access.

        Returns None if the path can't be determined statically
        (e.g., dynamic keys, local variables).
        """
        parts: list[str] = []
        current = node

        while True:
            node_type = type(current).__name__

            if node_type == "Getattr" or node_type == "OptionalGetattr":
                parts.append(current.attr)
                current = current.obj
            elif node_type == "Getitem":
                # Only static string keys
                if type(current.key).__name__ == "Const" and isinstance(current.key.value, str):
                    parts.append(current.key.value)
                    current = current.obj
                else:
                    return None  # Dynamic key
            elif node_type == "OptionalGetitem":
                if type(current.key).__name__ == "Const" and isinstance(current.key.value, str):
                    parts.append(current.key.value)
                    current = current.obj
                else:
                    return None
            elif node_type == "Name":
                name = current.name
                # Check if root is local
                if self._is_local(name):
                    return None  # Local var, not a context dep
                if name in _BUILTIN_NAMES:
                    return None  # Built-in
                parts.append(name)
                break
            else:
                return None  # Can't determine statically

        parts.reverse()
        return ".".join(parts)

    def _extract_targets(self, node: Any) -> set[str]:
        """Extract variable names from assignment target."""
        node_type = type(node).__name__

        if node_type == "Name":
            return {node.name}
        elif node_type == "Tuple":
            names: set[str] = set()
            for item in node.items:
                names |= self._extract_targets(item)
            return names

        return set()

    def _is_local(self, name: str) -> bool:
        """Check if a name is in local scope."""
        return any(name in scope for scope in self._scope_stack)

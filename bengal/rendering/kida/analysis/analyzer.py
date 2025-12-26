"""Block analyzer - unified entry point for template analysis.

Combines dependency analysis, purity checking, landmark detection,
and role classification into a unified analysis pass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.rendering.kida.analysis.cache import infer_cache_scope
from bengal.rendering.kida.analysis.config import DEFAULT_CONFIG, AnalysisConfig
from bengal.rendering.kida.analysis.dependencies import DependencyWalker
from bengal.rendering.kida.analysis.landmarks import LandmarkDetector
from bengal.rendering.kida.analysis.metadata import BlockMetadata, TemplateMetadata
from bengal.rendering.kida.analysis.purity import PurityAnalyzer
from bengal.rendering.kida.analysis.roles import classify_role

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Block, Template


class BlockAnalyzer:
    """Analyze template blocks and extract metadata.

    Combines dependency analysis, purity checking, landmark detection,
    and role classification into a unified analysis pass.

    Thread-safe: Stateless analyzers, creates new result objects.

    Example:
        >>> analyzer = BlockAnalyzer()
        >>> meta = analyzer.analyze(template_ast)
        >>> print(meta.blocks["nav"].cache_scope)
        'site'

    Configuration:
        >>> from bengal.rendering.kida.analysis import AnalysisConfig
        >>> config = AnalysisConfig(
        ...     page_prefixes=frozenset({"post.", "item."}),
        ...     site_prefixes=frozenset({"global.", "settings."}),
        ... )
        >>> analyzer = BlockAnalyzer(config=config)
    """

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        """Initialize analyzer with optional configuration.

        Args:
            config: Analysis configuration. Uses DEFAULT_CONFIG if not provided.
        """
        self._config = config or DEFAULT_CONFIG
        self._dep_walker = DependencyWalker()
        self._purity_analyzer = PurityAnalyzer(
            extra_pure_functions=self._config.extra_pure_functions,
            extra_impure_filters=self._config.extra_impure_filters,
        )
        self._landmark_detector = LandmarkDetector()

    def analyze(self, ast: Template) -> TemplateMetadata:
        """Analyze a template AST and return metadata.

        Args:
            ast: Parsed template AST (nodes.Template)

        Returns:
            TemplateMetadata with block information
        """
        blocks: dict[str, BlockMetadata] = {}

        # Collect blocks from AST
        block_nodes = self._collect_blocks(ast)

        for block_node in block_nodes:
            block_meta = self._analyze_block(block_node)
            blocks[block_meta.name] = block_meta

        # Analyze top-level dependencies (outside blocks)
        top_level_deps = self._analyze_top_level(ast, set(blocks.keys()))

        # Extract extends info
        extends = None
        if ast.extends:
            extends_expr = ast.extends.template
            if type(extends_expr).__name__ == "Const":
                extends = extends_expr.value

        return TemplateMetadata(
            name=None,  # Set by caller
            extends=extends,
            blocks=blocks,
            top_level_depends_on=top_level_deps,
        )

    def _analyze_block(self, block_node: Block) -> BlockMetadata:
        """Analyze a single block node."""
        # Dependency analysis
        depends_on = self._dep_walker.analyze(block_node)

        # Purity analysis
        is_pure = self._purity_analyzer.analyze(block_node)

        # Landmark detection
        landmarks = self._landmark_detector.detect(block_node)

        # Role classification
        inferred_role = classify_role(block_node.name, landmarks)

        # Cache scope inference
        cache_scope = infer_cache_scope(depends_on, is_pure, self._config)

        # Check if block emits any HTML
        emits_html = self._check_emits_html(block_node)

        return BlockMetadata(
            name=block_node.name,
            emits_html=emits_html,
            emits_landmarks=landmarks,
            inferred_role=inferred_role,
            depends_on=depends_on,
            is_pure=is_pure,
            cache_scope=cache_scope,
        )

    def _collect_blocks(self, ast: Template) -> list[Block]:
        """Recursively collect all Block nodes from AST."""
        blocks: list[Any] = []
        self._collect_blocks_recursive(ast.body, blocks)
        return blocks

    def _collect_blocks_recursive(self, nodes: Any, blocks: list[Any]) -> None:
        """Recursively find Block nodes."""
        for node in nodes:
            if type(node).__name__ == "Block":
                blocks.append(node)

            # Recurse into containers
            for attr in ("body", "else_", "empty"):
                if hasattr(node, attr):
                    children = getattr(node, attr)
                    if children:
                        self._collect_blocks_recursive(children, blocks)

            # Handle elif
            if hasattr(node, "elif_") and node.elif_:
                for _test, body in node.elif_:
                    self._collect_blocks_recursive(body, blocks)

            # Handle match cases
            if hasattr(node, "cases") and node.cases:
                for _pattern, body in node.cases:
                    self._collect_blocks_recursive(body, blocks)

    def _analyze_top_level(
        self,
        ast: Template,
        block_names: set[str],
    ) -> frozenset[str]:
        """Analyze dependencies in top-level code outside blocks.

        This captures dependencies from:
        - Code before/after blocks
        - Extends expression (e.g., dynamic parent template)
        - Context type declarations

        Does NOT include dependencies from inside blocks (those are
        tracked per-block).
        """
        deps: set[str] = set()

        # Analyze extends expression
        if ast.extends:
            extends_deps = self._dep_walker.analyze(ast.extends)
            deps.update(extends_deps)

        # Walk top-level nodes, excluding block bodies
        self._analyze_top_level_nodes(ast.body, block_names, deps)

        return frozenset(deps)

    def _analyze_top_level_nodes(
        self,
        nodes: Any,
        block_names: set[str],
        deps: set[str],
    ) -> None:
        """Walk nodes, collecting dependencies but skipping block bodies."""
        for node in nodes:
            node_type = type(node).__name__

            if node_type == "Block":
                # Skip block body - it's analyzed separately
                continue

            if node_type in (
                "Output",
                "If",
                "For",
                "Set",
                "Let",
                "With",
                "WithConditional",
                "Include",
                "Import",
                "FromImport",
                "Cache",
                "Match",
            ):
                # These nodes may have dependencies
                node_deps = self._dep_walker.analyze(node)
                deps.update(node_deps)

            elif node_type == "Data":
                # Static content has no dependencies
                continue

            elif node_type in ("Def", "Macro"):
                # Function definitions - analyze body for lexical scope access
                node_deps = self._dep_walker.analyze(node)
                deps.update(node_deps)

            else:
                # Unknown node type - try to analyze it
                try:
                    node_deps = self._dep_walker.analyze(node)
                    deps.update(node_deps)
                except Exception:
                    pass  # Skip nodes we can't analyze

    def _check_emits_html(self, node: Any) -> bool:
        """Check if a node produces any output."""
        node_type = type(node).__name__

        if node_type == "Data" and node.value.strip():
            return True
        if node_type == "Output":
            return True

        for attr in ("body", "else_", "empty"):
            if hasattr(node, attr):
                children = getattr(node, attr)
                if children:
                    for child in children:
                        if hasattr(child, "lineno") and self._check_emits_html(child):
                            return True

        # Handle elif
        if hasattr(node, "elif_") and node.elif_:
            for _test, body in node.elif_:
                for child in body:
                    if hasattr(child, "lineno") and self._check_emits_html(child):
                        return True

        return False

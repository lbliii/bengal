"""
Dependency visualizer for understanding build dependencies.

Generates visual representations of dependency graphs to help understand
what depends on what, and the "blast radius" of changes (what would
rebuild if a file changed).

Key Features:
    - DependencyNode: Single node with forward/reverse dependencies
    - DependencyGraph: Complete graph with traversal and visualization
    - DependencyVisualizer: Debug tool for analysis and export
    - Multiple output formats: Mermaid, DOT (Graphviz), ASCII tree

Use Cases:
    - Visualize what templates a page uses
    - See blast radius of changing a template
    - Identify highly-connected files (change triggers many rebuilds)
    - Export dependency diagrams for documentation

Example:
    >>> from bengal.debug import DependencyVisualizer
    >>> viz = DependencyVisualizer(cache=cache)
    >>> print(viz.visualize_page("content/docs/guide.md"))
    📄 guide.md
    ├─ 🎨 page.html
    │  └─ 🎨 base.html
    └─ 📊 authors.yaml

    >>> # What would rebuild if base.html changed?
    >>> affected = viz.get_blast_radius("templates/base.html")
    >>> print(f"{len(affected)} pages would rebuild")

Related Modules:
    - bengal.cache.dependency_tracker: Dependency tracking during builds
    - bengal.cache.build_cache: Persisted dependency information
    - bengal.debug.incremental_debugger: Rebuild analysis

See Also:
    - bengal/cli/commands/debug.py: CLI integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.debug.base import DebugRegistry, DebugReport, DebugTool, Severity

if TYPE_CHECKING:
    pass


@dataclass
class DependencyNode:
    """
    A single node in the dependency graph.

    Represents a file and tracks both forward dependencies (what this
    file depends on) and reverse dependencies (what depends on this file).

    Attributes:
        path: File path of this node.
        node_type: Classification: "page", "template", "partial", "data", "config".
        dependencies: Paths of files this node depends on.
        dependents: Paths of files that depend on this node.
        metadata: Additional node-specific data.

    Example:
        >>> node = DependencyNode(path="content/guide.md", node_type="page")
        >>> node.dependencies.add("templates/page.html")
        >>> node.is_leaf
        False
    """

    path: str
    node_type: str = "unknown"
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        """
        Check if node has no dependencies.

        Leaf nodes don't depend on anything else.
        """
        return len(self.dependencies) == 0

    @property
    def is_root(self) -> bool:
        """
        Check if nothing depends on this node.

        Root nodes are typically content pages that depend on
        templates but have nothing depending on them.
        """
        return len(self.dependents) == 0

    @property
    def short_path(self) -> str:
        """
        Get shortened path for compact display.

        Truncates long paths to ".../parent/file.ext" format.
        """
        path = Path(self.path)
        if len(path.parts) > 3:
            return f".../{'/'.join(path.parts[-2:])}"
        return self.path


@dataclass
class DependencyGraph:
    """
    Complete dependency graph for a project.

    Provides methods for traversal, querying, and visualization.
    Supports both forward (dependencies) and reverse (dependents)
    traversal, transitive closure, and multiple output formats.

    Attributes:
        nodes: Dictionary mapping file paths to DependencyNode instances.
        edges: Set of (from, to) tuples representing dependencies.

    Example:
        >>> graph = DependencyGraph()
        >>> graph.add_edge("page.md", "template.html")
        >>> deps = graph.get_dependencies("page.md")
        >>> blast = graph.get_blast_radius("template.html")
    """

    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    edges: set[tuple[str, str]] = field(default_factory=set)

    def add_node(self, path: str, node_type: str = "unknown") -> DependencyNode:
        """
        Add or get a node by path.

        If the node already exists, returns it without modification.

        Args:
            path: File path for the node.
            node_type: Node classification type.

        Returns:
            The new or existing DependencyNode.
        """
        if path not in self.nodes:
            self.nodes[path] = DependencyNode(path=path, node_type=node_type)
        return self.nodes[path]

    def add_edge(self, from_path: str, to_path: str) -> None:
        """
        Add a dependency edge (from depends on to).

        Creates nodes if they don't exist and updates both forward
        and reverse dependency sets.

        Args:
            from_path: Path that has the dependency.
            to_path: Path that is depended upon.
        """
        from_node = self.add_node(from_path)
        to_node = self.add_node(to_path)

        from_node.dependencies.add(to_path)
        to_node.dependents.add(from_path)
        self.edges.add((from_path, to_path))

    def get_dependencies(self, path: str, recursive: bool = False) -> set[str]:
        """
        Get dependencies of a node.

        Args:
            path: Node path
            recursive: Whether to get transitive dependencies

        Returns:
            Set of dependency paths
        """
        if path not in self.nodes:
            return set()

        deps = self.nodes[path].dependencies.copy()

        if recursive:
            visited = set()
            to_visit = list(deps)
            while to_visit:
                current = to_visit.pop()
                if current in visited:
                    continue
                visited.add(current)
                deps.add(current)
                if current in self.nodes:
                    to_visit.extend(self.nodes[current].dependencies)

        return deps

    def get_dependents(self, path: str, recursive: bool = False) -> set[str]:
        """
        Get what depends on a node (reverse dependencies).

        Args:
            path: Node path
            recursive: Whether to get transitive dependents

        Returns:
            Set of dependent paths
        """
        if path not in self.nodes:
            return set()

        dependents = self.nodes[path].dependents.copy()

        if recursive:
            visited = set()
            to_visit = list(dependents)
            while to_visit:
                current = to_visit.pop()
                if current in visited:
                    continue
                visited.add(current)
                dependents.add(current)
                if current in self.nodes:
                    to_visit.extend(self.nodes[current].dependents)

        return dependents

    def get_blast_radius(self, path: str) -> set[str]:
        """
        Get the "blast radius" of changing a file.

        Returns all pages that would need to rebuild if this file changed.

        Args:
            path: Path to the file that would change

        Returns:
            Set of page paths that would rebuild
        """
        # Get all transitive dependents
        all_affected = self.get_dependents(path, recursive=True)

        # Filter to only content pages
        pages = {p for p in all_affected if p.endswith((".md", ".markdown", ".rst"))}

        # Include the file itself if it's a page
        if path.endswith((".md", ".markdown", ".rst")):
            pages.add(path)

        return pages

    def to_mermaid(
        self,
        root: str | None = None,
        max_depth: int = 3,
        direction: str = "TB",
    ) -> str:
        """
        Generate Mermaid diagram of the graph.

        Args:
            root: Optional root node to start from
            max_depth: Maximum depth to traverse
            direction: Diagram direction (TB, BT, LR, RL)

        Returns:
            Mermaid diagram source code
        """
        lines = [f"graph {direction}"]

        # Define node styles
        lines.append("    %% Node styles")
        lines.append("    classDef page fill:#e1f5fe,stroke:#01579b")
        lines.append("    classDef template fill:#fff3e0,stroke:#e65100")
        lines.append("    classDef partial fill:#f3e5f5,stroke:#7b1fa2")
        lines.append("    classDef data fill:#e8f5e9,stroke:#2e7d32")
        lines.append("    classDef config fill:#ffebee,stroke:#c62828")
        lines.append("")

        visited: set[str] = set()
        node_ids: dict[str, str] = {}

        def get_node_id(path: str) -> str:
            if path not in node_ids:
                node_ids[path] = f"n{len(node_ids)}"
            return node_ids[path]

        def classify_node(path: str) -> str:
            if path.endswith((".md", ".markdown", ".rst")):
                return "page"
            if "template" in path.lower() or path.endswith((".html", ".jinja2")):
                return "template"
            if "partial" in path.lower() or "include" in path.lower():
                return "partial"
            if path.endswith((".yaml", ".yml", ".json")):
                if "config" in path.lower():
                    return "config"
                return "data"
            return "page"

        def add_node_and_deps(path: str, depth: int) -> None:
            if depth > max_depth or path in visited:
                return

            visited.add(path)
            node_id = get_node_id(path)
            node_type = classify_node(path)
            short_name = Path(path).name

            # Add node definition
            lines.append(f"    {node_id}[{short_name}]:::{node_type}")

            # Add edges to dependencies
            if path in self.nodes:
                for dep in self.nodes[path].dependencies:
                    if depth < max_depth:
                        dep_id = get_node_id(dep)
                        lines.append(f"    {node_id} --> {dep_id}")
                        add_node_and_deps(dep, depth + 1)

        # Start from root or all pages
        if root:
            add_node_and_deps(root, 0)
        else:
            # Add all pages and their immediate dependencies
            for path, node in self.nodes.items():
                if node.node_type == "page":
                    add_node_and_deps(path, 0)

        return "\n".join(lines)

    def to_dot(self, root: str | None = None, max_depth: int = 3) -> str:
        """
        Generate DOT format for Graphviz.

        Args:
            root: Optional root node to start from
            max_depth: Maximum depth to traverse

        Returns:
            DOT format source code
        """
        lines = ["digraph dependencies {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box, style=filled];")
        lines.append("")

        # Color scheme for node types
        colors = {
            "page": "#e1f5fe",
            "template": "#fff3e0",
            "partial": "#f3e5f5",
            "data": "#e8f5e9",
            "config": "#ffebee",
            "unknown": "#f5f5f5",
        }

        visited: set[str] = set()

        def classify_node(path: str) -> str:
            if path.endswith((".md", ".markdown", ".rst")):
                return "page"
            if "template" in path.lower() or path.endswith((".html", ".jinja2")):
                return "template"
            if "partial" in path.lower() or "include" in path.lower():
                return "partial"
            if path.endswith((".yaml", ".yml", ".json")):
                if "config" in path.lower():
                    return "config"
                return "data"
            return "unknown"

        def escape_label(s: str) -> str:
            return s.replace('"', '\\"').replace("\\", "\\\\")

        def add_node_and_deps(path: str, depth: int) -> None:
            if depth > max_depth or path in visited:
                return

            visited.add(path)
            node_type = classify_node(path)
            color = colors.get(node_type, colors["unknown"])
            short_name = Path(path).name

            # Add node
            lines.append(
                f'    "{escape_label(path)}" [label="{escape_label(short_name)}", fillcolor="{color}"];'
            )

            # Add edges
            if path in self.nodes:
                for dep in self.nodes[path].dependencies:
                    lines.append(f'    "{escape_label(path)}" -> "{escape_label(dep)}";')
                    if depth < max_depth:
                        add_node_and_deps(dep, depth + 1)

        # Start from root or all pages
        if root:
            add_node_and_deps(root, 0)
        else:
            for path, node in self.nodes.items():
                if node.node_type == "page":
                    add_node_and_deps(path, 0)

        lines.append("}")
        return "\n".join(lines)

    def format_tree(self, root: str, max_depth: int = 3) -> str:
        """
        Format dependencies as ASCII tree.

        Args:
            root: Root node to start from
            max_depth: Maximum depth to show

        Returns:
            ASCII tree representation
        """
        lines = [f"📄 {Path(root).name}"]

        def add_deps(path: str, depth: int, prefix: str) -> None:
            if depth >= max_depth or path not in self.nodes:
                return

            deps = sorted(self.nodes[path].dependencies)
            for i, dep in enumerate(deps):
                is_last = i == len(deps) - 1
                connector = "└─" if is_last else "├─"
                new_prefix = prefix + ("   " if is_last else "│  ")

                dep_name = Path(dep).name
                icon = self._get_icon(dep)
                lines.append(f"{prefix}{connector} {icon} {dep_name}")

                add_deps(dep, depth + 1, new_prefix)

        add_deps(root, 0, "")
        return "\n".join(lines)

    def _get_icon(self, path: str) -> str:
        """
        Get emoji icon for file type.

        Args:
            path: File path to classify.

        Returns:
            Emoji icon based on file extension.
        """
        if path.endswith((".md", ".markdown", ".rst")):
            return "📄"
        if path.endswith((".html", ".jinja2")):
            return "🎨"
        if path.endswith((".yaml", ".yml", ".json")):
            return "📊"
        if path.endswith((".css", ".scss", ".sass")):
            return "🎭"
        if path.endswith((".js", ".ts")):
            return "⚡"
        return "📁"


@DebugRegistry.register
class DependencyVisualizer(DebugTool):
    """
    Debug tool for visualizing dependencies.

    Helps understand the dependency structure of builds and
    visualize the blast radius of changes.

    Creation:
        Direct instantiation or via DebugRegistry:
            viz = DependencyVisualizer(cache=cache)

    Example:
        >>> viz = DependencyVisualizer(cache=cache)
        >>> graph = viz.build_graph()
        >>> print(graph.format_tree("content/posts/my-post.md"))
        >>> print(graph.to_mermaid(root="content/posts/my-post.md"))
    """

    name = "deps"
    description = "Visualize build dependencies"

    def analyze(self) -> DebugReport:
        """
        Analyze dependency structure.

        Returns:
            DebugReport with dependency analysis
        """
        report = self.create_report()
        report.summary = "Dependency structure analysis"

        graph = self.build_graph()

        report.statistics["total_nodes"] = len(graph.nodes)
        report.statistics["total_edges"] = len(graph.edges)

        # Count by type
        type_counts: dict[str, int] = {}
        for node in graph.nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1
        report.statistics["nodes_by_type"] = type_counts

        # Find highly connected nodes
        high_dependents = [
            (path, len(node.dependents))
            for path, node in graph.nodes.items()
            if len(node.dependents) > 10
        ]
        high_dependents.sort(key=lambda x: -x[1])

        if high_dependents:
            report.add_finding(
                title=f"{len(high_dependents)} files have >10 dependents",
                description="Changes to these files will trigger many rebuilds",
                severity=Severity.INFO,
                category="structure",
                metadata={"files": high_dependents[:10]},
                suggestion="Consider if these dependencies are necessary",
            )

        # Find isolated pages
        isolated = [
            path for path, node in graph.nodes.items() if node.node_type == "page" and node.is_leaf
        ]
        if isolated:
            report.add_finding(
                title=f"{len(isolated)} pages have no tracked dependencies",
                description="These pages don't depend on templates (unusual)",
                severity=Severity.INFO,
                category="structure",
                metadata={"pages": isolated[:10]},
            )

        # Generate recommendations
        report.recommendations = self._generate_recommendations(graph, report)

        # Store graph in metadata for export
        report.metadata["graph"] = graph

        return report

    def build_graph(self) -> DependencyGraph:
        """
        Build dependency graph from cache.

        Returns:
            DependencyGraph with all dependencies
        """
        graph = DependencyGraph()

        if not self.cache:
            return graph

        # Add all files as nodes
        for path in self.cache.file_fingerprints:
            node_type = self._classify_file(path)
            graph.add_node(path, node_type)

        # Add dependency edges
        for page, deps in self.cache.dependencies.items():
            for dep in deps:
                graph.add_edge(page, dep)

        return graph

    def visualize_page(self, page_path: str, max_depth: int = 3) -> str:
        """
        Visualize dependencies for a specific page.

        Args:
            page_path: Path to the page
            max_depth: Maximum depth to show

        Returns:
            ASCII tree of dependencies
        """
        graph = self.build_graph()
        return graph.format_tree(page_path, max_depth)

    def get_blast_radius(self, file_path: str) -> set[str]:
        """
        Get pages that would rebuild if file changed.

        Args:
            file_path: Path to the file that would change

        Returns:
            Set of page paths that would rebuild
        """
        graph = self.build_graph()
        return graph.get_blast_radius(file_path)

    def export_mermaid(
        self,
        output_path: Path | None = None,
        root: str | None = None,
    ) -> str:
        """
        Export dependency graph as Mermaid diagram.

        Args:
            output_path: Optional path to save the diagram
            root: Optional root node to start from

        Returns:
            Mermaid diagram source
        """
        graph = self.build_graph()
        mermaid = graph.to_mermaid(root=root)

        if output_path:
            # Wrap in markdown code block
            content = f"```mermaid\n{mermaid}\n```"
            output_path.write_text(content)

        return mermaid

    def export_dot(
        self,
        output_path: Path | None = None,
        root: str | None = None,
    ) -> str:
        """
        Export dependency graph as DOT format.

        Args:
            output_path: Optional path to save the file
            root: Optional root node to start from

        Returns:
            DOT format source
        """
        graph = self.build_graph()
        dot = graph.to_dot(root=root)

        if output_path:
            output_path.write_text(dot)

        return dot

    def _classify_file(self, path: str) -> str:
        """Classify file type for graph."""
        if path.endswith((".md", ".markdown", ".rst")):
            return "page"
        if path.endswith((".html", ".jinja2")):
            return "template"
        if "partial" in path.lower() or "include" in path.lower():
            return "partial"
        if path.endswith((".yaml", ".yml", ".json")):
            if "config" in path.lower():
                return "config"
            return "data"
        return "unknown"

    def _generate_recommendations(self, graph: DependencyGraph, report: DebugReport) -> list[str]:
        """Generate recommendations based on analysis."""
        recommendations: list[str] = []

        # Check for overly connected templates
        for path, node in graph.nodes.items():
            if node.node_type == "template" and len(node.dependents) > 50:
                recommendations.append(
                    f"Template {Path(path).name} affects >50 pages - changes are expensive"
                )
                break

        if not recommendations:
            recommendations.append("Dependency structure looks healthy! ✅")

        return recommendations

"""Shared utilities for graph analysis commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.cli.helpers import get_cli_output, load_site_from_cli
from bengal.utils.observability.logger import LogLevel, configure_logging

if TYPE_CHECKING:
    from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
    from bengal.cli.output import CLIOutput
    from bengal.protocols import SiteLike


def load_graph(
    source: str,
    config: str | None = None,
    *,
    quiet: bool = False,
) -> tuple[CLIOutput, SiteLike, KnowledgeGraph]:
    """
    Load a site, discover content, and build its knowledge graph.

    Common boilerplate shared by all graph analysis commands.

    Args:
        source: Path to site root.
        config: Optional path to config file.
        quiet: If True, suppress progress messages.

    Returns:
        Tuple of (cli, site, graph_obj).
    """
    from bengal.analysis.graph.knowledge_graph import KnowledgeGraph
    from bengal.orchestration.content import ContentOrchestrator

    cli = get_cli_output()
    configure_logging(level=LogLevel.WARNING)

    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    if not quiet:
        cli.info("🔍 Discovering site content...")

    content_orch = ContentOrchestrator(site)
    content_orch.discover()

    if not quiet:
        cli.info(f"📊 Building knowledge graph from {len(site.pages)} pages...")

    graph_obj = KnowledgeGraph(site)
    graph_obj.build()

    return cli, site, graph_obj


def page_incoming(graph: Any, page: Any) -> float:
    """Get incoming ref score for a page."""
    return graph.incoming_refs.get(page, 0.0)


def page_outgoing(graph: Any, page: Any) -> int:
    """Get outgoing ref count for a page."""
    return len(graph.outgoing_refs.get(page, set()))

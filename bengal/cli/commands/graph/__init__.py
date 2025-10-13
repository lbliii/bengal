"""Graph analysis and knowledge graph commands."""

from bengal.cli.commands.graph.analyze import graph
from bengal.cli.commands.graph.bridges import bridges
from bengal.cli.commands.graph.communities import communities
from bengal.cli.commands.graph.pagerank import pagerank
from bengal.cli.commands.graph.suggest import suggest

__all__ = ["graph", "pagerank", "communities", "bridges", "suggest"]

"""
Graph traversal utilities for analysis modules.

Provides BFS-based traversal algorithms used across path analysis,
centrality computation, and connectivity analysis.

This centralizes traversal logic that was previously duplicated in:
- path_analysis.py (find_shortest_path, _bfs_distances)

Example:
    >>> from bengal.analysis.utils import bfs_distances, bfs_path
    >>> distances = bfs_distances(graph.outgoing_refs, source, pages)
    >>> path = bfs_path(graph.outgoing_refs, source, target)

"""

from collections import deque
from typing import TypeVar

T = TypeVar("T")


def bfs_distances(
    outgoing_refs: dict[T, set[T]],
    source: T,
    targets: set[T] | list[T] | None = None,
) -> dict[T, int]:
    """
    Compute shortest path distances from source to all reachable nodes.

    Uses breadth-first search to find the minimum number of hops from
    the source node to all other reachable nodes in the graph.

    Args:
        outgoing_refs: Adjacency list mapping nodes to their neighbors
        source: Starting node for distance computation
        targets: Optional set/list of target nodes to consider.
                If provided, only these nodes will have distances computed.
                Nodes not in targets will have distance -1.
                If None, all reachable nodes are considered.

    Returns:
        Dictionary mapping nodes to their distances from source.
        Distance is -1 for unreachable nodes.
        Distance is 0 for the source node itself.

    Example:
        >>> # Compute distances to all nodes
        >>> distances = bfs_distances(graph.outgoing_refs, start_page)
        >>> print(f"Distance to target: {distances[target_page]}")

        >>> # Compute distances only to specific nodes
        >>> distances = bfs_distances(graph.outgoing_refs, start, target_set)

    """
    # Convert list to set for O(1) lookup
    target_set: set[T] | None = None
    if targets is not None:
        target_set = set(targets) if not isinstance(targets, set) else targets

    # Initialize distances
    if target_set is not None:
        distances: dict[T, int] = dict.fromkeys(target_set, -1)
        if source in target_set:
            distances[source] = 0
    else:
        distances = {source: 0}

    # BFS traversal
    queue: deque[T] = deque([source])

    while queue:
        current = queue.popleft()
        current_dist = distances.get(current, 0)

        neighbors = outgoing_refs.get(current, set())
        for neighbor in neighbors:
            # Skip if not in target set (when specified)
            if target_set is not None and neighbor not in target_set:
                continue

            # Skip if already visited
            if neighbor in distances and distances[neighbor] >= 0:
                continue

            distances[neighbor] = current_dist + 1
            queue.append(neighbor)

    return distances


def bfs_path(
    outgoing_refs: dict[T, set[T]],
    source: T,
    target: T,
) -> list[T] | None:
    """
    Find shortest path between two nodes using BFS.

    Args:
        outgoing_refs: Adjacency list mapping nodes to their neighbors
        source: Starting node
        target: Destination node

    Returns:
        List of nodes representing the shortest path from source to target,
        including both endpoints. Returns None if no path exists.

    Example:
        >>> path = bfs_path(graph.outgoing_refs, page_a, page_b)
        >>> if path:
        ...     print(f"Path length: {len(path) - 1} hops")
        ...     print(" -> ".join(p.title for p in path))

    """
    if source == target:
        return [source]

    # BFS with parent tracking
    queue: deque[T] = deque([source])
    visited: set[T] = {source}
    parent: dict[T, T] = {}

    while queue:
        current = queue.popleft()

        neighbors = outgoing_refs.get(current, set())
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)

                if neighbor == target:
                    # Reconstruct path
                    path = [target]
                    node = target
                    while node != source:
                        node = parent[node]
                        path.append(node)
                    return list(reversed(path))

    return None  # No path found


def bfs_predecessors(
    outgoing_refs: dict[T, set[T]],
    source: T,
    targets: set[T] | list[T],
) -> tuple[dict[T, list[T]], dict[T, int], dict[T, int], list[T]]:
    """
    BFS traversal collecting predecessor information for centrality computation.

    This is the core BFS used by Brandes' betweenness centrality algorithm.
    It computes shortest path counts and predecessor lists simultaneously.

    Args:
        outgoing_refs: Adjacency list mapping nodes to their neighbors
        source: Starting node for BFS
        targets: Set/list of nodes to consider in the graph

    Returns:
        Tuple of (predecessors, sigma, distance, stack) where:
        - predecessors: Map of node -> list of predecessor nodes on shortest paths
        - sigma: Map of node -> count of shortest paths from source
        - distance: Map of node -> distance from source (-1 if unreachable)
        - stack: Nodes in order of discovery (for back-propagation)

    Example:
        >>> preds, sigma, dist, stack = bfs_predecessors(refs, source, pages)
        >>> # sigma[target] = number of shortest paths to target
        >>> # preds[target] = nodes that precede target on shortest paths

    """
    target_set = set(targets) if not isinstance(targets, set) else targets

    # Initialize
    predecessors: dict[T, list[T]] = {node: [] for node in target_set}
    sigma: dict[T, int] = dict.fromkeys(target_set, 0)
    sigma[source] = 1
    distance: dict[T, int] = dict.fromkeys(target_set, -1)
    distance[source] = 0

    stack: list[T] = []
    queue: deque[T] = deque([source])

    while queue:
        current = queue.popleft()
        stack.append(current)

        neighbors = outgoing_refs.get(current, set())
        for neighbor in neighbors:
            if neighbor not in target_set:
                continue

            # First time seeing this neighbor
            if distance[neighbor] < 0:
                queue.append(neighbor)
                distance[neighbor] = distance[current] + 1

            # Is this a shortest path to neighbor?
            if distance[neighbor] == distance[current] + 1:
                sigma[neighbor] += sigma[current]
                predecessors[neighbor].append(current)

    return predecessors, sigma, distance, stack

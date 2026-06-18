"""
Deterministic build-time graph layout for Bengal SSG.

Produces reproducible, normalized ``(x, y)`` coordinates in ``[0, 1]`` for graph
nodes so the client renders *static* positions with no runtime force simulation.
This is what lets us drop D3 entirely: the expensive part (layout) moves to the
build, and the browser only draws.

Determinism is load-bearing. The coordinates ship inside ``graph.json`` and each
page's ``index.json`` ``.graph`` block, and Bengal guards warm==cold byte parity.
We therefore:

- seed a local PRNG (never the global ``random`` module),
- iterate nodes/edges in sorted order (set iteration order is per-process),
- round coordinates to a fixed precision (bounds JSON size + any float drift).

Two layouts are provided:

- :func:`compute_force_layout` — Fruchterman-Reingold for the full-graph explorer.
  Uses a Barnes-Hut quadtree for repulsion so it scales to large graphs; falls
  back to exact O(n^2) repulsion below a threshold (simpler + exact for small N).
- :func:`compute_radial_layout` — a concentric layout for the per-page minimap
  neighborhood: the current page pinned dead-center, neighbors placed on rings
  ordered by connectivity. Centered by construction, trivially deterministic.

Both return ``dict[node_id, (x, y)]`` with coordinates in ``[0, 1]``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# Decimals of precision for emitted coordinates. Enough for crisp rendering at
# any viewport; small enough to keep JSON compact and guard against any
# platform-level float drift breaking byte parity.
_COORD_PRECISION = 4

# Above this node count, use the Barnes-Hut approximation for repulsion; below
# it, exact pairwise repulsion is cheap and avoids approximation error.
_BARNES_HUT_THRESHOLD = 256

# Barnes-Hut opening angle. Smaller = more accurate + slower; 0.9 is the usual
# speed/quality sweet spot for force layouts.
_BH_THETA = 0.9

# Stop subdividing quadtree cells below this size. Without it, near-coincident
# nodes (which happen as the layout converges) drive unbounded recursion. Below
# this scale the points are effectively the same location, so collapsing them
# into one aggregate cell is both correct and cheap.
_MIN_CELL = 1e-6


class _Rng:
    """Tiny deterministic PRNG (xorshift64*), independent of global state.

    Seeded from an int; reproducible across processes and machines.
    """

    __slots__ = ("_s",)

    _MASK = 0xFFFFFFFFFFFFFFFF

    def __init__(self, seed: int) -> None:
        # Avoid the all-zero state (xorshift fixed point).
        self._s = (seed & self._MASK) or 0x9E3779B97F4A7C15

    def random(self) -> float:
        """Return a deterministic float in ``[0, 1)``."""
        x = self._s
        x ^= (x >> 12) & self._MASK
        x ^= (x << 25) & self._MASK
        x ^= (x >> 27) & self._MASK
        self._s = x & self._MASK
        return ((self._s * 0x2545F4914F6CDD1D) & self._MASK) / (self._MASK + 1)


def _round(value: float) -> float:
    return round(value, _COORD_PRECISION)


def _normalize(
    positions: dict[str, list[float]],
    *,
    margin: float = 0.06,
) -> dict[str, tuple[float, float]]:
    """Scale positions to fit ``[margin, 1 - margin]`` preserving aspect ratio."""
    if not positions:
        return {}

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    span = max(span_x, span_y) or 1.0

    inner = 1.0 - 2.0 * margin
    # Center the smaller axis within the unit box.
    off_x = margin + (span - span_x) / (2.0 * span) * inner
    off_y = margin + (span - span_y) / (2.0 * span) * inner

    out: dict[str, tuple[float, float]] = {}
    for node_id in sorted(positions):
        px, py = positions[node_id]
        nx = off_x + (px - min_x) / span * inner
        ny = off_y + (py - min_y) / span * inner
        out[node_id] = (_round(nx), _round(ny))
    return out


# ---------------------------------------------------------------------------
# Barnes-Hut quadtree (repulsion approximation)
# ---------------------------------------------------------------------------


class _BHNode:
    """A quadtree cell: either a leaf holding one body or an internal node."""

    __slots__ = ("body", "children", "cx", "cy", "mass", "size", "x0", "y0")

    def __init__(self, x0: float, y0: float, size: float) -> None:
        self.x0 = x0
        self.y0 = y0
        self.size = size
        self.cx = 0.0  # center of mass
        self.cy = 0.0
        self.mass = 0.0
        self.body: tuple[float, float] | None = None  # leaf position
        self.children: list[_BHNode | None] | None = None

    def _quadrant(self, x: float, y: float) -> int:
        half = self.size / 2.0
        return (1 if x >= self.x0 + half else 0) + (2 if y >= self.y0 + half else 0)

    def insert(self, x: float, y: float) -> None:
        # Update aggregate center of mass.
        total = self.mass + 1.0
        self.cx = (self.cx * self.mass + x) / total
        self.cy = (self.cy * self.mass + y) / total
        self.mass = total

        if self.body is None and self.children is None:
            self.body = (x, y)
            return

        # Near-coincident nodes: stop subdividing and let them aggregate into
        # this cell's center of mass (already updated above). Prevents unbounded
        # recursion as the layout converges.
        if self.size <= _MIN_CELL:
            return

        if self.children is None:
            # Subdivide: push the existing body down, then continue.
            self.children = [None, None, None, None]
            # Reaching here with children is None means a body was set earlier.
            assert self.body is not None
            bx, by = self.body
            self.body = None
            self._insert_into_child(bx, by)

        self._insert_into_child(x, y)

    def _insert_into_child(self, x: float, y: float) -> None:
        assert self.children is not None
        q = self._quadrant(x, y)
        child = self.children[q]
        if child is None:
            half = self.size / 2.0
            cx0 = self.x0 + (half if q & 1 else 0.0)
            cy0 = self.y0 + (half if q & 2 else 0.0)
            child = _BHNode(cx0, cy0, half)
            self.children[q] = child
        child.insert(x, y)

    def force_on(self, x: float, y: float, k2: float, theta: float) -> tuple[float, float]:
        """Accumulated repulsion on ``(x, y)`` from this subtree."""
        if self.mass == 0.0:
            return (0.0, 0.0)

        dx = x - self.cx
        dy = y - self.cy
        dist2 = dx * dx + dy * dy

        children = self.children
        # Treat far/aggregate cells as a single body (Barnes-Hut criterion).
        if children is None or (self.size * self.size < theta * theta * dist2):
            if dist2 < 1e-12:
                return (0.0, 0.0)
            inv = k2 * self.mass / dist2
            return (dx * inv, dy * inv)

        fx = 0.0
        fy = 0.0
        for child in children:
            if child is not None:
                cfx, cfy = child.force_on(x, y, k2, theta)
                fx += cfx
                fy += cfy
        return (fx, fy)


def compute_force_layout(
    node_ids: Sequence[str],
    edges: Sequence[tuple[str, str]],
    *,
    seed: int = 1,
    iterations: int | None = None,
    communities: Mapping[str, int] | None = None,
    weights: Mapping[tuple[str, str], float] | None = None,
) -> dict[str, tuple[float, float]]:
    """Fruchterman-Reingold layout, normalized to ``[0, 1]``.

    Args:
        node_ids: Node identifiers. Order is irrelevant — sorted internally.
        edges: ``(source, target)`` id pairs. Endpoints missing from
            ``node_ids`` are ignored.
        seed: PRNG seed for the deterministic initial placement.
        iterations: Override the (otherwise N-derived) iteration count.
        communities: Optional ``node_id -> community_id`` map. When given, the
            layout becomes community-aware: each community is assigned a ring
            centroid (deterministically, by sorted community id) and nodes are
            seeded near + gravitated toward their community's centroid instead of
            a single global center. This separates clusters into distinct visual
            lobes (the "topic map" look) rather than one center-piled hairball,
            and — because nodes start near their final neighborhood — tends to
            converge in fewer iterations.
        weights: Optional ``(source, target) -> weight`` map (any key order).
            Edge attraction is scaled by the weight (capped), so strongly /
            bidirectionally linked pairs sit closer together.

    Returns:
        ``dict[node_id, (x, y)]`` with coordinates in ``[0, 1]``. Empty input
        yields an empty dict; a single node is centered. Deterministic for a
        given (node set, edge set, communities, weights, seed).
    """
    ids = sorted(set(node_ids))
    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.5, 0.5)}

    rng = _Rng(seed)

    # Community centroids on a ring (deterministic: sorted community ids). Nodes
    # without a community fall to a synthetic center bucket so the math is total.
    centroids: dict[int, tuple[float, float]] = {}
    if communities:
        comm_ids = sorted({int(communities.get(nid, -1)) for nid in ids})
        num_comms = len(comm_ids)
        ring_r = 0.35
        for rank, cid in enumerate(comm_ids):
            if num_comms <= 1:
                centroids[cid] = (0.5, 0.5)
            else:
                angle = 2.0 * math.pi * rank / num_comms
                centroids[cid] = (0.5 + ring_r * math.cos(angle), 0.5 + ring_r * math.sin(angle))

    def _centroid(nid: str) -> tuple[float, float]:
        return (
            centroids.get(int(communities.get(nid, -1)), (0.5, 0.5)) if communities else (0.5, 0.5)
        )

    # Initial placement. With communities, seed each node near its centroid (so
    # clusters start apart); otherwise a deterministic scatter in the unit box.
    pos: dict[str, list[float]] = {}
    for nid in ids:
        if communities:
            cx, cy = _centroid(nid)
            pos[nid] = [cx + (rng.random() - 0.5) * 0.12, cy + (rng.random() - 0.5) * 0.12]
        else:
            pos[nid] = [rng.random(), rng.random()]

    valid = set(ids)
    clean_edges = sorted((s, t) for s, t in edges if s in valid and t in valid and s != t)

    # Normalize edge weights to sorted-pair keys for direction-independent lookup.
    weight_by_pair: dict[tuple[str, str], float] = {}
    if weights:
        for (s, t), w in weights.items():
            weight_by_pair[(s, t) if s <= t else (t, s)] = float(w)

    # FR ideal edge length for a unit area.
    k = math.sqrt(1.0 / n)
    k2 = k * k

    if iterations is None:
        # More nodes need more iterations to settle, but cap for build cost.
        iterations = min(300, max(60, int(30 * math.log(n + 1))))

    temp = 0.1  # initial max displacement per step (unit-square scale)
    cooling = temp / (iterations + 1)
    use_bh = n >= _BARNES_HUT_THRESHOLD

    for _ in range(iterations):
        disp: dict[str, list[float]] = {nid: [0.0, 0.0] for nid in ids}

        # --- Repulsion ---
        if use_bh:
            root = _BHNode(0.0, 0.0, 1.0)
            for nid in ids:  # sorted -> deterministic tree
                px, py = pos[nid]
                root.insert(px, py)
            for nid in ids:
                px, py = pos[nid]
                fx, fy = root.force_on(px, py, k2, _BH_THETA)
                disp[nid][0] += fx
                disp[nid][1] += fy
        else:
            for i in range(n):
                a = ids[i]
                ax, ay = pos[a]
                da = disp[a]
                for j in range(i + 1, n):
                    b = ids[j]
                    bx, by = pos[b]
                    dx = ax - bx
                    dy = ay - by
                    dist2 = dx * dx + dy * dy
                    if dist2 < 1e-12:
                        # Deterministic nudge for coincident nodes.
                        dx = (rng.random() - 0.5) * 1e-3
                        dy = (rng.random() - 0.5) * 1e-3
                        dist2 = dx * dx + dy * dy
                    f = k2 / dist2
                    fx = dx * f
                    fy = dy * f
                    da[0] += fx
                    da[1] += fy
                    db = disp[b]
                    db[0] -= fx
                    db[1] -= fy

        # --- Attraction along edges (springs), scaled by edge weight ---
        for s, t in clean_edges:
            sx, sy = pos[s]
            tx, ty = pos[t]
            dx = sx - tx
            dy = sy - ty
            dist = math.sqrt(dx * dx + dy * dy) or 1e-6
            w = weight_by_pair.get((s, t) if s <= t else (t, s), 1.0)
            f = (dist * dist) / k * min(w, 3.0)
            fx = (dx / dist) * f
            fy = (dy / dist) * f
            disp[s][0] -= fx
            disp[s][1] -= fy
            disp[t][0] += fx
            disp[t][1] += fy

        # --- Gravity. Community-aware: pull toward the community centroid (so
        # clusters stay as separated lobes) plus a weak global cohesion that
        # keeps the whole graph framed. Without communities, a single mild pull
        # toward center (keeps disconnected nodes in frame). ---
        for nid in ids:
            px, py = pos[nid]
            if communities:
                cx, cy = _centroid(nid)
                disp[nid][0] += (cx - px) * k * 0.9 + (0.5 - px) * k * 0.12
                disp[nid][1] += (cy - py) * k * 0.9 + (0.5 - py) * k * 0.12
            else:
                disp[nid][0] += (0.5 - px) * k * 0.5
                disp[nid][1] += (0.5 - py) * k * 0.5

        # --- Integrate, capped by temperature ---
        for nid in ids:
            dxn, dyn = disp[nid]
            length = math.sqrt(dxn * dxn + dyn * dyn) or 1e-9
            step = min(length, temp)
            p = pos[nid]
            p[0] += (dxn / length) * step
            p[1] += (dyn / length) * step

        temp -= cooling

    return _normalize(pos)


def compute_radial_layout(
    center_id: str,
    neighbor_ids: Sequence[str],
    *,
    connectivity: Mapping[str, int] | None = None,
    seed: int = 1,
) -> dict[str, tuple[float, float]]:
    """Concentric layout for a per-page minimap neighborhood.

    The center node is pinned at ``(0.5, 0.5)``; neighbors are distributed on one
    or two rings, ordered by connectivity (most-connected first), with a small
    deterministic angular jitter so rings don't look mechanical.

    Args:
        center_id: The current page's node id (placed dead-center).
        neighbor_ids: Connected node ids.
        connectivity: Optional ``id -> score`` used to order/ring neighbors.
        seed: PRNG seed for the deterministic jitter.

    Returns:
        ``dict[node_id, (x, y)]`` with coordinates in ``[0, 1]``.
    """
    out: dict[str, tuple[float, float]] = {center_id: (0.5, 0.5)}
    neighbors = [nid for nid in neighbor_ids if nid != center_id]
    if not neighbors:
        return out

    score = connectivity or {}
    # Most-connected neighbors sit on the inner ring; ties broken by id for
    # determinism.
    neighbors.sort(key=lambda nid: (-int(score.get(nid, 0)), nid))

    rng = _Rng(seed)
    count = len(neighbors)
    # One ring up to 8 neighbors, two rings beyond that.
    inner_count = count if count <= 8 else (count + 1) // 2
    rings = [
        (neighbors[:inner_count], 0.30),
        (neighbors[inner_count:], 0.46),
    ]

    for ring_nodes, radius in rings:
        m = len(ring_nodes)
        if m == 0:
            continue
        for i, nid in enumerate(ring_nodes):
            # Even angular spacing + small deterministic jitter.
            angle = (2.0 * math.pi * i) / m + (rng.random() - 0.5) * (0.6 / m)
            x = 0.5 + radius * math.cos(angle)
            y = 0.5 + radius * math.sin(angle)
            out[nid] = (_round(x), _round(y))
    return out

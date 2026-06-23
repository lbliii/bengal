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
- :func:`compute_hierarchical_layout` — per-community sub-layout packed into an
  atlas (topic map at scale). Used when Louvain detects multiple communities.
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

# Spacing knobs for the full-graph explorer. Large sites (1k+ nodes) otherwise
# compress into overlapping blobs: FR's ``k = sqrt(1/n)`` shrinks with N, and
# strong community gravity pulls intra-cluster nodes onto the same spokes.
_K_SCALE = 2.5  # multiplier on ideal edge length (larger => more spread)
_REPULSION_SOFTENING = 0.18  # min center-to-center distance as a fraction of k
_COMMUNITY_RING_R = 0.42  # community centroid ring radius (was 0.35)
_SEED_SPREAD = 0.22  # initial jitter around each community centroid
_COMMUNITY_GRAVITY = 0.65  # pull toward community centroid (was 0.9)
_GLOBAL_GRAVITY = 0.10  # weak pull toward graph center (was 0.12)
_OVERLAP_MIN_K = 0.45  # post-layout minimum center distance as a fraction of k
_OVERLAP_PASSES = 5  # relaxation sweeps before normalization

# Hierarchical layout: each Louvain community gets its own local box before packing.
_COMMUNITY_SLOT_MIN = 0.14  # smallest community footprint (pre-global-normalize)
_COMMUNITY_SLOT_MAX = 0.52  # largest community footprint
_COMMUNITY_PACK_RING = 0.38  # ring radius for packed community centers
_COMMUNITY_PACK_PAD = 0.04  # gap between adjacent community boxes
_SIZE_RADIUS_MIN = 0.006  # layout collision radius floor (normalized local space)
_SIZE_RADIUS_MAX = 0.024  # layout collision radius ceiling


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


def _relax_overlaps(
    positions: dict[str, list[float]],
    ids: Sequence[str],
    *,
    min_dist: float,
    rng: _Rng,
    passes: int,
    radii: Mapping[str, float] | None = None,
) -> None:
    """Push apart pairs closer than ``min_dist`` (deterministic, in-place)."""
    if min_dist <= 0.0 or len(ids) < 2 or passes <= 0:
        return

    n = len(ids)
    for _ in range(passes):
        moved = False
        for i in range(n):
            a = ids[i]
            ax, ay = positions[a]
            ra = radii.get(a, min_dist / 2.0) if radii else min_dist / 2.0
            for j in range(i + 1, n):
                b = ids[j]
                bx, by = positions[b]
                rb = radii.get(b, min_dist / 2.0) if radii else min_dist / 2.0
                pair_min = max(min_dist, ra + rb)
                pair_min2 = pair_min * pair_min
                dx = ax - bx
                dy = ay - by
                dist2 = dx * dx + dy * dy
                if dist2 >= pair_min2:
                    continue
                moved = True
                if dist2 < 1e-18:
                    dx = (rng.random() - 0.5) * pair_min
                    dy = (rng.random() - 0.5) * pair_min
                    dist2 = dx * dx + dy * dy
                dist = math.sqrt(dist2)
                shift = (pair_min - dist) * 0.55
                ux = dx / dist
                uy = dy / dist
                positions[a][0] = ax + ux * shift
                positions[a][1] = ay + uy * shift
                positions[b][0] = bx - ux * shift
                positions[b][1] = by - uy * shift
                ax, ay = positions[a]
        if not moved:
            break


def _layout_radius(size: float) -> float:
    """Map visual node size (8–50) to a layout collision radius in local space."""
    clamped = max(8.0, min(50.0, float(size)))
    t = (clamped - 8.0) / 42.0
    return _SIZE_RADIUS_MIN + t * (_SIZE_RADIUS_MAX - _SIZE_RADIUS_MIN)


def compute_community_bounds(
    coords: Mapping[str, tuple[float, float]],
    communities: Mapping[str, int],
) -> dict[int, dict[str, float]]:
    """Derive centroid + axis-aligned bounds per community id from final coords."""
    grouped: dict[int, list[tuple[float, float]]] = {}
    for nid in sorted(coords):
        cid = int(communities.get(nid, -1))
        grouped.setdefault(cid, []).append(coords[nid])

    out: dict[int, dict[str, float]] = {}
    for cid in sorted(grouped):
        pts = grouped[cid]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        out[cid] = {
            "x": _round(sum(xs) / len(xs)),
            "y": _round(sum(ys) / len(ys)),
            "min_x": _round(min(xs)),
            "min_y": _round(min(ys)),
            "max_x": _round(max(xs)),
            "max_y": _round(max(ys)),
        }
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

    def force_on(
        self,
        x: float,
        y: float,
        k2: float,
        theta: float,
        *,
        soft_dist2: float,
    ) -> tuple[float, float]:
        """Accumulated repulsion on ``(x, y)`` from this subtree."""
        if self.mass == 0.0:
            return (0.0, 0.0)

        dx = x - self.cx
        dy = y - self.cy
        dist2 = max(dx * dx + dy * dy, soft_dist2)

        children = self.children
        # Treat far/aggregate cells as a single body (Barnes-Hut criterion).
        if children is None or (self.size * self.size < theta * theta * dist2):
            inv = k2 * self.mass / dist2
            return (dx * inv, dy * inv)

        fx = 0.0
        fy = 0.0
        for child in children:
            if child is not None:
                cfx, cfy = child.force_on(x, y, k2, theta, soft_dist2=soft_dist2)
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
    node_sizes: Mapping[str, float] | None = None,
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
        node_sizes: Optional ``node_id -> visual size`` map (8–50). When given,
            the post-layout overlap pass reserves space proportional to size.

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
        ring_r = _COMMUNITY_RING_R
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
            pos[nid] = [
                cx + (rng.random() - 0.5) * _SEED_SPREAD,
                cy + (rng.random() - 0.5) * _SEED_SPREAD,
            ]
        else:
            pos[nid] = [rng.random(), rng.random()]

    valid = set(ids)
    clean_edges = sorted((s, t) for s, t in edges if s in valid and t in valid and s != t)

    # Normalize edge weights to sorted-pair keys for direction-independent lookup.
    weight_by_pair: dict[tuple[str, str], float] = {}
    if weights:
        for (s, t), w in weights.items():
            weight_by_pair[(s, t) if s <= t else (t, s)] = float(w)

    # FR ideal edge length for a unit area, scaled up so large graphs don't
    # collapse into overlapping clusters before normalization.
    k = math.sqrt(_K_SCALE / n)
    k2 = k * k
    soft_dist2 = (k * _REPULSION_SOFTENING) ** 2

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
                fx, fy = root.force_on(px, py, k2, _BH_THETA, soft_dist2=soft_dist2)
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
                    dist2 = max(dist2, soft_dist2)
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
                disp[nid][0] += (cx - px) * k * _COMMUNITY_GRAVITY + (
                    0.5 - px
                ) * k * _GLOBAL_GRAVITY
                disp[nid][1] += (cy - py) * k * _COMMUNITY_GRAVITY + (
                    0.5 - py
                ) * k * _GLOBAL_GRAVITY
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

    _relax_overlaps(
        pos,
        ids,
        min_dist=k * _OVERLAP_MIN_K,
        rng=rng,
        passes=_OVERLAP_PASSES,
        radii=(
            {nid: _layout_radius(node_sizes[nid]) for nid in ids if nid in node_sizes}
            if node_sizes
            else None
        ),
    )
    return _normalize(pos)


def compute_hierarchical_layout(
    node_ids: Sequence[str],
    edges: Sequence[tuple[str, str]],
    *,
    communities: Mapping[str, int],
    seed: int = 1,
    weights: Mapping[tuple[str, str], float] | None = None,
    node_sizes: Mapping[str, float] | None = None,
) -> dict[str, tuple[float, float]]:
    """Hierarchical layout: each community laid out locally, then packed into an atlas.

    Phase A — layout each Louvain community independently in its own unit box
    (so dense topics spread internally instead of fighting for one global centroid).
    Phase B — pack community boxes on a ring, sized by ``sqrt(node count)``.
    Phase C — normalize the composed atlas to ``[0, 1]``.

    Deterministic for a given (node set, edge set, communities, weights, seed).
    """
    ids = sorted(set(node_ids))
    if not ids:
        return {}
    if len(ids) == 1:
        return {ids[0]: (0.5, 0.5)}

    # Group members by community id (sorted for determinism).
    groups: dict[int, list[str]] = {}
    for nid in ids:
        cid = int(communities.get(nid, -1))
        groups.setdefault(cid, []).append(nid)

    valid = set(ids)
    clean_edges = sorted((s, t) for s, t in edges if s in valid and t in valid and s != t)

    weight_by_pair: dict[tuple[str, str], float] = {}
    if weights:
        for (s, t), w in weights.items():
            weight_by_pair[(s, t) if s <= t else (t, s)] = float(w)

    local_by_comm: dict[int, dict[str, tuple[float, float]]] = {}
    for cid in sorted(groups):
        members = groups[cid]
        if len(members) == 1:
            local_by_comm[cid] = {members[0]: (0.5, 0.5)}
            continue
        member_set = set(members)
        local_edges = [(s, t) for s, t in clean_edges if s in member_set and t in member_set]
        local_weights = {
            pair: weight_by_pair[pair]
            for pair in weight_by_pair
            if pair[0] in member_set and pair[1] in member_set
        }
        local_sizes = (
            {nid: node_sizes[nid] for nid in members if nid in node_sizes} if node_sizes else None
        )
        # Distinct seed per community so layouts don't mirror each other.
        local_by_comm[cid] = compute_force_layout(
            members,
            local_edges,
            seed=seed + (cid + 1) * 997,
            weights=local_weights or None,
            node_sizes=local_sizes,
        )

    # Slot size scales with sqrt(n) so large topics get more atlas real estate.
    comm_ids = sorted(groups)
    counts = {cid: len(groups[cid]) for cid in comm_ids}
    max_sqrt = max(math.sqrt(float(counts[cid])) for cid in comm_ids) or 1.0

    rng = _Rng(seed)
    num_comms = len(comm_ids)
    centers: dict[int, tuple[float, float]] = {}
    slots: dict[int, float] = {}
    for rank, cid in enumerate(comm_ids):
        sqrt_n = math.sqrt(float(counts[cid]))
        slot = _COMMUNITY_SLOT_MIN + (_COMMUNITY_SLOT_MAX - _COMMUNITY_SLOT_MIN) * (
            sqrt_n / max_sqrt
        )
        slots[cid] = slot
        if num_comms <= 1:
            centers[cid] = (0.5, 0.5)
        else:
            angle = 2.0 * math.pi * rank / num_comms + (rng.random() - 0.5) * 0.04
            centers[cid] = (
                0.5 + _COMMUNITY_PACK_RING * math.cos(angle),
                0.5 + _COMMUNITY_PACK_RING * math.sin(angle),
            )

    composed: dict[str, list[float]] = {}
    for cid in comm_ids:
        cx, cy = centers[cid]
        slot = slots[cid]
        inner = max(0.05, slot - _COMMUNITY_PACK_PAD)
        for nid in groups[cid]:
            lx, ly = local_by_comm[cid][nid]
            composed[nid] = [cx + (lx - 0.5) * inner, cy + (ly - 0.5) * inner]

    return _normalize(composed)


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

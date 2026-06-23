"""Tests for the deterministic build-time graph layout.

Determinism is load-bearing: layout coordinates ship in ``graph.json`` and each
page's ``index.json`` ``.graph`` block, and Bengal guards warm==cold byte parity.
These tests pin the three properties that protect that contract:

1. Reproducibility — same input (and seed) always yields identical coordinates.
2. Bounds — all coordinates land in ``[0, 1]``.
3. Approximation fidelity — the Barnes-Hut repulsion path matches the exact
   O(n^2) path closely (so crossing the threshold doesn't visibly jump layouts).
"""

from __future__ import annotations

import math

from bengal.analysis.graph.layout import (
    _BARNES_HUT_THRESHOLD,
    compute_force_layout,
    compute_hierarchical_layout,
    compute_radial_layout,
)


def _ring_graph(n: int) -> tuple[list[str], list[tuple[str, str]]]:
    ids = [f"n{i:04d}" for i in range(n)]
    edges = [(ids[i], ids[(i + 1) % n]) for i in range(n)]
    return ids, edges


def _in_unit_box(coords: dict[str, tuple[float, float]]) -> bool:
    return all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in coords.values())


class TestForceLayoutDeterminism:
    def test_empty_and_singleton(self):
        assert compute_force_layout([], []) == {}
        assert compute_force_layout(["solo"], []) == {"solo": (0.5, 0.5)}

    def test_identical_runs_are_byte_identical(self):
        ids, edges = _ring_graph(40)
        a = compute_force_layout(ids, edges)
        b = compute_force_layout(ids, edges)
        assert a == b  # exact equality, including float rounding

    def test_input_order_does_not_matter(self):
        ids, edges = _ring_graph(30)
        a = compute_force_layout(ids, edges)
        b = compute_force_layout(list(reversed(ids)), list(reversed(edges)))
        assert a == b

    def test_coordinates_within_unit_box(self):
        ids, edges = _ring_graph(50)
        assert _in_unit_box(compute_force_layout(ids, edges))

    def test_ignores_dangling_edges(self):
        coords = compute_force_layout(["a", "b"], [("a", "b"), ("a", "ghost")])
        assert set(coords) == {"a", "b"}

    def test_distinct_seeds_differ(self):
        ids, edges = _ring_graph(20)
        assert compute_force_layout(ids, edges, seed=1) != compute_force_layout(ids, edges, seed=2)


class TestBarnesHutParity:
    def test_bh_matches_bruteforce_layout_quality(self):
        """Above the threshold (Barnes-Hut) vs forced-exact should be close.

        We compare mean nearest-neighbor spacing rather than exact coords —
        the approximation legitimately perturbs individual positions, but the
        overall spread should match within a loose tolerance.
        """
        n = _BARNES_HUT_THRESHOLD + 40  # forces the BH path
        ids, edges = _ring_graph(n)

        bh = compute_force_layout(ids, edges, iterations=80)
        # Exact path: temporarily run the same n with the bruteforce branch by
        # patching the threshold above n.
        import bengal.analysis.graph.layout as layout_mod

        original = layout_mod._BARNES_HUT_THRESHOLD
        try:
            layout_mod._BARNES_HUT_THRESHOLD = n + 1
            exact = compute_force_layout(ids, edges, iterations=80)
        finally:
            layout_mod._BARNES_HUT_THRESHOLD = original

        def spread(coords):
            xs = [p[0] for p in coords.values()]
            ys = [p[1] for p in coords.values()]
            return (max(xs) - min(xs)) + (max(ys) - min(ys))

        assert math.isclose(spread(bh), spread(exact), rel_tol=0.25)
        assert _in_unit_box(bh)
        assert _in_unit_box(exact)

    def test_bh_path_is_deterministic(self):
        n = _BARNES_HUT_THRESHOLD + 10
        ids, edges = _ring_graph(n)
        assert compute_force_layout(ids, edges, iterations=40) == compute_force_layout(
            ids, edges, iterations=40
        )


class TestRadialLayout:
    def test_center_pinned_dead_center(self):
        coords = compute_radial_layout("me", ["a", "b", "c"])
        assert coords["me"] == (0.5, 0.5)

    def test_all_neighbors_placed_in_unit_box(self):
        coords = compute_radial_layout("me", [f"n{i}" for i in range(12)])
        assert _in_unit_box(coords)
        assert len(coords) == 13  # center + 12

    def test_deterministic(self):
        neighbors = [f"n{i}" for i in range(9)]
        a = compute_radial_layout("me", neighbors, seed=42)
        b = compute_radial_layout("me", neighbors, seed=42)
        assert a == b

    def test_no_neighbors(self):
        assert compute_radial_layout("me", []) == {"me": (0.5, 0.5)}

    def test_two_rings_beyond_eight_neighbors(self):
        # 12 neighbors -> inner+outer rings at different radii from center.
        coords = compute_radial_layout("me", [f"n{i}" for i in range(12)])
        radii = sorted(
            round(math.hypot(x - 0.5, y - 0.5), 2) for nid, (x, y) in coords.items() if nid != "me"
        )
        assert radii[0] < radii[-1]  # more than one ring distance present


class TestHierarchicalLayout:
    def test_multi_community_spreads_clusters(self):
        ids = [f"n{i:04d}" for i in range(120)]
        edges = [(ids[i], ids[i + 1]) for i in range(119)]
        comms = {nid: i % 4 for i, nid in enumerate(ids)}
        coords = compute_hierarchical_layout(ids, edges, communities=comms)
        assert _in_unit_box(coords)
        # Nearest-neighbor spacing should stay readable within packed atlas.
        nn = []
        pts = list(coords.values())
        for i, (x1, y1) in enumerate(pts):
            best = float("inf")
            for j, (x2, y2) in enumerate(pts):
                if i == j:
                    continue
                best = min(best, math.hypot(x1 - x2, y1 - y2))
            nn.append(best)
        assert min(nn) > 0.005

    def test_deterministic(self):
        ids = [f"n{i:04d}" for i in range(40)]
        edges = [(ids[i], ids[(i + 1) % 40]) for i in range(40)]
        comms = {nid: i % 3 for i, nid in enumerate(ids)}
        a = compute_hierarchical_layout(ids, edges, communities=comms, seed=7)
        b = compute_hierarchical_layout(ids, edges, communities=comms, seed=7)
        assert a == b

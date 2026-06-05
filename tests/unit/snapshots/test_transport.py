"""
Tests for snapshot transport helpers (issue #350, saga S2).

Covers MappingProxyType -> plain conversion for the spawn path and graph
immortalization for the fork/copy-on-write path.
"""

from __future__ import annotations

import pickle
from types import MappingProxyType

import pytest

from bengal.snapshots import create_site_snapshot
from bengal.snapshots.transport import (
    immortalize,
    immortalize_snapshot,
    is_immortal,
    proxy_to_plain,
    supports_immortalization,
)


def test_proxy_to_plain_converts_nested_proxies() -> None:
    proxy = MappingProxyType(
        {
            "a": 1,
            "nested": MappingProxyType({"b": 2}),
            "list": [MappingProxyType({"c": 3})],
            "tuple": (MappingProxyType({"d": 4}),),
        }
    )
    plain = proxy_to_plain(proxy)

    assert isinstance(plain, dict)
    assert isinstance(plain["nested"], dict)
    assert isinstance(plain["list"][0], dict)
    assert isinstance(plain["tuple"][0], dict)
    assert plain == {"a": 1, "nested": {"b": 2}, "list": [{"c": 3}], "tuple": ({"d": 4},)}


def test_proxy_to_plain_output_is_picklable() -> None:
    proxy = MappingProxyType({"x": MappingProxyType({"y": [1, 2, 3]})})

    # The proxy itself is NOT picklable...
    with pytest.raises((TypeError, pickle.PicklingError)):
        pickle.dumps(proxy)

    # ...but its plain projection round-trips.
    plain = proxy_to_plain(proxy)
    assert pickle.loads(pickle.dumps(plain)) == {"x": {"y": [1, 2, 3]}}


def test_proxy_to_plain_passes_scalars_through() -> None:
    assert proxy_to_plain(5) == 5
    assert proxy_to_plain("s") == "s"
    assert proxy_to_plain(None) is None


@pytest.mark.skipif(
    not supports_immortalization(),
    reason="interpreter lacks _Py_SetImmortal",
)
def test_immortalize_single_object_freezes_refcount() -> None:
    obj = ["canary"]
    assert not is_immortal(obj)
    assert immortalize(obj) is True
    assert is_immortal(obj)
    # Holding more references must not change the (frozen) refcount sentinel.
    _hold = [obj for _ in range(10)]
    assert is_immortal(obj)
    del _hold


def test_immortalize_unsupported_is_safe_noop() -> None:
    # Always callable without raising, regardless of interpreter support.
    result = immortalize(object())
    assert isinstance(result, bool)


@pytest.mark.bengal(testroot="test-large")
def test_immortalize_snapshot_freezes_frozen_world_only(site, build_site) -> None:
    build_site()
    snapshot = create_site_snapshot(site)

    count = immortalize_snapshot(snapshot)

    if not supports_immortalization():
        assert count == 0
        pytest.skip("interpreter lacks _Py_SetImmortal")

    # The frozen snapshot and a sample page snapshot are immortalized...
    assert count > 0
    assert is_immortal(snapshot)
    assert snapshot.pages
    assert is_immortal(snapshot.pages[0])

    # ...but the traversal must NOT have escaped into the mutable Site graph
    # (reachable via NavTree nodes). The mutable Site and its mutable pages
    # stay mortal so the dev/incremental path is unaffected.
    assert not is_immortal(site)
    if site.pages:
        assert not is_immortal(site.pages[0])

    # Snapshot remains fully usable after immortalization.
    assert snapshot.page_count == len(snapshot.pages)
    assert snapshot.root_section is not None

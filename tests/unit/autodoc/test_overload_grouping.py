"""
Tests for @overload grouping in the Python extractor (#328).

Locks: N overload stubs + the implementation collapse into ONE DocElement that
carries every signature variant under a single stable anchor, with NO duplicate
implementation peer, and round-trips through (de)serialization deterministically.
"""

from __future__ import annotations

from textwrap import dedent

from bengal.autodoc.base import DocElement
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.extractors.python.overloads import collapse_overloads
from bengal.autodoc.models.python import PythonFunctionMetadata
from bengal.rendering.template_functions.autodoc import MemberView


def _method(name: str, decorators: list[str], signature: str, desc: str = "") -> DocElement:
    el = DocElement(
        name=name,
        qualified_name=f"m.C.{name}",
        description=desc,
        element_type="method",
    )
    el.typed_metadata = PythonFunctionMetadata(signature=signature, decorators=tuple(decorators))
    el.metadata = {"decorators": list(decorators), "signature": signature}
    return el


def test_collapse_groups_stubs_and_impl_into_one():
    members = [
        _method("get", ["overload"], "def get(self, k: str) -> str"),
        _method("get", ["typing.overload"], "def get(self, k: int) -> int"),
        _method("get", [], "def get(self, k): ...", desc="Real implementation doc."),
        _method("plain", [], "def plain(self): ..."),
    ]
    collapsed = collapse_overloads(members)

    # Exactly one "get" remains (no duplicate impl peer) plus the untouched method.
    names = [m.name for m in collapsed]
    assert names.count("get") == 1
    assert "plain" in names
    assert len(collapsed) == 2

    get = next(m for m in collapsed if m.name == "get")
    assert get.metadata["is_overloaded"] is True
    # All three variants captured, in source order.
    assert get.metadata["overload_signatures"] == [
        "def get(self, k: str) -> str",
        "def get(self, k: int) -> int",
        "def get(self, k): ...",
    ]
    # The implementation's docstring is the canonical doc.
    assert get.description == "Real implementation doc."


def test_collapse_recognizes_dotted_overload_decorator():
    members = [
        _method("f", ["t.overload"], "def f(self, x: str) -> str"),
        _method("f", ["typing.overload"], "def f(self, x: int) -> int"),
        _method("f", [], "def f(self, x): ..."),
    ]
    collapsed = collapse_overloads(members)
    assert len(collapsed) == 1
    assert collapsed[0].metadata["is_overloaded"] is True
    assert len(collapsed[0].metadata["overload_signatures"]) == 3


def test_non_overloaded_members_are_untouched():
    members = [
        _method("a", [], "def a(self): ..."),
        _method("b", ["property"], "def b(self): ..."),
    ]
    collapsed = collapse_overloads(members)
    assert collapsed == members  # same objects, same order
    assert all("is_overloaded" not in m.metadata for m in collapsed)


def test_stub_only_group_keeps_last_stub_as_carrier():
    # No concrete implementation (e.g. .pyi-style); last stub carries the doc.
    members = [
        _method("g", ["overload"], "def g(x: str) -> str", desc="first"),
        _method("g", ["overload"], "def g(x: int) -> int", desc="last"),
    ]
    collapsed = collapse_overloads(members)
    assert len(collapsed) == 1
    assert collapsed[0].metadata["is_overloaded"] is True
    assert collapsed[0].description == "last"
    assert collapsed[0].metadata["overload_signatures"] == [
        "def g(x: str) -> str",
        "def g(x: int) -> int",
    ]


def test_extractor_end_to_end_class_overload(tmp_path):
    source = tmp_path / "ov.py"
    source.write_text(
        dedent('''
        from typing import overload


        class Store:
            """A store."""

            @overload
            def get(self, key: str) -> str: ...
            @overload
            def get(self, key: int) -> int: ...
            def get(self, key):
                """Get a value by key."""
                return key
        ''')
    )
    extractor = PythonExtractor()
    elements = extractor.extract(source)
    store = elements[0].children[0]
    assert store.name == "Store"

    gets = [c for c in store.children if c.name == "get"]
    # Exactly one collapsed member (single stable anchor), not three peers.
    assert len(gets) == 1
    get = gets[0]
    assert get.metadata.get("is_overloaded") is True
    assert len(get.metadata.get("overload_signatures", [])) == 3
    assert "Get a value by key" in get.description


def test_extractor_end_to_end_module_level_overload(tmp_path):
    source = tmp_path / "modov.py"
    source.write_text(
        dedent('''
        from typing import overload


        @overload
        def parse(x: str) -> str: ...
        @overload
        def parse(x: bytes) -> bytes: ...
        def parse(x):
            """Parse the input."""
            return x


        def helper():
            """A normal function."""
        ''')
    )
    extractor = PythonExtractor()
    elements = extractor.extract(source)
    module = elements[0]

    parses = [c for c in module.children if c.name == "parse"]
    assert len(parses) == 1  # collapsed, no duplicate peers
    assert parses[0].metadata.get("is_overloaded") is True
    assert len(parses[0].metadata.get("overload_signatures", [])) == 3
    # Non-overloaded function still present and untouched.
    helpers = [c for c in module.children if c.name == "helper"]
    assert len(helpers) == 1
    assert "is_overloaded" not in helpers[0].metadata


def test_overload_metadata_round_trips_through_serialization():
    members = [
        _method("get", ["overload"], "def get(self, k: str) -> str"),
        _method("get", ["overload"], "def get(self, k: int) -> int"),
        _method("get", [], "def get(self, k): ...", desc="doc"),
    ]
    collapsed = collapse_overloads(members)[0]
    data = collapsed.to_dict()
    restored = DocElement.from_dict(data)
    assert restored.metadata["is_overloaded"] is True
    assert restored.metadata["overload_signatures"] == [
        "def get(self, k: str) -> str",
        "def get(self, k: int) -> int",
        "def get(self, k): ...",
    ]


def test_member_view_single_anchor_for_overloaded_member():
    members = [
        _method("get", ["overload"], "def get(self, k: str) -> str"),
        _method("get", [], "def get(self, k): ...", desc="doc"),
    ]
    get = collapse_overloads(members)[0]
    get.href = "/api/m/C/get/"
    view = MemberView.from_doc_element(get)
    assert view.is_overloaded is True
    assert view.signature_variants == (
        "def get(self, k: str) -> str",
        "def get(self, k): ...",
    )
    # One stable anchor for the collapsed member.
    assert view.href == "/api/m/C/get/"


def test_member_view_anchor_falls_back_to_qualified_name():
    el = _method("get", [], "def get(self): ...")
    el.href = None
    view = MemberView.from_doc_element(el)
    # No #name collision risk: anchor derives from qualified name when no page href.
    assert view.href == "#m.C.get"

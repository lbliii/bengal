"""
Tests for inherited-member presentation in MemberView (#329).

Extraction of inherited members (synthesize_inherited_members) is already covered
by test_python_extractor.py. These tests lock the PRESENTATION layer: MemberView
must surface is_inherited / inherited_from from the synthetic metadata so the
template can render an attribution badge, and native members must NOT be flagged.
"""

from __future__ import annotations

from textwrap import dedent

from bengal.autodoc.base import DocElement
from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.models.python import PythonFunctionMetadata
from bengal.rendering.template_functions.autodoc import MemberView


def _method(name: str, metadata: dict | None = None) -> DocElement:
    el = DocElement(
        name=name,
        qualified_name=f"pkg.Child.{name}",
        description="A method.",
        element_type="method",
        metadata=metadata or {},
    )
    el.typed_metadata = PythonFunctionMetadata(signature=f"def {name}(self): ...")
    return el


def test_member_view_flags_inherited_member():
    el = _method("save", {"synthetic": True, "inherited_from": "pkg.Base"})
    view = MemberView.from_doc_element(el)
    assert view.is_inherited is True
    assert view.inherited_from == "pkg.Base"


def test_member_view_native_member_not_inherited():
    view = MemberView.from_doc_element(_method("compute", {}))
    # A native member MUST NOT be flagged inherited (otherwise every member would
    # show the badge — the assertion fails if the flag defaults wrong).
    assert view.is_inherited is False
    assert view.inherited_from is None


def test_member_view_inherited_without_explicit_source():
    # synthetic flag set but no inherited_from string: still inherited, no source.
    view = MemberView.from_doc_element(_method("x", {"synthetic": True}))
    assert view.is_inherited is True
    assert view.inherited_from is None


def test_extractor_inherited_members_surface_through_member_view(tmp_path):
    source = tmp_path / "inh.py"
    source.write_text(
        dedent('''
        class Base:
            """Base class."""

            def shared(self) -> None:
                """A shared method."""


        class Child(Base):
            """Child class."""

            def own(self) -> None:
                """A child-only method."""
        ''')
    )
    extractor = PythonExtractor(config={"include_inherited": True})
    elements = extractor.extract(source)
    module = elements[0]
    child = next(c for c in module.children if c.name == "Child")

    by_name = {c.name: c for c in child.children}
    assert "shared" in by_name, "inherited member should be synthesized"
    assert "own" in by_name

    inherited_view = MemberView.from_doc_element(by_name["shared"])
    own_view = MemberView.from_doc_element(by_name["own"])

    assert inherited_view.is_inherited is True
    assert inherited_view.inherited_from == "pkg.Base" or inherited_view.inherited_from.endswith(
        "Base"
    )
    # The class's own method must NOT be flagged inherited.
    assert own_view.is_inherited is False
    assert own_view.inherited_from is None


def test_include_inherited_default_off(tmp_path):
    # Guard: do NOT change include_inherited default. Without the flag, the child
    # must not receive synthesized inherited members.
    source = tmp_path / "inh2.py"
    source.write_text(
        dedent('''
        class Base:
            """Base."""

            def shared(self) -> None:
                """Shared."""


        class Child(Base):
            """Child."""

            def own(self) -> None:
                """Own."""
        ''')
    )
    extractor = PythonExtractor()  # default config: include_inherited False
    elements = extractor.extract(source)
    child = next(c for c in elements[0].children if c.name == "Child")
    names = {c.name for c in child.children}
    assert "own" in names
    assert "shared" not in names, "inherited members must be opt-in (default off)"

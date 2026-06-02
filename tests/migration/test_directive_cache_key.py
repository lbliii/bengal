"""Property/fuzz coverage for the Patitas directive cache key.

Regression guard for the order-sensitive directive-parity flake originally
reproduced under ``--randomly-seed=314926607`` (ROADMAP P1).

Root cause: ``HtmlRenderer._directive_ast_cache_key`` built a structural
fingerprint by probing a hand-picked list of node attributes
(``content``/``code``/``info``/``level``/``url``) and recursing only through
``block.children``. But several patitas node types carry their distinguishing
data elsewhere:

- ``List`` stores items in ``.items`` (not ``.children``) and the
  ordered/start/tight flags as scalars — none were hashed, so every directive
  whose body was a list collided on one key.
- ``ListItem`` carries the task-list ``checked`` flag.
- ``Table``/``TableRow`` use ``.head``/``.body``/``.cells``.
- ``FencedCode`` stores content as source offsets (ZCLH), so two different code
  blocks shared a key.

The global directive cache is enabled by default, so once the colliding key was
populated, later directives served the *first* directive's cached HTML. Whether
that surfaced as a failure depended on test ordering — hence the seed-dependent
flake.

These tests assert the load-bearing invariant directly: **the cache key must
distinguish any two directives that render to different HTML**, and **enabling
the cache must never change rendered output**. They fuzz across the structural
space (lists, tables, code, nesting) where the collision lived.
"""

from __future__ import annotations

import pytest

from bengal.cache.directive_cache import configure_cache, get_cache
from bengal.parsing.backends.patitas import (
    RenderConfig,
    create_markdown,
    render_config_context,
)
from bengal.parsing.backends.patitas.directives.registry import create_default_registry
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer

pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

_PLUGINS = ["table", "strikethrough", "task_lists", "math"]


def _make_md():
    return create_markdown(plugins=_PLUGINS, highlight=False)


def _cache_key(md, registry, source: str) -> str:
    """Compute the directive cache key for the first directive in source."""
    ast = md.parse_to_ast(source)
    directive = ast[0]
    with render_config_context(RenderConfig(highlight=False, directive_registry=registry)):
        renderer = HtmlRenderer(source)
        return renderer._directive_ast_cache_key(directive)


def _render_isolated(md, registry, source: str) -> str:
    """Render a single directive with a guaranteed-empty cache (cache off)."""
    ast = md.parse_to_ast(source)
    with render_config_context(RenderConfig(highlight=False, directive_registry=registry)):
        # No directive_cache passed -> caching path is bypassed entirely.
        return HtmlRenderer(source).render(ast)


# =============================================================================
# Body strategies — explore the structural space where the collision lived
# =============================================================================

_WORDS = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    min_size=1,
    max_size=12,
).filter(lambda s: s.strip() != "")


@st.composite
def _unordered_list(draw) -> str:
    items = draw(st.lists(_WORDS, min_size=1, max_size=4))
    return "\n".join(f"- {item}" for item in items)


@st.composite
def _ordered_list(draw) -> str:
    items = draw(st.lists(_WORDS, min_size=1, max_size=4))
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


@st.composite
def _task_list(draw) -> str:
    items = draw(st.lists(st.tuples(st.booleans(), _WORDS), min_size=1, max_size=4))
    return "\n".join(f"- [{'x' if checked else ' '}] {text}" for checked, text in items)


@st.composite
def _nested_list(draw) -> str:
    top = draw(_WORDS)
    inner = draw(st.lists(_WORDS, min_size=1, max_size=3))
    lines = [f"- {top}"]
    lines += [f"  - {item}" for item in inner]
    return "\n".join(lines)


@st.composite
def _code_block(draw) -> str:
    lang = draw(st.sampled_from(["", "python", "js", "rust"]))
    code = draw(st.lists(_WORDS, min_size=1, max_size=3))
    return "```" + lang + "\n" + "\n".join(code) + "\n```"


@st.composite
def _table(draw) -> str:
    a = draw(_WORDS)
    b = draw(_WORDS)
    return f"| {a} | {b} |\n|---|---|\n| {draw(_WORDS)} | {draw(_WORDS)} |"


@st.composite
def _paragraph(draw) -> str:
    return draw(st.lists(_WORDS, min_size=1, max_size=5).map(" ".join))


_BODY = st.one_of(
    _unordered_list(),
    _ordered_list(),
    _task_list(),
    _nested_list(),
    _code_block(),
    _table(),
    _paragraph(),
)


def _wrap(body: str, name: str = "note") -> str:
    return f":::{{{name}}}\n{body}\n:::\n"


# =============================================================================
# Property: distinct rendered output implies distinct cache key
# =============================================================================


class TestCacheKeyDistinguishesOutput:
    """The cache key must never collapse two differently-rendering directives."""

    @settings(
        max_examples=400,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    @given(body_a=_BODY, body_b=_BODY)
    def test_different_output_implies_different_key(self, body_a: str, body_b: str) -> None:
        """If two note directives render to different HTML, their keys differ.

        This is the core anti-leak invariant: equal keys must imply equal
        rendered output, otherwise the cache will serve stale HTML.
        """
        md = _make_md()
        registry = create_default_registry()

        src_a = _wrap(body_a)
        src_b = _wrap(body_b)

        html_a = _render_isolated(md, registry, src_a)
        html_b = _render_isolated(md, registry, src_b)
        key_a = _cache_key(md, registry, src_a)
        key_b = _cache_key(md, registry, src_b)

        if html_a != html_b:
            assert key_a != key_b, (
                "Directive cache key collision: two directives render to "
                "different HTML but share a cache key. The cached entry for the "
                "first would be served for the second.\n"
                f"  body_a={body_a!r}\n  body_b={body_b!r}\n  key={key_a!r}"
            )

    @settings(max_examples=200, deadline=None)
    @given(body=_BODY)
    def test_same_input_stable_key(self, body: str) -> None:
        """The same directive must always produce the same key (deterministic)."""
        md = _make_md()
        registry = create_default_registry()
        src = _wrap(body)
        assert _cache_key(md, registry, src) == _cache_key(md, registry, src)

    def test_list_variants_have_distinct_keys(self) -> None:
        """Explicit regression: the four list shapes from the failing test.

        These all collided on one key before the fix (seed 314926607).
        """
        md = _make_md()
        registry = create_default_registry()
        sources = {
            "unordered": _wrap("- Item 1\n- Item 2\n- Item 3"),
            "ordered": _wrap("1. First\n2. Second\n3. Third"),
            "nested": _wrap("- Level 1\n  - Level 2\n    - Level 3\n- Back to 1"),
            "task": _wrap("- [ ] Unchecked\n- [x] Checked\n- [ ] Another unchecked"),
        }
        keys = {name: _cache_key(md, registry, src) for name, src in sources.items()}
        assert len(set(keys.values())) == len(keys), f"Colliding keys: {keys}"

    def test_ordered_vs_unordered_distinct(self) -> None:
        """Ordered/unordered toggle must be reflected in the key."""
        md = _make_md()
        registry = create_default_registry()
        unordered = _cache_key(md, registry, _wrap("- a\n- b"))
        ordered = _cache_key(md, registry, _wrap("1. a\n2. b"))
        assert unordered != ordered

    def test_task_checked_state_distinct(self) -> None:
        """Task-list checkbox state must be reflected in the key."""
        md = _make_md()
        registry = create_default_registry()
        unchecked = _cache_key(md, registry, _wrap("- [ ] task"))
        checked = _cache_key(md, registry, _wrap("- [x] task"))
        assert unchecked != checked

    def test_fenced_code_content_distinct(self) -> None:
        """Different fenced-code content (ZCLH offsets) must yield distinct keys."""
        md = _make_md()
        registry = create_default_registry()
        one = _cache_key(md, registry, _wrap("```python\nprint(1)\n```"))
        two = _cache_key(md, registry, _wrap("```python\nprint(2)\n```"))
        assert one != two

    def test_table_cell_content_distinct(self) -> None:
        """Different table cell content must yield distinct keys."""
        md = _make_md()
        registry = create_default_registry()
        one = _cache_key(md, registry, _wrap("| A | B |\n|---|---|\n| 1 | 2 |"))
        two = _cache_key(md, registry, _wrap("| A | B |\n|---|---|\n| 9 | 8 |"))
        assert one != two


# =============================================================================
# Property: enabling the cache must not change output (end-to-end)
# =============================================================================


class TestCacheOnEqualsCacheOff:
    """Rendering a sequence with the cache enabled must equal cache-off output.

    This is the user-visible invariant the original flake violated: a directive
    rendered after another directive returned the earlier one's cached HTML.
    """

    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        # Snapshot + restore global cache enabled-state around each test.
        was_enabled = get_cache().stats().get("enabled", True)
        get_cache().clear()
        yield
        configure_cache(enabled=was_enabled)
        get_cache().clear()

    @settings(
        max_examples=150,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    @given(bodies=st.lists(_BODY, min_size=2, max_size=6))
    def test_sequence_render_matches_isolated(self, bodies: list[str]) -> None:
        """Rendering directives in sequence (cache on) == rendering each alone."""
        md = _make_md()
        registry = create_default_registry()
        sources = [_wrap(body) for body in bodies]

        # Cache-off reference: render each directive with an empty cache.
        expected = [_render_isolated(md, registry, src) for src in sources]

        # Cache-on: render the whole sequence through the global cache, which
        # is consulted via Markdown.__call__ -> _render_ast -> get_cache().
        configure_cache(enabled=True)
        get_cache().clear()
        actual = [md(src) for src in sources]

        assert actual == expected, (
            "Directive cache produced different output than cache-off rendering. "
            "A later directive likely served an earlier directive's cached HTML."
        )

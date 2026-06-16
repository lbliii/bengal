"""Public CSS minifier entry point.

Pipeline: tokenize -> parse rule tree -> (optimize values) -> (structural
rewrites) -> serialize. Every level is guarded at runtime: the engine re-parses
its own output and compares an independent meaning signature against the input.
On any mismatch — or any internal error — it returns the best previously-proven
result (down to the original input), so the minifier can never emit corrupted
CSS. This is what makes the #510 ``@scope … to (`` failure structurally
impossible: ``to (`` and ``to(`` have different signatures, so a bad collapse is
rejected.
"""

from typing import TYPE_CHECKING

from bengal.css.cascade import resolve, surviving_resolve_ok, tree_sig
from bengal.css.config import MinifyLevel
from bengal.css.dead_code import has_removable_dead_code, remove_dead_code_tree
from bengal.css.errors import warn
from bengal.css.nesting import flatten_nesting_tree, has_nested_rules
from bengal.css.optimize import optimize_tree
from bengal.css.parser import parse_stylesheet
from bengal.css.serializer import serialize
from bengal.css.structural import structural_optimize
from bengal.css.tokenizer import tokenize

if TYPE_CHECKING:
    from bengal.css.nodes import Node


def _parse(css: str) -> tuple[Node, ...]:
    return parse_stylesheet(tokenize(css))


def minify_css(
    css: str,
    *,
    level: MinifyLevel | str = MinifyLevel.SAFE,
    flatten_nesting: bool = False,
    remove_dead_code: bool = False,
) -> str:
    """Minify CSS text.

    Args:
        css: The CSS source to minify.
        level: ``"safe"`` (default, lossless), ``"optimize"`` (value
            normalization), or ``"aggressive"`` (cascade-invariant structural
            rewrites). Accepts a :class:`MinifyLevel` or its string value.
        flatten_nesting: When ``True``, de-sugar nested qualified rules into
            flat selectors for legacy browser targets (opt-in; default preserves
            native nesting).
        remove_dead_code: When ``True``, drop unreferenced ``@keyframes``,
            ``@font-face``, and custom-property definitions provable within the
            stylesheet (opt-in; default preserves all definitions).

    Returns:
        Minified CSS, guaranteed to be meaning-preserving. Returns the input
        unchanged if minification cannot be proven safe.
    """
    if not isinstance(css, str):
        warn("css_minifier_invalid_input", input_type=type(css).__name__)
        return str(css) if css else ""
    if not css:
        return css

    lvl = MinifyLevel.coerce(level)
    try:
        in_tree = _parse(css)
        in_sig = tree_sig(in_tree, normalize=False)

        safe_out = serialize(in_tree)
        if tree_sig(_parse(safe_out), normalize=False) != in_sig:
            warn("css_minifier_safe_guard_failed", input_length=len(css))
            return css
        best = safe_out
        pipeline_tree = in_tree

        if flatten_nesting and has_nested_rules(in_tree):
            flat_tree = flatten_nesting_tree(in_tree)
            flat_out = serialize(flat_tree)
            reparsed = _parse(flat_out)
            if not has_nested_rules(reparsed) and resolve(flat_tree, normalize=True) == resolve(
                reparsed, normalize=True
            ):
                best = flat_out
                pipeline_tree = flat_tree
            else:
                warn("css_minifier_nesting_guard_failed", input_length=len(css))

        if remove_dead_code and has_removable_dead_code(pipeline_tree):
            pruned_tree = remove_dead_code_tree(pipeline_tree)
            pruned_out = serialize(pruned_tree)
            reparsed = _parse(pruned_out)
            if surviving_resolve_ok(pipeline_tree, pruned_tree, normalize=True) and (
                surviving_resolve_ok(pipeline_tree, reparsed, normalize=True)
            ):
                best = pruned_out
                pipeline_tree = pruned_tree
            else:
                warn("css_minifier_dead_code_guard_failed", input_length=len(css))

        if lvl in (MinifyLevel.OPTIMIZE, MinifyLevel.AGGRESSIVE):
            opt_tree = optimize_tree(pipeline_tree)
            opt_out = serialize(opt_tree)
            in_norm_sig = tree_sig(in_tree, normalize=True)
            if tree_sig(_parse(opt_out), normalize=True) == in_norm_sig:
                best = opt_out
            else:
                warn("css_minifier_optimize_guard_failed", input_length=len(css))
                return best

        if lvl is MinifyLevel.AGGRESSIVE:
            agg_tree = structural_optimize(optimize_tree(pipeline_tree))
            agg_out = serialize(agg_tree)
            in_resolve = resolve(in_tree, normalize=True)
            if resolve(_parse(agg_out), normalize=True) == in_resolve:
                best = agg_out
            else:
                warn("css_minifier_aggressive_guard_failed", input_length=len(css))

        return best
    except Exception as exc:  # fail-safe: never corrupt output
        warn("css_minifier_failed", error=str(exc), error_type=type(exc).__name__)
        return css

#!/usr/bin/env python3
"""
CSS Minification Syntax Validation Tool

⚠️ NOTE: This is a manual diagnostic script for debugging.
For automated tests, see: tests/unit/core/test_asset_processing.py::TestCSSMinifierUtility

This script validates CSS syntax after minification for manual investigation.
Run with: python3 scripts/test_css_syntax_validation.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.assets.css_minifier import minify_css


def validate_css_syntax(css: str) -> list[str]:
    """Basic CSS syntax validation - check for common issues."""
    issues = []

    # Check for unmatched braces
    open_braces = css.count("{")
    close_braces = css.count("}")
    if open_braces != close_braces:
        issues.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

    # Check for unmatched parentheses
    open_parens = css.count("(")
    close_parens = css.count(")")
    if open_parens != close_parens:
        issues.append(f"Unmatched parentheses: {open_parens} open, {close_parens} close")

    # Check for unmatched brackets
    open_brackets = css.count("[")
    close_brackets = css.count("]")
    if open_brackets != close_brackets:
        issues.append(f"Unmatched brackets: {open_brackets} open, {close_brackets} close")

    # Check for unmatched quotes (simple check)
    single_quotes = css.count("'")
    double_quotes = css.count('"')
    if single_quotes % 2 != 0:
        issues.append(f"Unmatched single quotes: {single_quotes}")
    if double_quotes % 2 != 0:
        issues.append(f"Unmatched double quotes: {double_quotes}")

    # Check for common syntax errors
    if re.search(r"[{}]\s*[{}]", css):
        issues.append("Double braces detected")
    if re.search(r";\s*;", css):
        issues.append("Double semicolons detected")
    if re.search(r":\s*:", css):
        issues.append("Double colons detected")

    return issues


def test_real_world_patterns():
    """Test with real-world CSS patterns that might break."""

    test_cases = [
        # Real-world patterns that could break
        ("Complex selector chain", ".a > .b + .c ~ .d { color: red; }"),
        ("Nested @layer", "@layer a { @layer b { div { color: red; } } }"),
        ("Multiple @imports", '@import "a.css"; @import "b.css"; body { }'),
        ("@media with @layer", "@media (min-width: 768px) { @layer tokens { :root { } } }"),
        ("CSS Grid", "div { display: grid; grid-template-columns: repeat(3, 1fr); }"),
        ("Flexbox", "div { display: flex; gap: 1rem; }"),
        ("Custom properties in calc", ":root { --spacing: calc(1rem + 2px); }"),
        ("Multiple pseudo-classes", "a:hover:focus:active { color: red; }"),
        ("Attribute selector with value", 'input[type="text"] { }'),
        ("Complex :not()", "div:not(.a):not(.b) { }"),
        ("@supports with @layer", "@supports (display: grid) { @layer base { } }"),
        ("URLs with spaces", 'div { background: url("path with spaces.png"); }'),
        ("Color functions", "div { color: rgb(255, 0, 0); background: hsl(0, 100%, 50%); }"),
        ("Transform functions", "div { transform: translate(10px, 20px) rotate(45deg); }"),
        ("Multiple selectors", ".a, .b, .c { color: red; }"),
        ("Descendant selector", ".parent .child { }"),
        ("Adjacent sibling", ".prev + .next { }"),
        ("General sibling", ".sibling ~ .other { }"),
        ("Child combinator", ".parent > .child { }"),
        ("Pseudo-element with content", 'p::before { content: "→"; }'),
        ("@keyframes", "@keyframes fade { from { opacity: 0; } to { opacity: 1; } }"),
        ("@font-face", '@font-face { font-family: "Custom"; src: url("font.woff2"); }'),
        ("CSS nesting with &", ".btn { color: blue; &:hover { color: red; } }"),
        ("Multiple properties", "div { margin: 0; padding: 1rem; border: 1px solid #000; }"),
        ("!important", "div { color: red !important; margin: 0 !important; }"),
        ("Comments in strings", 'div { content: "/* not a comment */"; }'),
        ("Escaped characters", 'div { content: "Say \\"hello\\""; }'),
        ("Unicode in strings", 'div { content: "→ ← ↑ ↓"; }'),
        ("Empty rules", ".empty { } .not-empty { color: red; }"),
        ("Whitespace-only rules", ".whitespace {   }"),
    ]

    print("Testing CSS Minifier with Real-World Patterns")
    print("=" * 60)

    all_passed = True

    for name, css in test_cases:
        try:
            minified = minify_css(css)
            issues = validate_css_syntax(minified)

            if issues:
                print(f"❌ {name}")
                print(f"   Input:  {css[:80]}...")
                print(f"   Output: {minified[:80]}...")
                print(f"   Issues: {', '.join(issues)}")
                all_passed = False
            else:
                print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: Exception - {type(e).__name__}: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_real_world_patterns())

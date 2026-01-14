#!/usr/bin/env python3
"""
CSS Minifier Pattern Analysis Tool

⚠️ NOTE: This is a manual diagnostic script for debugging.
For automated tests, see: tests/unit/core/test_asset_processing.py::TestCSSMinifierUtility

This script analyzes specific CSS patterns that might break during minification.
Run with: python3 scripts/analyze_css_minifier_issues.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.assets.css_minifier import minify_css


def test_problematic_patterns():
    """Test patterns that commonly break CSS minification."""

    test_cases = [
        # Test 1: Spaces around operators in calc()
        ("calc() with spaces", "div { width: calc(100% - 20px); }", "calc(100%-20px)"),
        # Test 2: Spaces in function arguments
        ("function args", "div { transform: translate(10px, 20px); }", "translate(10px,20px)"),
        # Test 3: Spaces around colons in media queries
        ("media query", "@media (min-width: 768px) { }", "@media(min-width:768px)"),
        # Test 4: Spaces in attribute selectors
        ("attribute selector", 'a[href="test"] { }', 'a[href="test"]'),
        # Test 5: Spaces around combinators
        ("> combinator", ".parent > .child { }", ".parent>.child"),
        ("+ combinator", ".prev + .next { }", ".prev+.next"),
        ("~ combinator", ".sibling ~ .other { }", ".sibling~.other"),
        # Test 6: Spaces in pseudo-classes
        (":hover", ".btn:hover { }", ".btn:hover"),
        ("::before", "p::before { }", "p::before"),
        # Test 7: Spaces in @rules
        ("@layer", "@layer tokens { }", "@layer tokens"),
        ("@import", '@import "file.css";', '@import"file.css"'),
        ("@media", "@media screen { }", "@media screen"),
        # Test 8: Spaces around !important
        ("!important", "div { color: red !important; }", "!important"),
        # Test 9: Spaces in color values
        ("hex color", "div { color: #ff0000; }", "#ff0000"),
        ("rgb color", "div { color: rgb(255, 0, 0); }", "rgb(255,0,0)"),
        # Test 10: Spaces in URLs
        ("url()", 'div { background: url("image.png"); }', 'url("image.png")'),
        # Test 11: Spaces around operators
        ("+ operator", "div { margin: 10px + 5px; }", "10px+5px"),
        ("- operator", "div { margin: 10px - 5px; }", "10px-5px"),
        # Test 12: Spaces in custom properties
        ("custom property", ":root { --spacing: 1rem; }", "--spacing:1rem"),
        # Test 13: Spaces in @supports
        ("@supports", "@supports (display: grid) { }", "@supports(display:grid)"),
        # Test 14: Spaces in :not()
        (":not()", "div:not(.hidden) { }", ":not(.hidden)"),
        # Test 15: Spaces in :is()
        (":is()", "div:is(.a, .b) { }", ":is(.a,.b)"),
    ]

    print("Testing CSS Minifier for Problematic Patterns")
    print("=" * 60)

    issues = []

    for name, css, expected_substring in test_cases:
        try:
            minified = minify_css(css)
            if expected_substring not in minified:
                issues.append(f"{name}: Expected '{expected_substring}' not found in '{minified}'")
                print(f"❌ {name}")
                print(f"   Input:  {css}")
                print(f"   Output: {minified}")
                print(f"   Missing: {expected_substring}")
            else:
                print(f"✅ {name}")
        except Exception as e:
            issues.append(f"{name}: Exception - {e}")
            print(f"❌ {name}: Exception - {e}")

    print("\n" + "=" * 60)
    if issues:
        print(f"Found {len(issues)} issues:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(test_problematic_patterns())

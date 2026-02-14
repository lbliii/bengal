#!/usr/bin/env python3
"""
CSS Minification Diagnostic Tool

⚠️ NOTE: This is a manual diagnostic script for debugging.
For automated tests, see: tests/unit/core/test_asset_processing.py::TestCSSMinifierUtility

This script provides verbose output for manual investigation of CSS minification issues.
Run with: python3 scripts/test_css_minification.py
"""

import sys
from pathlib import Path

# Add bengal to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.assets.css_minifier import minify_css


def test_case(
    name: str,
    css: str,
    expected_contains: list[str] | None,
    expected_not_contains: list[str] | None,
):
    """Test a CSS minification case."""
    print(f"\n{'=' * 60}")
    print(f"Test: {name}")
    print(f"{'=' * 60}")
    print(f"\nOriginal CSS ({len(css)} chars):")
    print(css[:200] + ("..." if len(css) > 200 else ""))

    try:
        minified = minify_css(css)
        print(f"\nMinified CSS ({len(minified)} chars):")
        print(minified[:200] + ("..." if len(minified) > 200 else ""))

        # Check expectations
        issues = []
        if expected_contains:
            issues.extend(
                f"Missing expected: {expected}"
                for expected in expected_contains
                if expected not in minified
            )
        if expected_not_contains:
            issues.extend(
                f"Contains unexpected: {unexpected}"
                for unexpected in expected_not_contains
                if unexpected in minified
            )

        if issues:
            print("\n❌ ISSUES FOUND:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n✅ PASSED")
            return True
    except Exception as e:
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run diagnostic tests."""
    print("CSS Minification Diagnostic Tool")
    print("=" * 60)

    results = []

    # Test 1: Basic CSS
    results.append(
        test_case(
            "Basic CSS",
            "body { color: blue; margin: 0; }",
            ["body{", "color:blue", "margin:0"],
            None,
        )
    )

    # Test 2: CSS with comments
    results.append(
        test_case(
            "CSS with comments",
            "/* Comment */ body { color: blue; }",
            ["body{", "color:blue"],
            ["Comment", "/*", "*/"],
        )
    )

    # Test 3: @layer blocks
    results.append(
        test_case(
            "@layer blocks",
            "@layer tokens { :root { --color: blue; } }",
            ["@layer tokens", ":root{", "--color:blue"],
            None,
        )
    )

    # Test 4: CSS nesting
    results.append(
        test_case(
            "CSS nesting",
            ".button { color: blue; &:hover { color: red; } }",
            ["&:hover"],
            None,
        )
    )

    # Test 5: Strings with quotes
    results.append(
        test_case(
            "Strings with quotes",
            'body { font-family: "Helvetica Neue", sans-serif; }',
            ["Helvetica Neue"],
            None,
        )
    )

    # Test 6: Escaped quotes in strings
    results.append(
        test_case(
            "Escaped quotes",
            'body { content: "Say \\"hello\\""; }',
            ['Say "hello"'],
            None,
        )
    )

    # Test 7: CSS functions
    results.append(
        test_case(
            "CSS functions",
            "div { width: calc(100% - 20px); }",
            ["calc(100%-20px)"],
            None,
        )
    )

    # Test 8: Color-mix function (needs space before %)
    results.append(
        test_case(
            "color-mix function",
            "div { color: color-mix(in srgb, red 50%, blue 50%); }",
            ["color-mix(in srgb,red 50%,blue 50%)"],
            None,
        )
    )

    # Test 9: Multiple @layer blocks
    results.append(
        test_case(
            "Multiple @layer blocks",
            "@layer tokens { :root { --color: blue; } } @layer base { body { margin: 0; } }",
            ["@layer tokens", "@layer base"],
            None,
        )
    )

    # Test 10: @import statements
    results.append(
        test_case(
            "@import statements",
            '@import "reset.css"; body { color: blue; }',
            ['@import"reset.css"'],
            None,
        )
    )

    # Test 11: @media queries
    results.append(
        test_case(
            "@media queries",
            "@media (min-width: 768px) { body { font-size: 18px; } }",
            ["@media(min-width:768px)"],
            None,
        )
    )

    # Test 12: CSS custom properties
    results.append(
        test_case(
            "CSS custom properties",
            ":root { --spacing: 1rem; --color: #333; }",
            ["--spacing:1rem", "--color:#333"],
            None,
        )
    )

    # Test 13: Complex selectors
    results.append(
        test_case(
            "Complex selectors",
            ".parent > .child + .sibling { color: blue; }",
            [".parent>.child+.sibling"],
            None,
        )
    )

    # Test 14: Attribute selectors
    results.append(
        test_case(
            "Attribute selectors",
            'a[href^="https"] { color: green; }',
            ['a[href^="https"]'],
            None,
        )
    )

    # Test 15: Pseudo-elements
    results.append(test_case("Pseudo-elements", "p::before { content: ''; }", ["p::before"], None))

    # Test 16: Multiple spaces
    results.append(
        test_case(
            "Multiple spaces",
            "body    {    color:    blue;    }",
            ["body{", "color:blue"],
            None,
        )
    )

    # Test 17: Newlines and tabs
    results.append(
        test_case(
            "Newlines and tabs",
            "body\n{\n\tcolor:\tblue;\n}",
            ["body{", "color:blue"],
            None,
        )
    )

    # Test 18: Empty rules
    results.append(
        test_case(
            "Empty rules",
            ".empty { } .not-empty { color: blue; }",
            [".empty{}", ".not-empty{", "color:blue"],
            None,
        )
    )

    # Test 19: URLs in CSS
    results.append(
        test_case(
            "URLs in CSS",
            'body { background: url("image.png"); }',
            ['url("image.png")'],
            None,
        )
    )

    # Test 20: Multiple comments
    results.append(
        test_case(
            "Multiple comments",
            "/* First */ body { /* Second */ color: blue; /* Third */ }",
            ["body{", "color:blue"],
            ["First", "Second", "Third", "/*", "*/"],
        )
    )

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed < total:
        print("\n❌ Some tests failed - minification may have issues")
        return 1
    else:
        print("\n✅ All tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())

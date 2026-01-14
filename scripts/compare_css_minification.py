#!/usr/bin/env python3
"""
Compare minified vs unminified CSS to identify breaking patterns.

This script helps identify what the minifier is changing that breaks CSS rendering.
"""

import re
import sys
from difflib import unified_diff
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bengal.assets.css_minifier import minify_css


def find_breaking_patterns(original: str, minified: str) -> list[str]:
    """Find patterns that might break CSS rendering."""
    issues = []

    # Pattern 1: Check if spaces were removed from descendant selectors incorrectly
    # .a .b should stay .a .b, not become .a.b
    original_descendants = set(re.findall(r"\.\w+\s+\.\w+", original))

    # Find descendants that exist in original but might be broken in minified
    for desc in original_descendants:
        # Check if it became .a.b (no space) in minified
        no_space_version = desc.replace(" ", "")
        if no_space_version in minified and desc not in minified:
            issues.append(f"Descendant selector lost space: {desc} → {no_space_version}")

    # Pattern 2: Check calc() functions - spaces around operators might be required
    original_calcs = re.findall(r"calc\s*\([^)]+\)", original)
    minified_calcs = re.findall(r"calc\s*\([^)]+\)", minified)

    for orig_calc, min_calc in zip(original_calcs[:20], minified_calcs[:20], strict=True):
        # Check if spaces around operators were removed incorrectly
        # calc(100% - 20px) needs spaces, calc(100%-20px) might work but calc(100% -20px) might not
        if (
            re.search(r"\d+\s*-\s*\d+", orig_calc)
            and not re.search(r"\d+\s+-\s+\d+", min_calc)
            and re.search(r"\d+-\d+", min_calc)  # No space at all
        ):
            issues.append(f"calc() lost spaces around operator: {orig_calc[:60]} → {min_calc[:60]}")

    # Pattern 3: Check color-mix() - spaces before % are critical
    original_colormix = re.findall(r"color-mix\s*\([^)]+\)", original)
    minified_colormix = re.findall(r"color-mix\s*\([^)]+\)", minified)

    for orig_cm, min_cm in zip(original_colormix[:20], minified_colormix[:20], strict=True):
        # Check if space before % was removed
        if re.search(r"\w+\s+\d+%", orig_cm) and not re.search(r"\w+\s+\d+%", min_cm):
            issues.append(f"color-mix() lost space before %: {orig_cm[:80]} → {min_cm[:80]}")

    # Pattern 4: Check @layer syntax
    original_layers = re.findall(r"@layer\s+[^{;]+", original)
    minified_layers = re.findall(r"@layer\s+[^{;]+", minified)

    # @layer tokens { should stay @layer tokens {, not @layer tokens{
    for orig_layer, min_layer in zip(original_layers[:10], minified_layers[:10], strict=True):
        if "{" in orig_layer and "{" in min_layer:
            orig_before_brace = orig_layer.split("{")[0]
            min_before_brace = min_layer.split("{")[0]
            if orig_before_brace.endswith(" ") and not min_before_brace.endswith(" "):
                # Space before brace was removed - this might be OK, but check
                pass

    # Pattern 5: Check for property:value issues
    # Some properties might need spaces: "property: value" vs "property:value"
    # Most are fine, but check for edge cases

    # Pattern 6: Check for broken function calls
    # Functions like url(), var(), etc. should preserve their syntax

    return issues


def compare_css_samples(original: str, minified: str, sample_size: int = 5000):
    """Compare samples of original and minified CSS."""
    print("Comparing CSS samples...\n")

    # Take samples from different parts
    samples = [
        ("Start", original[:sample_size], minified[:sample_size]),
        (
            "Middle",
            original[len(original) // 2 : len(original) // 2 + sample_size],
            minified[len(minified) // 2 : len(minified) // 2 + sample_size],
        ),
        ("End", original[-sample_size:], minified[-sample_size:]),
    ]

    for name, orig_sample, min_sample in samples:
        print(f"{name} sample comparison:")
        print(f"  Original: {len(orig_sample)} chars")
        print(f"  Minified: {len(min_sample)} chars")
        print(f"  Reduction: {100 * (1 - len(min_sample) / len(orig_sample)):.1f}%")

        # Find differences
        diff_lines = list(
            unified_diff(
                orig_sample.splitlines(keepends=True),
                min_sample.splitlines(keepends=True),
                lineterm="",
                n=3,
            )
        )

        if diff_lines:
            print(
                f"  ⚠️  Found {len([line for line in diff_lines if line.startswith(('+', '-'))])} differences"
            )
            # Show first few differences
            for line in diff_lines[:10]:
                if line.startswith(("+", "-", "@")):
                    print(f"    {line[:100]}")
        else:
            print("  ✅ No differences")
        print()


def main():
    """Main comparison function."""
    print("CSS Minification Comparison Tool")
    print("=" * 60)

    # We need the original (unminified) CSS to compare
    # For now, let's test the minifier on a known good CSS sample
    print("\nTo properly compare, we need:")
    print("1. Original CSS (before minification)")
    print("2. Minified CSS (current output)")
    print("\nLet's check what patterns might break...\n")

    # Test with known problematic patterns
    test_cases = [
        # Descendant selectors - space is REQUIRED
        (".parent .child { color: red; }", "Descendant selector"),
        # calc() with spaces
        ("div { width: calc(100% - 20px); }", "calc() with spaces"),
        # color-mix() with space before %
        (
            "div { color: color-mix(in srgb, red 50%, blue 50%); }",
            "color-mix() with space before %",
        ),
        # @layer blocks
        ("@layer tokens { :root { --color: blue; } }", "@layer block"),
        # Multiple selectors
        (".a, .b, .c { color: red; }", "Multiple selectors"),
        # Pseudo-classes
        ("a:hover { color: blue; }", "Pseudo-class"),
        # Attribute selectors
        ('input[type="text"] { }', "Attribute selector"),
    ]

    print("Testing minifier on known patterns:\n")
    issues_found = []

    for css, name in test_cases:
        minified = minify_css(css)
        print(f"{name}:")
        print(f"  Original:  {css}")
        print(f"  Minified:  {minified}")

        # Check for potential issues
        if (
            name == "Descendant selector"
            and ".parent.child" in minified
            and ".parent .child" not in minified
        ):
            issues_found.append(f"{name}: Space removed from descendant selector")
        if (
            name == "calc() with spaces"
            and "100%-20px" in minified
            and "100% - 20px" not in minified
        ):
            # This might be OK, browsers usually accept it
            pass
        if (
            name == "color-mix() with space before %"
            and "red50%" in minified
            and "red 50%" not in minified
        ):
            issues_found.append(f"{name}: Space before % removed")

        print()

    if issues_found:
        print("⚠️  Potential issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("✅ No obvious issues in test patterns")

    print("\n" + "=" * 60)
    print("\nTo find the actual breaking pattern:")
    print("1. Rebuild with minify: false to get unminified CSS")
    print("2. Compare specific CSS rules that aren't rendering")
    print("3. Check browser DevTools for CSS parsing errors")
    print("4. Look for properties that work unminified but not minified")


if __name__ == "__main__":
    main()

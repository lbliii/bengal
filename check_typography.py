#!/usr/bin/env python3
"""
Comprehensive typography diagnostic script.
Checks all text size attributes and their resolution.
"""

from pathlib import Path
import re
import sys

def check_css_file(css_path: Path):
    """Check a CSS file for typography issues."""
    if not css_path.exists():
        print(f"❌ CSS file not found: {css_path}")
        return False
    
    css = css_path.read_text()
    issues = []
    
    print(f"📄 Checking: {css_path}")
    print("=" * 70)
    
    # 1. Check @layer blocks
    layer_count = css.count("@layer tokens")
    print(f"\n1. @layer tokens blocks: {layer_count}")
    if layer_count == 0:
        issues.append("No @layer tokens blocks found")
    else:
        print("   ✅ @layer blocks present")
    
    # 2. Check typography variable definitions
    print("\n2. Typography Variable Definitions:")
    required_vars = [
        "--font-size-xs", "--font-size-sm", "--font-size-base",
        "--font-size-lg", "--font-size-xl", "--font-size-2xl",
        "--font-size-3xl", "--font-size-4xl", "--font-size-5xl", "--font-size-6xl"
    ]
    
    for var in required_vars:
        if f"{var}:" in css:
            # Get the value
            match = re.search(f'{var}:\\s*([^;]+);', css)
            if match:
                value = match.group(1).strip()
                if "clamp" in value:
                    print(f"   ✅ {var} = {value[:60]}...")
                else:
                    print(f"   ⚠️  {var} = {value[:60]}... (not clamp)")
            else:
                print(f"   ❌ {var} defined but no value found")
                issues.append(f"{var} has no value")
        else:
            print(f"   ❌ {var} NOT DEFINED")
            issues.append(f"{var} not defined")
    
    # 3. Check semantic variable definitions
    print("\n3. Semantic Variable Definitions:")
    semantic_vars = [
        "--text-body", "--text-h1", "--text-h2", "--text-h3",
        "--text-h4", "--text-h5", "--text-h6", "--text-lead"
    ]
    
    for var in semantic_vars:
        if f"{var}:" in css:
            match = re.search(f'{var}:\\s*var\\(([^)]+)\\)', css)
            if match:
                ref = match.group(1)
                print(f"   ✅ {var} = var({ref})")
                
                # Verify the reference exists
                if f"{ref}:" not in css:
                    print(f"      ❌ But {ref} is NOT DEFINED!")
                    issues.append(f"{var} references undefined {ref}")
            else:
                print(f"   ⚠️  {var} defined but doesn't reference var()")
        else:
            print(f"   ❌ {var} NOT DEFINED")
            issues.append(f"{var} not defined")
    
    # 4. Check variable usage in selectors
    print("\n4. Variable Usage in Selectors:")
    selectors_to_check = [
        ("body", "--text-body"),
        ("h1", "--text-h1"),
        ("h2", "--text-h2"),
        ("h3", "--text-h3"),
    ]
    
    for selector, var in selectors_to_check:
        pattern = f'{selector}\\s*\\{{[^}}]*font-size[^}}]*var\\({var[2:]}\\)[^}}]*\\}}'
        matches = re.findall(pattern, css, re.DOTALL)
        if matches:
            print(f"   ✅ {selector} uses {var}")
        else:
            # Check if it uses font-size at all
            pattern2 = f'{selector}\\s*\\{{[^}}]*font-size[^}}]*\\}}'
            matches2 = re.findall(pattern2, css, re.DOTALL)
            if matches2:
                print(f"   ⚠️  {selector} has font-size but not {var}")
                issues.append(f"{selector} doesn't use {var}")
            else:
                print(f"   ❌ {selector} has no font-size rule")
                issues.append(f"{selector} has no font-size")
    
    # 5. Check variable resolution chains
    print("\n5. Variable Resolution Chains:")
    chains = [
        ("--text-h1", "--font-size-5xl"),
        ("--text-body", "--font-size-base"),
    ]
    
    for semantic, foundation in chains:
        # Check semantic -> foundation
        match1 = re.search(f'{semantic}:\\s*var\\(([^)]+)\\)', css)
        if match1 and match1.group(1) == foundation:
            # Check foundation -> clamp
            match2 = re.search(f'{foundation}:\\s*([^;]+);', css)
            if match2 and "clamp" in match2.group(1):
                print(f"   ✅ {semantic} → {foundation} → clamp()")
            else:
                print(f"   ⚠️  {semantic} → {foundation} but foundation not clamp")
                issues.append(f"{semantic} chain broken at {foundation}")
        else:
            print(f"   ❌ {semantic} doesn't reference {foundation}")
            issues.append(f"{semantic} chain broken")
    
    # Summary
    print("\n" + "=" * 70)
    if issues:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ All checks passed! Typography should work correctly.")
        return True

def main():
    """Main diagnostic function."""
    print("🔍 Bengal Typography Diagnostic Tool")
    print("=" * 70)
    
    # Check built CSS
    css_path = Path("site/public/assets/css/style.css")
    if not css_path.exists():
        print(f"\n❌ Built CSS not found at {css_path}")
        print("   Run: python -m bengal.cli site build")
        return 1
    
    success = check_css_file(css_path)
    
    # Additional checks
    print("\n" + "=" * 70)
    print("6. Additional Checks:")
    
    # Check HTML references
    html_path = Path("site/public/index.html")
    if html_path.exists():
        html = html_path.read_text()
        if 'href="/assets/css/style.css"' in html or 'href="/assets/css/style.' in html:
            print("   ✅ HTML references CSS file")
        else:
            print("   ⚠️  HTML CSS reference not found")
    
    # Check file size
    css_size = css_path.stat().st_size
    print(f"   CSS file size: {css_size:,} bytes ({css_size/1024:.1f} KB)")
    if css_size < 1000:
        print("   ⚠️  CSS file seems too small")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())


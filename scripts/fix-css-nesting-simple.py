#!/usr/bin/env python3
"""
Simple, reliable CSS nesting converter using regex.

Converts CSS nesting to traditional selectors that work everywhere.
"""

import re
import sys
from pathlib import Path


def transform_css_nesting(content: str) -> str:
    """
    Transform CSS nesting using regex - simple and reliable.
    
    Strategy:
    1. Find all rule blocks: "selector { ... }"
    2. Within each block, find nested "&:selector { ... }" patterns
    3. Extract and transform them to "parent:selector { ... }"
    """
    result = content
    
    # Pattern to match a CSS rule block (handles nested braces)
    # Captures: (selector, content_with_nesting)
    rule_pattern = r'([^{]+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    def transform_rule(match):
        selector = match.group(1).strip()
        block_content = match.group(2)
        
        # Skip @rules (they handle their own nesting)
        if selector.strip().startswith('@'):
            return match.group(0)
        
        # Clean @layer prefixes but preserve the layer declaration
        selector_clean = re.sub(r'^@layer\s+\w+\s*', '', selector).strip()
        has_layer = selector.strip().startswith('@layer')
        layer_decl = ''
        if has_layer:
            layer_match = re.match(r'(@layer\s+\w+)\s*', selector)
            if layer_match:
                layer_decl = layer_match.group(1) + ' '
        
        if not selector_clean or selector_clean.startswith('@'):
            return match.group(0)
        
        # Find all nested & selectors in the block
        # Pattern: & followed by :, ::, ., [, or identifier
        nested_pattern = r'&\s*([:.#\[\w\s-]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        nested_rules = []
        remaining_content = block_content
        
        def extract_nested(m):
            nested_selector_part = m.group(1).strip()
            nested_block = m.group(2)
            
            # Build full selector
            if nested_selector_part.startswith(':'):
                # &:hover, &::before
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith('.'):
                # &.class
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith('['):
                # &[attr]
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith(' '):
                # & .child (descendant)
                full_selector = selector_clean + nested_selector_part
            else:
                # &child (compound) or other
                full_selector = selector_clean + nested_selector_part
            
            # Preserve @layer if present
            if has_layer:
                nested_rules.append(f"{layer_decl}{full_selector} {{{nested_block}}}")
            else:
                nested_rules.append(f"{full_selector} {{{nested_block}}}")
            return ""  # Remove from original block
        
        # Extract all nested rules
        remaining_content = re.sub(nested_pattern, extract_nested, remaining_content, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        remaining_content = re.sub(r'\n\s*\n\s*\n', '\n\n', remaining_content)
        
        # Reconstruct: original selector with remaining content, then nested rules
        if nested_rules:
            return f"{selector}{{{remaining_content}}}\n" + "\n".join(nested_rules)
        else:
            return match.group(0)
    
    # Process all rule blocks (iterate to handle deeply nested cases)
    max_iterations = 10
    for _ in range(max_iterations):
        new_result = re.sub(rule_pattern, transform_rule, result, flags=re.MULTILINE | re.DOTALL)
        if new_result == result:
            break
        result = new_result
    
    return result


def process_file(file_path: Path) -> bool:
    """Process a single CSS file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Check if file has nesting
        if not re.search(r'&\s*[:.\[#\w]', content):
            return False
        
        transformed = transform_css_nesting(content)
        
        if transformed != content:
            file_path.write_text(transformed, encoding='utf-8')
            print(f"✓ Fixed: {file_path}")
            return True
        
        return False
    except Exception as e:
        print(f"✗ Error: {file_path}: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:]]
    else:
        css_dir = Path('bengal/themes/default/assets/css')
        files = list(css_dir.rglob('*.css'))
    
    changed = 0
    for file_path in files:
        if process_file(file_path):
            changed += 1
    
    print(f"\n{'No' if changed == 0 else 'Fixed'} files.")


if __name__ == '__main__':
    main()


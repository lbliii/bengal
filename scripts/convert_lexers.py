#!/usr/bin/env python3
"""Script to convert regex lexers to state machine lexers.

This script:
1. Extracts language data (keywords, operators, etc.) from existing lexers
2. Classifies languages by family (comment style, string syntax)
3. Generates state machine lexers using appropriate mixins

Usage:
    python scripts/convert_lexers.py --analyze     # Show what would be converted
    python scripts/convert_lexers.py --generate    # Generate all lexers
    python scripts/convert_lexers.py --generate rust  # Generate single lexer
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

LEXERS_DIR = Path(__file__).parent.parent / "bengal/rendering/rosettes/lexers"


@dataclass
class LexerSpec:
    """Extracted specification from a regex lexer."""

    name: str
    aliases: tuple[str, ...]
    filenames: tuple[str, ...]
    mimetypes: tuple[str, ...]

    # Comment style
    comment_family: str  # "c_style", "hash", "sql", "lisp", "lua", "haskell", "markup", "none"

    # Extracted data
    keywords: frozenset[str] = field(default_factory=frozenset)
    keyword_constants: frozenset[str] = field(default_factory=frozenset)
    keyword_declarations: frozenset[str] = field(default_factory=frozenset)
    keyword_namespace: frozenset[str] = field(default_factory=frozenset)
    types: frozenset[str] = field(default_factory=frozenset)
    builtins: frozenset[str] = field(default_factory=frozenset)
    exceptions: frozenset[str] = field(default_factory=frozenset)

    # Operators (extracted from rules)
    operators_3char: frozenset[str] = field(default_factory=frozenset)
    operators_2char: frozenset[str] = field(default_factory=frozenset)
    operators_1char: frozenset[str] = field(default_factory=frozenset)

    # String syntax
    has_single_quote: bool = True
    has_double_quote: bool = True
    has_backtick: bool = False
    has_triple_quote: bool = False
    string_prefixes: frozenset[str] = field(default_factory=frozenset)

    # Number syntax
    has_underscore_sep: bool = True
    integer_suffixes: tuple[str, ...] = ()
    float_suffixes: tuple[str, ...] = ()
    imaginary_suffix: str | None = None

    # Special features
    special_features: list[str] = field(default_factory=list)


def classify_comment_style(source: str) -> str:
    """Determine comment style from lexer source."""
    if "//.*$" in source and "/\\*" in source:
        return "c_style"
    if "#.*$" in source and "/\\*" not in source:
        return "hash"
    if "--.*$" in source and "/\\*" in source:
        return "sql"
    if "--.*$" in source and "{-" in source:
        return "haskell"
    if "--.*$" in source and "--\\[\\[" in source:
        return "lua"
    if ";.*$" in source:
        return "lisp"
    if "<!--" in source:
        return "markup"
    if "<#" in source and "#>" in source:
        return "powershell"
    return "none"


def extract_tuple_constant(source: str, name: str) -> tuple[str, ...]:
    """Extract a tuple constant like _KEYWORDS from source."""
    # Look for pattern: _NAME = (\n    "word",\n    ...)
    pattern = rf"{name}\s*=\s*\(([\s\S]*?)\)"
    match = re.search(pattern, source)
    if not match:
        return ()

    content = match.group(1)
    # Extract quoted strings
    strings = re.findall(r'"([^"]+)"', content)
    return tuple(strings)


def extract_operators_from_rules(
    source: str,
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Extract operators from Rule patterns."""
    ops_3 = set()
    ops_2 = set()
    ops_1 = set()

    # Find operator patterns in rules
    # Look for patterns like r"===|!==|>>>" or r"[+\-*/%]"
    operator_patterns = re.findall(
        r'Rule\(re\.compile\(r["\']([^"\']+)["\'].*?TokenType\.OPERATOR', source
    )

    for pattern in operator_patterns:
        # Handle alternation patterns like "===|!==|>>>"
        if "|" in pattern and not pattern.startswith("["):
            for op in pattern.split("|"):
                op = op.strip()
                if len(op) >= 3:
                    ops_3.add(op)
                elif len(op) == 2:
                    ops_2.add(op)
                elif len(op) == 1:
                    ops_1.add(op)

        # Handle character class patterns like "[+\-*/%]"
        char_class = re.search(r"\[([^\]]+)\]", pattern)
        if char_class:
            chars = char_class.group(1).replace("\\", "")
            for c in chars:
                if c.isascii() and not c.isalnum():
                    ops_1.add(c)

    return frozenset(ops_3), frozenset(ops_2), frozenset(ops_1)


def analyze_lexer(path: Path) -> LexerSpec | None:
    """Analyze a lexer file and extract its specification."""
    source = path.read_text()

    # Skip base classes and already-converted files
    if "_sm.py" in path.name or path.name.startswith("_"):
        return None

    # Extract class name and metadata
    class_match = re.search(r"class (\w+Lexer)\(PatternLexer\):", source)
    if not class_match:
        return None

    # Extract metadata
    name_match = re.search(r'name\s*=\s*"([^"]+)"', source)
    aliases_match = re.search(r"aliases\s*=\s*\(([^)]*)\)", source)
    filenames_match = re.search(r"filenames\s*=\s*\(([^)]*)\)", source)

    name = name_match.group(1) if name_match else path.stem
    aliases = tuple(re.findall(r'"([^"]+)"', aliases_match.group(1))) if aliases_match else ()
    filenames = tuple(re.findall(r'"([^"]+)"', filenames_match.group(1))) if filenames_match else ()

    # Classify comment style
    comment_family = classify_comment_style(source)

    # Extract keywords and builtins
    keywords = frozenset(extract_tuple_constant(source, "_KEYWORDS"))
    types = frozenset(extract_tuple_constant(source, "_TYPES"))
    builtins = frozenset(extract_tuple_constant(source, "_BUILTINS"))
    constants = frozenset(extract_tuple_constant(source, "_CONSTANTS"))
    exceptions = frozenset(extract_tuple_constant(source, "_EXCEPTIONS"))
    reserved = frozenset(extract_tuple_constant(source, "_RESERVED"))

    # Combine keywords with reserved
    all_keywords = keywords | reserved

    # Extract operators
    ops_3, ops_2, ops_1 = extract_operators_from_rules(source)

    # Detect string features
    has_triple_quote = '"""' in source or "'''" in source
    has_backtick = "`" in source and "backtick" not in source.lower()  # Template literals
    string_prefixes = frozenset()
    if re.search(r"\[fFrRbBuU\]", source):
        string_prefixes = frozenset("fFrRbBuU")

    # Detect number features
    imaginary = None
    if re.search(r"\d+[jJ]", source) or "imaginary" in source.lower():
        imaginary = "j"
    if re.search(r"\d+i[^a-z]", source):
        imaginary = "i"

    int_suffixes = ()
    if "BigInt" in source or re.search(r"\d+n\b", source):
        int_suffixes = ("n",)
    if re.search(r"i8|i16|i32|i64|u8|u16|u32|u64", source):
        int_suffixes = (
            "i8",
            "i16",
            "i32",
            "i64",
            "i128",
            "isize",
            "u8",
            "u16",
            "u32",
            "u64",
            "u128",
            "usize",
        )

    float_suffixes = ()
    if re.search(r"f32|f64", source):
        float_suffixes = ("f32", "f64")

    # Detect special features
    special = []
    if "@" in source and "decorator" in source.lower():
        special.append("decorators")
    if "'" in source and "lifetime" in source.lower():
        special.append("lifetimes")
    if "#[" in source or "#!" in source:
        special.append("attributes")
    if "=>" in source and "arrow" in source.lower():
        special.append("arrow_functions")
    if "macro" in source.lower():
        special.append("macros")

    return LexerSpec(
        name=name,
        aliases=aliases,
        filenames=filenames,
        mimetypes=(),
        comment_family=comment_family,
        keywords=all_keywords,
        keyword_constants=constants,
        types=types,
        builtins=builtins,
        exceptions=exceptions,
        operators_3char=ops_3,
        operators_2char=ops_2,
        operators_1char=ops_1,
        has_triple_quote=has_triple_quote,
        has_backtick=has_backtick,
        string_prefixes=string_prefixes,
        integer_suffixes=int_suffixes,
        float_suffixes=float_suffixes,
        imaginary_suffix=imaginary,
        special_features=special,
    )


def analyze_all_lexers() -> dict[str, LexerSpec]:
    """Analyze all lexers in the directory."""
    specs = {}
    for path in sorted(LEXERS_DIR.glob("*.py")):
        if path.name.startswith("_") or "_sm" in path.name:
            continue
        spec = analyze_lexer(path)
        if spec:
            specs[spec.name] = spec
    return specs


def print_analysis():
    """Print analysis of all lexers."""
    specs = analyze_all_lexers()

    # Group by comment family
    families: dict[str, list[str]] = {}
    for name, spec in specs.items():
        families.setdefault(spec.comment_family, []).append(name)

    print("=" * 70)
    print("LEXER ANALYSIS")
    print("=" * 70)
    print(f"\nTotal lexers: {len(specs)}")

    print("\n## By Comment Family\n")
    for family, names in sorted(families.items(), key=lambda x: -len(x[1])):
        print(f"{family:12} ({len(names):2}): {', '.join(sorted(names))}")

    print("\n## Mixin Requirements\n")
    for name, spec in sorted(specs.items()):
        mixins = []
        if spec.comment_family == "c_style":
            mixins.append("CStyleCommentsMixin")
        elif spec.comment_family == "hash":
            mixins.append("HashCommentsMixin")
        else:
            mixins.append(f"custom:{spec.comment_family}")

        mixins.append("CStyleNumbersMixin")
        mixins.append("CStyleStringsMixin")

        features = []
        if spec.has_triple_quote:
            features.append("triple-quote")
        if spec.has_backtick:
            features.append("backtick")
        if spec.imaginary_suffix:
            features.append(f"imaginary({spec.imaginary_suffix})")
        if spec.special_features:
            features.extend(spec.special_features)

        feat_str = f" [{', '.join(features)}]" if features else ""
        print(f"  {name:15} → {' + '.join(mixins)}{feat_str}")

    print("\n## Complexity Estimate\n")
    easy = [
        n
        for n, s in specs.items()
        if s.comment_family in ("c_style", "hash") and not s.special_features
    ]
    medium = [
        n
        for n, s in specs.items()
        if s.comment_family in ("c_style", "hash") and s.special_features
    ]
    hard = [n for n, s in specs.items() if s.comment_family not in ("c_style", "hash", "none")]

    print(f"  Easy   ({len(easy):2}): Standard C/hash comments, no special features")
    print(
        f"  Medium ({len(medium):2}): Standard comments + special features (decorators, macros, etc.)"
    )
    print(f"  Hard   ({len(hard):2}): Non-standard comment syntax or special parsing needs")

    return specs


# =============================================================================
# Template for generating lexers
# =============================================================================

LEXER_TEMPLATE = '''"""Hand-written {name_title} lexer using composable scanner mixins.

O(n) guaranteed, zero regex, thread-safe.
"""

from __future__ import annotations

from collections.abc import Iterator

from bengal.rendering.rosettes._types import Token, TokenType
from bengal.rendering.rosettes.lexers._state_machine import StateMachineLexer
from bengal.rendering.rosettes.lexers._scanners import (
{mixin_imports}
)

__all__ = ["{class_name}"]


# Language-specific data
{keyword_definitions}


class {class_name}(
{mixin_classes}
    StateMachineLexer,
):
    """{name_title} lexer using composable mixins."""

    name = "{name}"
    aliases = {aliases}
    filenames = {filenames}
    mimetypes = {mimetypes}

{config_definitions}

    def tokenize(self, code: str) -> Iterator[Token]:
        """Tokenize {name_title} source code."""
        pos = 0
        length = len(code)
        line = 1
        line_start = 0

        while pos < length:
            char = code[pos]
            col = pos - line_start + 1

{tokenize_body}

            # Unknown
            yield Token(TokenType.ERROR, char, line, col)
            pos += 1

{helper_methods}
'''


def generate_lexer(spec: LexerSpec) -> str:
    """Generate a state machine lexer from a spec."""
    # This would be filled in with the actual generation logic
    # For now, return a placeholder
    return f"# TODO: Generate {spec.name} lexer\n"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] == "--analyze":
        print_analysis()
    elif sys.argv[1] == "--generate":
        if len(sys.argv) > 2:
            # Generate specific lexer
            name = sys.argv[2]
            specs = analyze_all_lexers()
            if name in specs:
                print(generate_lexer(specs[name]))
            else:
                print(f"Unknown lexer: {name}")
        else:
            # Generate all
            print("Would generate all lexers...")
    else:
        print(__doc__)

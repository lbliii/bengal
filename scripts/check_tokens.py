import sys

from bengal.rendering.parsers.patitas.lexer import Lexer


def print_tokens(markdown_input):
    print(f"Markdown: '{markdown_input.replace('\\n', '\\\\n')}'")
    lexer = Lexer(markdown_input)
    for token in lexer.tokenize():
        print(
            f"  {token.type.name}: '{token.value.replace('\\n', '\\\\n')}' (indent={token.line_indent}, offset={token.location.offset})"
        )
    print()


if len(sys.argv) > 1:
    print_tokens(sys.argv[1].replace("\\n", "\n"))
else:
    # Example 230
    print_tokens("   > # Foo\n   > bar\n > baz\n")

    # Example 237
    print_tokens("> ```\nfoo\n```\n")

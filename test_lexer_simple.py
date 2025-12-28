#!/usr/bin/env python3
import sys

sys.path.insert(0, ".")

from bengal.rendering.parsers.patitas.lexer import Lexer

# Use a raw string to avoid shell interpretation
source = r"```" + "\n" + "code" + "\n" + r"```"
print(f"Source: {repr(source)}")
print(f"Length: {len(source)}")

lexer = Lexer(source)
tokens = []
for i, token in enumerate(lexer.tokenize()):
    tokens.append(token)
    print(f"{i}: {token.type.name} = {repr(token.value[:30])}")
    if i >= 10:
        print("STOPPING - too many tokens")
        break

print(f"\nTotal: {len(tokens)} tokens")

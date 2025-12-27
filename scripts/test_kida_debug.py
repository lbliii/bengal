#!/usr/bin/env python3
"""Debug Kida block compilation."""

import sys

sys.path.insert(0, "/Users/llane/Documents/github/python/bengal")

from bengal.rendering.kida.compiler import Compiler
from bengal.rendering.kida.parser import Parser

# Simple parent template
parent_src = """<!DOCTYPE html>
<html>
<body>
{% block content %}DEFAULT{% endblock %}
</body>
</html>"""

# Parse and compile
parser = Parser()
ast = parser.parse(parent_src)
print("=== AST ===")
print(ast)

compiler = Compiler()
code = compiler.compile(ast, filename="parent.html")
print("\n=== Generated Python ===")
import ast as pyast

print(pyast.unparse(code))

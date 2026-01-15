from bengal.parsing.backends.patitas import parse

markdown = "> # Foo\n> bar\n> baz\n"
html = parse(markdown)
print(f"Markdown:\n{markdown}")
print(f"HTML:\n{html}")

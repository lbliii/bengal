from bengal.rendering.parsers.patitas import parse

markdown = "> ```\nfoo\n```\n"
html = parse(markdown)
print(f"Markdown:\n{markdown}")
print(f"HTML:\n{html}")

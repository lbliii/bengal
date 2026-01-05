from bengal.rendering.parsers.patitas.parser import Parser

markdown = "   > > 1.  one\n>>\n>>     two\n"
parser = Parser(markdown)
blocks = parser.parse()


def dump_node(node, indent=0):
    print("  " * indent + f"{type(node).__name__}")
    if hasattr(node, "children"):
        for child in node.children:
            dump_node(child, indent + 1)
    if hasattr(node, "items"):
        for item in node.items:
            dump_node(item, indent + 1)


for b in blocks:
    dump_node(b)

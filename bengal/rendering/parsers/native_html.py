from html.parser import HTMLParser


class NativeHTMLParser(HTMLParser):
    """Stdlib HTML parser for validation: Mimics bs4 for decompose and get_text."""

    def __init__(self):
        super().__init__()
        self.document: list[str] = []  # Build simple text tree
        self.in_code_block = False

    def feed(self, data: str) -> None:
        # Track state for code blocks
        for tag in self.parse_tags(data):
            if tag.lower() in ("code", "pre"):
                self.in_code_block = not self.in_code_block  # Toggle
            if not self.in_code_block:
                self.document.append(tag)  # Simplified: append tags outside code

        # Get text without code blocks
        self.document = [part for part in self.document if not self.in_code_block]

    def parse_tags(self, html: str):
        # Simple tag parser (for validation, not full DOM)
        import re

        return re.findall(r"<(\w+)(?:\s[^>]*)?>", html)

    def get_text(self) -> str:
        return "".join(self.document)

    def decompose_code_blocks(self) -> None:
        # Reset to exclude code (called before get_text)
        self.document = [part for part in self.document if not self.in_code_block]

    def find_all_tags(self) -> int:
        """Simple count for len(soup.find_all())."""
        return len(self.document)

"""Site management module."""


class Site:
    """
    Represents a site.

    Attributes:
        title: Site title
        url: Site URL

    """

    def __init__(self, title: str, url: str):
        """Initialize site."""
        self.title = title
        self.url = url

    def build(self) -> None:
        """Build the site."""

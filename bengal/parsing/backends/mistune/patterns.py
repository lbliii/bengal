"""
Compiled regex patterns for Mistune parser.

Pre-compiled patterns for performance-critical operations:
- Heading detection and anchor injection
- TOC extraction
- Code fence info parsing
- HTML tag stripping
"""

from __future__ import annotations

import re

# Pattern to extract line highlight syntax from code fence info string
# Matches: python {5} or yaml {1,3,5} or js {1-3,5,7-9}
HL_LINES_PATTERN = re.compile(r"^(\S+)\s*\{([^}]+)\}$")

# Pattern to parse code fence info with optional title and line highlights
# Matches: python, python title="file.py", python {1,3}, python title="file.py" {1,3}
# Order: language [title="..."] [{lines}]
CODE_INFO_PATTERN = re.compile(
    r"^(?P<lang>\S+)"  # Language (required, no spaces)
    r'(?:\s+title="(?P<title>[^"]*)")?'  # title="..." (optional)
    r"(?:\s*\{(?P<hl>[^}]+)\})?$"  # {1,3-5} line highlights (optional)
)

# Pattern for heading anchor injection (5-10x faster than BeautifulSoup)
HEADING_PATTERN = re.compile(r"<(h[234])([^>]*)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)

# Pattern for extracting TOC from anchored headings
TOC_HEADING_PATTERN = re.compile(
    r'<(h[234])\s+id="([^"]+)"[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL
)

# Pattern to strip HTML tags from text
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Pattern for explicit heading anchor syntax: ## Title {#custom-id}
# MyST Markdown compatible - allows letters, numbers, hyphens, underscores
EXPLICIT_ID_PATTERN = re.compile(r"\s*\{#([a-zA-Z][a-zA-Z0-9_-]*)\}\s*$")

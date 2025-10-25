"""Test tab rendering issue with code blocks."""

from bengal.rendering.parsers import MistuneParser

parser = MistuneParser()

content = """
::::{tab-set}
:::{tab-item} pyenv

```bash
# Install pyenv
brew install pyenv
pyenv install 3.14.0
```

:::

:::{tab-item} Official Installer

Download from [python.org/downloads](python.org/downloads).

:::

::::
"""

result = parser.parse(content, {})
print("=" * 80)
print("RENDERED HTML:")
print("=" * 80)
print(result)
print("=" * 80)

# Count div tags
open_divs = result.count("<div")
close_divs = result.count("</div>")
print(f"\nOpen <div> tags: {open_divs}")
print(f"Close </div> tags: {close_divs}")
print(f"Balance: {open_divs - close_divs}")


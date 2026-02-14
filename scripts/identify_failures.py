import json
import re
import traceback
from pathlib import Path

from bengal.parsing.backends.patitas import parse

spec_path = Path(
    "/Users/llane/Documents/github/python/bengal/tests/rendering/parsers/test_patitas/commonmark_spec_0_31_2.json"
)
spec = json.loads(spec_path.read_text())


def normalize_html(html_string):
    result = html_string.strip()
    # Normalize empty tag formats
    result = re.sub(r"<(br|hr|img)(\s[^>]*)?\s*/?>", r"<\1\2>", result)
    result = re.sub(r"\s*/>", ">", result)
    # Strip heading IDs added by Patitas
    result = re.sub(r'<(h[1-6])\s+id="[^"]*">', r"<\1>", result)
    # CommonMark tests often use double spaces or specific newline chars that might need normalization
    # but let's start with this.
    return result


failing_by_section = {}

for ex in spec:
    section = ex["section"]
    number = ex["example"]

    try:
        actual = parse(ex["markdown"])
        expected = normalize_html(ex["html"])
        actual_norm = normalize_html(actual)

        if expected != actual_norm:
            if section not in failing_by_section:
                failing_by_section[section] = []
            failing_by_section[section].append(
                {
                    "example": number,
                    "markdown": ex["markdown"],
                    "expected": expected,
                    "actual": actual_norm,
                }
            )
    except Exception as e:
        if section not in failing_by_section:
            failing_by_section[section] = []
        failing_by_section[section].append(
            {
                "example": number,
                "markdown": ex["markdown"],
                "expected": ex["html"],
                "actual": f"ERROR: {e!s}\n{traceback.format_exc()}",
            }
        )

for section, failures in failing_by_section.items():
    print(f"### {section} ({len(failures)} failures)")
    for f in failures[:3]:  # Show first 3 failures per section
        print(f"Example {f['example']}:")
        print(f"  Markdown: {f['markdown']!r}")
        print(f"  Expected: {f['expected']!r}")
        print(f"  Actual:   {f['actual']!r}")
    if len(failures) > 3:
        print(f"  ... and {len(failures) - 3} more")
    print()

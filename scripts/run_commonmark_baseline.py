#!/usr/bin/env python3
"""Run CommonMark baseline and write results to file."""

import json
import re
from pathlib import Path

from bengal.rendering.parsers.patitas import parse

spec = json.loads(Path("tests/rendering/parsers/patitas/commonmark_spec_0_31_2.json").read_text())


def normalize_html(html_string):
    result = html_string.strip()
    result = re.sub(r"<(br|hr|img)(\s[^>]*)?\s*/?>", r"<\1\2>", result)
    result = re.sub(r"\s*/>", ">", result)
    return result


by_section = {}
for ex in spec:
    section = ex["section"]
    if section not in by_section:
        by_section[section] = {"passed": 0, "failed": 0}
    try:
        actual = parse(ex["markdown"])
        expected = normalize_html(ex["html"])
        actual_norm = normalize_html(actual)
        if expected == actual_norm:
            by_section[section]["passed"] += 1
        else:
            by_section[section]["failed"] += 1
    except:
        by_section[section]["failed"] += 1

total_passed = sum(c["passed"] for c in by_section.values())
with open("commonmark_baseline.txt", "w") as f:
    f.write(f"BASELINE: {total_passed}/652 ({total_passed / 652 * 100:.1f}%)\n\n")
    for section, counts in sorted(by_section.items()):
        total = counts["passed"] + counts["failed"]
        rate = counts["passed"] / total * 100 if total else 0
        f.write(f"{section}: {counts['passed']}/{total} ({rate:.0f}%)\n")
print(f"Done: {total_passed}/652")

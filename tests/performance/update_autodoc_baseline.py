"""Regenerate tests/performance fixture baseline for autodoc regression tests."""

from __future__ import annotations

import json

from tests.performance.autodoc_regression_fixtures import (
    baseline_path,
    build_autodoc_like_html,
    build_real_members_template_html,
    collect_output_metrics,
)


def main() -> None:
    fixture = {
        "member_count": 120,
        "include_assets": True,
        "include_empty_member_names": False,
    }
    html = build_autodoc_like_html(**fixture)
    metrics = collect_output_metrics(html)
    payload = {
        "fixture_version": 1,
        "fixture": fixture,
        "metrics": metrics.to_dict(),
        "budgets": {
            "max_total_bytes": int(metrics.total_bytes * 1.25),
            "max_empty_member_name_count": 2,
            "max_bytes_growth_ratio": 1.25,
        },
        "fixture_matrix": {},
    }
    for profile in ("public_heavy", "internal_heavy", "long_signatures"):
        rendered = build_real_members_template_html(profile)
        rendered_metrics = collect_output_metrics(rendered)
        payload["fixture_matrix"][profile] = {
            "metrics": rendered_metrics.to_dict(),
            "budgets": {
                "max_total_bytes": int(rendered_metrics.total_bytes * 1.25),
                "max_empty_member_name_count": 2,
            },
        }

    path = baseline_path()
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Updated autodoc render baseline: {path}")


if __name__ == "__main__":
    main()

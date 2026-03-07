"""Shared fixtures and metrics for autodoc render regression tests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from kida import Environment
from kida.environment import FileSystemLoader


@dataclass(frozen=True, slots=True)
class RenderOutputMetrics:
    """Normalized metrics used by render-output regression tests."""

    total_bytes: int
    details_count: int
    empty_member_name_count: int
    asset_ref_count: int
    shape_hash: str

    def to_dict(self) -> dict[str, int | str]:
        """Serialize metrics for readable assertions/debugging."""
        return {
            "total_bytes": self.total_bytes,
            "details_count": self.details_count,
            "empty_member_name_count": self.empty_member_name_count,
            "asset_ref_count": self.asset_ref_count,
            "shape_hash": self.shape_hash,
        }


def baseline_path() -> Path:
    """Return the baseline file for autodoc regression metrics."""
    return Path(__file__).parent / "fixtures" / "autodoc_render_baseline.json"


def load_baseline() -> dict[str, object]:
    """Load and parse the checked-in baseline JSON."""
    return json.loads(baseline_path().read_text())


def build_autodoc_like_html(
    *,
    member_count: int,
    include_assets: bool,
    include_empty_member_names: bool,
) -> str:
    """
    Build deterministic autodoc-like HTML used by regression tests.

    The structure intentionally mirrors the critical tags from autodoc member cards:
    - `<details class="autodoc-member">`
    - `<code class="autodoc-member-name">...</code>`
    """
    parts: list[str] = [
        "<!doctype html><html><head>",
        '<link rel="stylesheet" href="/assets/css/site.css">',
        '<script src="/assets/js/site.js"></script>',
        "</head><body>",
    ]
    for index in range(member_count):
        member_name = "" if include_empty_member_names and index % 3 == 0 else f"member_{index}"
        parts.append(
            f'<details class="autodoc-member" data-member="method">'
            f'<summary class="autodoc-member-header">'
            f'<code class="autodoc-member-name">{member_name}</code>'
            f"</summary>"
            f'<div class="autodoc-member-body"><p>Member {index} docs.</p></div>'
            f"</details>"
        )
        if include_assets and index % 20 == 0:
            parts.append(f'<img src="/assets/images/pic-{index}.png" />')
            parts.append(f'<link rel="preload" href="/assets/fonts/font-{index}.woff2" as="font">')
    parts.append("</body></html>")
    return "".join(parts)


def collect_output_metrics(rendered_html: str) -> RenderOutputMetrics:
    """Collect shape/size counters from rendered HTML."""
    # Normalize with newline separators to make hashes stable/readable across runs.
    normalized = rendered_html.replace("><", ">\n<")
    return RenderOutputMetrics(
        total_bytes=len(normalized.encode("utf-8")),
        details_count=normalized.count('<details class="autodoc-member"'),
        empty_member_name_count=normalized.count('<code class="autodoc-member-name"></code>'),
        asset_ref_count=normalized.count("/assets/"),
        shape_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class _MemberViewStub:
    """Minimal member-like object matching members.html template expectations."""

    name: str
    signature: str
    description: str
    return_type: str
    return_description: str
    params: tuple[object, ...]
    is_async: bool
    is_property: bool
    is_classmethod: bool
    is_staticmethod: bool
    is_abstract: bool
    is_deprecated: bool
    is_private: bool
    href: str
    decorators: tuple[str, ...]


def build_real_members_template_html(profile: str) -> str:
    """
    Render real autodoc members template through Kida.

    Profiles:
    - public_heavy
    - internal_heavy
    - long_signatures
    """
    repo_root = Path(__file__).resolve().parents[2]
    template_root = repo_root / "bengal" / "themes" / "default" / "templates"

    env = Environment(loader=FileSystemLoader(str(template_root)))
    env.add_filter("member_view", lambda value: value)
    env.add_filter("markdownify", lambda value: value)

    def make_member(
        index: int, *, private: bool = False, long_sig: bool = False
    ) -> _MemberViewStub:
        prefix = "_" if private else ""
        signature = (
            f"{prefix}method_{index}("
            "alpha: int, beta: str | None = None, gamma: list[str] | None = None)"
        )
        if long_sig:
            signature += " -> dict[str, tuple[int, str, float]]"
        description = (
            "Detailed member description with contextual notes and examples for rendering."
            if long_sig
            else ""
        )
        return _MemberViewStub(
            name=f"{prefix}method_{index}",
            signature=signature,
            description=description,
            return_type="None",
            return_description="",
            params=(),
            is_async=False,
            is_property=False,
            is_classmethod=False,
            is_staticmethod=False,
            is_abstract=False,
            is_deprecated=False,
            is_private=private,
            href=f"#method_{index}",
            decorators=(),
        )

    if profile == "public_heavy":
        members = [make_member(i, private=False) for i in range(40)]
    elif profile == "internal_heavy":
        members = [make_member(i, private=i % 5 != 0) for i in range(45)]
    elif profile == "long_signatures":
        members = [make_member(i, private=False, long_sig=True) for i in range(30)]
    else:
        raise ValueError(f"Unknown profile: {profile}")

    template = env.get_template("autodoc/partials/members.html")
    return template.render(
        members=members,
        title="Members",
        member_type="method",
        first_open=True,
    )

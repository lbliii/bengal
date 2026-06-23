#!/usr/bin/env python3
"""Phase 3 docs IA migration — physical restructure with aliases (issues #619–#625)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DOCS = _REPO / "site" / "content" / "docs"

# (source relative to _DOCS, dest relative to _DOCS)
DIR_MOVES: list[tuple[str, str]] = [
    ("content/authoring", "build-sites/write/authoring"),
    ("content/reuse", "build-sites/write/reuse"),
    ("content/organization", "build-sites/structure/organization"),
    ("content/collections", "build-sites/structure/collections"),
    ("content/i18n", "build-sites/structure/i18n"),
    ("content/versioning", "build-sites/structure/versioning"),
    ("content/analysis", "build-sites/structure/analysis"),
    ("content/sources", "build-sites/extend/sources"),
    ("theming/assets", "build-sites/customize/assets"),
    ("theming/recipes", "build-sites/customize/recipes"),
    ("theming/templating", "build-sites/customize/templating"),
    ("theming/themes", "build-sites/customize/themes"),
    ("building/configuration", "ship/configuration"),
    ("building/deployment", "ship/deployment"),
    ("building/performance", "ship/performance"),
    ("building/troubleshooting", "ship/troubleshooting"),
    ("content/validation", "ship/validate"),
    ("tutorials/sites", "examples/sites"),
]

FILE_MOVES: list[tuple[str, str]] = [
    ("content/multilingual.md", "build-sites/structure/i18n/multilingual.md"),
    ("theming/_index.md", "build-sites/customize/_index.md"),
    ("theming/capabilities-vs-theme.md", "build-sites/customize/capabilities-vs-theme.md"),
    ("theming/theme-creation.md", "build-sites/customize/theme-creation.md"),
    ("building/_index.md", "ship/_index.md"),
    ("building/ai-native-output.md", "ship/ai-native-output.md"),
    ("building/connect-to-ide.md", "ship/connect-to-ide.md"),
    ("building/dx-hints.md", "ship/dx-hints.md"),
    ("building/output-formats.md", "ship/output-formats.md"),
    ("building/seo.md", "ship/seo.md"),
    ("extending/_index.md", "build-sites/extend/_index.md"),
    ("extending/build-hooks.md", "build-sites/extend/build-hooks.md"),
    ("extending/collections.md", "build-sites/extend/collections.md"),
    ("extending/custom-directives.md", "build-sites/extend/custom-directives.md"),
    ("extending/custom-skeletons.md", "build-sites/extend/custom-skeletons.md"),
    ("extending/custom-sources.md", "build-sites/extend/custom-sources.md"),
    ("extending/plugins.md", "build-sites/extend/plugins.md"),
    ("extending/shortcodes.md", "build-sites/extend/shortcodes.md"),
    ("extending/theme-customization.md", "build-sites/extend/theme-customization.md"),
]

# Longest-first URL path rewrites (old prefix -> new prefix, no trailing slash)
URL_REWRITES: list[tuple[str, str]] = [
    ("docs/content/validation", "docs/ship/validate"),
    ("docs/content/authoring", "docs/build-sites/write/authoring"),
    ("docs/content/reuse", "docs/build-sites/write/reuse"),
    ("docs/content/organization", "docs/build-sites/structure/organization"),
    ("docs/content/collections", "docs/build-sites/structure/collections"),
    ("docs/content/i18n", "docs/build-sites/structure/i18n"),
    ("docs/content/versioning", "docs/build-sites/structure/versioning"),
    ("docs/content/analysis", "docs/build-sites/structure/analysis"),
    ("docs/content/sources", "docs/build-sites/extend/sources"),
    ("docs/content/multilingual", "docs/build-sites/structure/i18n/multilingual"),
    ("docs/content", "docs/build-sites"),
    ("docs/theming", "docs/build-sites/customize"),
    ("docs/extending", "docs/build-sites/extend"),
    ("docs/building", "docs/ship"),
    ("docs/tutorials/sites", "docs/examples/sites"),
]

SECTION_STUBS: dict[str, tuple[str, str, list[str]]] = {
    "content/_index.md": (
        "Content (Moved)",
        "build-sites",
        ["/docs/content/"],
    ),
    "theming/_index.md": (
        "Theming (Moved)",
        "build-sites/customize",
        ["/docs/theming/"],
    ),
    "extending/_index.md": (
        "Extending (Moved)",
        "build-sites/extend",
        ["/docs/extending/"],
    ),
    "building/_index.md": (
        "Building (Moved)",
        "ship",
        ["/docs/building/"],
    ),
}


def _doc_url(rel: str) -> str:
    """Map a docs-relative path to a public URL prefix."""
    rel = rel.removesuffix(".md")
    if rel.endswith("/_index"):
        rel = rel[: -len("/_index")]
    return f"/docs/{rel}/" if rel else "/docs/"


def _git_mv(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit(f"Destination already exists: {dest}")
    subprocess.run(["git", "mv", str(src), str(dest)], cwd=_REPO, check=True)


def _move_paths() -> dict[str, str]:
    """Execute moves; return old_rel -> new_rel mapping for every .md file."""
    mapping: dict[str, str] = {}

    for src_rel, dest_rel in DIR_MOVES:
        src = _DOCS / src_rel
        dest = _DOCS / dest_rel
        if not src.exists():
            if dest.exists():
                for path in sorted(dest.rglob("*.md")):
                    rel_under = path.relative_to(dest).as_posix()
                    mapping[f"{src_rel}/{rel_under}"] = f"{dest_rel}/{rel_under}"
            else:
                print(f"skip missing dir: {src_rel}")
            continue
        _git_mv(src, dest)
        for path in sorted(dest.rglob("*.md")):
            rel_under = path.relative_to(dest).as_posix()
            old_rel = f"{src_rel}/{rel_under}"
            new_rel = f"{dest_rel}/{rel_under}"
            mapping[old_rel] = new_rel

    for src_rel, dest_rel in FILE_MOVES:
        src = _DOCS / src_rel
        dest = _DOCS / dest_rel
        if not src.exists():
            if dest.exists():
                mapping[src_rel] = dest_rel
            else:
                print(f"skip missing file: {src_rel}")
            continue
        _git_mv(src, dest)
        mapping[src_rel] = dest_rel

    return mapping


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str, str]:
    if not text.startswith("---"):
        return {}, text, ""
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text, ""
    fm_block = text[3:end].strip()
    body = text[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip()
    return fm, body, fm_block


def _inject_aliases(path: Path, aliases: list[str]) -> None:
    if not aliases:
        return
    raw = path.read_text(encoding="utf-8")
    _, _, _ = _parse_frontmatter(raw)
    existing: list[str] = []
    m = re.search(r"^aliases:\s*\n((?:\s+-\s+.+\n)+)", raw, re.MULTILINE)
    if m:
        existing = re.findall(r"^\s+-\s+(.+)$", m.group(1), re.MULTILINE)
        existing = [e.strip().strip("'\"") for e in existing]
    elif re.search(r"^aliases:\s*\[", raw, re.MULTILINE):
        m2 = re.search(r"^aliases:\s*\[(.*?)\]", raw, re.MULTILINE)
        if m2:
            existing = [a.strip().strip("'\"") for a in m2.group(1).split(",") if a.strip()]

    merged = list(dict.fromkeys(existing + aliases))
    alias_lines = "aliases:\n" + "\n".join(f"  - {a}" for a in merged)

    if m:
        new_raw = re.sub(
            r"^aliases:\s*\n(?:\s+-\s+.+\n)+", alias_lines + "\n", raw, count=1, flags=re.MULTILINE
        )
    elif re.search(r"^aliases:\s*\[", raw, re.MULTILINE):
        new_raw = re.sub(r"^aliases:\s*\[.*?\]", alias_lines, raw, count=1, flags=re.MULTILINE)
    else:
        # Insert after opening --- block, before body fields end
        end = raw.find("\n---", 3)
        insert_at = end
        new_raw = raw[:insert_at] + "\n" + alias_lines + raw[insert_at:]

    path.write_text(new_raw, encoding="utf-8")


def _add_aliases(mapping: dict[str, str]) -> None:
    for old_rel, new_rel in mapping.items():
        old_url = _doc_url(old_rel)
        _inject_aliases(_DOCS / new_rel, [old_url])


def _rewrite_text(text: str) -> str:
    for old, new in URL_REWRITES:
        text = text.replace(f"/{old}/", f"/{new}/")
        text = text.replace(f"/{old}]", f"/{new}]")
        text = text.replace(f"[[{old}", f"[[{new}")
        text = text.replace(f"[[{old}|", f"[[{new}|")
        text = text.replace(f":link: /{old}/", f":link: /{new}/")
        text = text.replace(f":link: ./{old.split('/')[-1]}/", f":link: /{new}/")
    # Relative legacy section links in hub prose
    text = text.replace("./content/", "./build-sites/")
    text = text.replace("./building/", "./ship/")
    text = text.replace("./theming/", "./build-sites/customize/")
    text = text.replace("./extending/", "./build-sites/extend/")
    text = text.replace("../content/", "../build-sites/")
    text = text.replace("../building/", "../ship/")
    text = text.replace("../theming/", "../build-sites/customize/")
    text = text.replace("../extending/", "../build-sites/extend/")
    return text


def _update_cross_refs() -> None:
    roots = [
        _DOCS,
        _REPO / "site" / "content" / "_snippets",
        _REPO / "README.md",
        _REPO / "CONTRIBUTING.md",
        _REPO / "tests" / "unit" / "docs",
    ]
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            paths = [root]
        else:
            paths = sorted(root.rglob("*.md")) + sorted(root.rglob("*.yaml"))
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            original = path.read_text(encoding="utf-8")
            updated = _rewrite_text(original)
            if updated != original:
                path.write_text(updated, encoding="utf-8")


def _write_section_stubs() -> None:
    for stub_rel, (title, target, _aliases) in SECTION_STUBS.items():
        path = _DOCS / stub_rel
        path.parent.mkdir(parents=True, exist_ok=True)
        target_url = f"/docs/{target}/"
        content = f"""---
title: {title}
description: This section moved — follow the link below
draft: false
url: {target_url}
---

# {title}

This documentation section has moved to **[{target.replace("/", " → ").title()}]({target_url})**.

See [[docs/{target}|the new hub]] for the updated navigation.
"""
        path.write_text(content, encoding="utf-8")


def _write_build_sites_hub() -> None:
    path = _DOCS / "build-sites/_index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """---
title: Build Sites
description: Write, structure, customize, and extend your Bengal site
weight: 20
icon: hammer
tags:
- persona-writer
- persona-themer
- persona-extender
aliases:
  - /docs/content/
  - /docs/theming/
  - /docs/extending/
---

# Build Sites

Everything between first draft and production deploy: authoring, site structure,
theming, and extensions.

:::{note}
**Do I need this?** **Writers** start in [[docs/build-sites/write|Write]].
**Theme developers** go to [[docs/build-sites/customize|Customize]].
**Plugin authors** see [[docs/build-sites/extend|Extend]].
Operators shipping builds should use [[docs/ship|Ship]] instead.
:::

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## By task

| I want to… | Go to… |
|------------|--------|
| Write Markdown and directives | [[docs/build-sites/write|Write]] |
| Organize pages, menus, versions | [[docs/build-sites/structure|Structure]] |
| Customize templates and CSS | [[docs/build-sites/customize|Customize]] |
| Add plugins, sources, directives | [[docs/build-sites/extend|Extend]] |
"""
    path.write_text(content, encoding="utf-8")


def _write_subsection_hubs() -> None:
    hubs = {
        "build-sites/write/_index.md": (
            "Write",
            "Author content, reuse snippets, and apply MyST directives",
            10,
            "persona-writer",
        ),
        "build-sites/structure/_index.md": (
            "Structure",
            "Organize pages, collections, i18n, versioning, and site analysis",
            15,
            "persona-writer",
        ),
        "build-sites/extend/_index.md": (
            "Extend",
            "Plugins, custom directives, remote sources, and build hooks",
            25,
            "persona-extender",
        ),
    }
    for rel, (title, desc, weight, tag) in hubs.items():
        path = _DOCS / rel
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""---
title: {title}
description: {desc}
weight: {weight}
tags:
- {tag}
---

# {title}

{desc}

:::{"{"}child-cards{"}"}
:columns: 2
:include: sections
:fields: title, description, icon
:::
""",
            encoding="utf-8",
        )


def _write_examples_hub() -> None:
    path = _DOCS / "examples/_index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = """---
title: Examples
description: Sample sites, scaffolds, and common content patterns
weight: 45
icon: lightbulb
tags:
- persona-writer
aliases:
  - /docs/tutorials/sites/
---

# Examples

Copy-paste scaffolds and walkthrough sites — blog, multi-author, skeleton YAML,
and common content patterns.

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## Scenarios

- [[docs/tutorials/user-scenarios|User Scenarios]] — blog, docs, portfolio patterns
- [[docs/tutorials/user-scenarios-specialized|Specialized Scenarios]] — i18n, landing pages, changelog
"""
    path.write_text(content, encoding="utf-8")


def _move_architecture_internals() -> None:
    src = _DOCS / "reference" / "architecture"
    dest = _REPO / "docs" / "architecture"
    if not src.exists():
        return
    # Move subdirectories and files except _index.md
    dest.mkdir(parents=True, exist_ok=True)
    for child in sorted(src.iterdir()):
        if child.name == "_index.md":
            continue
        target = dest / child.name
        if target.exists():
            raise SystemExit(f"Architecture dest exists: {target}")
        _git_mv(child, target)

    overview = """---
title: Architecture
description: High-level Bengal architecture overview for contributors
weight: 50
icon: folder
tags:
- architecture
---

# Architecture Overview

Bengal is organized as small subsystems with clear boundaries. This page orients
**contributors and extenders**; end users should stay in [[docs/build-sites|Build Sites]]
and [[docs/reference|Reference]].

## Contributor documentation

The full architecture tree (core pipeline, rendering, tooling, meta) lives in the
repository at [`docs/architecture/`](https://github.com/lbliii/bengal/tree/main/docs/architecture/)
— not duplicated on the public docs site.

## Subsystems at a glance

| Subsystem | Package | Docs |
|-----------|---------|------|
| CLI & config | `bengal/cli/`, `bengal/config/` | [Tooling](https://github.com/lbliii/bengal/tree/main/docs/architecture/tooling/) |
| Discovery & content | `bengal/content/` | [Core](https://github.com/lbliii/bengal/tree/main/docs/architecture/core/) |
| Build orchestration | `bengal/orchestration/` | [Pipeline](https://github.com/lbliii/bengal/tree/main/docs/architecture/core/pipeline/) |
| Rendering & themes | `bengal/rendering/` | [Rendering](https://github.com/lbliii/bengal/tree/main/docs/architecture/rendering/) |
| Dev server | `bengal/server/` | [Server](https://github.com/lbliii/bengal/tree/main/docs/architecture/tooling/server/) |

## Lookup references (on-site)

- [[docs/reference/directives|Directives]]
- [[docs/reference/kida-syntax|Kida Syntax]]
- [[docs/reference/architecture/tooling/cli|CLI Reference]]
"""
    (_DOCS / "reference" / "architecture" / "_index.md").write_text(overview, encoding="utf-8")


def _update_docs_landing() -> None:
    path = _DOCS / "_index.md"
    text = path.read_text(encoding="utf-8")
    replacements = [
        (
            """:::{card} Content & Theming
:icon: edit
:link: ./content/
:description: Author, organize, theme, and extend your site
Markdown, directives, templates, plugins, and custom sources.
:::{/card}

:::{card} Building & Shipping
:icon: rocket
:link: ./building/
:description: Configure, validate, optimize, and deploy
Config, SEO, performance, health checks, and CI/CD deployment.
:::{/card}""",
            """:::{card} Build Sites
:icon: hammer
:link: ./build-sites/
:description: Write, structure, customize, and extend
Authoring, organization, theming, plugins, and custom sources.
:::{/card}

:::{card} Ship
:icon: rocket
:link: ./ship/
:description: Configure, validate, optimize, and deploy
Config, SEO, performance, health checks, and CI/CD deployment.
:::{/card}

:::{card} Examples
:icon: lightbulb
:link: ./examples/
:description: Sample sites and content patterns
Blog scaffolds, skeleton YAML, and scenario walkthroughs.
:::{/card}""",
        ),
        (
            "**Writing content?** Go to **Content**. **Deploying or tuning\nbuilds?** See **Building**.",
            "**Writing content?** Go to **Build Sites**. **Deploying or tuning\nbuilds?** See **Ship**.",
        ),
        (
            "Start with [[docs/get-started/quickstart-writer|Writer Quickstart]], then\n[[docs/content/authoring|Authoring]] and [[docs/content/organization|Organization]].",
            "Start with [[docs/get-started/quickstart-writer|Writer Quickstart]], then\n[[docs/build-sites/write|Write]] and [[docs/build-sites/structure|Structure]].",
        ),
        (
            "Start with [[docs/get-started/quickstart-themer|Themer Quickstart]], then\n[[docs/theming|Theming]] and [[docs/reference/kida-syntax|Kida Syntax]].",
            "Start with [[docs/get-started/quickstart-themer|Themer Quickstart]], then\n[[docs/build-sites/customize|Customize]] and [[docs/reference/kida-syntax|Kida Syntax]].",
        ),
        (
            "Start with [[docs/building/configuration|Configuration]], then\n[[docs/content/validation|Validation]] and [[docs/building/deployment|Deployment]].",
            "Start with [[docs/ship/configuration|Configuration]], then\n[[docs/ship/validate|Validation]] and [[docs/ship/deployment|Deployment]].",
        ),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    print("Phase 3: moving directories and files…")
    mapping = _move_paths()
    print(f"  moved {len(mapping)} markdown paths")

    print("Adding aliases…")
    _add_aliases(mapping)

    print("Writing hubs and stubs…")
    _write_build_sites_hub()
    _write_subsection_hubs()
    _write_examples_hub()
    _write_section_stubs()

    print("Relocating architecture internals…")
    _move_architecture_internals()

    print("Updating cross-references…")
    _update_cross_refs()
    _update_docs_landing()

    # Fix drift test hub list
    drift_test = _REPO / "tests" / "unit" / "docs" / "test_doc_reality_drift.py"
    if drift_test.exists():
        t = drift_test.read_text(encoding="utf-8")
        t = t.replace('_DOCS / "content" / "_index.md",', '_DOCS / "build-sites" / "_index.md",')
        t = t.replace(
            '_DOCS / "theming" / "_index.md",', '_DOCS / "build-sites" / "customize" / "_index.md",'
        )
        t = t.replace(
            '_DOCS / "extending" / "_index.md",', '_DOCS / "build-sites" / "extend" / "_index.md",'
        )
        t = t.replace('_DOCS / "building" / "_index.md",', '_DOCS / "ship" / "_index.md",')
        t = t.replace(
            '_DOCS / "content" / "authoring" / "external-references.md",',
            '_DOCS / "build-sites" / "write" / "authoring" / "external-references.md",',
        )
        t = t.replace(
            '_DOCS / "reference" / "architecture" / "tooling" / "cli.md"',
            '_REPO / "docs" / "architecture" / "tooling" / "cli.md"',
        )
        drift_test.write_text(t, encoding="utf-8")

    print("Done. Run tests and `bengal build --source site --all-versions` to verify.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

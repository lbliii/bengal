"""First-party capability registrations shipped with Bengal."""

from __future__ import annotations

from bengal.capabilities.spec import (
    CapabilityAsset,
    CapabilityInitContract,
    CapabilitySpec,
    FenceRenderSpec,
    RuntimeFetchAsset,
)

MERMAID_CAPABILITY = CapabilitySpec(
    name="mermaid",
    default_pin="10",
    assets=(
        CapabilityAsset(
            rel_path="mermaid.min.js",
            url_template="https://cdn.jsdelivr.net/npm/mermaid@{pin}/dist/mermaid.min.js",
        ),
    ),
    html_patterns=(r"""class=["']mermaid["']""",),
    source_patterns=(r"```mermaid|:::\{mermaid\}",),
    metadata_keys=("mermaid",),
    fence_languages=("mermaid",),
    fence_render=FenceRenderSpec(element="div", css_class="mermaid", escape_content=True),
    implies=("iconify",),
    init=CapabilityInitContract(
        load_position="body",
        defer=True,
        lazy_loader_key="mermaid",
        lazy_selector=".mermaid",
        companion_scripts=("js/mermaid-toolbar.js", "js/mermaid-theme.js"),
    ),
)

KATEX_CAPABILITY = CapabilitySpec(
    name="katex",
    default_pin="0.16.11",
    assets=(
        CapabilityAsset(
            rel_path="katex.min.js",
            url_template="https://cdn.jsdelivr.net/npm/katex@{pin}/dist/katex.min.js",
        ),
        CapabilityAsset(
            rel_path="katex.min.css",
            url_template="https://cdn.jsdelivr.net/npm/katex@{pin}/dist/katex.min.css",
        ),
    ),
    html_patterns=(r"""class=["'](?:math(?:-block)?)["']""",),
    source_patterns=(
        r"(?:\$\$[\s\S]+?\$\$|(?<!\$)\$(?!\$)[^\n$]+\$(?!\$)|"
        r"\{math\}`|:::\{math\}|\\begin\{)",
    ),
    metadata_keys=("math", "katex"),
    init=CapabilityInitContract(
        load_position="body",
        defer=True,
        css_files=("katex.min.css",),
        companion_scripts=("js/enhancements/math.js",),
    ),
)

ICONIFY_CAPABILITY = CapabilitySpec(
    name="iconify",
    default_pin="1",
    assets=(
        CapabilityAsset(
            rel_path="iconify/fa.json",
            url_template="https://unpkg.com/@iconify-json/fa@{pin}/icons.json",
        ),
        CapabilityAsset(
            rel_path="iconify/mdi.json",
            url_template="https://unpkg.com/@iconify-json/mdi@{pin}/icons.json",
        ),
        CapabilityAsset(
            rel_path="iconify/logos.json",
            url_template="https://unpkg.com/@iconify-json/logos@{pin}/icons.json",
        ),
    ),
    depends_on=("mermaid",),
    init=CapabilityInitContract(
        load_position="body",
        defer=True,
        runtime_fetch_assets=(
            RuntimeFetchAsset("fa", "iconify/fa.json"),
            RuntimeFetchAsset("mdi", "iconify/mdi.json"),
            RuntimeFetchAsset("logos", "iconify/logos.json"),
        ),
        runtime_global="BENGAL_MERMAID_ICON_PACKS",
    ),
)

BUILTIN_CAPABILITIES: tuple[CapabilitySpec, ...] = (
    MERMAID_CAPABILITY,
    KATEX_CAPABILITY,
    ICONIFY_CAPABILITY,
)

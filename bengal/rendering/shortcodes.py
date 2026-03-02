"""Template-based shortcode preprocessor for content.

Shortcodes allow content authors to embed template-rendered snippets
without writing Python. Place templates in templates/shortcodes/ and
call them from content using Hugo-compatible syntax:

    {{< audio src=/audio/test.mp3 >}}
    {{< blockquote author="Jane" >}}Quote text{{< /blockquote >}}

Shortcodes run before Markdown parsing. Each call is replaced with
the rendered output of templates/shortcodes/{name}.html.

Thread Safety:
    Stateless. Safe for concurrent use across render threads.

"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalRenderingError, ErrorCode
from bengal.utils.observability.logger import get_logger
from bengal.utils.xref import resolve_link_to_url_and_page

if TYPE_CHECKING:
    from bengal.protocols import PageLike, SiteLike, TemplateEngine

logger = get_logger(__name__)

# Self-closing: {{< name args >}} or {{< name args />}}
# Paired opening: {{< name args >}} or {{% name args %}}
# Paired closing: {{< /name >}} or {{% /name %}}
# Args: [^>]* allows / in paths (e.g. src=/audio/test.mp3)
# /? = optional slash before > (for {{< name />}})
SHORTCODE_SELF_CLOSING = re.compile(
    r"\{\{<\s*([\w/.-]+)(?:\s+([^>]*))?\s*/?\s*>\s*\}\}",
    re.DOTALL,
)
SHORTCODE_OPENING = re.compile(
    r"\{\{([<%])\s*([\w/.-]+)(?:\s+([^>%]*?))?\s*[>%]\s*\}\}",
    re.DOTALL,
)
SHORTCODE_CLOSING = re.compile(
    r"\{\{([<%])\s*/\s*([\w/.-]+)\s*[>%]\s*\}\}",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class ShortcodeParams:
    """Parsed shortcode arguments (Hugo-compatible)."""

    named: dict[str, str] = field(default_factory=dict)
    positional: list[str] = field(default_factory=list)

    def get(self, key: str | int, default: str = "") -> str:
        """Get argument by name or position (Hugo .Get)."""
        if isinstance(key, int):
            if 0 <= key < len(self.positional):
                return self.positional[key]
            return default
        return self.named.get(key, default)

    def get_int(self, key: str | int, default: int = 0) -> int:
        """Get argument as int (Hugo scalar support)."""
        raw = self.get(key, "")
        if not raw:
            return default
        try:
            return int(float(raw))
        except ValueError, TypeError:
            return default

    def get_bool(self, key: str | int, default: bool = False) -> bool:
        """Get argument as bool (Hugo: true/false, 1/0)."""
        raw = self.get(key, "").lower().strip()
        if not raw:
            return default
        if raw in ("true", "1", "yes", "on"):
            return True
        if raw in ("false", "0", "no", "off"):
            return False
        return default

    @property
    def is_named_params(self) -> bool:
        """True if named args were used (Hugo .IsNamedParams)."""
        return bool(self.named)

    @property
    def params(self) -> dict[str, str] | list[str]:
        """All params as dict (named) or list (positional) (Hugo .Params)."""
        return self.named if self.named else self.positional


class ShortcodeContext:
    """Hugo-compatible shortcode context for templates."""

    def __init__(
        self,
        params: ShortcodeParams,
        inner: str,
        site: SiteLike,
        page: PageLike,
        parent: ShortcodeContext | None = None,
    ) -> None:
        self._params = params
        self._inner = inner
        self._site = site
        self._page = page
        self._parent = parent

    def Get(self, key: str | int, default: str = "") -> str:
        return self._params.get(key, default)

    def GetInt(self, key: str | int, default: int = 0) -> int:
        return self._params.get_int(key, default)

    def GetBool(self, key: str | int, default: bool = False) -> bool:
        return self._params.get_bool(key, default)

    def Ref(self, path: str) -> str:
        """Resolve path to absolute URL (Hugo ref)."""
        xref = getattr(self._site, "xref_index", None) or {}
        current = _page_dir(self._page)
        url, _ = resolve_link_to_url_and_page(xref, path, current)
        return url or path

    def RelRef(self, path: str) -> str:
        """Resolve path to relative URL from current page (Hugo relref)."""
        xref = getattr(self._site, "xref_index", None) or {}
        current = _page_dir(self._page)
        url, target_page = resolve_link_to_url_and_page(xref, path, current)
        if target_page:
            from_href = getattr(self._page, "href", "/") or "/"
            to_href = getattr(target_page, "href", "") or ""
            return _relative_url(from_href, to_href)
        return url or path

    @property
    def Inner(self) -> str:
        return self._inner

    @property
    def InnerDeindent(self) -> str:
        """Inner content with leading indentation stripped (Hugo parity)."""
        return self._inner

    @property
    def IsNamedParams(self) -> bool:
        return self._params.is_named_params

    @property
    def Params(self) -> dict[str, str] | list[str]:
        return self._params.params

    @property
    def Page(self) -> PageLike:
        return self._page

    @property
    def Site(self) -> SiteLike:
        return self._site

    @property
    def Parent(self) -> ShortcodeContext | None:
        """Parent shortcode context when nested (e.g. img inside gallery)."""
        return self._parent


def _parse_args(args_str: str) -> ShortcodeParams:
    """Parse shortcode arguments into named and positional."""
    args_str = args_str.strip()
    if not args_str:
        return ShortcodeParams()

    named: dict[str, str] = {}

    # Check for named params (key=value)
    if "=" in args_str:
        # Named params: key=value or key="value with spaces"
        pattern = re.compile(
            r'(\w[\w-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))',
            re.ASCII,
        )
        for m in pattern.finditer(args_str):
            key = m.group(1)
            value = m.group(2) or m.group(3) or m.group(4) or ""
            named[key] = value
        # If we found named params, use only those (Hugo: no mixing)
        if named:
            return ShortcodeParams(named=named)

    # Positional: space-separated, quoted strings preserved
    tokens: list[str] = []
    current = ""
    in_quote: str | None = None
    i = 0
    while i < len(args_str):
        c = args_str[i]
        if in_quote:
            if c == in_quote:
                in_quote = None
                tokens.append(current)
                current = ""
            else:
                current += c
            i += 1
            continue
        if c in ('"', "'"):
            if current:
                tokens.append(current)
                current = ""
            in_quote = c
            i += 1
            continue
        if c.isspace():
            if current:
                tokens.append(current)
                current = ""
            i += 1
            continue
        current += c
        i += 1
    if current:
        tokens.append(current)
    return ShortcodeParams(positional=tokens)


def _page_dir(page: PageLike) -> str | None:
    """Content-relative directory for current page (for Ref/RelRef)."""
    sp = getattr(page, "source_path", None)
    if sp is None:
        return None
    path_str = str(sp).replace("\\", "/")
    path_str = path_str.replace(".md", "").rstrip("/")
    for prefix in ("content/", "content\\"):
        if path_str.startswith(prefix):
            path_str = path_str[len(prefix) :]
            break
    is_index = path_str.endswith(("/_index", "\\_index"))
    if is_index:
        path_str = path_str[:-7]
        return path_str if path_str else None
    if "/" in path_str:
        return path_str.rsplit("/", 1)[0]
    return path_str or None


def _shortcodes_used_in_content(content: str) -> frozenset[str]:
    """Extract shortcode names used in content ({{< name or {{% name)."""
    names: set[str] = set()
    for pattern in (SHORTCODE_OPENING, SHORTCODE_SELF_CLOSING):
        for m in pattern.finditer(content):
            name = m.group(2).strip()
            if name and not name.startswith("/"):
                names.add(name)
    return frozenset(names)


def has_shortcode(page: PageLike, name: str) -> bool:
    """Return True if page content uses the given shortcode."""
    source = getattr(page, "_source", None) or getattr(page, "_raw_content", "")
    return name in _shortcodes_used_in_content(str(source or ""))


def _relative_url(from_url: str, to_url: str) -> str:
    """Compute relative URL from from_url to to_url (both absolute paths)."""
    from_parts = [p for p in from_url.strip("/").split("/") if p]
    to_parts = [p for p in to_url.strip("/").split("/") if p]
    # Find common prefix
    i = 0
    while i < len(from_parts) and i < len(to_parts) and from_parts[i] == to_parts[i]:
        i += 1
    # Go up from from_url
    ups = len(from_parts) - i
    result = [".."] * ups + to_parts[i:]
    out = "/".join(result) if result else "."
    return f"{out}/" if to_parts and not out.endswith("/") else out


def _deindent(text: str) -> str:
    """Strip common leading indentation (Hugo InnerDeindent)."""
    lines = text.split("\n")
    if not lines:
        return text
    # Find minimum indent (excluding empty lines)
    min_indent: int | None = None
    for line in lines:
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if min_indent is None or indent < min_indent:
            min_indent = indent
    if min_indent is None or min_indent == 0:
        return text
    return "\n".join(line[min_indent:] if len(line) >= min_indent else line for line in lines)


def _find_paired_content(
    content: str, start: int, open_delim: str, name: str
) -> tuple[str, int] | None:
    """Find inner content and end position for paired shortcode."""
    delim_char = "<" if open_delim == "<" else "%"
    close_pattern = re.compile(
        rf"\{{{{[{delim_char}]\s*/\s*{re.escape(name)}\s*[>%]\s*\}}\}}",
        re.DOTALL,
    )
    close_m = close_pattern.search(content, start)
    if not close_m:
        return None
    inner = content[start : close_m.start()]
    return inner, close_m.end()


_MAX_SHORTCODE_DEPTH = 20


def expand_shortcodes(
    content: str,
    template_engine: TemplateEngine,
    page: PageLike,
    site: SiteLike,
    *,
    parse_markdown: Callable[[str], str] | None = None,
    parent_ctx: ShortcodeContext | None = None,
    _depth: int = 0,
) -> str:
    """Expand shortcode calls in content before Markdown parsing.

    Replaces {{< name args >}} and {{% name args %}}...{{% /name %}}
    with rendered template output. Unknown shortcodes are left as-is
    (no template found).

    Notation:
        - {{< name >}} (standard): inner content passed raw to template
        - {{% name %}} (markdown): inner content parsed as Markdown first

    Args:
        content: Raw page content (Markdown with shortcodes)
        template_engine: Engine for rendering shortcode templates
        page: Current page (for template context)
        site: Site instance
        parse_markdown: Optional callback to parse Markdown to HTML.
            When provided, {{% %}} inner content is parsed before rendering.
            When None, both notations pass inner content raw.

    Returns:
        Content with shortcodes expanded to HTML
    """
    if "{{<" not in content and "{{%" not in content:
        return content
    sc_cfg = site.config.get("shortcodes") or {}
    strict = bool(sc_cfg.get("strict", False))
    if _depth >= _MAX_SHORTCODE_DEPTH:
        logger.warning(
            "shortcode_max_depth_exceeded",
            depth=_depth,
            source=str(getattr(page, "source_path", "?")),
        )
        return content

    result_parts: list[str] = []
    pos = 0

    while True:
        # Find next shortcode (self-closing or opening)
        self_m = SHORTCODE_SELF_CLOSING.search(content, pos)
        open_m = SHORTCODE_OPENING.search(content, pos)

        # Prefer paired over self-closing when both match (e.g. {{< blockquote >}}...{{< /blockquote >}})
        start, kind, name, args_str, delim = -1, "", "", "", None
        if open_m:
            open_end = open_m.end()
            inner_result = _find_paired_content(content, open_end, open_m.group(1), open_m.group(2))
            if inner_result is not None:
                kind, start, name, args_str, delim = (
                    "paired",
                    open_m.start(),
                    open_m.group(2),
                    open_m.group(3) or "",
                    open_m.group(1),
                )
        if kind != "paired" and self_m and (start < 0 or self_m.start() <= start):
            kind, start, name, args_str, delim = (
                "self",
                self_m.start(),
                self_m.group(1),
                self_m.group(2) or "",
                None,
            )

        if kind == "":
            result_parts.append(content[pos:])
            break

        params = _parse_args(args_str)

        # Emit content before this shortcode
        result_parts.append(content[pos:start])

        def _line_at(pos: int) -> int:
            return content[:pos].count("\n") + 1

        if kind == "self":
            # Self-closing: {{< name args >}} or {{< name args />}}
            assert self_m is not None
            end = self_m.end()
            fallback = content[start:end]
            html = _render_shortcode(
                template_engine,
                site,
                page,
                name,
                params,
                "",
                fallback,
                parent_ctx,
                strict=strict,
                source_path=getattr(page, "source_path", None),
                line_number=_line_at(start),
            )
            result_parts.append(html)
            pos = end
            continue

        # Paired: we have inner_result from above
        assert open_m is not None
        assert inner_result is not None
        open_end = open_m.end()
        inner, close_end = inner_result
        fallback = content[start:close_end]
        inner = _deindent(inner)
        # Recursive expansion: shortcodes in inner get this shortcode as parent
        outer_ctx = ShortcodeContext(params, "", site, page, parent_ctx)
        inner = expand_shortcodes(
            inner,
            template_engine,
            page,
            site,
            parse_markdown=parse_markdown,
            parent_ctx=outer_ctx,
            _depth=_depth + 1,
        )
        # {{% %}} = Markdown notation: parse inner after expansion
        if delim == "%" and parse_markdown is not None:
            inner = parse_markdown(inner)
        html = _render_shortcode(
            template_engine,
            site,
            page,
            name,
            params,
            inner,
            fallback,
            parent_ctx,
            strict=strict,
            source_path=getattr(page, "source_path", None),
            line_number=_line_at(start),
        )
        result_parts.append(html)
        pos = close_end

    return "".join(result_parts)


def _render_shortcode(
    template_engine: TemplateEngine,
    site: SiteLike,
    page: PageLike,
    name: str,
    params: ShortcodeParams,
    inner: str,
    fallback: str,
    parent_ctx: ShortcodeContext | None = None,
    *,
    strict: bool = False,
    source_path: object = None,
    line_number: int | None = None,
) -> str:
    """Render a shortcode template or return fallback when not found."""
    template_name = f"shortcodes/{name}.html"
    path_str = str(source_path or getattr(page, "source_path", "?"))
    if not template_engine.template_exists(template_name):
        if strict:
            loc = f" at {path_str}:{line_number}" if line_number else f" at {path_str}"
            raise BengalRenderingError(
                f"Unknown shortcode '{name}'{loc}",
                code=ErrorCode.T001,
                file_path=source_path,
                line_number=line_number,
                suggestion="Add templates/shortcodes/{name}.html or disable shortcodes.strict",
            )
        logger.debug(
            "shortcode_template_not_found",
            name=name,
            template=template_name,
            source=path_str,
        )
        return fallback

    shortcode_ctx = ShortcodeContext(params, inner, site, page, parent_ctx)
    context: dict[str, Any] = {
        "page": page,
        "site": site,
        "config": site.config,
        "shortcode": shortcode_ctx,
        "Get": shortcode_ctx.Get,
        "Inner": inner,
        "IsNamedParams": params.is_named_params,
        "Params": params.params,
    }

    try:
        return template_engine.render_template(template_name, context)
    except Exception as e:
        if strict:
            loc = f" at {path_str}:{line_number}" if line_number else f" at {path_str}"
            raise BengalRenderingError(
                f"Shortcode '{name}' render failed{loc}: {e}",
                code=ErrorCode.T003,
                file_path=source_path,
                line_number=line_number,
            ) from e
        logger.warning(
            "shortcode_render_failed",
            name=name,
            template=template_name,
            error=str(e),
            source=path_str,
        )
        return fallback

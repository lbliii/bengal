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
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalRenderingError, ErrorCode
from bengal.utils.observability.logger import get_logger
from bengal.utils.xref import resolve_link_to_url_and_page

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.protocols import PageLike, SiteLike, TemplateEngine

logger = get_logger(__name__)

_SHORTCODE_NAME = re.compile(r"([\w/.-]+)(?:\s+(.*))?\Z", re.DOTALL)


@dataclass(frozen=True, slots=True)
class _ShortcodeToken:
    """A shortcode delimiter found by the single-pass scanner."""

    start: int
    end: int
    delim: str
    name: str
    args: str
    closing: bool = False
    self_closing: bool = False


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
        xref = self._site.xref_index or {}
        current = _page_dir(self._page)
        url, _ = resolve_link_to_url_and_page(xref, path, current)
        return url or path

    def RelRef(self, path: str) -> str:
        """Resolve path to relative URL from current page (Hugo relref)."""
        xref = self._site.xref_index or {}
        current = _page_dir(self._page)
        url, target_page = resolve_link_to_url_and_page(xref, path, current)
        if target_page:
            from_href = self._page.href or "/"
            to_href = target_page.href or ""
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
    sp = page.source_path
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
    return frozenset(token.name for token in _scan_shortcode_tokens(content) if not token.closing)


def has_shortcode(page: PageLike, name: str) -> bool:
    """Return True if page content uses the given shortcode."""
    # Page uses _source or _raw_content; protocol has no raw_content
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


def _parse_shortcode_token(content: str, start: int, delim: str) -> _ShortcodeToken | None:
    """Parse a shortcode token that starts at ``start``."""
    close = ">}}" if delim == "<" else "%}}"
    body_start = start + 3
    body_end = content.find(close, body_start)
    if body_end < 0:
        return None

    raw_body = content[body_start:body_end].strip()
    end = body_end + len(close)
    if not raw_body:
        return None

    closing = raw_body.startswith("/")
    if closing:
        raw_body = raw_body[1:].strip()

    self_closing = False
    if not closing and delim == "<" and raw_body.endswith("/"):
        self_closing = True
        raw_body = raw_body[:-1].rstrip()

    match = _SHORTCODE_NAME.match(raw_body)
    if not match:
        return None

    return _ShortcodeToken(
        start=start,
        end=end,
        delim=delim,
        name=match.group(1),
        args=match.group(2) or "",
        closing=closing,
        self_closing=self_closing,
    )


def _scan_shortcode_tokens(content: str) -> list[_ShortcodeToken]:
    """Scan shortcode delimiters in one pass."""
    tokens: list[_ShortcodeToken] = []
    pos = 0
    length = len(content)
    while pos < length:
        start = content.find("{{", pos)
        if start < 0:
            break
        if start + 2 >= length or content[start + 2] not in ("<", "%"):
            pos = start + 2
            continue
        delim = content[start + 2]
        token = _parse_shortcode_token(content, start, delim)
        if token is None:
            pos = start + 2
            continue
        tokens.append(token)
        pos = token.end
    return tokens


def _match_shortcode_pairs(tokens: list[_ShortcodeToken]) -> dict[int, int]:
    """Match opening and closing shortcode token indexes using a stack."""
    stack: list[int] = []
    pairs: dict[int, int] = {}
    for idx, token in enumerate(tokens):
        if token.self_closing:
            continue
        if token.closing:
            for stack_pos in range(len(stack) - 1, -1, -1):
                opener = tokens[stack[stack_pos]]
                if opener.name == token.name and opener.delim == token.delim:
                    pairs[stack[stack_pos]] = idx
                    del stack[stack_pos:]
                    break
            continue
        stack.append(idx)
    return pairs


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
            source=str(page.source_path),
        )
        return content

    tokens = _scan_shortcode_tokens(content)
    if not tokens:
        return content
    pairs = _match_shortcode_pairs(tokens)
    result_parts: list[str] = []
    pos = 0

    def _line_at(offset: int) -> int:
        return content[:offset].count("\n") + 1

    for idx, token in enumerate(tokens):
        if token.start < pos or token.closing:
            continue

        pair_idx = pairs.get(idx)
        is_paired = pair_idx is not None
        is_self = token.self_closing or (token.delim == "<" and not is_paired)

        if not is_paired and not is_self:
            continue

        params = _parse_args(token.args)
        result_parts.append(content[pos : token.start])

        if is_self:
            fallback = content[token.start : token.end]
            html = _render_shortcode(
                template_engine,
                site,
                page,
                token.name,
                params,
                "",
                fallback,
                parent_ctx,
                strict=strict,
                source_path=page.source_path,
                line_number=_line_at(token.start),
            )
            result_parts.append(html)
            pos = token.end
            continue

        close_token = tokens[pair_idx]
        inner = _deindent(content[token.end : close_token.start])
        fallback = content[token.start : close_token.end]
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
        if token.delim == "%" and parse_markdown is not None:
            inner = parse_markdown(inner)
        html = _render_shortcode(
            template_engine,
            site,
            page,
            token.name,
            params,
            inner,
            fallback,
            parent_ctx,
            strict=strict,
            source_path=page.source_path,
            line_number=_line_at(token.start),
        )
        result_parts.append(html)
        pos = close_token.end

    result_parts.append(content[pos:])

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
    path_str = str(source_path or page.source_path)
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

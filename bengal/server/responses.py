"""
Response builders for Bengal dev server.

Pure functions and data for building HTTP responses—no transport coupling.
Shared by the HTTP handler and future ASGI app.
"""

from __future__ import annotations

# HTML template for "rebuilding" page shown during builds
# Uses CSS animation and auto-retry via meta refresh + live reload script
# Features Bengal branding with rosette logo and cat theme
# Placeholders: %PATH%, %ACCENT%, %ACCENT_RGB%, %BG_PRIMARY%, %BG_SECONDARY%, %BG_TERTIARY%
REBUILDING_PAGE_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="2">
    <title>Rebuilding... | Bengal</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(145deg, %BG_PRIMARY% 0%, %BG_SECONDARY% 50%, %BG_TERTIARY% 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e8e4de;
            overflow: hidden;
            position: relative;
        }
        /* Subtle pattern overlay */
        body::before {
            content: '';
            position: absolute;
            inset: 0;
            background-image: radial-gradient(circle at 20% 30%, rgba(%ACCENT_RGB%, 0.03) 0%, transparent 50%),
                              radial-gradient(circle at 80% 70%, rgba(%ACCENT_RGB%, 0.03) 0%, transparent 50%);
            pointer-events: none;
        }
        .container {
            text-align: center;
            padding: 2.5rem;
            position: relative;
            z-index: 1;
        }
        .logo-container {
            margin-bottom: 1.5rem;
            position: relative;
        }
        .logo {
            width: 72px;
            height: 72px;
            margin: 0 auto;
            color: %ACCENT%;
            animation: pulse 2s ease-in-out infinite;
        }
        .logo svg {
            width: 100%;
            height: 100%;
            filter: drop-shadow(0 0 12px rgba(%ACCENT_RGB%, 0.3));
        }
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.08);
                opacity: 0.85;
            }
        }
        /* Orbiting dots around logo */
        .orbit {
            position: absolute;
            width: 120px;
            height: 120px;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            animation: orbit 3s linear infinite;
        }
        .orbit::before, .orbit::after {
            content: '';
            position: absolute;
            width: 6px;
            height: 6px;
            background: %ACCENT%;
            border-radius: 50%;
        }
        .orbit::before { top: 0; left: 50%; transform: translateX(-50%); }
        .orbit::after { bottom: 0; left: 50%; transform: translateX(-50%); opacity: 0.5; }
        @keyframes orbit {
            from { transform: translate(-50%, -50%) rotate(0deg); }
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        .brand {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: %ACCENT%;
            margin-bottom: 1.5rem;
            opacity: 0.9;
        }
        h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #f5f3ef;
            letter-spacing: -0.01em;
        }
        .subtitle {
            color: #9a9488;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        .path {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: rgba(%ACCENT_RGB%, 0.08);
            border: 1px solid rgba(%ACCENT_RGB%, 0.15);
            border-radius: 0.5rem;
            font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
            font-size: 0.8rem;
            color: %ACCENT%;
        }
        .paw-prints {
            margin-top: 2rem;
            display: flex;
            justify-content: center;
            gap: 0.75rem;
        }
        .paw {
            width: 16px;
            height: 16px;
            opacity: 0;
            animation: fadeWalk 2s ease-in-out infinite;
        }
        .paw:nth-child(1) { animation-delay: 0s; }
        .paw:nth-child(2) { animation-delay: 0.4s; }
        .paw:nth-child(3) { animation-delay: 0.8s; }
        @keyframes fadeWalk {
            0%, 100% { opacity: 0; transform: translateY(0); }
            30%, 70% { opacity: 0.6; transform: translateY(-4px); }
        }
        .paw svg {
            width: 100%;
            height: 100%;
            fill: %ACCENT%;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo-container">
            <div class="orbit"></div>
            <div class="logo">
                <!-- Bengal Rosette Logo -->
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <ellipse cx="12" cy="11" rx="5" ry="1.5" fill="currentColor" opacity="0.25"/>
                    <path d="M7 10 L7 11 A5 1.5 0 0 0 17 11 L17 10" fill="currentColor" opacity="0.35"/>
                    <ellipse cx="12" cy="10" rx="5" ry="4" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="12" cy="10" rx="2" ry="1.5" fill="currentColor"/>
                    <path d="M9 8 A3 2 0 0 1 14 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.4"/>
                    <ellipse cx="6.5" cy="17.5" rx="3" ry="0.8" fill="currentColor" opacity="0.2"/>
                    <path d="M3.5 17 L3.5 17.5 A3 0.8 0 0 0 9.5 17.5 L9.5 17" fill="currentColor" opacity="0.3"/>
                    <ellipse cx="6.5" cy="17" rx="3" ry="2.5" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="6.5" cy="17" rx="1.2" ry="0.9" fill="currentColor"/>
                    <ellipse cx="17.5" cy="16.5" rx="2.8" ry="0.7" fill="currentColor" opacity="0.2"/>
                    <path d="M14.7 16 L14.7 16.5 A2.8 0.7 0 0 0 20.3 16.5 L20.3 16" fill="currentColor" opacity="0.3"/>
                    <ellipse cx="17.5" cy="16" rx="2.8" ry="2.2" stroke="currentColor" stroke-width="1.5"/>
                    <ellipse cx="17.5" cy="16" rx="1" ry="0.7" fill="currentColor"/>
                </svg>
            </div>
        </div>
        <div class="brand">Bengal</div>
        <h1>Rebuilding site...</h1>
        <p class="subtitle">This page will refresh automatically when ready.</p>
        <div class="path">%PATH%</div>
        <div class="paw-prints">
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
            <div class="paw">
                <svg viewBox="0 0 24 24"><path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-4.5 2c-.83 0-1.5.67-1.5 1.5S6.67 15 7.5 15 9 14.33 9 13.5 8.33 12 7.5 12zm9 0c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM12 16c-1.1 0-2 .45-2 1s.9 1 2 1 2-.45 2-1-.9-1-2-1zm-4 2c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1zm8 0c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>
            </div>
        </div>
    </div>
    <script>
        // Connect to live reload for faster refresh
        const es = new EventSource('/__bengal_reload__');
        es.onmessage = (e) => {
            if (e.data === 'reload' || e.data.includes('"action":"reload"')) {
                window.location.reload();
            }
        };
    </script>
</body>
</html>
"""

# Palette color schemes for the rebuilding page (dark mode colors)
# Each palette maps to: (accent_hex, accent_rgb, bg_primary, bg_secondary, bg_tertiary)
PALETTE_COLORS: dict[str, tuple[str, str, str, str, str]] = {
    # Snow Lynx - Icy teal
    "snow-lynx": ("#6EC4BC", "110, 196, 188", "#18191A", "#252729", "#333538"),
    # Silver Bengal - Pure silver (monochromatic)
    "silver-bengal": ("#D1D5DB", "209, 213, 219", "#000000", "#0F0F0F", "#1A1A1A"),
    # Charcoal Bengal - Golden glitter
    "charcoal-bengal": ("#C9A84D", "201, 168, 77", "#0C0B0A", "#14130F", "#1E1C18"),
    # Brown Bengal - Warm amber
    "brown-bengal": ("#FFAD3D", "255, 173, 61", "#1F1811", "#2D2218", "#3D3020"),
    # Blue Bengal - Powder blue
    "blue-bengal": ("#9DBDD9", "157, 189, 217", "#141B22", "#1B2430", "#243140"),
}

# Default palette colors (Snow Lynx - the default palette)
DEFAULT_PALETTE = "snow-lynx"


def get_rebuilding_page_html(path: str, palette: str | None = None) -> bytes:
    """
    Generate themed HTML for the "rebuilding" placeholder page.

    Creates a visually appealing loading page shown during site rebuilds.
    The page features Bengal branding, animated elements, and automatically
    refreshes when the build completes (via meta refresh and live reload).

    Args:
        path: URL path that triggered the rebuild (shown to user for context)
        palette: Theme name from PALETTE_COLORS (e.g., 'snow-lynx', 'charcoal-bengal').
                 Falls back to DEFAULT_PALETTE if None or invalid.

    Returns:
        Complete HTML document as bytes, ready to serve.

    Example:
        >>> html = get_rebuilding_page_html("/blog/my-post", "charcoal-bengal")
        >>> b"Rebuilding" in html
        True

    """
    # Get colors for the palette (or default)
    palette_key = palette or DEFAULT_PALETTE
    if palette_key not in PALETTE_COLORS:
        palette_key = DEFAULT_PALETTE

    accent, accent_rgb, bg_primary, bg_secondary, bg_tertiary = PALETTE_COLORS[palette_key]

    # Apply all replacements
    html = REBUILDING_PAGE_HTML
    html = html.replace(b"%PATH%", path.encode("utf-8"))
    html = html.replace(b"%ACCENT%", accent.encode("utf-8"))
    html = html.replace(b"%ACCENT_RGB%", accent_rgb.encode("utf-8"))
    html = html.replace(b"%BG_PRIMARY%", bg_primary.encode("utf-8"))
    html = html.replace(b"%BG_SECONDARY%", bg_secondary.encode("utf-8"))
    html = html.replace(b"%BG_TERTIARY%", bg_tertiary.encode("utf-8"))

    return html
